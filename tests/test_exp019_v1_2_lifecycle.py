"""Tests for the EXP-019 v1.2 attempt lifecycle manager (PR-7).

Synthetic fixtures only: synthetic slot identifiers, synthetic bytes, and
temporary local stores. No experimental allocation, run root, host
session, generation, or external checkpoint is involved. The lifecycle
must remain inactive without a registered v1.2 experiment: it registers
nothing and issues no host request.
"""

from __future__ import annotations

import pytest

from aipf import exp019_v1_2_lifecycle as lifecycle_module
from aipf.exp019_protocol import frozen_protocol
from aipf.exp019_v1_2_lifecycle import (
    INDETERMINATE_PROCEDURE,
    MAX_RETRIES,
    AttemptLifecycle,
    AuthorizationError,
    InvalidTransitionError,
    LifecycleStore,
)

SLOT = "ZZZZZZ"
SLOT_B = "YYYYYY"


def _auth(slot=SLOT, attempt=1, **overrides) -> dict:
    """A scope-bound H3 authorization record for one attempt."""
    record = {
        "authorization_id": "synthetic-auth-1",
        "authorized_by": "synthetic-owner",
        "reason": "synthetic unresolved outcome",
        "procedure": INDETERMINATE_PROCEDURE,
        "action": "INDETERMINATE_FINAL",
        "run_id": "synthetic-run",
        "slot_id": slot,
        "attempt_number": attempt,
        "contract_version": "1.2.0",
    }
    record.update(overrides)
    return record


def _verify_anchor(record, anchor_ref) -> bool:
    """Synthetic trusted-verifier stub at the PR-9 boundary.

    Stands in for verification against actual external publication,
    which does not exist in this PR; production configurations without
    a verifier cannot anchor at all.
    """
    return isinstance(anchor_ref, str) and "anchor" in anchor_ref


def _lifecycle(tmp_path, name="store") -> AttemptLifecycle:
    return AttemptLifecycle(LifecycleStore(tmp_path / name),
                            anchor_verifier=_verify_anchor)


def _started(tmp_path, name="store", slot=SLOT) -> AttemptLifecycle:
    life = _lifecycle(tmp_path, name)
    life.plan_slot(slot)
    life.start_invocation(slot)
    return life


def _failed_attempt(life: AttemptLifecycle, slot=SLOT) -> dict:
    life.confirm_no_result(slot, evidence="host_error_recorded",
                           failure_classification="host_technical_error")
    return life.finalize_attempt(slot, "FAILURE")


# =============================================================================
# Ordinary progression and closure levels
# =============================================================================


def test_successful_progression_and_distinct_closures(tmp_path) -> None:
    life = _started(tmp_path)
    digest = life.record_output(SLOT, b"synthetic raster bytes")
    record = life.finalize_attempt(SLOT, "ADMIT")
    assert record["disposition"] == "ADMIT"
    assert record["retained_artifact_sha256"] == digest
    assert record["anchor_state"] == "recorded-unanchored"

    life.record_external_anchor(SLOT, 1, "synthetic-anchor-1")
    life.close_invocation(SLOT)
    assert life.slot_state(SLOT)["state"] == "invocation_closed"
    # Invocation closure is not slot closure, and neither closes a run.
    assert life.run_summary()["run_closed"] is False

    life.close_slot(SLOT)
    assert life.slot_state(SLOT)["state"] == "slot_closed"
    summary = life.close_run()
    assert summary["run_closed"] is True
    assert summary["complete"] is True


def test_slot_closure_does_not_authorize_further_generation(tmp_path) -> None:
    life = _started(tmp_path)
    life.record_output(SLOT, b"bytes")
    life.finalize_attempt(SLOT, "ADMIT")
    life.close_invocation(SLOT)
    life.close_slot(SLOT)
    with pytest.raises(InvalidTransitionError):
        life.start_invocation(SLOT)
    with pytest.raises(InvalidTransitionError):
        life.request_retry(SLOT)


def test_run_cannot_close_with_unclosed_slots(tmp_path) -> None:
    life = _started(tmp_path)
    with pytest.raises(InvalidTransitionError):
        life.close_run()
    assert life.run_summary()["run_closed"] is False


# =============================================================================
# Retry rules
# =============================================================================


def test_valid_technical_retry_progression(tmp_path) -> None:
    life = _started(tmp_path)
    _failed_attempt(life)
    # Blocked until the predecessor terminal record is anchored.
    with pytest.raises(InvalidTransitionError, match="externally anchored"):
        life.request_retry(SLOT)
    life.record_external_anchor(SLOT, 1, "anchor-1")
    state = life.request_retry(SLOT)
    assert state["current_attempt"] == 2
    assert state["attempts"][2]["predecessor_attempt"] == 1

    life.record_output(SLOT, b"second attempt bytes")
    record = life.finalize_attempt(SLOT, "ADMIT")
    assert record["attempt_number"] == 2
    assert record["predecessor_attempt"] == 1


def test_retry_budget_is_frozen_at_two(tmp_path) -> None:
    assert MAX_RETRIES == 2
    life = _started(tmp_path)
    for attempt in (1, 2, 3):
        _failed_attempt(life)
        life.record_external_anchor(SLOT, attempt, f"anchor-{attempt}")
        if attempt < 3:
            life.request_retry(SLOT)
    with pytest.raises(InvalidTransitionError, match="exhausted"):
        life.request_retry(SLOT)
    state = life.slot_state(SLOT)
    assert sorted(state["attempts"]) == [1, 2, 3]  # monotonic, in order
    # Exhausted without admission: closable, but the run is incomplete.
    life.close_invocation(SLOT)
    life.close_slot(SLOT)
    assert life.close_run()["complete"] is False


def test_no_retry_after_admit_or_indeterminate(tmp_path) -> None:
    life = _started(tmp_path)
    life.record_output(SLOT, b"bytes")
    life.finalize_attempt(SLOT, "ADMIT")
    life.record_external_anchor(SLOT, 1, "anchor-a")
    with pytest.raises(InvalidTransitionError, match="only after"):
        life.request_retry(SLOT)


def test_no_replacement_of_evaluable_image(tmp_path) -> None:
    """A returned evaluable artifact cannot be regenerated away."""
    life = _started(tmp_path)
    life.record_output(SLOT, b"evaluable bytes", technically_evaluable=True)
    with pytest.raises(InvalidTransitionError):
        life.finalize_attempt(SLOT, "FAILURE")
    with pytest.raises(InvalidTransitionError):
        life.request_retry(SLOT)


# =============================================================================
# Unknown outcomes, PENDING_UNKNOWN, and indeterminate closure
# =============================================================================


def test_unknown_outcome_stays_pending_and_blocks_retry_and_closure(
        tmp_path) -> None:
    life = _started(tmp_path)
    life.mark_pending_unknown(SLOT, reason="synthetic interruption")
    state = life.slot_state(SLOT)
    assert state["attempts"][1]["state"] == "PENDING_UNKNOWN"
    assert life.run_summary()["pending_unknown_attempts"] == 1
    with pytest.raises(InvalidTransitionError):
        life.request_retry(SLOT)
    with pytest.raises(InvalidTransitionError):
        life.close_invocation(SLOT)
    with pytest.raises(InvalidTransitionError):
        life.finalize_attempt(SLOT, "FAILURE")


def test_indeterminate_closure_requires_h3_authorization(tmp_path) -> None:
    life = _started(tmp_path)
    life.mark_pending_unknown(SLOT)
    with pytest.raises(AuthorizationError):
        life.finalize_attempt(SLOT, "INDETERMINATE_FINAL")
    with pytest.raises(AuthorizationError):
        life.finalize_attempt(
            SLOT, "INDETERMINATE_FINAL",
            authorization=_auth(procedure="some-other-procedure"))
    # Scope binding: another slot, attempt, run, action, or contract
    # version is not authorization for this attempt.
    for overrides in ({"slot_id": SLOT_B}, {"attempt_number": 2},
                      {"run_id": "another-run"}, {"action": "ADMIT"},
                      {"contract_version": "9.9.9"}, {"reason": ""}):
        with pytest.raises(AuthorizationError):
            life.finalize_attempt(SLOT, "INDETERMINATE_FINAL",
                                  authorization=_auth(**overrides))
    record = life.finalize_attempt(SLOT, "INDETERMINATE_FINAL",
                                   authorization=_auth())
    assert record["disposition"] == "INDETERMINATE_FINAL"
    life.close_invocation(SLOT)
    life.close_slot(SLOT)
    # An indeterminate slot is accounted for, and the run is incomplete.
    summary = life.close_run()
    assert summary["terminal_dispositions"] == ["INDETERMINATE_FINAL"]
    assert summary["complete"] is False


def test_contract_violation_goes_to_pending_review_then_indeterminate(
        tmp_path) -> None:
    life = _started(tmp_path)
    life.record_output(SLOT, b"violating bytes")
    life.record_contract_violation(SLOT, detail="synthetic violation")
    assert life.slot_state(SLOT)["attempts"][1]["state"] == \
        "indeterminate_pending_review"
    # The artifact is preserved, never silently replaced by a retry.
    with pytest.raises(InvalidTransitionError):
        life.request_retry(SLOT)
    life.finalize_attempt(SLOT, "INDETERMINATE_FINAL",
                          authorization=_auth())


# =============================================================================
# Retained-output resumption and recovery
# =============================================================================


def test_retained_output_resumption_uses_the_same_attempt(tmp_path) -> None:
    life = _started(tmp_path)
    digest = life.record_output(SLOT, b"retained bytes")

    reloaded = AttemptLifecycle(life.store)  # state rebuilt from events
    assert reloaded.resume_invocation(SLOT) == 1
    state = reloaded.slot_state(SLOT)
    assert state["current_attempt"] == 1
    assert sorted(state["attempts"]) == [1]  # no new attempt was opened
    record = reloaded.finalize_attempt(SLOT, "ADMIT")
    assert record["retained_artifact_sha256"] == digest


def test_resumption_without_retained_output_is_rejected(tmp_path) -> None:
    life = _started(tmp_path)
    with pytest.raises(InvalidTransitionError, match="retained output"):
        life.resume_invocation(SLOT)


def test_interrupted_write_leaves_no_event_and_no_duplicate(tmp_path) -> None:
    life = _started(tmp_path)
    events_before = len(life.store.events)
    # Simulate a torn write: a staged file that was never renamed.
    debris = life.store.staging_dir / "torn-write.json.tmp"
    debris.write_bytes(b'{"type": "attempt_terminal", "slot_id": "ZZ')
    life.store.recover()
    assert len(life.store.events) == events_before
    assert not debris.exists()

    reloaded = AttemptLifecycle(life.store)
    reloaded.record_output(SLOT, b"bytes")
    record = reloaded.finalize_attempt(SLOT, "ADMIT")
    again = reloaded.finalize_attempt(SLOT, "ADMIT")
    assert again == record  # repeated finalization: same record, no dup
    terminal_events = [e for e in reloaded.store.events
                       if e["type"] == "attempt_terminal"]
    assert len(terminal_events) == 1


def test_repeated_finalization_with_different_disposition_raises(
        tmp_path) -> None:
    life = _started(tmp_path)
    _failed_attempt(life)
    with pytest.raises(InvalidTransitionError, match="already terminal"):
        life.finalize_attempt(SLOT, "ADMIT")


def test_orphaned_output_bytes_are_never_accepted(tmp_path) -> None:
    life = _started(tmp_path)
    # Bytes committed to the output store outside any lifecycle event.
    orphan_digest = life.store.retain_output(b"orphan bytes")
    assert life.store.orphaned_outputs() == (orphan_digest,)
    # An orphan alone cannot support ADMIT for an open attempt.
    with pytest.raises(InvalidTransitionError):
        life.finalize_attempt(SLOT, "ADMIT")
    life.record_evidence_returned(SLOT, orphan_digest)
    assert life.store.orphaned_outputs() == ()
    life.finalize_attempt(SLOT, "ADMIT")


def test_anchor_is_exactly_once(tmp_path) -> None:
    life = _started(tmp_path)
    _failed_attempt(life)
    life.record_external_anchor(SLOT, 1, "anchor-1")
    again = life.record_external_anchor(SLOT, 1, "anchor-1")
    assert again["anchor_state"] == "externally-anchored"
    with pytest.raises(InvalidTransitionError, match="never anchored twice"):
        life.record_external_anchor(SLOT, 1, "anchor-2")
    anchor_events = [e for e in life.store.events
                     if e["type"] == "external_anchor_recorded"]
    assert len(anchor_events) == 1


# =============================================================================
# Invalid transitions and evidence rules
# =============================================================================


def test_admit_requires_evaluable_retained_output(tmp_path) -> None:
    life = _started(tmp_path)
    with pytest.raises(InvalidTransitionError):
        life.finalize_attempt(SLOT, "ADMIT")
    life.record_output(SLOT, b"not evaluable", technically_evaluable=False)
    with pytest.raises(InvalidTransitionError, match="technically evaluable"):
        life.finalize_attempt(SLOT, "ADMIT")


def test_failure_requires_affirmative_no_result_evidence(tmp_path) -> None:
    life = _started(tmp_path)
    with pytest.raises(InvalidTransitionError):
        life.finalize_attempt(SLOT, "FAILURE")
    # An operator statement that no image was seen is not affirmative.
    with pytest.raises(InvalidTransitionError, match="affirmative"):
        life.confirm_no_result(
            SLOT, evidence="operator_saw_no_image",
            failure_classification="host_technical_error")
    with pytest.raises(InvalidTransitionError, match="classification"):
        life.confirm_no_result(
            SLOT, evidence="host_completed_no_image",
            failure_classification="something_unclassified")
    life.confirm_no_result(SLOT, evidence="host_completed_no_image",
                           failure_classification="host_technical_error")
    assert life.finalize_attempt(SLOT, "FAILURE")["disposition"] == "FAILURE"


def test_invalid_transitions_from_planned_state(tmp_path) -> None:
    life = _lifecycle(tmp_path)
    life.plan_slot(SLOT)
    with pytest.raises(InvalidTransitionError):
        life.record_output(SLOT, b"bytes")
    with pytest.raises(InvalidTransitionError):
        life.close_slot(SLOT)
    life.start_invocation(SLOT)
    with pytest.raises(InvalidTransitionError):
        life.start_invocation(SLOT)
    with pytest.raises(InvalidTransitionError):
        life.finalize_attempt(SLOT, "NOT_A_DISPOSITION")


def test_multiple_slots_close_independently_and_run_accounts_for_all(
        tmp_path) -> None:
    life = _lifecycle(tmp_path)
    for slot in (SLOT, SLOT_B):
        life.plan_slot(slot)
        life.start_invocation(slot)
    life.record_output(SLOT, b"a")
    life.finalize_attempt(SLOT, "ADMIT")
    life.close_invocation(SLOT)
    life.close_slot(SLOT)
    with pytest.raises(InvalidTransitionError):
        life.close_run()  # second slot still unresolved
    life.mark_pending_unknown(SLOT_B)
    life.finalize_attempt(SLOT_B, "INDETERMINATE_FINAL",
                          authorization=_auth(slot=SLOT_B))
    life.close_invocation(SLOT_B)
    life.close_slot(SLOT_B)
    summary = life.close_run()
    assert summary["complete"] is False
    assert sorted(summary["terminal_dispositions"]) == [
        "ADMIT", "INDETERMINATE_FINAL"]
    # Exactly one run closure; repetition returns the same summary.
    assert life.close_run() == summary
    run_events = [e for e in life.store.events if e["type"] == "run_closed"]
    assert len(run_events) == 1


# =============================================================================
# Technical-failure classification, anchoring proof, and crash recovery
# =============================================================================


def test_safety_refusal_failure_never_authorizes_retry(tmp_path) -> None:
    life = _started(tmp_path)
    life.confirm_no_result(SLOT, evidence="safety_refusal_recorded",
                           failure_classification="safety_refusal")
    record = life.finalize_attempt(SLOT, "FAILURE")
    assert record["failure_classification"] == "safety_refusal"
    life.record_external_anchor(SLOT, 1, "anchor-1")
    with pytest.raises(InvalidTransitionError, match="technical"):
        life.request_retry(SLOT)


def test_anchoring_blocked_without_trusted_verifier(tmp_path) -> None:
    """Production advancement stays blocked: no verifier, no anchor."""
    life = AttemptLifecycle(LifecycleStore(tmp_path / "plain"))
    life.plan_slot(SLOT)
    life.start_invocation(SLOT)
    life.confirm_no_result(SLOT, evidence="host_error_recorded",
                           failure_classification="host_technical_error")
    life.finalize_attempt(SLOT, "FAILURE")
    with pytest.raises(AuthorizationError, match="cannot be verified"):
        life.record_external_anchor(SLOT, 1, "claimed-anchor")
    with pytest.raises(InvalidTransitionError, match="externally anchored"):
        life.request_retry(SLOT)
    assert life.external_anchor_pending() == (
        {"slot_id": SLOT, "attempt_number": 1, "disposition": "FAILURE"},)


def test_forged_anchor_reference_is_rejected(tmp_path) -> None:
    life = _started(tmp_path)
    _failed_attempt(life)
    with pytest.raises(AuthorizationError, match="not verified"):
        life.record_external_anchor(SLOT, 1, "forged-ref")
    assert life.slot_state(SLOT)["attempts"][1]["anchor_state"] == \
        "recorded-unanchored"


def test_indeterminate_closure_preserves_retained_output(tmp_path) -> None:
    life = _started(tmp_path)
    digest = life.record_output(SLOT, b"preserved bytes")
    life.record_contract_violation(SLOT, detail="synthetic")
    record = life.finalize_attempt(SLOT, "INDETERMINATE_FINAL",
                                   authorization=_auth())
    # Retained output is bound into the record, never discarded, and an
    # indeterminate closure is not an admission or a retry grant.
    assert record["retained_artifact_sha256"] == digest
    assert life.store.read_output(digest) == b"preserved bytes"
    with pytest.raises(InvalidTransitionError):
        life.request_retry(SLOT)
    assert life.slot_state(SLOT)["state"] == "invocation_started"


def test_crash_at_terminal_write_boundary_recovers_without_duplicate(
        tmp_path, monkeypatch) -> None:
    life = _started(tmp_path)
    life.record_output(SLOT, b"bytes")
    real_replace = lifecycle_module.os.replace

    def exploding_replace(src, dst):
        raise OSError("synthetic crash at commit boundary")

    monkeypatch.setattr(lifecycle_module.os, "replace", exploding_replace)
    with pytest.raises(OSError):
        life.finalize_attempt(SLOT, "ADMIT")
    monkeypatch.setattr(lifecycle_module.os, "replace", real_replace)

    reloaded = AttemptLifecycle(life.store)  # recover() already ran
    assert reloaded.slot_state(SLOT)["attempts"][1]["disposition"] is None
    record = reloaded.finalize_attempt(SLOT, "ADMIT")
    assert reloaded.finalize_attempt(SLOT, "ADMIT") == record
    terminal = [e for e in reloaded.store.events
                if e["type"] == "attempt_terminal"]
    assert len(terminal) == 1


def test_crash_at_invocation_start_leaves_no_duplicate(tmp_path,
                                                       monkeypatch) -> None:
    life = _lifecycle(tmp_path)
    life.plan_slot(SLOT)
    monkeypatch.setattr(
        lifecycle_module.os, "replace",
        lambda src, dst: (_ for _ in ()).throw(
            OSError("synthetic crash")))
    with pytest.raises(OSError):
        life.start_invocation(SLOT)
    monkeypatch.undo()

    reloaded = AttemptLifecycle(life.store)
    reloaded.start_invocation(SLOT)
    with pytest.raises(InvalidTransitionError):
        reloaded.start_invocation(SLOT)
    started = [e for e in reloaded.store.events
               if e["type"] == "invocation_started"]
    assert len(started) == 1


def test_recovery_fails_closed_on_corrupt_event_sequence(tmp_path) -> None:
    store = LifecycleStore(tmp_path / "corrupt")
    store.events_dir.joinpath("fake.json").write_text(
        '{"type": "slot_planned", "slot_id": "ZZZZZZ", "seq": 42, '
        '"event_id": "fake"}', encoding="utf-8")
    with pytest.raises(InvalidTransitionError, match="contiguous"):
        LifecycleStore(tmp_path / "corrupt")


def test_pending_unknown_cannot_be_relabelled_technical_failure(
        tmp_path) -> None:
    life = _started(tmp_path)
    life.mark_pending_unknown(SLOT)
    with pytest.raises(InvalidTransitionError):
        life.confirm_no_result(SLOT, evidence="host_error_recorded",
                               failure_classification="host_technical_error")


def test_exception_output_does_not_echo_identifiers(tmp_path) -> None:
    life = _lifecycle(tmp_path)
    with pytest.raises(InvalidTransitionError) as excinfo:
        life.slot_state("SECRET1")
    assert "SECRET1" not in str(excinfo.value)


# =============================================================================
# Activation lockout: PR-7 remains inactive without registered v1.2
# =============================================================================


def test_lifecycle_remains_inactive_without_registered_v1_2(tmp_path) -> None:
    public = {n for n in vars(lifecycle_module) if not n.startswith("_")}
    assert not {"generate", "generate_image", "allocate", "create_run",
                "commit_checkpoint", "reveal"} & public
    with pytest.raises(ValueError,
                       match="unknown EXP-019 frozen protocol version"):
        frozen_protocol("1.2.0")
    # The lifecycle operates only on an explicitly supplied synthetic
    # local store; it creates no run root and issues no host request.
    life = _started(tmp_path)
    assert (tmp_path / "store" / "events").is_dir()
    assert life.run_summary()["run_closed"] is False
