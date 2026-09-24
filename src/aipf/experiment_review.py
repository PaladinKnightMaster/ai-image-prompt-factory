from __future__ import annotations

import hashlib
import json
import secrets
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .experiment_execution import OUTPUTS_DIRNAME, load_run
from .experiment_runs import sha256_file
from .experiments import load_experiment


BLIND_REVIEW_DIRNAME = "blind-review"
REVIEW_PRIVATE_DIRNAME = ".review-private"
REVIEW_MANIFEST_NAME = "manifest.json"
REVIEW_DRAFT_NAME = "review.json"
REVIEW_FROZEN_NAME = "review.frozen.json"
REVIEW_REVEAL_NAME = "reveal.json"
REVIEW_MAPPING_NAME = "mapping.json"
REVIEW_ID_LENGTH = 8
REVIEW_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        delete=False,
        dir=path.parent,
        suffix=".tmp",
    ) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temp_path = Path(handle.name)
    temp_path.replace(path)


def _canonical_sha256(payload: dict) -> str:
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _all_outputs_generated(run: dict) -> bool:
    outputs = [
        output
        for variant in run.get("variants", [])
        for output in variant.get("outputs", [])
    ]
    return bool(outputs) and all(
        output.get("status") == "generated" for output in outputs
    )


def _dimension_guidance(dimension: str) -> str:
    if dimension == "technical_defects":
        return (
            "5 = clean with no meaningful visible defects; "
            "1 = severe visible defects. Higher is better."
        )
    return "5 = strongest/best result; 1 = weakest/worst result."


def _new_review_id(used: set[str]) -> str:
    while True:
        review_id = "R" + "".join(
            secrets.choice(REVIEW_ALPHABET)
            for _ in range(REVIEW_ID_LENGTH - 1)
        )
        if review_id not in used:
            used.add(review_id)
            return review_id


def _resolve_source_image(
    run_path: Path,
    variant_id: str,
    image_name: str,
) -> Path:
    """Resolve neutral V3.3 storage, with legacy variant dirs as fallback."""
    candidates = [
        run_path.parent / OUTPUTS_DIRNAME / image_name,
        run_path.parent / variant_id / image_name,
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    raise FileNotFoundError(candidates[0])


def create_review_package(
    run_file: str | Path,
    *,
    output: str | Path | None = None,
    reviewer_id: str | None = None,
) -> dict:
    """Create a doubly blinded reviewer package.

    Generation blind IDs remain private. Reviewer-visible files receive a
    second independent review ID. The review-ID mapping is committed by hash
    before review and stored outside the reviewer-facing directory.
    """
    run_path, run = load_run(run_file)
    if run.get("experiment_id") == "EXP-019":
        if reviewer_id is None:
            raise ValueError("EXP-019 requires explicit reviewer_id R1 or R2")
        from .exp019_review import create_package
        return create_package(run_path, reviewer_id=reviewer_id, output=output)
    if reviewer_id is not None:
        raise ValueError("reviewer_id is reserved for two-review protocols")

    if run.get("status") != "completed" or not _all_outputs_generated(run):
        raise ValueError(
            "blind review requires a completed run with every output "
            "successfully generated"
        )

    experiment = load_experiment(run["experiment_id"])
    evaluation_dimensions = list(
        experiment.get("evaluation_dimensions", [])
    )
    if not evaluation_dimensions:
        raise ValueError(
            f"experiment {run['experiment_id']} has no evaluation_dimensions"
        )

    destination = (
        Path(output).expanduser().resolve()
        if output
        else run_path.parent / BLIND_REVIEW_DIRNAME
    )
    destination.mkdir(parents=True, exist_ok=False)

    private_dir = run_path.parent / REVIEW_PRIVATE_DIRNAME
    private_dir.mkdir(parents=True, exist_ok=True)
    mapping_path = private_dir / REVIEW_MAPPING_NAME
    if mapping_path.exists():
        raise FileExistsError(
            f"review mapping already exists: {mapping_path}"
        )

    used_review_ids: set[str] = set()
    items: list[dict] = []
    mapping_entries: list[dict] = []

    for variant in run["variants"]:
        for output_item in variant["outputs"]:
            generation_id = output_item["blind_id"]
            image_name = output_item.get("image")
            expected_hash = output_item.get("image_sha256")

            if not image_name or not expected_hash:
                raise ValueError(
                    f"generated output {generation_id} is missing image metadata"
                )

            source = _resolve_source_image(
                run_path,
                variant["variant_id"],
                image_name,
            )
            actual_hash = sha256_file(source)
            if actual_hash != expected_hash:
                raise ValueError(
                    f"image hash mismatch for generation output {generation_id}"
                )

            review_id = _new_review_id(used_review_ids)
            suffix = source.suffix.lower() or ".png"
            review_name = f"{review_id}{suffix}"
            review_image = destination / review_name
            shutil.copy2(source, review_image)

            copied_hash = sha256_file(review_image)
            if copied_hash != expected_hash:
                raise ValueError(
                    f"copied image hash mismatch for review_id {review_id}"
                )

            # Reviewer-facing package deliberately omits the image hash.
            # The same hash is retained only in the private mapping below so
            # integrity can still be verified after the review is frozen.
            items.append(
                {
                    "review_id": review_id,
                    "image": review_name,
                }
            )
            mapping_entries.append(
                {
                    "review_id": review_id,
                    "blind_id": generation_id,
                    "variant_id": variant["variant_id"],
                    "factor": variant.get("factor"),
                    "replicate": output_item.get("replicate"),
                    "image_sha256": copied_hash,
                }
            )

    # Review IDs are independently random. Sort by review ID only; this neither
    # restores generation order nor reveals treatment grouping.
    items.sort(key=lambda item: item["review_id"])
    mapping_entries.sort(key=lambda item: item["review_id"])

    mapping_core = {
        "run_id": run["run_id"],
        "experiment_id": run["experiment_id"],
        "entries": mapping_entries,
    }
    mapping_commitment_sha256 = _canonical_sha256(mapping_core)
    run_sha256 = sha256_file(run_path)
    created_at = _utc_now()

    manifest_payload = {
        "run_id": run["run_id"],
        "experiment_id": run["experiment_id"],
        "created_at_utc": created_at,
        "status": "open",
        "run_sha256": run_sha256,
        "mapping_commitment_sha256": mapping_commitment_sha256,
        "review_count": len(items),
        "score_scale": {
            "min": 1,
            "max": 5,
            "higher_is_better": True,
        },
        "evaluation_dimensions": evaluation_dimensions,
        "dimension_guidance": {
            dimension: _dimension_guidance(dimension)
            for dimension in evaluation_dimensions
        },
        "items": items,
    }
    review_package_sha256 = _canonical_sha256(manifest_payload)
    manifest = {
        **manifest_payload,
        "review_package_sha256": review_package_sha256,
    }

    review = {
        "run_id": run["run_id"],
        "experiment_id": run["experiment_id"],
        "review_package_sha256": review_package_sha256,
        "mapping_commitment_sha256": mapping_commitment_sha256,
        "status": "open",
        "created_at_utc": created_at,
        "frozen_at_utc": None,
        "review_sha256": None,
        "score_scale": {
            "min": 1,
            "max": 5,
            "higher_is_better": True,
        },
        "evaluation_dimensions": evaluation_dimensions,
        "items": [
            {
                "review_id": item["review_id"],
                "scores": {
                    dimension: None
                    for dimension in evaluation_dimensions
                },
                "notes": "",
            }
            for item in items
        ],
    }

    mapping = {
        **mapping_core,
        "created_at_utc": created_at,
        "mapping_commitment_sha256": mapping_commitment_sha256,
        "review_package_sha256": review_package_sha256,
    }

    _write_json_atomic(destination / REVIEW_MANIFEST_NAME, manifest)
    _write_json_atomic(destination / REVIEW_DRAFT_NAME, review)
    _write_json_atomic(mapping_path, mapping)

    readme = f"""# AIPF Blind Review Package

Run: `{run['run_id']}`  
Experiment: `{run['experiment_id']}`  
Images: `{len(items)}`

Each image has a fresh review ID that is independent from the generation blind
ID. Review only this directory. Do not inspect the private `run.json`,
`.review-private/`, prompts, or generation metadata until the review is frozen.

Score every evaluation dimension from 1 to 5. Higher is always better. For
`technical_defects`, 5 means clean/no meaningful defects and 1 means severe
visible defects.

Enter scores and optional notes in `review.json`, then freeze the review:

```text
aipf experiment-review-freeze <blind-review/review.json>
```

After freezing, reveal the committed treatment mapping with:

```text
aipf experiment-review-reveal <run.json>
```
"""
    (destination / "README.md").write_text(readme, encoding="utf-8")

    return {
        "run_id": run["run_id"],
        "review_count": len(items),
        "output": str(destination),
        "manifest": str(destination / REVIEW_MANIFEST_NAME),
        "review": str(destination / REVIEW_DRAFT_NAME),
        "review_package_sha256": review_package_sha256,
        "mapping_commitment_sha256": mapping_commitment_sha256,
    }


def _verify_review_manifest(manifest: dict) -> None:
    expected = manifest.get("review_package_sha256")
    if not expected:
        raise ValueError("review manifest is missing review_package_sha256")

    payload = dict(manifest)
    payload.pop("review_package_sha256", None)
    actual = _canonical_sha256(payload)
    if actual != expected:
        raise ValueError("review manifest package hash verification failed")


def _validate_review_against_manifest(review: dict, manifest: dict) -> None:
    """Reject reviewer edits to protocol-locked package structure."""
    _verify_review_manifest(manifest)

    locked_fields = (
        "run_id",
        "experiment_id",
        "review_package_sha256",
        "mapping_commitment_sha256",
        "created_at_utc",
        "score_scale",
        "evaluation_dimensions",
    )
    for field in locked_fields:
        if review.get(field) != manifest.get(field):
            raise ValueError(
                f"review {field} does not match reviewer manifest"
            )

    if review.get("frozen_at_utc") is not None:
        raise ValueError("open review must not set frozen_at_utc")
    if review.get("review_sha256") is not None:
        raise ValueError("open review must not set review_sha256")

    manifest_ids = [item.get("review_id") for item in manifest.get("items", [])]
    review_ids = [item.get("review_id") for item in review.get("items", [])]

    if (
        not manifest_ids
        or len(manifest_ids) != len(set(manifest_ids))
    ):
        raise ValueError("review manifest has invalid or duplicate review IDs")

    if len(review_ids) != len(manifest_ids) or set(review_ids) != set(manifest_ids):
        raise ValueError(
            "review items do not exactly match reviewer manifest review IDs"
        )


def _validate_review_scores(
    review: dict,
    *,
    expected_dimensions: list[str] | None = None,
) -> None:
    dimensions = review.get("evaluation_dimensions", [])
    items = review.get("items", [])
    if not isinstance(dimensions, list) or not dimensions:
        raise ValueError("review has no evaluation dimensions")
    if (
        any(not isinstance(dimension, str) or not dimension for dimension in dimensions)
        or len(dimensions) != len(set(dimensions))
    ):
        raise ValueError("review evaluation_dimensions must be unique non-empty strings")
    if expected_dimensions is not None and dimensions != expected_dimensions:
        raise ValueError(
            "review evaluation_dimensions do not match reviewer manifest"
        )
    if not isinstance(items, list) or not items:
        raise ValueError("review has no items")

    seen_ids: set[str] = set()
    for item in items:
        review_id = item.get("review_id")
        if not review_id:
            raise ValueError("review item is missing review_id")
        if review_id in seen_ids:
            raise ValueError(f"duplicate review_id: {review_id}")
        seen_ids.add(review_id)

        scores = item.get("scores")
        if not isinstance(scores, dict) or set(scores) != set(dimensions):
            raise ValueError(
                f"review scores for {review_id} do not match "
                "evaluation_dimensions"
            )
        for dimension in dimensions:
            score = scores.get(dimension)
            if isinstance(score, bool) or not isinstance(score, int):
                raise ValueError(
                    f"score for {review_id}/{dimension} must be an integer"
                )
            if not 1 <= score <= 5:
                raise ValueError(
                    f"score for {review_id}/{dimension} must be between 1 and 5"
                )

        if not isinstance(item.get("notes"), str):
            raise ValueError(f"review notes for {review_id} must be a string")


def _verify_frozen_review(frozen: dict) -> None:
    expected = frozen.get("review_sha256")
    if not expected:
        raise ValueError("frozen review is missing review_sha256")
    payload = dict(frozen)
    payload.pop("review_sha256", None)
    actual = _canonical_sha256(payload)
    if actual != expected:
        raise ValueError("frozen review hash verification failed")


def freeze_review(review_file: str | Path) -> dict:
    """Validate a completed blind review and write an immutable snapshot."""
    path = Path(review_file).expanduser().resolve()
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(path)

    review = json.loads(path.read_text(encoding="utf-8"))
    if review.get("status") != "open":
        raise ValueError("only an open review can be frozen")

    manifest_path = path.parent / REVIEW_MANIFEST_NAME
    if not manifest_path.exists() or not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    _validate_review_against_manifest(review, manifest)
    _validate_review_scores(
        review,
        expected_dimensions=list(manifest["evaluation_dimensions"]),
    )
    if review.get("experiment_id") == "EXP-019":
        from jsonschema import Draft202012Validator
        from .io import load_json
        review_schema = load_json("data/schemas/experiment_review.schema.json")
        if list(Draft202012Validator(review_schema).iter_errors(review)):
            raise ValueError("EXP-019 review schema validation failed")
        from .exp019_review import validate_review_details
        validate_review_details(review, manifest)

    frozen_path = path.parent / REVIEW_FROZEN_NAME
    if frozen_path.exists():
        raise FileExistsError(
            f"frozen review already exists: {frozen_path}"
        )

    frozen = dict(review)
    frozen["status"] = "frozen"
    frozen["frozen_at_utc"] = _utc_now()
    frozen["review_sha256"] = None
    hash_payload = dict(frozen)
    hash_payload.pop("review_sha256", None)
    frozen["review_sha256"] = _canonical_sha256(hash_payload)
    _write_json_atomic(frozen_path, frozen)

    return {
        "run_id": frozen["run_id"],
        "status": "frozen",
        "review": str(frozen_path),
        "review_sha256": frozen["review_sha256"],
    }


def reveal_review(run_file: str | Path) -> dict:
    """Reveal the committed treatment mapping only after review freeze."""
    run_path, run = load_run(run_file)
    if run.get("experiment_id") == "EXP-019":
        from .exp019_review import reveal
        return reveal(run_path)
    review_dir = run_path.parent / BLIND_REVIEW_DIRNAME
    frozen_path = review_dir / REVIEW_FROZEN_NAME
    mapping_path = run_path.parent / REVIEW_PRIVATE_DIRNAME / REVIEW_MAPPING_NAME

    if not frozen_path.exists():
        raise ValueError("review must be frozen before treatment mapping reveal")
    if not mapping_path.exists():
        raise FileNotFoundError(mapping_path)

    frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    _verify_frozen_review(frozen)

    mapping_core = {
        "run_id": mapping["run_id"],
        "experiment_id": mapping["experiment_id"],
        "entries": mapping["entries"],
    }
    actual_commitment = _canonical_sha256(mapping_core)
    expected_commitment = mapping.get("mapping_commitment_sha256")
    if actual_commitment != expected_commitment:
        raise ValueError("review mapping commitment verification failed")

    if frozen.get("mapping_commitment_sha256") != expected_commitment:
        raise ValueError("frozen review does not match committed review mapping")
    if frozen.get("review_package_sha256") != mapping.get(
        "review_package_sha256"
    ):
        raise ValueError("frozen review does not match review package")
    if frozen.get("run_id") != run.get("run_id"):
        raise ValueError("frozen review belongs to a different run")

    reveal_path = review_dir / REVIEW_REVEAL_NAME
    if reveal_path.exists():
        raise FileExistsError(f"review reveal already exists: {reveal_path}")

    reveal = {
        "run_id": run["run_id"],
        "experiment_id": run["experiment_id"],
        "revealed_at_utc": _utc_now(),
        "review_sha256": frozen["review_sha256"],
        "mapping_commitment_sha256": expected_commitment,
        "items": mapping["entries"],
    }
    _write_json_atomic(reveal_path, reveal)

    return {
        "run_id": run["run_id"],
        "status": "revealed",
        "reveal": str(reveal_path),
        "item_count": len(mapping["entries"]),
        "review_sha256": frozen["review_sha256"],
    }
