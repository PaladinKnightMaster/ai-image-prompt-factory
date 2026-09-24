"""Offline-only rehearsal of frozen EXP-019 infrastructure. No provider calls."""
from __future__ import annotations

import base64
import hashlib
import json
import struct
import zlib
from pathlib import Path
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator

from aipf.exp019_analysis import _band, _contrast, analyze_exp019
from aipf.exp019_execution import execute_exp019_run
from aipf.exp019_protocol import validate_run
from aipf.experiment_review import create_review_package, freeze_review, reveal_review
from aipf.experiment_execution import import_output
from aipf.experiment_runs import create_run_plan, load_run_plan, write_run_plan
from aipf.io import load_json


def _png(index: int) -> bytes:
    """Small valid synthetic raster bytes for an offline transport test."""
    def chunk(kind: bytes, body: bytes) -> bytes:
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)
    pixel = bytes((index % 256, 40, 90, 255))
    raw = (b"\0" + pixel * 1024) * 1536
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1024, 1536, 8, 6, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")


def _run(tmp_path: Path):
    plan = create_run_plan(
        "EXP-019", replicates=4, size="1024x1536", quality="high",
        model="gpt-image-2-2026-04-21", model_snapshot="gpt-image-2-2026-04-21",
        generation_mode="api",
    )
    return write_run_plan(plan, tmp_path / "runs")


def _assert_run_schema(run: dict) -> None:
    schema = load_json("data/schemas/experiment_run.schema.json")
    assert not list(Draft202012Validator(schema).iter_errors(run))


class FakeImages:
    def __init__(self, failures: int = 0, refusal: bool = False):
        self.calls = []
        self.failures = failures
        self.refusal = refusal

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        if self.refusal:
            raise ValueError("provider safety refusal")
        if len(self.calls) <= self.failures:
            raise ConnectionError("synthetic transport failure")
        item = SimpleNamespace(b64_json=base64.b64encode(_png(len(self.calls))).decode(), revised_prompt="provider echo if available")
        return SimpleNamespace(data=[item], created=1234567890, _request_id=f"req-synthetic-{len(self.calls)}",
                               model=None, size="1024x1536", quality="high", background="opaque", output_format="png")


def _filled_review(path: Path, score_by_condition: dict, mapping_path: Path, *, reviewer_offset=0, neutral_failure=False):
    review = json.loads(path.read_text(encoding="utf-8"))
    review["reviewer_pseudonym"] = "synthetic-" + review["reviewer_id"]
    review["attestations"] = {"independent_reviewer": True, "individual_image_review": True,
                              "treatment_blind_until_freeze": True}
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    by_id = {entry["review_id"]: entry["variant_id"] for entry in mapping["entries"]}
    for item in review["items"]:
        condition = by_id[item["review_id"]]
        item["scores"] = {"art_material_fidelity": score_by_condition[condition] + reviewer_offset,
                          "semantic_compliance": 4, "aesthetic_quality": 4, "technical_defects": 4}
        item["diagnostics"] = {
            "target_region_localization": "yes",
            "controlled_tonal_transition_visible": "yes",
            "integrated_with_flat_print_structure": "yes",
            "generic_global_or_3d_shading": "none",
            "airbrushed_or_overlay_like_gradient": "none",
        }
        item["failure_observations"] = {"target_gradation_materially_absent_or_generic": neutral_failure}
        item["failure_classes"] = []
    path.write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")


def test_exp019_plan_exact_order_and_tamper_rejection(tmp_path):
    run_file = _run(tmp_path)
    run = load_run_plan(run_file)
    _assert_run_schema(run)
    assert [slot["variant_id"] for slot in run["invocation_order"]] == list("BACCBABC AABC".replace(" ", ""))
    assert len({slot["blind_id"] for slot in run["invocation_order"]}) == 12
    assert run["settings"] == {"replicates": 4, "size": "1024x1536", "quality": "high", "background": "opaque", "seed": None, "image_count_per_invocation": 1}
    assert run["reference_inputs"] == [] and run["execution_provenance"]["receipt_required"]
    assert execute_exp019_run(run_file, dry_run=True)["slots"][0]["prompt_sha256"] == run["variants"][2]["prompt_sha256"]
    run["invocation_order"][0]["variant_id"] = "C"
    with pytest.raises(ValueError, match="invocation order"):
        validate_run(run)
    run = load_run_plan(run_file)
    run["variants"][0]["prompt"] += " altered"
    with pytest.raises(ValueError, match="prompt or hash"):
        validate_run(run)


def test_exp019_rejects_nonfrozen_plan_config():
    with pytest.raises(ValueError, match="exact generation settings"):
        create_run_plan("EXP-019")


def test_exp019_manual_import_cannot_bypass_attempt_provenance(tmp_path):
    run_file = _run(tmp_path)
    image = tmp_path / "offline.png"
    image.write_bytes(_png(1))
    slot = load_run_plan(run_file)["invocation_order"][0]
    with pytest.raises(ValueError, match="manual import is disabled"):
        import_output(run_file, blind_id=slot["blind_id"], image=image)


def test_exp019_offline_synthetic_two_review_lifecycle(tmp_path):
    run_file = _run(tmp_path)
    fake = FakeImages(failures=1)
    completed = execute_exp019_run(run_file, client=SimpleNamespace(images=fake))
    assert completed["status"] == "completed" and completed["generated"] == 12
    run = load_run_plan(run_file)
    _assert_run_schema(run)
    assert len(fake.calls) == 13
    assert all(call["model"] == "gpt-image-2-2026-04-21" and call["size"] == "1024x1536" and call["quality"] == "high" and call["background"] == "opaque" and call["n"] == 1 for call in fake.calls)
    condition_by_hash = {v["prompt_sha256"]: v["variant_id"] for v in run["variants"]}
    successful_order = [condition_by_hash[hashlib.sha256(call["prompt"].encode()).hexdigest()] for call in fake.calls[1:]]
    assert successful_order == [slot["variant_id"] for slot in run["invocation_order"]]
    first = run["variants"][2]["outputs"][0]
    assert [event["event"] for event in first["attempt_events"]] == ["started", "technical_failure", "started", "success"]
    assert len(first["receipt_history"]) == 2
    assert all("event_sha256" in event for event in first["attempt_events"])
    metadata = json.loads((run_file.parent / "outputs" / first["metadata"]).read_text(encoding="utf-8"))
    assert metadata["provider_response"]["request_id"] == "req-synthetic-2"
    assert metadata["provider_response"]["revised_prompt"] == "provider echo if available"

    packages = {r: create_review_package(run_file, reviewer_id=r) for r in ("R1", "R2")}
    for reviewer_id, package in packages.items():
        manifest = Path(package["manifest"]).read_text(encoding="utf-8")
        assert run["run_id"] not in manifest
        assert json.loads(manifest)["run_id"].startswith("review-batch-")
        assert "bokashi" not in manifest.lower()
        assert "prompt_sha256" not in manifest and "variant_id" not in manifest and "blind_id" not in manifest
        reviewer_files = list(Path(package["manifest"]).parent.glob("*.png"))
        assert len(reviewer_files) == 12
        assert all(path.stem.startswith("R") and path.stem not in {"C", "A", "B"} for path in reviewer_files)
        _filled_review(Path(package["review"]), {"C": 3, "A": 2, "B": 4},
                       run_file.parent / ".review-private" / f"{reviewer_id}.mapping.json", neutral_failure=True)
    assert packages["R1"]["mapping_commitment_sha256"] != packages["R2"]["mapping_commitment_sha256"]
    freeze_review(packages["R1"]["review"])
    with pytest.raises(ValueError, match="both EXP-019 reviews"):
        reveal_review(run_file)
    freeze_review(packages["R2"]["review"])
    revealed = reveal_review(run_file)
    assert set(revealed["review_hashes"]) == {"R1", "R2"}
    result = analyze_exp019(run_file)
    assert result["condition_means"]["B"]["art_material_fidelity"] == 4
    assert result["contrasts"]["B-C"]["delta"] == 1
    assert result["contrasts"]["B-A"]["delta"] == 2
    assert result["contrasts"]["B-C"]["pairwise"]["B_wins"] == 16
    assert result["evidence_classification"] == "supports"  # synthetic arithmetic only
    assert all(not sample["reviewers"]["R1"]["term_realization_failure"] for sample in result["samples"] if sample["condition"] == "C")
    assert all(sample["reviewers"]["R1"]["term_realization_failure"] for sample in result["samples"] if sample["condition"] in {"A", "B"})
    assert all("TERM_REALIZATION_FAILURE" not in sample["reviewers"]["R1"]["derived_failure_classes"] for sample in result["samples"] if sample["condition"] == "C")
    assert all("TERM_REALIZATION_FAILURE" in sample["reviewers"]["R1"]["derived_failure_classes"] for sample in result["samples"] if sample["condition"] in {"A", "B"})
    assert not list(Draft202012Validator(load_json("data/schemas/exp019_result.schema.json")).iter_errors(result))
    # A completed run is never regenerated when execution is invoked again.
    assert execute_exp019_run(run_file, client=SimpleNamespace(images=fake))["generated"] == 0
    assert len(fake.calls) == 13


def _synthetic_case(tmp_path, reviewer_primaries, secondary_B=4):
    run_file = _run(tmp_path)
    assert execute_exp019_run(run_file, client=SimpleNamespace(images=FakeImages()))["status"] == "completed"
    for reviewer_id in ("R1", "R2"):
        package = create_review_package(run_file, reviewer_id=reviewer_id)
        review_path = Path(package["review"])
        mapping_path = run_file.parent / ".review-private" / f"{reviewer_id}.mapping.json"
        _filled_review(review_path, reviewer_primaries[reviewer_id], mapping_path)
        if secondary_B != 4:
            review = json.loads(review_path.read_text(encoding="utf-8"))
            by_id = {entry["review_id"]: entry["variant_id"] for entry in json.loads(mapping_path.read_text(encoding="utf-8"))["entries"]}
            for item in review["items"]:
                if by_id[item["review_id"]] == "B":
                    item["scores"]["semantic_compliance"] = secondary_B
            review_path.write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")
        freeze_review(review_path)
    reveal_review(run_file)
    return run_file, analyze_exp019(run_file)


@pytest.mark.parametrize(
    ("ratings", "secondary_B", "safeguard"),
    [
        ({"R1": {"C": 4, "A": 3, "B": 5}, "R2": {"C": 5, "A": 3, "B": 5}}, 4, "ceiling"),
        ({"R1": {"C": 1, "A": 1, "B": 2}, "R2": {"C": 1, "A": 1, "B": 2}}, 4, "floor"),
        ({"R1": {"C": 1, "A": 1, "B": 4}, "R2": {"C": 3, "A": 3, "B": 4}}, 4, "reviewer_ambiguity"),
        ({"R1": {"C": 3, "A": 2, "B": 4}, "R2": {"C": 3, "A": 2, "B": 4}}, 3, "side_effect_veto"),
    ],
)
def test_exp019_registered_safeguards_cap_synthetic_support(tmp_path, ratings, secondary_B, safeguard):
    _run_file, result = _synthetic_case(tmp_path, ratings, secondary_B)
    assert result["initial_evidence_classification"] == "supports"
    assert result["safeguards"][safeguard]
    assert result["evidence_classification"] == "inconclusive"
    if safeguard == "ceiling":
        sample = next(item for item in result["samples"] if item["condition"] == "C")
        assert sample["reviewers"]["R1"]["scores"]["art_material_fidelity"] == 4
        assert sample["reviewers"]["R2"]["scores"]["art_material_fidelity"] == 5
        assert sample["averaged_scores"]["art_material_fidelity"] == 4.5


def test_exp019_mixed_contrasts_remain_separate(tmp_path):
    ratings = {"R1": {"C": 2, "A": 3, "B": 3}, "R2": {"C": 2, "A": 4, "B": 4}}
    _run_file, result = _synthetic_case(tmp_path, ratings)
    assert result["contrasts"]["B-C"]["delta"] == 1.5
    assert result["contrasts"]["B-A"]["delta"] == 0
    assert result["evidence_classification"] == "inconclusive"


def test_exp019_review_requires_frozen_categorical_diagnostics(tmp_path):
    run_file = _run(tmp_path)
    execute_exp019_run(run_file, client=SimpleNamespace(images=FakeImages()))
    package = create_review_package(run_file, reviewer_id="R1")
    review_path = Path(package["review"])
    mapping_path = run_file.parent / ".review-private" / "R1.mapping.json"
    _filled_review(review_path, {"C": 3, "A": 2, "B": 4}, mapping_path)
    review = json.loads(review_path.read_text(encoding="utf-8"))
    review["items"][0]["diagnostics"]["target_region_localization"] = None
    review_path.write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid diagnostic"):
        freeze_review(review_path)


def test_exp019_tampered_receipt_cannot_support_analysis(tmp_path):
    ratings = {"R1": {"C": 3, "A": 2, "B": 4}, "R2": {"C": 3, "A": 2, "B": 4}}
    run_file, _result = _synthetic_case(tmp_path, ratings)
    run = load_run_plan(run_file)
    first = run["variants"][2]["outputs"][0]
    receipt = run_file.parent / first["receipt_history"][0]["file"]
    receipt.write_text(receipt.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(ValueError, match="receipt hash mismatch"):
        analyze_exp019(run_file)


def test_exp019_attempt_ledger_cannot_be_cleared_to_reroll(tmp_path):
    run_file = _run(tmp_path)
    fake = FakeImages()
    execute_exp019_run(run_file, client=SimpleNamespace(images=fake))
    run = load_run_plan(run_file)
    first = run["variants"][2]["outputs"][0]
    first["attempt_events"] = []
    first["receipt_history"] = []
    first["status"] = "planned"
    run_file.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unbound or missing attempt receipt"):
        execute_exp019_run(run_file, client=SimpleNamespace(images=fake))
    assert len(fake.calls) == 12


def test_exp019_three_technical_failures_stop_without_reroll(tmp_path):
    run_file = _run(tmp_path)
    fake = FakeImages(failures=12)
    result = execute_exp019_run(run_file, client=SimpleNamespace(images=fake))
    assert result["status"] == "incomplete" and len(fake.calls) == 3
    run = load_run_plan(run_file)
    _assert_run_schema(run)
    first = run["variants"][2]["outputs"][0]
    assert [event["event"] for event in first["attempt_events"]] == ["started", "technical_failure"] * 3
    assert len(first["receipt_history"]) == 3
    again = execute_exp019_run(run_file, client=SimpleNamespace(images=fake))
    assert again["status"] == "incomplete" and len(fake.calls) == 3


def test_exp019_safety_refusal_is_terminal(tmp_path):
    run_file = _run(tmp_path)
    fake = FakeImages(refusal=True)
    assert execute_exp019_run(run_file, client=SimpleNamespace(images=fake))["status"] == "incomplete"
    assert len(fake.calls) == 1
    first = load_run_plan(run_file)["variants"][2]["outputs"][0]
    assert first["attempt_events"][1]["event"] == "safety_refusal"


def test_exp019_analysis_bands_and_pairwise_demotion():
    assert [_band(delta) for delta in (1, .5, 0, -.5, -1)] == ["supports", "weakly_supports", "inconclusive", "weakly_contradicts", "contradicts"]
    # Mean B > C by 0.5, but B wins only eight of sixteen non-tied pairs.
    scores = {"B": [5, 5, 1, 1], "C": [3, 3, 2, 2]}
    samples = {key: [{"averaged_scores": {"art_material_fidelity": value}} for value in vals] for key, vals in scores.items()}
    means = {key: {"art_material_fidelity": sum(vals) / 4} for key, vals in scores.items()}
    contrast = _contrast(samples, "C", means)
    assert contrast["raw_classification"] == "weakly_supports"
    assert contrast["pairwise"] == {"B_wins": 8, "B_losses": 8, "ties": 0, "direction_wins": 8, "non_tied": 16}
    assert contrast["classification"] == "inconclusive"
