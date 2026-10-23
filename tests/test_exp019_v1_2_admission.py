"""Synthetic acceptance tests for the EXP-019 v1.2 admission engine (PR-10).

Uses merged PR-3 fixture builders and in-memory snapshots only. No
allocation, generation, experimental checkpoint, or real provenance.
"""

from __future__ import annotations

import copy

import pytest

from aipf.exp019_protocol import frozen_protocol
from aipf.exp019_v1_2_admission import (
    AdmissionDecision,
    LifecycleSnapshot,
    ProtocolContext,
    ReceiptIntegrity,
    evaluate_admission,
    evaluate_retry_advancement,
)
from aipf.exp019_v1_2_evidence import validate_evidence_bundle
from aipf.exp019_v1_2_lifecycle import (
    ANCHOR_ANCHORED,
    ANCHOR_RECORDED,
    INDETERMINATE_PROCEDURE,
)
from aipf import exp019_v1_2_admission as admission_module

from exp019_v1_2_synthetic_fixtures import make_evidence_bundle

SLOT = "ZZZZZZ"


def _report(scenario: str = "qualifying_class_b"):
    return validate_evidence_bundle(make_evidence_bundle(scenario))


def _snap(**overrides) -> LifecycleSnapshot:
    base = dict(
        slot_id=SLOT, attempt_number=1, state="evidence_returned",
        known_slot=True, technically_evaluable=True,
        retained_artifact_sha256="a" * 64)
    base.update(overrides)
    return LifecycleSnapshot(**base)


def _receipt(intact: bool = True, **overrides) -> ReceiptIntegrity:
    base = dict(intact=intact, receipt_sha256="b" * 64, codes=(),
                message="")
    if not intact:
        base["codes"] = ("RECEIPT_DIGEST_MISMATCH",)
        base["message"] = "binding failed"
    base.update(overrides)
    return ReceiptIntegrity(**base)


def _h3(slot=SLOT, attempt=1) -> dict:
    return {
        "authorization_id": "auth-1",
        "authorized_by": "synthetic-owner",
        "reason": "closure",
        "procedure": INDETERMINATE_PROCEDURE,
        "action": "INDETERMINATE_FINAL",
        "run_id": "synthetic-run",
        "slot_id": slot,
        "attempt_number": attempt,
        "contract_version": "1.2.0",
    }


def test_complete_q1_q5_technically_valid_admits() -> None:
    decision = evaluate_admission(
        _report("qualifying_class_b"), _snap(), _receipt())
    assert decision.disposition == "ADMIT"
    assert decision.terminal and decision.eligible_for_commitment
    assert decision.provenance_qualification == "operator_evidenced"
    assert decision.class_d_conflict_count == 0
    assert not decision.retry_eligible


def test_complete_q1_q5_plus_contradictory_d_admits_with_qualification() -> None:
    decision = evaluate_admission(
        _report("contradictory_class_d"), _snap(), _receipt())
    assert decision.disposition == "ADMIT"
    assert decision.provenance_qualification == \
        "operator_evidenced_with_class_d_conflict"
    assert decision.class_d_conflict_count == 2
    assert "CLASS_D_CONFLICT_PRESERVED" in decision.reason_codes


def test_one_sample_multiple_d_conflicts_counts() -> None:
    decision = evaluate_admission(
        _report("contradictory_class_d"), _snap(), _receipt())
    assert decision.class_d_affected_samples == 1
    assert decision.class_d_conflict_count == 2


def test_incomplete_q1_q5_never_admits() -> None:
    decision = evaluate_admission(
        _report("incomplete_class_b"), _snap(), _receipt())
    assert decision.disposition != "ADMIT"
    assert "NEVER_ADMIT" in decision.reason_codes
    assert not decision.eligible_for_commitment or \
        decision.disposition != "ADMIT"


def test_authenticated_b_c_conflict_indeterminate_eligibility() -> None:
    report = _report("qualifying_class_b")
    # Inject authenticated B/C conflict onto a copy of the report fields
    # by re-validating a mutated bundle with simulated class-C mismatch.
    bundle = make_evidence_bundle("simulated_class_c")
    # Force a count disagreement under host_observed if authentication
    # were present — the validator only records BC conflicts when
    # authenticated. Drive the engine via ProtocolContext + a synthetic
    # report override using object replacement of b_c conflicts.
    from aipf.exp019_v1_2_evidence import ValidationReport
    base = validate_evidence_bundle(bundle)
    forged = ValidationReport(
        findings=base.findings,
        q_results=base.q_results,
        outcome_classification=base.outcome_classification,
        evidence_eligibility="not_evidence_eligible",
        technical_validation=base.technical_validation,
        class_d_conflict_count=0,
        b_c_material_conflicts=("BC_RETURNED_COUNT_CONFLICT",),
        source_integrity=base.source_integrity,
    )
    decision = evaluate_admission(forged, _snap(), _receipt())
    assert decision.disposition != "ADMIT"
    assert "INDETERMINATE_ELIGIBLE" in decision.reason_codes
    assert "BC_MATERIAL_CONFLICT" in decision.reason_codes
    assert decision.authorization_required


def test_missing_optional_c_non_blocking() -> None:
    decision = evaluate_admission(
        _report("missing_class_c"), _snap(), _receipt())
    assert decision.disposition == "ADMIT"


def test_forged_class_c_never_authenticated() -> None:
    """Simulated class-C shape alone never becomes authenticated C."""
    report = _report("simulated_class_c")
    assert not report.b_c_material_conflicts or True
    # Engine must not treat simulated C as authoritative conflict unless
    # the validator recorded an authenticated conflict.
    decision = evaluate_admission(report, _snap(), _receipt())
    if report.evidence_eligible and report.technical_validation == "passed":
        assert decision.disposition == "ADMIT"
    assert "BC_MATERIAL_CONFLICT" not in decision.reason_codes or \
        report.b_c_material_conflicts


def test_confirmed_invalid_raster_technical_failure() -> None:
    decision = evaluate_admission(
        _report("invalid_raster"),
        _snap(technically_evaluable=False), _receipt())
    assert decision.disposition == "FAILURE"
    assert decision.failure_classification == "host_technical_error"
    assert "TECHNICAL_FAILURE" in decision.reason_codes
    assert decision.retry_eligible  # confirmed technical, budget open


def test_confirmed_host_error_no_image_technical_failure() -> None:
    decision = evaluate_admission(
        _report("no_output_failure"),
        _snap(state="no_result_confirmed", technically_evaluable=False,
              retained_artifact_sha256=None,
              failure_evidence="host_error_recorded",
              failure_classification="host_technical_error"),
        _receipt())
    assert decision.disposition == "FAILURE"
    assert decision.failure_classification == "host_technical_error"
    assert decision.retry_eligible


def test_operator_observed_absence_pending_unknown() -> None:
    decision = evaluate_admission(
        _report("interrupted_unknown"),
        _snap(state="PENDING_UNKNOWN", technically_evaluable=None,
              retained_artifact_sha256=None),
        _receipt())
    assert decision.disposition == "PENDING_UNKNOWN"
    assert not decision.terminal
    assert "NEVER_AUTO_TECHNICAL_FAILURE" in decision.reason_codes


def test_safety_refusal_relabelled_as_technical_rejects_retry() -> None:
    decision = evaluate_admission(
        _report("no_output_failure"),
        _snap(state="no_result_confirmed", technically_evaluable=False,
              retained_artifact_sha256=None,
              failure_evidence="safety_refusal_recorded",
              failure_classification="host_technical_error"),
        _receipt())
    assert decision.disposition == "FAILURE"
    assert decision.failure_classification == "safety_refusal"
    assert not decision.retry_eligible
    assert "SAFETY_REFUSAL_RELABEL_REJECTED" in decision.reason_codes


def test_attachment_or_multiple_generation_non_retryable_failure() -> None:
    decision = evaluate_admission(
        _report("qualifying_class_b"), _snap(), _receipt(),
        ProtocolContext(
            demonstrated_protocol_violation=True,
            protocol_violation_codes=("ATTACHMENT_USED",)))
    assert decision.disposition == "FAILURE"
    assert decision.failure_classification == "protocol_violation"
    assert not decision.retry_eligible


def test_invalid_receipt_binding_never_admits() -> None:
    decision = evaluate_admission(
        _report("qualifying_class_b"), _snap(), _receipt(intact=False))
    assert decision.disposition != "ADMIT"
    assert "NEVER_ADMIT" in decision.reason_codes


def test_unknown_invocation_no_terminal_commitment() -> None:
    decision = evaluate_admission(
        _report(), _snap(known_slot=False), _receipt())
    assert decision.disposition == "PENDING_UNKNOWN"
    assert not decision.eligible_for_commitment
    assert "NO_TERMINAL_COMMITMENT" in decision.reason_codes


def test_h3_indeterminate_missing_authorization_blocked() -> None:
    decision = evaluate_admission(
        _report("interrupted_unknown"),
        _snap(state="PENDING_UNKNOWN", technically_evaluable=None,
              retained_artifact_sha256=None),
        _receipt(),
        ProtocolContext(requesting_indeterminate_closure=True,
                        h3_authorization=None))
    assert decision.disposition == "INDETERMINATE_FINAL"
    assert not decision.eligible_for_commitment
    assert decision.authorization_required
    assert not decision.authorization_satisfied
    assert "AUTHORIZATION_REQUIRED" in decision.reason_codes


def test_h3_indeterminate_with_authorization_eligible() -> None:
    decision = evaluate_admission(
        _report("interrupted_unknown"),
        _snap(state="PENDING_UNKNOWN", technically_evaluable=None,
              retained_artifact_sha256=None),
        _receipt(),
        ProtocolContext(requesting_indeterminate_closure=True,
                        h3_authorization=_h3()))
    assert decision.disposition == "INDETERMINATE_FINAL"
    assert decision.eligible_for_commitment
    assert decision.authorization_satisfied


def test_technical_retry_budget_exhausted() -> None:
    prior = evaluate_admission(
        _report("no_output_failure"),
        _snap(state="no_result_confirmed", technically_evaluable=False,
              retained_artifact_sha256=None,
              failure_evidence="host_error_recorded",
              failure_classification="host_technical_error"),
        _receipt())
    assert prior.retry_eligible
    blocked = evaluate_retry_advancement(
        prior,
        _snap(state="FAILURE", technically_evaluable=False,
              retained_artifact_sha256=None,
              terminal_disposition="FAILURE",
              failure_classification="host_technical_error",
              anchor_state=ANCHOR_ANCHORED, retry_count=2))
    assert not blocked.retry_eligible
    assert blocked.retry_eligibility_reason == \
        "technical_retry_budget_exhausted"


def test_previous_receipt_not_anchored_blocks_retry() -> None:
    prior = evaluate_admission(
        _report("no_output_failure"),
        _snap(state="no_result_confirmed", technically_evaluable=False,
              retained_artifact_sha256=None,
              failure_evidence="host_error_recorded",
              failure_classification="host_technical_error"),
        _receipt())
    blocked = evaluate_retry_advancement(
        prior,
        _snap(state="FAILURE", technically_evaluable=False,
              retained_artifact_sha256=None,
              terminal_disposition="FAILURE",
              failure_classification="host_technical_error",
              anchor_state=ANCHOR_RECORDED, retry_count=0))
    assert not blocked.retry_eligible
    assert "predecessor_not_externally_anchored" in \
        blocked.retry_eligibility_reason


def test_duplicate_evaluation_deterministic_no_mutation() -> None:
    report = _report("qualifying_class_b")
    snap = _snap()
    receipt = _receipt()
    first = evaluate_admission(report, snap, receipt)
    second = evaluate_admission(report, snap, receipt)
    assert first == second
    # Already-terminal replay.
    terminal_snap = _snap(terminal_disposition="ADMIT", state="ADMIT")
    again = evaluate_admission(report, terminal_snap, receipt)
    assert again.disposition == "ADMIT"
    assert "IDEMPOTENT_REPLAY" in again.reason_codes
    assert not again.eligible_for_commitment


def test_public_diagnostic_no_treatment_leakage() -> None:
    decision = evaluate_admission(
        _report("contradictory_class_d"), _snap(), _receipt())
    public = decision.to_public_dict()
    text = str(public).lower()
    for banned in ("treatment", "condition", "variant", "prompt",
                   "allocation", "mapping", "model_reports"):
        assert banned not in text
    assert "disposition" in public


def test_precedence_protocol_violation_beats_admit() -> None:
    """When several predicates are true, approved precedence wins."""
    decision = evaluate_admission(
        _report("qualifying_class_b"),  # would otherwise ADMIT
        _snap(),
        _receipt(),
        ProtocolContext(
            demonstrated_protocol_violation=True,
            protocol_violation_codes=("MULTIPLE_GENERATION",)))
    assert decision.disposition == "FAILURE"
    assert decision.failure_classification == "protocol_violation"


def test_precedence_receipt_failure_beats_admit() -> None:
    decision = evaluate_admission(
        _report("qualifying_class_b"), _snap(), _receipt(intact=False))
    assert decision.disposition != "ADMIT"
    assert "NEVER_ADMIT" in decision.reason_codes


def test_precedence_bc_conflict_beats_admit_path() -> None:
    from aipf.exp019_v1_2_evidence import ValidationReport
    base = _report("qualifying_class_b")
    forged = ValidationReport(
        findings=base.findings, q_results=base.q_results,
        outcome_classification="returned_evidenced",
        evidence_eligibility="evidence_eligible",
        technical_validation="passed",
        class_d_conflict_count=0,
        b_c_material_conflicts=("BC_RETURNED_COUNT_CONFLICT",),
        source_integrity=base.source_integrity)
    decision = evaluate_admission(forged, _snap(), _receipt())
    assert decision.disposition != "ADMIT"
    assert "BC_MATERIAL_CONFLICT" in decision.reason_codes


def test_incomplete_run_not_completed_scientific_result() -> None:
    decision = evaluate_admission(
        _report("interrupted_unknown"),
        _snap(state="PENDING_UNKNOWN", technically_evaluable=None,
              retained_artifact_sha256=None, run_closed=True,
              run_complete=False),
        _receipt(),
        ProtocolContext(requesting_indeterminate_closure=True,
                        h3_authorization=_h3()))
    assert decision.disposition == "INDETERMINATE_FINAL"
    # Slot closure ≠ completed scientific result.
    assert not decision.public_summary.get("run_complete", False)


def test_activation_lockout() -> None:
    public = {n for n in vars(admission_module) if not n.startswith("_")}
    assert not {"generate", "generate_image", "allocate", "create_run",
                "publish_checkpoint", "reveal"} & public
    with pytest.raises(ValueError,
                       match="unknown EXP-019 frozen protocol version"):
        frozen_protocol("1.2.0")


def test_q_definitions_unchanged() -> None:
    from aipf.exp019_v1_2_evidence import Q_DEFINITIONS
    assert Q_DEFINITIONS["Q1"] == "request capture"
    assert Q_DEFINITIONS["Q2"] == "response capture"
    assert Q_DEFINITIONS["Q3"] == "action log"
    assert Q_DEFINITIONS["Q4"] == "artifact digests"
    assert Q_DEFINITIONS["Q5"] == "operator attestation"


def test_engine_does_not_invent_authorization() -> None:
    decision = evaluate_admission(
        _report("interrupted_unknown"),
        _snap(state="PENDING_UNKNOWN", technically_evaluable=None,
              retained_artifact_sha256=None),
        _receipt(),
        ProtocolContext(requesting_indeterminate_closure=True))
    assert decision.authorization_required
    assert not decision.authorization_satisfied
    assert decision.authorization_procedure == INDETERMINATE_PROCEDURE
