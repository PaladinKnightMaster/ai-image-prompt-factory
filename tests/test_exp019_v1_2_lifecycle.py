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
AUTH = {
    "authorization_id": "synthetic-auth-1",
    "authorized_by": "synthetic-owner",
    "procedure": INDETERMINATE_PROCEDURE,
}


def _lifecycle(tmp_path, name="store") -> AttemptLifecycle:
    return AttemptLifecycle(LifecycleStore(tmp_path / name))


def _started(tmp_path, name="store", slot=SLOT) -> AttemptLifecycle:
    life = _lifecycle(tmp_path, name)
    life.plan_slot(slot)
    life.start_invocation(slot)
    return life


def _failed_attempt(life: AttemptLifecycle, slot=SLOT) -> dict:
    life.confirm_no_result(slot, evidence="host_error_recorded")
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
    life.record_external_anchor(SLOT, 1, "a")
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
            authorization={"authorization_id": "x", "authorized_by": "y",
                           "procedure": "some-other-procedure"})
    record = life.finalize_attempt(SLOT, "INDETERMINATE_FINAL",
                                   authorization=AUTH)
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
    life.finalize_attempt(SLOT, "INDETERMINATE_FINAL", authorization=AUTH)


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
        life.confirm_no_result(SLOT, evidence="operator_saw_no_image")
    life.confirm_no_result(SLOT, evidence="host_completed_no_image")
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
    life.finalize_attempt(SLOT_B, "INDETERMINATE_FINAL", authorization=AUTH)
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
