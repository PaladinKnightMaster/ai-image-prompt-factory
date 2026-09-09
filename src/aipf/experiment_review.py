from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .experiment_execution import load_run
from .experiment_runs import sha256_file
from .experiments import load_experiment


BLIND_REVIEW_DIRNAME = "blind-review"
REVIEW_MANIFEST_NAME = "manifest.json"
REVIEW_DRAFT_NAME = "review.json"
REVIEW_FROZEN_NAME = "review.frozen.json"


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
        output.get("status") == "generated"
        for output in outputs
    )


def _dimension_guidance(dimension: str) -> str:
    if dimension == "technical_defects":
        return (
            "5 = clean with no meaningful visible defects; "
            "1 = severe visible defects. Higher is better."
        )

    return "5 = strongest/best result; 1 = weakest/worst result."


def create_review_package(
    run_file: str | Path,
    *,
    output: str | Path | None = None,
) -> dict:
    """Create a reviewer-facing package with no treatment mapping.

    The package deliberately excludes variant IDs, factors, prompts,
    prompt hashes, replicate numbers, and generation metadata. The private
    ``run.json`` remains the only source of the control/treatment mapping.
    """
    run_path, run = load_run(run_file)

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

    items: list[dict] = []

    for variant in run["variants"]:
        for output_item in variant["outputs"]:
            blind_id = output_item["blind_id"]
            image_name = output_item.get("image")
            expected_hash = output_item.get("image_sha256")

            if not image_name or not expected_hash:
                raise ValueError(
                    f"generated output {blind_id} is missing image metadata"
                )

            source = (
                run_path.parent
                / variant["variant_id"]
                / image_name
            )

            if not source.exists() or not source.is_file():
                raise FileNotFoundError(source)

            actual_hash = sha256_file(source)

            if actual_hash != expected_hash:
                raise ValueError(
                    f"image hash mismatch for blind_id {blind_id}"
                )

            suffix = source.suffix.lower() or ".png"
            review_name = f"{blind_id}{suffix}"
            review_image = destination / review_name
            shutil.copy2(source, review_image)

            copied_hash = sha256_file(review_image)
            if copied_hash != expected_hash:
                raise ValueError(
                    f"copied image hash mismatch for blind_id {blind_id}"
                )

            items.append(
                {
                    "blind_id": blind_id,
                    "image": review_name,
                    "image_sha256": copied_hash,
                }
            )

    # Blind IDs are random. Sorting makes the package deterministic without
    # restoring the private control/treatment grouping.
    items.sort(key=lambda item: item["blind_id"])

    run_sha256 = sha256_file(run_path)

    manifest_payload = {
        "run_id": run["run_id"],
        "experiment_id": run["experiment_id"],
        "created_at_utc": _utc_now(),
        "status": "open",
        "run_sha256": run_sha256,
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
        "status": "open",
        "created_at_utc": _utc_now(),
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
                "blind_id": item["blind_id"],
                "scores": {
                    dimension: None
                    for dimension in evaluation_dimensions
                },
                "notes": "",
            }
            for item in items
        ],
    }

    _write_json_atomic(
        destination / REVIEW_MANIFEST_NAME,
        manifest,
    )
    _write_json_atomic(
        destination / REVIEW_DRAFT_NAME,
        review,
    )

    readme = f"""# AIPF Blind Review Package

Run: `{run['run_id']}`  
Experiment: `{run['experiment_id']}`  
Images: `{len(items)}`

Review each image using only its blind ID. Do not inspect the private
`run.json`, variant directories, prompts, or generation metadata until the
review has been frozen.

Score every evaluation dimension from 1 to 5. Higher is always better.
For `technical_defects`, 5 means clean/no meaningful defects and 1 means
severe visible defects.

Enter scores and optional notes in `review.json`, then freeze the review:

```text
aipf experiment-review-freeze <blind-review/review.json>
```

The frozen review is written to `review.frozen.json`. Do not edit that file
before treatment mapping is revealed.
"""
    (destination / "README.md").write_text(
        readme,
        encoding="utf-8",
    )

    return {
        "run_id": run["run_id"],
        "review_count": len(items),
        "output": str(destination),
        "manifest": str(destination / REVIEW_MANIFEST_NAME),
        "review": str(destination / REVIEW_DRAFT_NAME),
        "review_package_sha256": review_package_sha256,
    }


def _validate_review_scores(review: dict) -> None:
    dimensions = review.get("evaluation_dimensions", [])
    items = review.get("items", [])

    if not dimensions:
        raise ValueError("review has no evaluation dimensions")

    if not items:
        raise ValueError("review has no items")

    seen_ids: set[str] = set()

    for item in items:
        blind_id = item.get("blind_id")
        if not blind_id:
            raise ValueError("review item is missing blind_id")
        if blind_id in seen_ids:
            raise ValueError(f"duplicate review blind_id: {blind_id}")
        seen_ids.add(blind_id)

        scores = item.get("scores", {})

        if set(scores) != set(dimensions):
            raise ValueError(
                f"review scores for {blind_id} do not match "
                "evaluation_dimensions"
            )

        for dimension in dimensions:
            score = scores.get(dimension)

            if isinstance(score, bool) or not isinstance(
                score,
                (int, float),
            ):
                raise ValueError(
                    f"score for {blind_id}/{dimension} must be a number"
                )

            if not 1 <= score <= 5:
                raise ValueError(
                    f"score for {blind_id}/{dimension} must be between 1 and 5"
                )


def freeze_review(
    review_file: str | Path,
) -> dict:
    """Validate a completed blind review and write an immutable snapshot."""
    path = Path(review_file).expanduser().resolve()

    if not path.exists() or not path.is_file():
        raise FileNotFoundError(path)

    review = json.loads(path.read_text(encoding="utf-8"))

    if review.get("status") != "open":
        raise ValueError("only an open review can be frozen")

    _validate_review_scores(review)

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
