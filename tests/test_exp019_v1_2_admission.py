"""Synthetic acceptance tests for the EXP-019 v1.2 admission engine (PR-10).

Uses merged PR-3 fixture builders and in-memory snapshots only. No
allocation, generation, experimental checkpoint, or real provenance.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from aipf.exp019_protocol import frozen_protocol
from aipf.exp019_v1_2_admission import (
    LifecycleSnapshot,
    ProtocolContext,
    ReceiptIntegrity,
    evaluate_admission,
    evaluate_retry_advancement,
)
from aipf.exp019_v1_2_checkpoints import VerificationResult
from aipf.exp019_v1_2_evidence import ValidationReport, validate_evidence_bundle
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


def _prospective() -> ReceiptIntegrity:
    return ReceiptIntegrity.prospective()


def _verified(digest: str = "b" * 64) -> ReceiptIntegrity:
    return ReceiptIntegrity.verified(digest)


def _anchor_ok() -> VerificationResult:
    return VerificationResult(
        verified=True, head_commit="c" * 40,
        evidence_sha256="d" * 64, codes=(),
        message="verified", factual_claim_proven=False)


def _anchor_fail() -> VerificationResult:
    return VerificationResult(
        verified=False, head_commit=None, evidence_sha256=None,
        codes=("HEAD_MISMATCH",), message="not verified")


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


# =============================================================================
# A1 — Prospective vs retrospective integrity
# =============================================================================


def test_prospective_admit_without_terminal_receipt() -> None:
    """First-attempt ADMIT must not require a receipt not yet constructed."""
    decision = evaluate_admission(
        _report("qualifying_class_b"), _snap(), _prospective())
    assert decision.disposition == "ADMIT"
    assert decision.eligible_for_commitment
    assert _prospective().receipt_present is False


def test_prospective_cannot_claim_placeholder_intact_bypass() -> None:
    """A retrospective 'intact' without a present receipt fails closed."""
    bogus = ReceiptIntegrity.missing_when_required()
    decision = evaluate_admission(
        _report("qualifying_class_b"), _snap(), bogus)
    assert decision.disposition != "ADMIT"
    assert "NEVER_ADMIT" in decision.reason_codes


def test_retrospective_failed_receipt_never_admits() -> None:
    decision = evaluate_admission(
        _report("qualifying_class_b"), _snap(),
        ReceiptIntegrity.failed("RECEIPT_DIGEST_MISMATCH"))
    assert decision.disposition != "ADMIT"
    assert "NEVER_ADMIT" in decision.reason_codes


def test_already_terminal_requires_verified_receipt() -> None:
    decision = evaluate_admission(
        _report("qualifying_class_b"),
        _snap(terminal_disposition="ADMIT", state="ADMIT"),
        _prospective())
    assert decision.disposition != "ADMIT" or \
        "NEVER_ADMIT" in decision.reason_codes
    assert "RECEIPT_STAGE_MISMATCH" in decision.reason_codes or \
        "NEVER_ADMIT" in decision.reason_codes


def test_already_terminal_missing_receipt_never_valid() -> None:
    decision = evaluate_admission(
        _report("qualifying_class_b"),
        _snap(terminal_disposition="ADMIT", state="ADMIT"),
        ReceiptIntegrity.missing_when_required())
    assert "NEVER_ADMIT" in decision.reason_codes
    assert "IDEMPOTENT_REPLAY" not in decision.reason_codes


def test_already_terminal_with_verified_receipt_replays() -> None:
    decision = evaluate_admission(
        _report("qualifying_class_b"),
        _snap(terminal_disposition="ADMIT", state="ADMIT"),
        _verified())
    assert decision.disposition == "ADMIT"
    assert "IDEMPOTENT_REPLAY" in decision.reason_codes
    assert not decision.eligible_for_commitment


def test_complete_q1_q5_technically_valid_admits() -> None:
    decision = evaluate_admission(
        _report("qualifying_class_b"), _snap(), _prospective())
    assert decision.disposition == "ADMIT"
    assert decision.terminal and decision.eligible_for_commitment
    assert decision.provenance_qualification == "operator_evidenced"
    assert decision.class_d_conflict_count == 0
    assert not decision.retry_eligible


def test_complete_q1_q5_plus_contradictory_d_admits_with_qualification() -> None:
    decision = evaluate_admission(
        _report("contradictory_class_d"), _snap(), _prospective())
    assert decision.disposition == "ADMIT"
    assert decision.provenance_qualification == \
        "operator_evidenced_with_class_d_conflict"
    assert decision.class_d_conflict_count == 2
    assert "CLASS_D_CONFLICT_PRESERVED" in decision.reason_codes


def test_one_sample_multiple_d_conflicts_counts() -> None:
    decision = evaluate_admission(
        _report("contradictory_class_d"), _snap(), _prospective())
    assert decision.class_d_affected_samples == 1
    assert decision.class_d_conflict_count == 2


def test_incomplete_q1_q5_never_admits() -> None:
    decision = evaluate_admission(
        _report("incomplete_class_b"), _snap(), _prospective())
    assert decision.disposition != "ADMIT"
    assert "NEVER_ADMIT" in decision.reason_codes


def test_authenticated_b_c_conflict_indeterminate_eligibility() -> None:
    bundle = make_evidence_bundle("simulated_class_c")
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
    decision = evaluate_admission(forged, _snap(), _prospective())
    assert decision.disposition != "ADMIT"
    assert "INDETERMINATE_ELIGIBLE" in decision.reason_codes
    assert "BC_MATERIAL_CONFLICT" in decision.reason_codes
    assert decision.authorization_required


def test_missing_optional_c_non_blocking() -> None:
    decision = evaluate_admission(
        _report("missing_class_c"), _snap(), _prospective())
    assert decision.disposition == "ADMIT"


def test_forged_class_c_never_authenticated() -> None:
    report = _report("simulated_class_c")
    decision = evaluate_admission(report, _snap(), _prospective())
    if report.evidence_eligible and report.technical_validation == "passed":
        assert decision.disposition == "ADMIT"
    assert "BC_MATERIAL_CONFLICT" not in decision.reason_codes or \
        report.b_c_material_conflicts


def test_confirmed_invalid_raster_technical_failure() -> None:
    decision = evaluate_admission(
        _report("invalid_raster"),
        _snap(technically_evaluable=False), _prospective())
    assert decision.disposition == "FAILURE"
    assert decision.failure_classification == "host_technical_error"
    assert "TECHNICAL_FAILURE" in decision.reason_codes
    assert decision.retry_eligible


def test_confirmed_host_error_no_image_technical_failure() -> None:
    decision = evaluate_admission(
        _report("no_output_failure"),
        _snap(state="no_result_confirmed", technically_evaluable=False,
              retained_artifact_sha256=None,
              failure_evidence="host_error_recorded",
              failure_classification="host_technical_error"),
        _prospective())
    assert decision.disposition == "FAILURE"
    assert decision.failure_classification == "host_technical_error"
    assert decision.retry_eligible


def test_operator_observed_absence_pending_unknown() -> None:
    decision = evaluate_admission(
        _report("interrupted_unknown"),
        _snap(state="PENDING_UNKNOWN", technically_evaluable=None,
              retained_artifact_sha256=None),
        _prospective())
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
        _prospective())
    assert decision.disposition == "FAILURE"
    assert decision.failure_classification == "safety_refusal"
    assert not decision.retry_eligible
    assert "SAFETY_REFUSAL_RELABEL_REJECTED" in decision.reason_codes


def test_attachment_or_multiple_generation_non_retryable_failure() -> None:
    decision = evaluate_admission(
        _report("qualifying_class_b"), _snap(), _prospective(),
        ProtocolContext(
            demonstrated_protocol_violation=True,
            protocol_violation_codes=("ATTACHMENT_USED",)))
    assert decision.disposition == "FAILURE"
    assert decision.failure_classification == "protocol_violation"
    assert not decision.retry_eligible


def test_unknown_invocation_no_terminal_commitment() -> None:
    decision = evaluate_admission(
        _report(), _snap(known_slot=False), _prospective())
    assert decision.disposition == "PENDING_UNKNOWN"
    assert not decision.eligible_for_commitment
    assert "NO_TERMINAL_COMMITMENT" in decision.reason_codes


def test_h3_indeterminate_missing_authorization_blocked() -> None:
    decision = evaluate_admission(
        _report("interrupted_unknown"),
        _snap(state="PENDING_UNKNOWN", technically_evaluable=None,
              retained_artifact_sha256=None),
        _prospective(),
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
        _prospective(),
        ProtocolContext(requesting_indeterminate_closure=True,
                        h3_authorization=_h3()))
    assert decision.disposition == "INDETERMINATE_FINAL"
    assert decision.eligible_for_commitment
    assert decision.authorization_satisfied


# =============================================================================
# A2 — Retry classification and PR-9 anchor authority
# =============================================================================


def test_technical_retry_budget_exhausted() -> None:
    prior = evaluate_admission(
        _report("no_output_failure"),
        _snap(state="no_result_confirmed", technically_evaluable=False,
              retained_artifact_sha256=None,
              failure_evidence="host_error_recorded",
              failure_classification="host_technical_error"),
        _prospective())
    assert prior.retry_eligible
    blocked = evaluate_retry_advancement(
        prior,
        _snap(state="FAILURE", technically_evaluable=False,
              retained_artifact_sha256=None,
              terminal_disposition="FAILURE",
              failure_classification="host_technical_error",
              anchor_state=ANCHOR_ANCHORED, retry_count=2),
        anchor_verification=_anchor_ok())
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
        _prospective())
    blocked = evaluate_retry_advancement(
        prior,
        _snap(state="FAILURE", technically_evaluable=False,
              retained_artifact_sha256=None,
              terminal_disposition="FAILURE",
              failure_classification="host_technical_error",
              anchor_state=ANCHOR_RECORDED, retry_count=0),
        anchor_verification=_anchor_fail())
    assert not blocked.retry_eligible
    assert "predecessor_not_externally_anchored" in \
        blocked.retry_eligibility_reason


def test_caller_anchor_state_alone_cannot_authorize_retry() -> None:
    prior = evaluate_admission(
        _report("no_output_failure"),
        _snap(state="no_result_confirmed", technically_evaluable=False,
              retained_artifact_sha256=None,
              failure_evidence="host_error_recorded",
              failure_classification="host_technical_error"),
        _prospective())
    blocked = evaluate_retry_advancement(
        prior,
        _snap(state="FAILURE", technically_evaluable=False,
              retained_artifact_sha256=None,
              terminal_disposition="FAILURE",
              failure_classification="host_technical_error",
              anchor_state=ANCHOR_ANCHORED, retry_count=0),
        anchor_verification=None)
    assert not blocked.retry_eligible
    assert "UNTRUSTED_ANCHOR_CLAIM" in blocked.reason_codes


def test_forged_retry_eligible_flag_cannot_bypass_classification() -> None:
    from aipf.exp019_v1_2_admission import AdmissionDecision
    forged = AdmissionDecision(
        disposition="FAILURE", terminal=True,
        eligible_for_commitment=False,
        reason_codes=("FORGED",),
        retry_eligible=True,
        failure_classification="safety_refusal",
        message="forged")
    blocked = evaluate_retry_advancement(
        forged,
        _snap(state="FAILURE", technically_evaluable=False,
              retained_artifact_sha256=None,
              terminal_disposition="FAILURE",
              failure_classification="safety_refusal",
              anchor_state=ANCHOR_ANCHORED, retry_count=0),
        anchor_verification=_anchor_ok())
    assert not blocked.retry_eligible
    assert "NON_RETRYABLE" in blocked.reason_codes


def test_verified_anchor_authorizes_technical_retry() -> None:
    prior = evaluate_admission(
        _report("no_output_failure"),
        _snap(state="no_result_confirmed", technically_evaluable=False,
              retained_artifact_sha256=None,
              failure_evidence="host_error_recorded",
              failure_classification="host_technical_error"),
        _prospective())
    allowed = evaluate_retry_advancement(
        prior,
        _snap(state="FAILURE", technically_evaluable=False,
              retained_artifact_sha256=None,
              terminal_disposition="FAILURE",
              failure_classification="host_technical_error",
              anchor_state=ANCHOR_ANCHORED, retry_count=0),
        anchor_verification=_anchor_ok())
    assert allowed.retry_eligible
    assert "TECHNICAL_RETRY_AUTHORIZED" in allowed.reason_codes


def test_duplicate_evaluation_deterministic_no_mutation() -> None:
    report = _report("qualifying_class_b")
    snap = _snap()
    receipt = _prospective()
    first = evaluate_admission(report, snap, receipt)
    second = evaluate_admission(report, snap, receipt)
    assert first == second


def test_public_diagnostic_no_treatment_leakage() -> None:
    decision = evaluate_admission(
        _report("contradictory_class_d"), _snap(), _prospective())
    public = decision.to_public_dict()
    text = str(public).lower()
    for banned in ("treatment", "condition", "variant", "prompt",
                   "allocation", "mapping", "model_reports"):
        assert banned not in text


def test_precedence_protocol_violation_beats_admit() -> None:
    decision = evaluate_admission(
        _report("qualifying_class_b"),
        _snap(),
        _prospective(),
        ProtocolContext(
            demonstrated_protocol_violation=True,
            protocol_violation_codes=("MULTIPLE_GENERATION",)))
    assert decision.disposition == "FAILURE"
    assert decision.failure_classification == "protocol_violation"


def test_precedence_receipt_failure_beats_admit() -> None:
    decision = evaluate_admission(
        _report("qualifying_class_b"), _snap(),
        ReceiptIntegrity.failed("RECEIPT_DIGEST_MISMATCH"))
    assert decision.disposition != "ADMIT"
    assert "NEVER_ADMIT" in decision.reason_codes


def test_precedence_bc_conflict_beats_admit_path() -> None:
    base = _report("qualifying_class_b")
    forged = ValidationReport(
        findings=base.findings, q_results=base.q_results,
        outcome_classification="returned_evidenced",
        evidence_eligibility="evidence_eligible",
        technical_validation="passed",
        class_d_conflict_count=0,
        b_c_material_conflicts=("BC_RETURNED_COUNT_CONFLICT",),
        source_integrity=base.source_integrity)
    decision = evaluate_admission(forged, _snap(), _prospective())
    assert decision.disposition != "ADMIT"
    assert "BC_MATERIAL_CONFLICT" in decision.reason_codes


def test_incomplete_run_not_completed_scientific_result() -> None:
    decision = evaluate_admission(
        _report("interrupted_unknown"),
        _snap(state="PENDING_UNKNOWN", technically_evaluable=None,
              retained_artifact_sha256=None, run_closed=True,
              run_complete=False),
        _prospective(),
        ProtocolContext(requesting_indeterminate_closure=True,
                        h3_authorization=_h3()))
    assert decision.disposition == "INDETERMINATE_FINAL"
    assert not decision.public_summary.get("run_complete", False)


def test_untrusted_evidence_object_rejected() -> None:
    impostor = SimpleNamespace(
        outcome_classification="returned_evidenced",
        evidence_eligibility="evidence_eligible",
        technical_validation="passed",
        class_d_conflict_count=0,
        b_c_material_conflicts=(),
        q_results=(),
        errors=(),
        evidence_eligible=True,
        evidence_eligible_with_conflict=False,
    )
    decision = evaluate_admission(impostor, _snap(), _prospective())
    assert decision.disposition != "ADMIT"
    assert "UNTRUSTED_EVIDENCE_OBJECT" in decision.reason_codes


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
        _prospective(),
        ProtocolContext(requesting_indeterminate_closure=True))
    assert decision.authorization_required
    assert not decision.authorization_satisfied
    assert decision.authorization_procedure == INDETERMINATE_PROCEDURE


def test_first_attempt_sequence_with_merged_components(tmp_path) -> None:
    """Prospective decide → commit receipt → retrospective verify."""
    from aipf.exp019_v1_2_lifecycle import AttemptLifecycle, LifecycleStore
    from aipf.exp019_v1_2_receipts import (
        finalize_attempt_with_receipt,
        verify_terminal_receipt,
    )

    store = LifecycleStore(tmp_path / "store")
    life = AttemptLifecycle(store, run_id="synthetic-run")
    life.plan_slot(SLOT)
    life.start_invocation(SLOT)
    bundle = make_evidence_bundle("qualifying_class_b")
    report = validate_evidence_bundle(bundle)
    assert report.evidence_eligible
    raster = bundle["raster_bytes"]
    life.record_output(SLOT, raster, technically_evaluable=True)
    retained = life.slot_state(SLOT)["attempts"][1]["retained_artifact_sha256"]

    # Prospective admission — no receipt yet.
    decision = evaluate_admission(
        report,
        LifecycleSnapshot(
            slot_id=SLOT, attempt_number=1, state="evidence_returned",
            technically_evaluable=True,
            retained_artifact_sha256=retained),
        _prospective())
    assert decision.disposition == "ADMIT"
    assert decision.eligible_for_commitment

    # Commit via PR-7/PR-8 — engine itself writes nothing.
    receipt = finalize_attempt_with_receipt(
        life, SLOT, "ADMIT", slot_position=1,
        frozen_prompt_sha256=bundle["observation"]["protocol_constants"][
            "prompt_sha256"],
        evidence_bundle=bundle,
        validation_report=report)
    verified = verify_terminal_receipt(receipt, lifecycle=life)
    assert verified.verified

    # Retrospective replay requires the verified receipt.
    replay = evaluate_admission(
        report,
        LifecycleSnapshot(
            slot_id=SLOT, attempt_number=1, state="ADMIT",
            technically_evaluable=True,
            terminal_disposition="ADMIT",
            retained_artifact_sha256=receipt["output"]["output_sha256"]),
        ReceiptIntegrity.verified(receipt["receipt_sha256"]))
    assert replay.disposition == "ADMIT"
    assert "IDEMPOTENT_REPLAY" in replay.reason_codes
