"""Deterministic analysis of the frozen EXP-019 three-condition protocol."""
from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from .exp019_protocol import REVIEWERS, find_slot, frozen_protocol
from .experiment_execution import load_run
from .experiment_review import _verify_frozen_review
from .experiment_runs import sha256_file
from .io import load_json

DIMENSIONS = ("art_material_fidelity", "semantic_compliance", "aesthetic_quality", "technical_defects")
LEVELS = ("contradicts", "weakly_contradicts", "inconclusive", "weakly_supports", "supports")


def _band(delta: float) -> str:
    if delta >= 1.0:
        return "supports"
    if delta >= 0.5:
        return "weakly_supports"
    if delta <= -1.0:
        return "contradicts"
    if delta <= -0.5:
        return "weakly_contradicts"
    return "inconclusive"


def _contrast(samples: dict[str, list[dict]], comparator: str, means: dict) -> dict:
    delta = means["B"]["art_material_fidelity"] - means[comparator]["art_material_fidelity"]
    raw_band = _band(delta)
    wins = losses = ties = 0
    for b in samples["B"]:
        for other in samples[comparator]:
            difference = b["averaged_scores"]["art_material_fidelity"] - other["averaged_scores"]["art_material_fidelity"]
            wins += difference > 0
            losses += difference < 0
            ties += difference == 0
    if wins + losses + ties != 16:
        raise ValueError("EXP-019 contrast requires 16 cross-condition pairs")
    direction_wins = wins if delta > 0 else losses if delta < 0 else 0
    consistency_adjusted = delta != 0 and direction_wins <= (wins + losses) / 2
    classification = raw_band
    if consistency_adjusted:
        index = LEVELS.index(classification)
        classification = LEVELS[index + (1 if index < 2 else -1 if index > 2 else 0)]
    return {
        "contrast": f"B-{comparator}", "delta": delta,
        "raw_classification": raw_band, "classification": classification,
        "pairwise": {"B_wins": wins, "B_losses": losses, "ties": ties,
                     "direction_wins": direction_wins, "non_tied": wins + losses},
        "moved_one_level_toward_inconclusive": consistency_adjusted,
    }


def _overall(first: str, second: str) -> str:
    positive = {"supports", "weakly_supports"}
    negative = {"contradicts", "weakly_contradicts"}
    if first in positive and second in positive:
        return "supports" if "supports" in (first, second) else "weakly_supports"
    if first in negative and second in negative:
        return "contradicts" if first == second == "contradicts" else "weakly_contradicts"
    return "inconclusive"


def analyze_exp019(run_file: str | Path, *, output: str | Path | None = None) -> dict:
    run_path, run = load_run(run_file)
    if run.get("experiment_id") != "EXP-019" or run.get("status") != "completed":
        raise ValueError("EXP-019 analysis requires a completed frozen run")
    from .exp019_receipt import _receipt_location, validate_run_receipt
    from .exp019_review import verify_reveal_against_private
    from .exp019_anchor import verify_external
    run_receipt = validate_run_receipt(run_path, run)
    verify_external(run_path, run, require_reviews=True)
    definition, _fixture = frozen_protocol(run["experiment_version"])
    root = run_path.parent
    reveal_path = root / "blind-review" / "reveal.json"
    if not reveal_path.is_file():
        raise ValueError("EXP-019 analysis requires treatment reveal after two review freezes")
    reveal = json.loads(reveal_path.read_text(encoding="utf-8"))
    verify_reveal_against_private(run_path, run, reveal)
    if reveal.get("run_id") != run["run_id"] or reveal.get("plan_commitment_sha256") != run["plan_commitment_sha256"]:
        raise ValueError("EXP-019 reveal/run binding mismatch")
    if set(reveal.get("reviews", {})) != set(REVIEWERS):
        raise ValueError("EXP-019 reveal lacks both review commitments")
    frozen_by_reviewer = {}
    for reviewer_id in REVIEWERS:
        path = root / "blind-review" / reviewer_id / "review.frozen.json"
        if not path.is_file():
            raise ValueError("EXP-019 frozen review missing")
        frozen = json.loads(path.read_text(encoding="utf-8"))
        _verify_frozen_review(frozen)
        binding = reveal["reviews"][reviewer_id]
        if frozen.get("review_sha256") != binding.get("review_sha256") or sha256_file(path) != binding.get("frozen_file_sha256"):
            raise ValueError("EXP-019 review hash mismatch after reveal")
        frozen_by_reviewer[reviewer_id] = {item["review_id"]: item for item in frozen["items"]}

    revealed_by_slot = {item["slot_id"]: item for item in reveal.get("items", [])}
    expected_ids = {slot["blind_id"] for slot in run["invocation_order"]}
    if len(reveal.get("items", [])) != 12 or set(revealed_by_slot) != expected_ids:
        raise ValueError("EXP-019 reveal does not bind exactly 12 slots")

    samples: dict[str, list[dict]] = {"C": [], "A": [], "B": []}
    generation_slots = []
    reviewer_ambiguity_count = 0
    for slot in run["invocation_order"]:
        variant, source = find_slot(run, slot["blind_id"])
        item = revealed_by_slot[slot["blind_id"]]
        if item.get("position") != slot["position"] or item.get("condition") != slot["variant_id"] or item.get("replicate") != slot["replicate"] or item.get("image_sha256") != source.get("image_sha256"):
            raise ValueError("EXP-019 revealed slot binding mismatch")
        image_path = root / "outputs" / str(source.get("image"))
        if not image_path.is_file() or sha256_file(image_path) != source.get("image_sha256"):
            raise ValueError("EXP-019 output image hash mismatch")
        events = source.get("attempt_events", [])
        starts = [event for event in events if event.get("event") == "started"]
        outcomes = [event for event in events if event.get("event") != "started"]
        if not starts or len(starts) != len(outcomes) or outcomes[-1].get("event") != "success" or outcomes[-1].get("image_sha256") != source["image_sha256"] or any(event.get("event") != "technical_failure" for event in outcomes[:-1]):
            raise ValueError("EXP-019 attempt provenance invalid")
        if len(source.get("receipt_history", [])) != len(outcomes):
            raise ValueError("EXP-019 receipt history incomplete")
        if run["experiment_version"] == "1.1.0":
            from .exp019_host import verify_host_attempts
            verify_host_attempts(root, run, source, slot["position"])
        else:
            receipt_schema = load_json("data/schemas/exp019_execution_receipt.schema.json")
            for index, receipt_binding in enumerate(source["receipt_history"], start=1):
                receipt_path = root / receipt_binding["file"]
                if not receipt_path.is_file() or sha256_file(receipt_path) != receipt_binding["sha256"]:
                    raise ValueError("EXP-019 execution receipt hash mismatch")
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                if list(Draft202012Validator(receipt_schema).iter_errors(receipt)):
                    raise ValueError("EXP-019 execution receipt schema invalid")
                if (receipt["run_id"] != run["run_id"] or receipt["slot_id"] != slot["blind_id"]
                        or receipt["slot_position"] != slot["position"]
                        or receipt["plan_commitment_sha256"] != run["plan_commitment_sha256"]
                        or receipt["fixture_sha256"] != run["fixture_sha256"]
                        or receipt["definition_sha256"] != run["experiment_definition_sha256"]
                        or receipt["prompt_sha256"] != variant["prompt_sha256"]
                        or receipt["settings"] != run["settings"]
                        or receipt["attempt_events"] != events[:index * 2]):
                    raise ValueError("EXP-019 execution receipt provenance mismatch")
                expected_image_hash = source["image_sha256"] if index == len(outcomes) else None
                if receipt["output_image_sha256"] != expected_image_hash:
                    raise ValueError("EXP-019 receipt output binding mismatch")
        metadata_path = root / "outputs" / str(source.get("metadata"))
        if not metadata_path.is_file() or sha256_file(metadata_path) != source.get("metadata_sha256"):
            raise ValueError("EXP-019 provider metadata hash mismatch")
        reviews = {}
        for reviewer_id in REVIEWERS:
            review_id = item["review_ids"][reviewer_id]
            if review_id not in frozen_by_reviewer[reviewer_id]:
                raise ValueError("EXP-019 sample/reviewer mapping mismatch")
            review = frozen_by_reviewer[reviewer_id][review_id]
            if set(review["scores"]) != set(DIMENSIONS):
                raise ValueError("EXP-019 raw review dimensions mismatch")
            reviews[reviewer_id] = {
                "review_id": review_id, "scores": review["scores"],
                "diagnostics": review["diagnostics"],
                "failure_observations": review["failure_observations"],
                "failure_classes": review["failure_classes"],
                "term_realization_failure": slot["variant_id"] in {"A", "B"} and review["failure_observations"]["target_gradation_materially_absent_or_generic"],
            }
            reviews[reviewer_id]["derived_failure_classes"] = review["failure_classes"] + (
                ["TERM_REALIZATION_FAILURE"] if reviews[reviewer_id]["term_realization_failure"] else []
            )
        primary_gap = abs(reviews["R1"]["scores"]["art_material_fidelity"] - reviews["R2"]["scores"]["art_material_fidelity"])
        reviewer_ambiguity_count += primary_gap >= 2
        averaged = {dimension: (reviews["R1"]["scores"][dimension] + reviews["R2"]["scores"][dimension]) / 2 for dimension in DIMENSIONS}
        sample = {"slot_id": slot["blind_id"], "position": slot["position"],
                  "condition": slot["variant_id"], "replicate": slot["replicate"],
                  "image_sha256": source["image_sha256"], "reviewers": reviews,
                  "averaged_scores": averaged}
        samples[slot["variant_id"]].append(sample)
        generation_slots.append({
            "slot_id": slot["blind_id"], "position": slot["position"],
            "condition": slot["variant_id"], "replicate": slot["replicate"],
            "prompt_sha256": variant["prompt_sha256"], "attempt_events": events,
            "receipt_history": source["receipt_history"], "output_sha256": source["image_sha256"],
            "metadata_file": source["metadata"], "metadata_sha256": source["metadata_sha256"],
        })
    if any(len(items) != 4 for items in samples.values()):
        raise ValueError("EXP-019 requires four samples per condition")
    means = {condition: {dimension: sum(item["averaged_scores"][dimension] for item in items) / 4 for dimension in DIMENSIONS} for condition, items in samples.items()}
    contrasts = {name: _contrast(samples, comparator, means) for name, comparator in (("B-C", "C"), ("B-A", "A"))}
    ceiling = all(item["averaged_scores"]["art_material_fidelity"] >= 4.5 for item in samples["C"])
    floor = all(means[c]["art_material_fidelity"] <= 2.0 for c in ("C", "A", "B")) and not any(item["averaged_scores"]["art_material_fidelity"] > 3.0 for items in samples.values() for item in items)
    reviewer_ambiguity = reviewer_ambiguity_count >= 4
    side_effects = [{"dimension": dimension, "comparator": comparator,
                     "delta_B_minus_comparator": means["B"][dimension] - means[comparator][dimension]}
                    for dimension in DIMENSIONS[1:] for comparator in ("C", "A")
                    if means["B"][dimension] - means[comparator][dimension] <= -1.0]
    initial = _overall(contrasts["B-C"]["classification"], contrasts["B-A"]["classification"])
    # The three registered experiment-level safeguards cap the whole result.
    # The side-effect veto limits supportive evidence, while a negative primary
    # result remains reportable as negative evidence.
    final = "inconclusive" if ceiling or floor or reviewer_ambiguity else initial
    if side_effects and final in {"supports", "weakly_supports"}:
        final = "inconclusive"
    result = {
        "schema_version": run["experiment_version"], "result_id": run["run_id"] + ".result",
        "experiment_id": "EXP-019", "experiment_version": run["experiment_version"], "run_id": run["run_id"],
        "status": "completed", "definition_sha256": run["experiment_definition_sha256"],
        "fixture_sha256": run["fixture_sha256"], "plan_commitment_sha256": run["plan_commitment_sha256"],
        "run_receipt_sha256": sha256_file(_receipt_location(run_path, run)[0]),
        "run_evidence_sha256": run_receipt["evidence_sha256"],
        "prompt_hashes": {v["variant_id"]: v["prompt_sha256"] for v in run["variants"]},
        "generation": ({"host_product": "ChatGPT Images", "mode": "host_native",
                        "backend_snapshot": run["model_snapshot"], "settings": run["settings"],
                        "reference_inputs": [], "slots": generation_slots}
                       if run["experiment_version"] == "1.1.0" else
                       {"provider": "openai", "mode": "generate", "requested_model": run["model"],
                        "recorded_model_snapshot": run["model_snapshot"], "settings": run["settings"],
                        "reference_inputs": [], "slots": generation_slots}),
        "review": {"records": reveal["reviews"], "reveal_file_sha256": sha256_file(reveal_path),
                   "revealed_at_utc": reveal["revealed_at_utc"]},
        "samples": sum((samples[c] for c in ("C", "A", "B")), []),
        "condition_means": means, "contrasts": contrasts,
        "safeguards": {"ceiling": ceiling, "floor": floor, "reviewer_ambiguity": reviewer_ambiguity,
                       "reviewer_ambiguity_sample_count": reviewer_ambiguity_count,
                       "side_effect_veto": bool(side_effects), "side_effects": side_effects,
                       "provenance_valid": True},
        "initial_evidence_classification": initial,
        "evidence_classification": final,
        "statistical_significance_claim": False,
    }
    schema = load_json("data/schemas/exp019_host_result.schema.json" if run["experiment_version"] == "1.1.0" else "data/schemas/exp019_result.schema.json")
    errors = list(Draft202012Validator(schema).iter_errors(result))
    if errors:
        raise ValueError("EXP-019 result schema invalid: " + "; ".join(error.message for error in errors))
    if output is not None:
        destination = Path(output).expanduser().resolve()
        if run["experiment_version"] == "1.1.0" and destination != (root / "analysis-private" / "EXP-019.analysis.json").resolve():
            raise ValueError("EXP-019 v1.1 raw result must remain in its private analysis directory")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(result, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        validate_exp019_result(run_path, destination)
    return result


def validate_exp019_result(run_file: str | Path, result_file: str | Path) -> dict:
    """Recompute all evidence and arithmetic; JSON-schema validity alone is insufficient."""
    persisted = json.loads(Path(result_file).expanduser().resolve().read_text(encoding="utf-8"))
    schema = load_json("data/schemas/exp019_host_result.schema.json" if persisted.get("experiment_version") == "1.1.0" else "data/schemas/exp019_result.schema.json")
    if list(Draft202012Validator(schema).iter_errors(persisted)):
        raise ValueError("EXP-019 persisted result schema invalid")
    expected = analyze_exp019(run_file)
    if persisted != expected:
        raise ValueError("EXP-019 persisted result differs from frozen evidence or derived analysis")
    return persisted
