"""Offline adversarial tests against an actual temporary bare Git remote."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import subprocess
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from aipf.exp019_anchor import (GitRemoteProvenanceBackend, _git as _anchor_git, append_attempt_checkpoint,
                               ensure_run_root, verify_external)
from aipf.exp019_analysis import analyze_exp019, validate_exp019_result
from aipf.exp019_execution import _save_run, _write_receipt, execute_exp019_run
from aipf.exp019_protocol import append_attempt_event, find_slot
from aipf.exp019_receipt import validate_run_receipt
from aipf.exp019_review import write_freeze_commitment
from aipf.experiment_review import _canonical_sha256, create_review_package, freeze_review, reveal_review
from aipf.experiment_runs import create_run_plan, load_run_plan, sha256_file, write_run_plan


def _git(*args: str) -> str:
    result = subprocess.run(["git", *args], capture_output=True, text=True, check=True)
    return result.stdout.strip()


def _new_run(root: Path) -> Path:
    plan = create_run_plan("EXP-019", replicates=4, size="1024x1536", quality="high",
                           model="gpt-image-2-2026-04-21", model_snapshot="gpt-image-2-2026-04-21",
                           generation_mode="api")
    return write_run_plan(plan, root / "runs")


def _raster() -> bytes:
    output = BytesIO()
    Image.new("RGB", (1024, 1536), "gray").save(output, format="PNG")
    return output.getvalue()


class FakeImages:
    def __init__(self):
        self.calls = []
        self.image = base64.b64encode(_raster()).decode("ascii")

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(data=[SimpleNamespace(b64_json=self.image, revised_prompt=None)],
                               _request_id="offline-only", created=1)


@pytest.fixture(scope="module")
def partial_seed(tmp_path_factory):
    root = tmp_path_factory.mktemp("exp019-partial-anchor")
    remote = root / "remote.git"
    _git("init", "--bare", "-q", str(remote))
    prior = os.environ.get("AIPF_EXP019_PROVENANCE_REMOTE")
    os.environ["AIPF_EXP019_PROVENANCE_REMOTE"] = str(remote)
    try:
        run_file = _new_run(root)
        run = load_run_plan(run_file)
        ensure_run_root(run_file, run)
        slot = run["invocation_order"][0]
        variant, output = find_slot(run, slot["blind_id"])
        append_attempt_event(output, {"event": "started", "attempt_number": 1,
                                      "at_utc": "2026-01-01T00:00:00+00:00",
                                      "prompt_sha256": variant["prompt_sha256"]})
        append_attempt_event(output, {"event": "technical_failure", "attempt_number": 1,
                                      "at_utc": "2026-01-01T00:01:00+00:00", "error": "original error"})
        output["status"] = "failed"
        run["status"] = "running"
        _write_receipt(run_file.parent, run, variant, output, slot["position"])
        _save_run(run_file, run)
        append_attempt_checkpoint(run_file, run, output["blind_id"], 1)
        verify_external(run_file, run)
        return run_file, remote
    finally:
        if prior is None:
            os.environ.pop("AIPF_EXP019_PROVENANCE_REMOTE", None)
        else:
            os.environ["AIPF_EXP019_PROVENANCE_REMOTE"] = prior


@pytest.fixture(scope="module")
def completed_seed(tmp_path_factory):
    root = tmp_path_factory.mktemp("exp019-complete-anchor")
    remote = root / "remote.git"
    _git("init", "--bare", "-q", str(remote))
    prior = os.environ.get("AIPF_EXP019_PROVENANCE_REMOTE")
    os.environ["AIPF_EXP019_PROVENANCE_REMOTE"] = str(remote)
    try:
        run_file = _new_run(root)
        fake = FakeImages()
        assert execute_exp019_run(run_file, client=SimpleNamespace(images=fake))["status"] == "completed"
        assert len(fake.calls) == 12
        return run_file, remote
    finally:
        if prior is None:
            os.environ.pop("AIPF_EXP019_PROVENANCE_REMOTE", None)
        else:
            os.environ["AIPF_EXP019_PROVENANCE_REMOTE"] = prior


def _clone(seed, tmp_path, monkeypatch):
    run_file, remote = seed
    cloned_remote = tmp_path / "remote.git"
    shutil.copytree(remote, cloned_remote)
    cloned_root = tmp_path / "run"
    shutil.copytree(run_file.parent, cloned_root)
    state_path = cloned_root / ".provenance-private" / "anchor-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["remote_sha256"] = hashlib.sha256(str(cloned_remote).encode()).hexdigest()
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    monkeypatch.setenv("AIPF_EXP019_PROVENANCE_REMOTE", str(cloned_remote))
    return cloned_root / run_file.name, cloned_remote


def _freeze_two(run_file: Path) -> dict:
    packages = {}
    for reviewer in ("R1", "R2"):
        package = create_review_package(run_file, reviewer_id=reviewer)
        path = Path(package["review"])
        review = json.loads(path.read_text(encoding="utf-8"))
        review["reviewer_pseudonym"] = "synthetic-" + reviewer
        review["attestations"] = {"independent_reviewer": True, "individual_image_review": True,
                                  "treatment_blind_until_freeze": True}
        mapping = json.loads((run_file.parent / ".review-private" / f"{reviewer}.mapping.json").read_text(encoding="utf-8"))
        conditions = {item["review_id"]: item["variant_id"] for item in mapping["entries"]}
        for item in review["items"]:
            item["scores"] = {"art_material_fidelity": {"C": 3, "A": 2, "B": 4}[conditions[item["review_id"]]],
                              "semantic_compliance": 4, "aesthetic_quality": 4, "technical_defects": 4}
            item["diagnostics"] = {"target_region_localization": "yes", "controlled_tonal_transition_visible": "yes",
                                   "integrated_with_flat_print_structure": "yes", "generic_global_or_3d_shading": "none",
                                   "airbrushed_or_overlay_like_gradient": "none"}
            item["failure_observations"] = {"target_gradation_materially_absent_or_generic": False}
        path.write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")
        packages[reviewer] = package
    return packages


def _replace_first_attempt(run_file: Path) -> None:
    run = load_run_plan(run_file)
    slot = run["invocation_order"][0]
    variant, output = find_slot(run, slot["blind_id"])
    for binding in output["receipt_history"]:
        (run_file.parent / binding["file"]).unlink()
        (run_file.parent / binding["commitment_file"]).unlink()
    output["attempt_events"] = []
    append_attempt_event(output, {"event": "started", "attempt_number": 1,
                                  "at_utc": "2026-01-01T00:00:00+00:00", "prompt_sha256": variant["prompt_sha256"]})
    append_attempt_event(output, {"event": "technical_failure", "attempt_number": 1,
                                  "at_utc": "2026-01-01T00:01:00+00:00", "error": "forged failure"})
    output["receipt_history"] = []
    _write_receipt(run_file.parent, run, variant, output, slot["position"])
    _save_run(run_file, run)


def test_remote_root_duplicate_id_and_private_payload(tmp_path, monkeypatch, partial_seed):
    run_file, remote = _clone(partial_seed, tmp_path, monkeypatch)
    run = load_run_plan(run_file)
    state = verify_external(run_file, run)
    assert state["root_commit"] != state["head_commit"]
    backend = GitRemoteProvenanceBackend(str(remote))
    for checkpoint in state["checkpoints"]:
        record = checkpoint["record"]
        assert set(record) == {"schema_version", "run_id", "sequence", "event_type", "evidence_sha256", "previous_anchor_commit"}
        text = _git(f"--git-dir={remote}", "show", f"{checkpoint['commit']}:checkpoint.json")
        assert all(secret not in text for secret in ("bokashi", "prompt", "variant_id", "blind_id", "scores", "diagnostics", "mapping", "treatment"))
    assert backend.verify(state["ref"], state["checkpoints"]) == state["head_commit"]
    cloned_new = _new_run(tmp_path / "another")
    new_run = load_run_plan(cloned_new)
    new_run["run_id"] = run["run_id"]
    with pytest.raises(ValueError):
        ensure_run_root(cloned_new, new_run)


def test_coordinated_attempt_rewrite_is_blocked_before_provider(tmp_path, monkeypatch, partial_seed):
    run_file, _remote = _clone(partial_seed, tmp_path, monkeypatch)
    _replace_first_attempt(run_file)
    fake = FakeImages()
    with pytest.raises(ValueError, match="evidence|checkpoint"):
        execute_exp019_run(run_file, client=SimpleNamespace(images=fake))
    assert fake.calls == []


def test_remote_ref_deletion_and_advancement_fail_closed(tmp_path, monkeypatch, partial_seed):
    run_file, remote = _clone(partial_seed, tmp_path, monkeypatch)
    run = load_run_plan(run_file)
    state = verify_external(run_file, run)
    _git(f"--git-dir={remote}", "update-ref", "-d", state["ref"])
    with pytest.raises(ValueError, match="missing|moved"):
        verify_external(run_file, run)
    with pytest.raises(ValueError):
        ensure_run_root(run_file, run)
    (run_file.parent / ".provenance-private" / "anchor-state.json").unlink()
    with pytest.raises(ValueError, match="cannot initialize"):
        ensure_run_root(run_file, run)


def test_unexpected_remote_advance_rejects_retry(tmp_path, monkeypatch, partial_seed):
    run_file, remote = _clone(partial_seed, tmp_path, monkeypatch)
    run = load_run_plan(run_file)
    state = verify_external(run_file, run)
    backend = GitRemoteProvenanceBackend(str(remote))
    extra = {"schema_version": "1.0.0", "run_id": run["run_id"], "sequence": 2,
             "event_type": "attempt", "evidence_sha256": "0" * 64,
             "previous_anchor_commit": state["head_commit"]}
    backend.append(state["ref"], state["head_commit"], extra)
    with pytest.raises(ValueError, match="moved"):
        backend.append(state["ref"], state["head_commit"], extra)
    with pytest.raises(ValueError, match="moved"):
        verify_external(run_file, run)
    fake = FakeImages()
    with pytest.raises(ValueError):
        execute_exp019_run(run_file, client=SimpleNamespace(images=fake))
    assert fake.calls == []


def test_offline_full_remote_git_lifecycle(tmp_path, monkeypatch, completed_seed):
    run_file, remote = _clone(completed_seed, tmp_path, monkeypatch)
    run = load_run_plan(run_file)
    state = verify_external(run_file, run)
    assert len(state["checkpoints"]) == 13
    assert [slot["variant_id"] for slot in run["invocation_order"]] == list("BACCBABCAABC")
    packages = _freeze_two(run_file)
    freeze_review(packages["R1"]["review"])
    with pytest.raises(ValueError):
        reveal_review(run_file)
    freeze_review(packages["R2"]["review"])
    assert len(verify_external(run_file, run, require_reviews=True)["checkpoints"]) == 15
    assert reveal_review(run_file)["status"] == "revealed"
    result_path = tmp_path / "synthetic.result.json"
    result = analyze_exp019(run_file, output=result_path)
    assert result["contrasts"]["B-C"]["delta"] == 1
    assert result["contrasts"]["B-A"]["delta"] == 2
    assert validate_exp019_result(run_file, result_path) == result
    receipt = validate_run_receipt(run_file)
    assert receipt["external_provenance"]["backend"] == "remote_git"
    assert receipt["external_provenance"]["root_anchor_commit"] == state["root_commit"]
    backend = GitRemoteProvenanceBackend(str(remote))
    current = verify_external(run_file, run, require_reviews=True)
    extra = {"schema_version": "1.0.0", "run_id": run["run_id"], "sequence": len(current["checkpoints"]),
             "event_type": "review_freeze", "evidence_sha256": "0" * 64,
             "previous_anchor_commit": current["head_commit"]}
    backend.append(current["ref"], current["head_commit"], extra)
    with pytest.raises(ValueError, match="moved"):
        validate_run_receipt(run_file)
    with pytest.raises(ValueError, match="moved"):
        validate_exp019_result(run_file, result_path)


@pytest.mark.parametrize("reviewer", ["R1", "R2"])
def test_recreated_review_commitment_cannot_pass_reveal(tmp_path, monkeypatch, completed_seed, reviewer):
    run_file, _remote = _clone(completed_seed, tmp_path, monkeypatch)
    packages = _freeze_two(run_file)
    for name in ("R1", "R2"):
        freeze_review(packages[name]["review"])
    path = run_file.parent / "blind-review" / reviewer / "review.frozen.json"
    frozen = json.loads(path.read_text(encoding="utf-8"))
    old = frozen["items"][0]["scores"]["art_material_fidelity"]
    frozen["items"][0]["scores"]["art_material_fidelity"] = 5 if old != 5 else 1
    frozen["review_sha256"] = _canonical_sha256({k: v for k, v in frozen.items() if k != "review_sha256"})
    path.write_text(json.dumps(frozen, indent=2) + "\n", encoding="utf-8")
    commitment = run_file.parent / ".review-private" / f"{reviewer}.freeze.commitment.json"
    commitment.unlink()
    write_freeze_commitment(path)
    with pytest.raises(ValueError, match="evidence|checkpoint"):
        reveal_review(run_file)


def test_local_checkpoint_record_tampering_fails(tmp_path, monkeypatch, partial_seed):
    run_file, _remote = _clone(partial_seed, tmp_path, monkeypatch)
    path = run_file.parent / ".provenance-private" / "anchor-state.json"
    original = json.loads(path.read_text(encoding="utf-8"))
    for field, value in (("sequence", 7), ("sequence", 0), ("event_type", "review_freeze"),
                         ("previous_anchor_commit", "0" * 40), ("run_id", "wrong-run"),
                         ("evidence_sha256", "0" * 64)):
        altered = json.loads(json.dumps(original))
        altered["checkpoints"][-1]["record"][field] = value
        path.write_text(json.dumps(altered) + "\n", encoding="utf-8")
        with pytest.raises(ValueError):
            verify_external(run_file, load_run_plan(run_file))
    path.write_text(json.dumps(original) + "\n", encoding="utf-8")


def test_no_configured_production_remote_blocks_provider(tmp_path, monkeypatch):
    monkeypatch.delenv("AIPF_EXP019_PROVENANCE_REMOTE", raising=False)
    run_file = _new_run(tmp_path)
    fake = FakeImages()
    with pytest.raises(ValueError, match="requires AIPF_EXP019_PROVENANCE_REMOTE"):
        execute_exp019_run(run_file, client=SimpleNamespace(images=fake))
    assert fake.calls == []


def test_rewritten_receipt_timestamp_and_local_hashes_fail_remote(tmp_path, monkeypatch, partial_seed):
    run_file, _remote = _clone(partial_seed, tmp_path, monkeypatch)
    run = load_run_plan(run_file)
    slot = run["invocation_order"][0]
    _variant, output = find_slot(run, slot["blind_id"])
    binding = output["receipt_history"][0]
    receipt_path = run_file.parent / binding["file"]
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["recorded_at_utc"] = "2030-01-01T00:00:00Z"
    receipt_path.write_text(json.dumps(receipt) + "\n", encoding="utf-8")
    binding["sha256"] = sha256_file(receipt_path)
    commitment_path = run_file.parent / binding["commitment_file"]
    commitment = json.loads(commitment_path.read_text(encoding="utf-8"))
    commitment["receipt_sha256"] = binding["sha256"]
    commitment_path.write_text(json.dumps(commitment) + "\n", encoding="utf-8")
    binding["commitment_sha256"] = sha256_file(commitment_path)
    _save_run(run_file, run)
    with pytest.raises(ValueError, match="evidence|checkpoint"):
        verify_external(run_file, run)


@pytest.mark.parametrize("kind", ["diagnostic", "failure_flag", "mapping", "sample_set"])
def test_replaced_review_evidence_still_fails_remote(tmp_path, monkeypatch, completed_seed, kind):
    run_file, _remote = _clone(completed_seed, tmp_path, monkeypatch)
    packages = _freeze_two(run_file)
    for reviewer in ("R1", "R2"):
        freeze_review(packages[reviewer]["review"])
    frozen_path = run_file.parent / "blind-review" / "R1" / "review.frozen.json"
    mapping_path = run_file.parent / ".review-private" / "R1.mapping.json"
    frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    if kind == "diagnostic":
        frozen["items"][0]["diagnostics"]["target_region_localization"] = "no"
    elif kind == "failure_flag":
        frozen["items"][0]["failure_observations"]["target_gradation_materially_absent_or_generic"] = True
    elif kind == "mapping":
        mapping["entries"][0]["review_id"] = "Rforged"
    else:
        mapping["entries"].pop()
    if kind in {"mapping", "sample_set"}:
        core = {key: mapping[key] for key in ("run_id", "experiment_id", "reviewer_id", "review_batch_id", "entries")}
        mapping["mapping_commitment_sha256"] = _canonical_sha256(core)
        mapping_path.write_text(json.dumps(mapping) + "\n", encoding="utf-8")
        frozen["mapping_commitment_sha256"] = mapping["mapping_commitment_sha256"]
    frozen["review_sha256"] = _canonical_sha256({key: value for key, value in frozen.items() if key != "review_sha256"})
    frozen_path.write_text(json.dumps(frozen) + "\n", encoding="utf-8")
    commitment = run_file.parent / ".review-private" / "R1.freeze.commitment.json"
    commitment.unlink()
    write_freeze_commitment(frozen_path)
    with pytest.raises(ValueError, match="evidence|checkpoint"):
        reveal_review(run_file)


def test_missing_or_reordered_local_checkpoint_fails(tmp_path, monkeypatch, partial_seed):
    run_file, _remote = _clone(partial_seed, tmp_path, monkeypatch)
    path = run_file.parent / ".provenance-private" / "anchor-state.json"
    original = json.loads(path.read_text(encoding="utf-8"))
    for change in ("missing", "reordered"):
        state = json.loads(json.dumps(original))
        if change == "missing":
            state["checkpoints"].pop()
        else:
            state["checkpoints"].reverse()
        path.write_text(json.dumps(state) + "\n", encoding="utf-8")
        with pytest.raises(ValueError):
            verify_external(run_file, load_run_plan(run_file))
    path.write_text(json.dumps(original) + "\n", encoding="utf-8")


def test_non_linear_remote_commit_is_rejected(tmp_path, monkeypatch, partial_seed):
    run_file, remote = _clone(partial_seed, tmp_path, monkeypatch)
    state = verify_external(run_file, load_run_plan(run_file))
    record = {"schema_version": "1.0.0", "run_id": state["run_id"], "sequence": 2,
              "event_type": "attempt", "evidence_sha256": "0" * 64,
              "previous_anchor_commit": state["head_commit"]}
    blob = _anchor_git("hash-object", "-w", "--stdin", git_dir=remote,
                       input_bytes=(json.dumps(record) + "\n").encode())
    tree = _anchor_git("mktree", git_dir=remote,
                       input_bytes=f"100644 blob {blob}\tcheckpoint.json\n".encode())
    sibling = _anchor_git("commit-tree", tree, "-p", state["root_commit"], "-m", "sibling", git_dir=remote)
    merged = _anchor_git("commit-tree", tree, "-p", state["head_commit"], "-p", sibling,
                         "-m", "non-linear", git_dir=remote)
    _anchor_git("update-ref", state["ref"], merged, state["head_commit"], git_dir=remote)
    expected = state["checkpoints"] + [{"commit": merged, "record": record,
                                         "private_binding": {"slot_id": "opaque", "attempt_number": 2}}]
    with pytest.raises(ValueError, match="not linear"):
        GitRemoteProvenanceBackend(str(remote)).verify(state["ref"], expected)
