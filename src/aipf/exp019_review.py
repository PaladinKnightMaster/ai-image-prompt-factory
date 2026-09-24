"""Two independent blind-review lifecycles for frozen EXP-019."""
from __future__ import annotations

import json
import secrets
import shutil
from pathlib import Path

from .exp019_protocol import REVIEWERS, find_slot
from .experiment_execution import load_run
from .experiment_runs import sha256_file
from .experiment_review import (
    _canonical_sha256, _dimension_guidance, _new_review_id, _utc_now,
    _verify_frozen_review, _write_json_atomic,
)


def create_package(run_file: str | Path, *, reviewer_id: str, output: str | Path | None = None) -> dict:
    run_path, run = load_run(run_file)
    if reviewer_id not in REVIEWERS:
        raise ValueError("EXP-019 reviewer_id must be R1 or R2")
    if run.get("status") != "completed" or any(
        item.get("status") != "generated" for v in run["variants"] for item in v["outputs"]
    ):
        raise ValueError("EXP-019 review requires all 12 generated slots")
    expected_destination = (run_path.parent / "blind-review" / reviewer_id).resolve()
    if output is not None and Path(output).expanduser().resolve() != expected_destination:
        raise ValueError("EXP-019 reviewer packages must use their committed per-reviewer paths")
    destination = expected_destination
    destination.mkdir(parents=True, exist_ok=False)
    private_path = run_path.parent / ".review-private" / f"{reviewer_id}.mapping.json"
    if private_path.exists():
        raise FileExistsError(private_path)

    from .exp019_protocol import frozen_protocol
    from .io import load_json
    definition, _fixture = frozen_protocol()
    prereg = definition["preregistration"]
    available_failure_classes = sorted(set(load_json("evaluation/failure_taxonomy.json")["classes"]) - {"TERM_REALIZATION_FAILURE"})
    items, mapping_entries, used = [], [], set()
    for slot in run["invocation_order"]:
        variant, source_item = find_slot(run, slot["blind_id"])
        image_name = source_item.get("image")
        if not image_name or not source_item.get("image_sha256"):
            raise ValueError("EXP-019 slot lacks output binding")
        source = run_path.parent / "outputs" / image_name
        if not source.is_file() or sha256_file(source) != source_item["image_sha256"]:
            raise ValueError("EXP-019 source output hash mismatch")
        review_id = _new_review_id(used)
        name = review_id + source.suffix.lower()
        shutil.copy2(source, destination / name)
        if sha256_file(destination / name) != source_item["image_sha256"]:
            raise ValueError("EXP-019 copied review output hash mismatch")
        items.append({"review_id": review_id, "image": name})
        mapping_entries.append({
            "review_id": review_id, "blind_id": slot["blind_id"],
            "variant_id": variant["variant_id"], "replicate": slot["replicate"],
            "image_sha256": source_item["image_sha256"],
        })
    # Each package gets independently random IDs and an independent order.
    items.sort(key=lambda row: row["review_id"])
    mapping_entries.sort(key=lambda row: row["review_id"])
    review_batch_id = "review-batch-" + secrets.token_hex(16)
    mapping_core = {"run_id": run["run_id"], "experiment_id": "EXP-019",
                    "reviewer_id": reviewer_id, "review_batch_id": review_batch_id,
                    "entries": mapping_entries}
    mapping_commitment = _canonical_sha256(mapping_core)
    created = _utc_now()
    dimensions = definition["evaluation_dimensions"]
    manifest_core = {
        "run_id": review_batch_id, "experiment_id": "EXP-019", "reviewer_id": reviewer_id,
        "created_at_utc": created, "status": "open", "run_sha256": sha256_file(run_path),
        "mapping_commitment_sha256": mapping_commitment, "review_count": 12,
        "score_scale": {"min": 1, "max": 5, "higher_is_better": True},
        "evaluation_dimensions": dimensions,
        "dimension_guidance": {d: _dimension_guidance(d) for d in dimensions},
        "primary_rubric": prereg["primary_rubric"],
        "diagnostic_schema": prereg["diagnostics"],
        "available_failure_classes": available_failure_classes,
        "reviewer_visible_context": prereg["review"]["reviewer_visible_context"].split(" Do not use")[0],
        "items": items,
    }
    manifest_hash = _canonical_sha256(manifest_core)
    manifest = {**manifest_core, "review_package_sha256": manifest_hash}
    review = {
        "run_id": review_batch_id, "experiment_id": "EXP-019", "reviewer_id": reviewer_id,
        "reviewer_pseudonym": "",
        "attestations": {"independent_reviewer": False, "individual_image_review": False,
                         "treatment_blind_until_freeze": False},
        "review_package_sha256": manifest_hash, "mapping_commitment_sha256": mapping_commitment,
        "status": "open", "created_at_utc": created, "frozen_at_utc": None,
        "review_sha256": None, "score_scale": manifest_core["score_scale"],
        "evaluation_dimensions": dimensions,
        "items": [{
            "review_id": item["review_id"],
            "scores": {dimension: None for dimension in dimensions},
            "diagnostics": {name: None for name in prereg["diagnostics"]},
            "failure_observations": {"target_gradation_materially_absent_or_generic": None},
            "failure_classes": [], "notes": "",
        } for item in items],
    }
    mapping = {**mapping_core, "created_at_utc": created,
               "mapping_commitment_sha256": mapping_commitment,
               "review_package_sha256": manifest_hash}
    _write_json_atomic(destination / "manifest.json", manifest)
    _write_json_atomic(destination / "review.json", review)
    _write_json_atomic(private_path, mapping)
    (destination / "README.md").write_text(
        "# EXP-019 blind review\n\nReview each image individually. Do not compare images side by side. "
        "The artifact is a Japanese woodblock print; the upper sky is the designated effect region. "
        "Record all four scores, five diagnostics, the neutral target-effect failure observation, "
        "and any applicable general failure classes before freezing this review. "
        "Enter your distinct reviewer pseudonym and affirm the three review attestations. "
        "Do not inspect run files, prompts, generation metadata, or private mappings.\n",
        encoding="utf-8",
    )
    return {"reviewer_id": reviewer_id, "manifest": str(destination / "manifest.json"),
            "review": str(destination / "review.json"), "review_package_sha256": manifest_hash,
            "mapping_commitment_sha256": mapping_commitment}


def validate_review_details(review: dict, manifest: dict) -> None:
    from .io import load_json
    if review.get("reviewer_id") != manifest.get("reviewer_id") or review.get("reviewer_id") not in REVIEWERS:
        raise ValueError("EXP-019 reviewer identity mismatch")
    if not isinstance(review.get("reviewer_pseudonym"), str) or not review["reviewer_pseudonym"].strip():
        raise ValueError("EXP-019 reviewer pseudonym is required")
    if review.get("attestations") != {
        "independent_reviewer": True, "individual_image_review": True,
        "treatment_blind_until_freeze": True,
    }:
        raise ValueError("EXP-019 blind independent review attestations are required")
    if len(review.get("items", [])) != 12 or manifest.get("review_count") != 12:
        raise ValueError("EXP-019 review must contain 12 images")
    allowed_classes = set(load_json("evaluation/failure_taxonomy.json")["classes"])
    allowed_classes.discard("TERM_REALIZATION_FAILURE")
    for item in review["items"]:
        diagnostics = item.get("diagnostics")
        if not isinstance(diagnostics, dict) or set(diagnostics) != set(manifest["diagnostic_schema"]):
            raise ValueError("EXP-019 categorical diagnostics are incomplete")
        for name, choices in manifest["diagnostic_schema"].items():
            if diagnostics[name] not in choices:
                raise ValueError(f"EXP-019 invalid diagnostic {name}")
        observation = item.get("failure_observations")
        if not isinstance(observation, dict) or set(observation) != {"target_gradation_materially_absent_or_generic"} or type(observation["target_gradation_materially_absent_or_generic"]) is not bool:
            raise ValueError("EXP-019 neutral target-effect failure observation is required")
        classes = item.get("failure_classes")
        if not isinstance(classes, list) or len(classes) != len(set(classes)) or not set(classes) <= allowed_classes:
            raise ValueError("EXP-019 invalid blind failure taxonomy classes")


def reveal(run_file: str | Path) -> dict:
    run_path, run = load_run(run_file)
    root = run_path.parent
    reveal_path = root / "blind-review" / "reveal.json"
    if reveal_path.exists():
        raise FileExistsError(reveal_path)
    review_records = {}
    mappings = {}
    reviewer_pseudonyms = set()
    for reviewer_id in REVIEWERS:
        directory = root / "blind-review" / reviewer_id
        frozen_path = directory / "review.frozen.json"
        mapping_path = root / ".review-private" / f"{reviewer_id}.mapping.json"
        manifest_path = directory / "manifest.json"
        if not frozen_path.is_file() or not mapping_path.is_file() or not manifest_path.is_file():
            raise ValueError("both EXP-019 reviews must be frozen before reveal")
        frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
        mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        _verify_frozen_review(frozen)
        core = {"run_id": mapping["run_id"], "experiment_id": mapping["experiment_id"],
                "reviewer_id": mapping["reviewer_id"],
                "review_batch_id": mapping["review_batch_id"], "entries": mapping["entries"]}
        if _canonical_sha256(core) != mapping.get("mapping_commitment_sha256"):
            raise ValueError("EXP-019 private mapping commitment mismatch")
        if frozen.get("reviewer_id") != reviewer_id or mapping.get("reviewer_id") != reviewer_id:
            raise ValueError("EXP-019 reviewer identity mismatch")
        if (frozen.get("run_id") != mapping.get("review_batch_id")
                or manifest.get("run_id") != mapping.get("review_batch_id")
                or mapping.get("run_id") != run["run_id"]):
            raise ValueError("EXP-019 review belongs to another run")
        if frozen.get("mapping_commitment_sha256") != mapping["mapping_commitment_sha256"] or frozen.get("review_package_sha256") != mapping.get("review_package_sha256") or frozen.get("review_package_sha256") != manifest.get("review_package_sha256"):
            raise ValueError("EXP-019 frozen review/package commitment mismatch")
        if manifest.get("run_sha256") != sha256_file(run_path):
            raise ValueError("EXP-019 run changed after review package creation")
        from .experiment_review import _verify_review_manifest
        _verify_review_manifest(manifest)
        validate_review_details(frozen, manifest)
        pseudonym = frozen["reviewer_pseudonym"].strip().casefold()
        if pseudonym in reviewer_pseudonyms:
            raise ValueError("EXP-019 requires two distinct reviewer pseudonyms")
        reviewer_pseudonyms.add(pseudonym)
        entry_by_source = {entry["blind_id"]: entry for entry in mapping["entries"]}
        expected_ids = {slot["blind_id"] for slot in run["invocation_order"]}
        if len(mapping["entries"]) != 12 or set(entry_by_source) != expected_ids:
            raise ValueError("EXP-019 reviewer mapping source set mismatch")
        if {item["review_id"] for item in frozen["items"]} != {entry["review_id"] for entry in mapping["entries"]}:
            raise ValueError("EXP-019 frozen review ID set mismatch")
        images_by_review_id = {item["review_id"]: item["image"] for item in manifest["items"]}
        for entry in mapping["entries"]:
            image_name = images_by_review_id.get(entry["review_id"])
            if not image_name or Path(image_name).name != image_name:
                raise ValueError("EXP-019 reviewer image binding missing")
            review_image = directory / image_name
            if not review_image.is_file() or sha256_file(review_image) != entry["image_sha256"]:
                raise ValueError("EXP-019 reviewer-visible image hash mismatch")
        for slot in run["invocation_order"]:
            _variant, output = find_slot(run, slot["blind_id"])
            entry = entry_by_source[slot["blind_id"]]
            if entry["image_sha256"] != output["image_sha256"] or entry["variant_id"] != slot["variant_id"] or entry["replicate"] != slot["replicate"]:
                raise ValueError("EXP-019 private mapping output binding mismatch")
            source = root / "outputs" / str(output.get("image"))
            if not source.is_file() or sha256_file(source) != output["image_sha256"]:
                raise ValueError("EXP-019 source output changed before reveal")
        review_records[reviewer_id] = {"review_sha256": frozen["review_sha256"],
                                       "frozen_file_sha256": sha256_file(frozen_path),
                                       "mapping_commitment_sha256": mapping["mapping_commitment_sha256"],
                                       "review_package_sha256": frozen["review_package_sha256"]}
        mappings[reviewer_id] = entry_by_source
    revealed = {
        "run_id": run["run_id"], "experiment_id": "EXP-019", "revealed_at_utc": _utc_now(),
        "plan_commitment_sha256": run["plan_commitment_sha256"], "reviews": review_records,
        "items": [{
            "slot_id": slot["blind_id"], "position": slot["position"],
            "condition": slot["variant_id"], "replicate": slot["replicate"],
            "image_sha256": find_slot(run, slot["blind_id"])[1]["image_sha256"],
            "review_ids": {reviewer: mappings[reviewer][slot["blind_id"]]["review_id"] for reviewer in REVIEWERS},
        } for slot in run["invocation_order"]],
    }
    _write_json_atomic(reveal_path, revealed)
    return {"run_id": run["run_id"], "status": "revealed", "reveal": str(reveal_path),
            "review_hashes": {reviewer: review_records[reviewer]["review_sha256"] for reviewer in REVIEWERS}}
