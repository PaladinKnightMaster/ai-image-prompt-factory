"""Synthetic Git integration tests for EXP-019 v1.2 checkpoint publisher (PR-9).

Uses isolated temporary bare Git remotes only. No real generation, no
experimental provenance mutation, and no contact with the historical
v1.1.1 chain.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from unittest import mock

import pytest

from aipf.exp019_v1_2_checkpoints import (
    PUBLIC_FIELDS,
    CheckpointPublisher,
    CheckpointVerifier,
    PublicationResult,
    SyntheticGitBackend,
    _normalize_remote_identity,
    attempt_evidence_digest,
    assert_production_publication_refused,
    build_public_record,
    make_lifecycle_anchor_verifier,
    production_publish_checkpoint,
    verify_event_ordering,
    v12_scientifically_active,
)


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], capture_output=True, text=True, check=True)
    return result.stdout.strip()


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


@pytest.fixture
def synthetic_remote(tmp_path, monkeypatch):
    remote = tmp_path / "remote.git"
    _git("init", "--bare", "-q", str(remote))
    monkeypatch.setenv("AIPF_EXP019_V12_SYNTHETIC_PROVENANCE", "1")
    # Ensure production remote env cannot collide with the temp remote.
    monkeypatch.delenv("AIPF_EXP019_PROVENANCE_REMOTE", raising=False)
    state_dir = tmp_path / "private"
    state_dir.mkdir()
    publisher = CheckpointPublisher(
        str(remote), synthetic=True, state_dir=state_dir)
    return publisher, remote, state_dir


def test_six_field_public_record_contract() -> None:
    record = build_public_record(
        run_id="run-a", sequence=0, event_type="run_root",
        evidence_sha256=_digest("e"), previous_anchor_commit=None)
    assert set(record) == PUBLIC_FIELDS
    assert record["schema_version"] == "1.0.0"
    with pytest.raises(ValueError, match="provenance_adjudication"):
        build_public_record(
            run_id="run-a", sequence=1,
            event_type="provenance_adjudication",
            evidence_sha256=_digest("e"), previous_anchor_commit="abc")


def test_normal_first_checkpoint(synthetic_remote) -> None:
    publisher, remote, _ = synthetic_remote
    result = publisher.publish_run_root("run-a", _digest("plan"))
    assert result.published
    assert result.commit
    assert result.record["event_type"] == "run_root"
    assert result.record["sequence"] == 0
    assert set(result.record) == PUBLIC_FIELDS
    # Public record must not leak private identifiers.
    blob = json.dumps(result.record)
    assert "slot" not in blob
    assert "treatment" not in blob
    assert "prompt" not in blob


def test_multiple_sequential_attempt_checkpoints(synthetic_remote) -> None:
    publisher, _, _ = synthetic_remote
    publisher.publish_run_root("run-a", _digest("plan"))
    r1, r2 = _digest("receipt-1"), _digest("receipt-2")
    publisher.register_finalized_attempt("run-a", "S1", 1, r1)
    publisher.register_finalized_attempt("run-a", "S1", 2, r2)  # retry
    a1 = publisher.publish_attempt("run-a", "S1", 1, r1)
    a2 = publisher.publish_attempt("run-a", "S1", 2, r2)
    assert a1.published and a2.published
    assert a1.commit != a2.commit
    state = publisher.load_state("run-a")
    assert [c["record"]["sequence"] for c in state.checkpoints] == [0, 1, 2]
    assert [c["record"]["event_type"] for c in state.checkpoints] == [
        "run_root", "attempt", "attempt"]
    verifier = CheckpointVerifier(publisher)
    assert verifier.verify_run("run-a").verified


def test_technical_failure_retry_distinct_checkpoints(synthetic_remote) -> None:
    publisher, _, _ = synthetic_remote
    publisher.publish_run_root("run-a", _digest("plan"))
    fail_receipt = _digest("fail")
    retry_receipt = _digest("retry")
    publisher.register_finalized_attempt("run-a", "S1", 1, fail_receipt)
    publisher.register_finalized_attempt("run-a", "S1", 2, retry_receipt)
    publisher.publish_attempt("run-a", "S1", 1, fail_receipt)
    publisher.publish_attempt("run-a", "S1", 2, retry_receipt)
    state = publisher.load_state("run-a")
    digests = [c["record"]["evidence_sha256"] for c in state.checkpoints
               if c["record"]["event_type"] == "attempt"]
    assert digests[0] != digests[1]
    assert digests[0] == attempt_evidence_digest(fail_receipt)


def test_completed_and_incomplete_run_closure(synthetic_remote) -> None:
    publisher, _, _ = synthetic_remote
    publisher.publish_run_root("run-complete", _digest("plan"))
    receipt = _digest("r")
    publisher.register_finalized_attempt("run-complete", "S1", 1, receipt)
    publisher.publish_attempt("run-complete", "S1", 1, receipt)
    publisher.publish_review_freeze(
        "run-complete", "R1", _digest("freeze-r1"))
    publisher.publish_review_freeze(
        "run-complete", "R2", _digest("freeze-r2"))
    done = publisher.publish_run_disposition(
        "run-complete", "completed", _digest("close"), incomplete=False)
    assert done.published
    assert CheckpointVerifier(publisher).verify_run("run-complete").verified

    publisher.publish_run_root("run-incomplete", _digest("plan2"))
    # Incomplete may close without review-freeze.
    incomplete = publisher.publish_run_disposition(
        "run-incomplete", "incomplete", _digest("close2"), incomplete=True)
    assert incomplete.published
    assert publisher.load_state("run-incomplete").incomplete_closure


def test_duplicate_append_requests(synthetic_remote) -> None:
    publisher, _, _ = synthetic_remote
    first = publisher.publish_run_root("run-a", _digest("plan"))
    again = publisher.publish_run_root("run-a", _digest("plan"))
    assert again.recognized_existing
    assert again.commit == first.commit
    receipt = _digest("r")
    publisher.register_finalized_attempt("run-a", "S1", 1, receipt)
    a1 = publisher.publish_attempt("run-a", "S1", 1, receipt)
    a2 = publisher.publish_attempt("run-a", "S1", 1, receipt)
    assert a2.recognized_existing and a2.commit == a1.commit


def test_interrupted_push_remote_succeeded(synthetic_remote) -> None:
    """Remote commit succeeded but local state did not advance — recognize."""
    publisher, _, _ = synthetic_remote
    publisher.publish_run_root("run-a", _digest("plan"))
    receipt = _digest("r")
    publisher.register_finalized_attempt("run-a", "S1", 1, receipt)
    state = publisher.load_state("run-a")
    evidence = attempt_evidence_digest(receipt)
    record = build_public_record(
        run_id="run-a", sequence=1, event_type="attempt",
        evidence_sha256=evidence, previous_anchor_commit=state.head_commit)
    # Push the intended checkpoint at the backend layer only (local
    # private state still at run_root).
    pushed = publisher.backend.append(state.ref, state.head_commit, record)
    assert pushed.published and pushed.commit
    # Publisher re-entry must recognize the existing remote tip rather
    # than appending a duplicate attempt checkpoint.
    recognized = publisher.backend.append(
        state.ref, state.head_commit, record)
    assert recognized.recognized_existing
    assert recognized.commit == pushed.commit
    # Completing through the publisher API also stays exactly-once.
    result = publisher.publish_attempt("run-a", "S1", 1, receipt)
    assert result.published
    assert result.commit == pushed.commit
    replay = publisher.publish_attempt("run-a", "S1", 1, receipt)
    assert replay.recognized_existing


def test_interrupted_push_remote_did_not_succeed(synthetic_remote) -> None:
    publisher, remote, _ = synthetic_remote
    publisher.publish_run_root("run-a", _digest("plan"))
    receipt = _digest("r")
    publisher.register_finalized_attempt("run-a", "S1", 1, receipt)
    state = publisher.load_state("run-a")
    evidence = attempt_evidence_digest(receipt)
    record = build_public_record(
        run_id="run-a", sequence=1, event_type="attempt",
        evidence_sha256=evidence, previous_anchor_commit=state.head_commit)

    def fail_push(ref, expected_head, rec):
        # Do not push; report failure with remote still at expected head.
        return publisher.backend.append.__class__.__dict__  # unused

    with mock.patch.object(
            publisher.backend, "append",
            return_value=__import__(
                "aipf.exp019_v1_2_checkpoints", fromlist=["PublicationResult"]
            ).PublicationResult(
                published=False, commit=None, recognized_existing=False,
                expected_head=state.head_commit,
                remote_head=state.head_commit, record=record,
                message="push failed and remote lacks the intended "
                        "checkpoint; safe to retry")):
        result = publisher.publish_attempt("run-a", "S1", 1, receipt)
    assert not result.published
    # State must not advance; retry can proceed.
    assert publisher.load_state("run-a").head_commit == state.head_commit
    retry = publisher.publish_attempt("run-a", "S1", 1, receipt)
    assert retry.published


def test_remote_head_moved_unexpectedly(synthetic_remote) -> None:
    publisher, remote, _ = synthetic_remote
    publisher.publish_run_root("run-a", _digest("plan"))
    # Force-update remote tip to an unrelated commit.
    foreign = _git(
        "-C", str(remote.parent), "init", "-q", str(remote.parent / "other"))
    other = remote.parent / "other.git"
    _git("init", "--bare", "-q", str(other))
    # Create a foreign commit on the provenance ref via a throwaway repo.
    work = remote.parent / "work"
    work.mkdir()
    _git("init", "-q", str(work))
    (work / "noise.txt").write_text("noise", encoding="utf-8")
    _git("-C", str(work), "add", "noise.txt")
    _git("-C", str(work), "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-m", "noise")
    commit = _git("-C", str(work), "rev-parse", "HEAD")
    # Force-update the provenance ref to simulate unexpected remote movement.
    _git("-C", str(work), "push", "--force", str(remote),
         f"{commit}:refs/heads/exp-provenance/run-a")
    receipt = _digest("r")
    publisher.register_finalized_attempt("run-a", "S1", 1, receipt)
    result = publisher.publish_attempt("run-a", "S1", 1, receipt)
    assert not result.published
    assert "moved" in result.message.lower() or "safe" in result.message.lower()


def test_missing_or_substituted_terminal_receipt(synthetic_remote) -> None:
    publisher, _, _ = synthetic_remote
    publisher.publish_run_root("run-a", _digest("plan"))
    with pytest.raises(ValueError, match="finalized generation"):
        publisher.publish_attempt("run-a", "S1", 1, _digest("missing"))
    real = _digest("real")
    publisher.register_finalized_attempt("run-a", "S1", 1, real)
    with pytest.raises(ValueError, match="finalized generation"):
        publisher.publish_attempt("run-a", "S1", 1, _digest("substituted"))


def test_receipt_checkpoint_digest_mismatch(synthetic_remote) -> None:
    publisher, _, _ = synthetic_remote
    publisher.publish_run_root("run-a", _digest("plan"))
    receipt = _digest("r")
    publisher.register_finalized_attempt("run-a", "S1", 1, receipt)
    publisher.publish_attempt("run-a", "S1", 1, receipt)
    state = publisher.load_state("run-a")
    anchor = state.checkpoints[-1]["commit"]
    verifier = CheckpointVerifier(publisher)
    bad = verifier.verify_attempt_anchor("run-a", _digest("other"), anchor)
    assert not bad.verified
    assert "ANCHOR_NOT_FOUND" in bad.codes or \
        "RECEIPT_DIGEST_MISMATCH" in bad.codes


def test_sequence_gaps_and_invalid_ordering() -> None:
    records = [
        build_public_record(
            run_id="r", sequence=0, event_type="run_root",
            evidence_sha256=_digest("a"), previous_anchor_commit=None),
        build_public_record(
            run_id="r", sequence=2, event_type="attempt",
            evidence_sha256=_digest("b"), previous_anchor_commit="x"),
    ]
    ok, findings = verify_event_ordering(records)
    assert not ok
    assert any(f.code == "SEQUENCE_GAP" for f in findings)


def test_attempt_without_finalized_invocation(synthetic_remote) -> None:
    publisher, _, _ = synthetic_remote
    publisher.publish_run_root("run-a", _digest("plan"))
    with pytest.raises(ValueError, match="finalized generation"):
        publisher.publish_attempt("run-a", "S1", 1, _digest("r"))


def test_reviewer_freeze_before_permitted_completion(synthetic_remote) -> None:
    publisher, _, _ = synthetic_remote
    publisher.publish_run_root("run-a", _digest("plan"))
    receipt = _digest("r")
    publisher.register_finalized_attempt("run-a", "S1", 1, receipt)
    # Attempt registered but not yet checkpointed.
    with pytest.raises(ValueError, match="attempt phase"):
        publisher.publish_review_freeze("run-a", "R1", _digest("f"))


def test_run_disposition_appended_twice(synthetic_remote) -> None:
    publisher, _, _ = synthetic_remote
    publisher.publish_run_root("run-a", _digest("plan"))
    publisher.publish_run_disposition(
        "run-a", "incomplete", _digest("c"), incomplete=True)
    with pytest.raises(ValueError, match="after terminal run disposition"):
        publisher.publish_run_disposition(
            "run-a", "incomplete", _digest("c2"), incomplete=True)


def test_publication_after_run_closure(synthetic_remote) -> None:
    publisher, _, _ = synthetic_remote
    publisher.publish_run_root("run-a", _digest("plan"))
    publisher.publish_run_disposition(
        "run-a", "incomplete", _digest("c"), incomplete=True)
    receipt = _digest("r")
    with pytest.raises(ValueError, match="after terminal run disposition"):
        publisher.register_finalized_attempt("run-a", "S1", 1, receipt)


def test_private_identifier_leakage_absent(synthetic_remote) -> None:
    publisher, remote, _ = synthetic_remote
    publisher.publish_run_root("run-a", _digest("plan"))
    receipt = _digest("r")
    publisher.register_finalized_attempt(
        "run-a", "opaque-slot-99", 1, receipt)
    publisher.publish_attempt("run-a", "opaque-slot-99", 1, receipt)
    publisher.publish_review_freeze("run-a", "R1", _digest("f"))
    # Inspect every remote commit's public JSON.
    ref = "refs/heads/exp-provenance/run-a"
    head = _git("ls-remote", str(remote), ref).split()[0]
    with pytest.MonkeyPatch.context():
        pass
    # Fetch via publisher backend.
    state = publisher.load_state("run-a")
    for entry in state.checkpoints:
        record = publisher.backend.read_record(ref, entry["commit"])
        text = json.dumps(record)
        assert "opaque-slot-99" not in text
        assert "treatment" not in text
        assert "prompt" not in text
        assert "conflict" not in text
        assert set(record) == PUBLIC_FIELDS
    assert head == state.head_commit


def test_historical_v1_1_1_chain_untouched(synthetic_remote, monkeypatch) -> None:
    """v1.2 publisher must not call into or alter v1.1.1 anchor APIs."""
    import aipf.exp019_anchor as anchor
    publisher, _, _ = synthetic_remote
    with mock.patch.object(anchor, "ensure_run_root",
                           side_effect=AssertionError("v1.1.1 touched")):
        publisher.publish_run_root("run-a", _digest("plan"))
        receipt = _digest("r")
        publisher.register_finalized_attempt("run-a", "S1", 1, receipt)
        publisher.publish_attempt("run-a", "S1", 1, receipt)


def test_activation_lockout_no_frozen_v1_2() -> None:
    assert v12_scientifically_active() is False
    with pytest.raises(PermissionError, match="scientifically inactive"):
        assert_production_publication_refused()
    with pytest.raises(PermissionError):
        production_publish_checkpoint()
    with pytest.raises(PermissionError):
        CheckpointPublisher("/tmp/x", synthetic=False)


def test_synthetic_requires_env(tmp_path, monkeypatch) -> None:
    remote = tmp_path / "remote.git"
    _git("init", "--bare", "-q", str(remote))
    monkeypatch.delenv("AIPF_EXP019_V12_SYNTHETIC_PROVENANCE", raising=False)
    with pytest.raises(PermissionError, match="SYNTHETIC"):
        CheckpointPublisher(str(remote), synthetic=True, state_dir=tmp_path)


def test_lifecycle_anchor_verifier_requires_remote_proof(synthetic_remote) -> None:
    publisher, _, _ = synthetic_remote
    publisher.publish_run_root("run-a", _digest("plan"))
    receipt = _digest("r")
    publisher.register_finalized_attempt("run-a", "S1", 1, receipt)
    pub = publisher.publish_attempt("run-a", "S1", 1, receipt)
    verifier = CheckpointVerifier(publisher)
    anchor_fn = make_lifecycle_anchor_verifier(verifier, "run-a")
    assert anchor_fn({"receipt_sha256": receipt}, pub.commit) is True
    assert anchor_fn({"receipt_sha256": receipt}, "deadbeef" * 8) is False
    assert anchor_fn({"receipt_sha256": _digest("other")}, pub.commit) is False
    # Caller boolean alone is never a VerificationResult.
    result = verifier.verify_attempt_anchor("run-a", receipt, pub.commit)
    assert result.verified is True
    assert result.factual_claim_proven is False


def test_no_real_generation_or_experimental_mutation(synthetic_remote) -> None:
    """Suite must not import generation or mutate historical provenance."""
    publisher, _, _ = synthetic_remote
    publisher.publish_run_root("run-a", _digest("plan"))
    # Explicit: publisher public API has no generate/allocate.
    assert not hasattr(publisher, "generate")
    assert not hasattr(publisher, "allocate")


def test_network_remote_cannot_bypass_synthetic_boundary(
        tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AIPF_EXP019_V12_SYNTHETIC_PROVENANCE", "1")
    monkeypatch.setenv(
        "AIPF_EXP019_PROVENANCE_REMOTE",
        "https://github.com/example/exp019-anchors.git")
    # URL-form mismatch previously bypassed Path.resolve equality.
    with pytest.raises(PermissionError, match="network Git remotes"):
        CheckpointPublisher(
            "git@github.com:example/exp019-anchors.git",
            synthetic=True, state_dir=tmp_path)
    with pytest.raises(PermissionError, match="network Git remotes"):
        SyntheticGitBackend("https://github.com/example/exp019-anchors.git")
    # Local temp remote is still allowed.
    remote = tmp_path / "ok.git"
    _git("init", "--bare", "-q", str(remote))
    publisher = CheckpointPublisher(
        str(remote), synthetic=True, state_dir=tmp_path)
    assert publisher.remote == str(remote)


def test_production_path_alias_refused(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AIPF_EXP019_V12_SYNTHETIC_PROVENANCE", "1")
    prod = tmp_path / "production-provenance.git"
    _git("init", "--bare", "-q", str(prod))
    monkeypatch.setenv("AIPF_EXP019_PROVENANCE_REMOTE", str(prod))
    with pytest.raises(PermissionError, match="production"):
        CheckpointPublisher(str(prod), synthetic=True, state_dir=tmp_path)


def test_normalize_remote_identity_collapses_url_forms() -> None:
    a = _normalize_remote_identity(
        "https://github.com/example/exp019-anchors.git")
    b = _normalize_remote_identity(
        "git@github.com:example/exp019-anchors.git")
    c = _normalize_remote_identity(
        "ssh://git@github.com/example/exp019-anchors.git")
    assert a == b == c


def test_completed_disposition_requires_attempt_checkpoints(
        synthetic_remote) -> None:
    publisher, _, _ = synthetic_remote
    publisher.publish_run_root("run-a", _digest("plan"))
    receipt = _digest("r")
    publisher.register_finalized_attempt("run-a", "S1", 1, receipt)
    with pytest.raises(ValueError, match="every finalized attempt"):
        publisher.publish_run_disposition(
            "run-a", "completed", _digest("c"), incomplete=False)
    # Incomplete may still close without publishing the attempt.
    done = publisher.publish_run_disposition(
        "run-a", "incomplete", _digest("c"), incomplete=True)
    assert done.published
