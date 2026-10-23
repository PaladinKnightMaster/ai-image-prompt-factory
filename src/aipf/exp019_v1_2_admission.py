"""EXP-019 v1.2 admission decision engine (PR-10).

Pure, deterministic evaluation of the approved G1 admission / failure
policy. Consumes validated evidence, a lifecycle snapshot, receipt
integrity status, and protocol context. Returns a structured
``AdmissionDecision`` without mutating lifecycle state, writing
receipts, publishing checkpoints, generating images, or creating
experimental runs.

Dispositions (approved terminology)::

    ADMIT
    FAILURE
    INDETERMINATE_FINAL
    PENDING_UNKNOWN   — operational, non-terminal

The engine separates the *decision* from durable *commitment* of that
decision. Lifecycle (PR-7), receipts (PR-8), and checkpoints (PR-9)
retain ownership of persistence and external anchoring.

A digest commitment never proves host-side factual claims. Class-D
reports never become authenticated class-C evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Optional, Sequence

from .exp019_v1_2_evidence import Q_DEFINITIONS, ValidationReport
from .exp019_v1_2_lifecycle import (
    ANCHOR_ANCHORED,
    INDETERMINATE_PROCEDURE,
    MAX_RETRIES,
    NON_RETRYABLE_FAILURES,
    RETRYABLE_TECHNICAL_FAILURES,
    TERMINAL_DISPOSITIONS,
)

EXPERIMENT_VERSION = "1.2.0"
CONTRACT_VERSION = "1.2.0"

#: Public dispositions the engine may recommend. ``PENDING_UNKNOWN`` is
#: operational and never a terminal commitment.
DECISION_DISPOSITIONS = TERMINAL_DISPOSITIONS + ("PENDING_UNKNOWN",)

#: Provenance qualifications attached to ADMIT decisions.
PROVENANCE_QUALIFICATIONS = frozenset({
    "operator_evidenced",
    "operator_evidenced_with_class_d_conflict",
})

#: Forbidden keys in public decision summaries (treatment / private).
_FORBIDDEN_PUBLIC_KEYS = frozenset({
    "treatment", "treatment_id", "condition", "condition_id",
    "variant", "variant_id", "prompt", "prompt_text", "mapping",
    "allocation", "private_path", "model_reports",
})


@dataclass(frozen=True)
class LifecycleSnapshot:
    """Read-only view of one invocation attempt for decision evaluation.

    Constructed by callers from PR-7 state; this module never writes it.
    """

    slot_id: str
    attempt_number: int
    state: str
    known_slot: bool = True
    technically_evaluable: Optional[bool] = None
    failure_evidence: Optional[str] = None
    failure_classification: Optional[str] = None
    retained_artifact_sha256: Optional[str] = None
    predecessor_attempt: Optional[int] = None
    terminal_disposition: Optional[str] = None
    anchor_state: Optional[str] = None
    retry_count: int = 0  # completed technical retries after first attempt
    run_closed: bool = False
    run_complete: bool = False


@dataclass(frozen=True)
class ReceiptIntegrity:
    """Whether a prepared / verified terminal receipt binding is intact."""

    intact: bool
    receipt_sha256: Optional[str] = None
    codes: tuple[str, ...] = ()
    message: str = ""


@dataclass(frozen=True)
class ProtocolContext:
    """Frozen protocol / evidence-contract identities for the decision."""

    experiment_version: str = EXPERIMENT_VERSION
    contract_version: str = CONTRACT_VERSION
    evidence_contract_version: str = CONTRACT_VERSION
    max_retries: int = MAX_RETRIES
    h3_authorization: Optional[Mapping] = None
    demonstrated_protocol_violation: bool = False
    protocol_violation_codes: tuple[str, ...] = ()
    #: When True, the caller is requesting H3 closure of an unresolved
    #: outcome (not an ordinary mid-run admission branch).
    requesting_indeterminate_closure: bool = False


@dataclass(frozen=True)
class AdmissionDecision:
    """Deterministic admission evaluation result (not a durable commit)."""

    disposition: str
    terminal: bool
    eligible_for_commitment: bool
    reason_codes: tuple[str, ...]
    evidence_references: tuple[str, ...] = ()
    provenance_qualification: Optional[str] = None
    class_d_conflict_count: int = 0
    class_d_affected_samples: int = 0
    retry_eligible: bool = False
    retry_eligibility_reason: Optional[str] = None
    failure_classification: Optional[str] = None
    authorization_required: bool = False
    authorization_procedure: Optional[str] = None
    authorization_satisfied: bool = False
    message: str = ""
    public_summary: Mapping = field(default_factory=dict)

    def to_public_dict(self) -> dict:
        """Treatment-free public diagnostic summary."""
        payload = {
            "disposition": self.disposition,
            "terminal": self.terminal,
            "eligible_for_commitment": self.eligible_for_commitment,
            "reason_codes": list(self.reason_codes),
            "evidence_references": list(self.evidence_references),
            "provenance_qualification": self.provenance_qualification,
            "class_d_conflict_count": self.class_d_conflict_count,
            "class_d_affected_samples": self.class_d_affected_samples,
            "retry_eligible": self.retry_eligible,
            "retry_eligibility_reason": self.retry_eligibility_reason,
            "failure_classification": self.failure_classification,
            "authorization_required": self.authorization_required,
            "authorization_procedure": self.authorization_procedure,
            "authorization_satisfied": self.authorization_satisfied,
            "message": self.message,
        }
        for key in _FORBIDDEN_PUBLIC_KEYS:
            assert key not in payload
        return payload


def _q_map(report: ValidationReport) -> dict:
    return {r.check: r for r in report.q_results}


def _all_admit_q_pass(report: ValidationReport) -> bool:
    checks = _q_map(report)
    for name in ("Q1", "Q2", "Q3", "Q5"):
        result = checks.get(name)
        if result is None or result.passed is not True:
            return False
    q4 = checks.get("Q4")
    if q4 is not None and q4.passed is False:
        return False
    return True


def _h3_authorization_valid(auth: Optional[Mapping],
                            snapshot: LifecycleSnapshot,
                            context: ProtocolContext) -> bool:
    if not isinstance(auth, Mapping):
        return False
    required = {
        "authorization_id": None,
        "authorized_by": None,
        "reason": None,
        "procedure": INDETERMINATE_PROCEDURE,
        "action": "INDETERMINATE_FINAL",
        "slot_id": snapshot.slot_id,
        "attempt_number": snapshot.attempt_number,
        "contract_version": context.contract_version,
    }
    for key, expected in required.items():
        value = auth.get(key)
        if expected is None:
            if not value:
                return False
        elif value != expected:
            return False
    return True


def _retry_assessment(disposition: str, failure_classification: Optional[str],
                      snapshot: LifecycleSnapshot,
                      context: ProtocolContext) -> tuple[bool, Optional[str]]:
    """Whether a terminal FAILURE may authorize a technical retry.

    Lifecycle still enforces the frozen max of two retries and external
    anchoring of the predecessor. A generic FAILURE is never enough.
    """
    if disposition != "FAILURE":
        return False, "retry_only_after_terminal_technical_failure"
    if failure_classification in NON_RETRYABLE_FAILURES:
        return False, f"non_retryable:{failure_classification}"
    if failure_classification not in RETRYABLE_TECHNICAL_FAILURES:
        return False, "generic_failure_does_not_authorize_retry"
    if snapshot.technically_evaluable is True:
        return False, "technically_evaluable_output_not_retryable"
    if snapshot.retry_count >= context.max_retries:
        return False, "technical_retry_budget_exhausted"
    if snapshot.anchor_state != ANCHOR_ANCHORED and \
            snapshot.terminal_disposition == "FAILURE":
        # Evaluating a not-yet-committed decision: commitment and anchor
        # happen after. For a prior terminal that is still unanchored,
        # advancement is blocked.
        pass
    if snapshot.terminal_disposition == "FAILURE" and \
            snapshot.anchor_state != ANCHOR_ANCHORED:
        return False, "predecessor_not_externally_anchored"
    return True, "confirmed_technical_failure"


def evaluate_admission(
        validated_evidence: Optional[ValidationReport],
        lifecycle_snapshot: LifecycleSnapshot,
        receipt_integrity: ReceiptIntegrity,
        protocol_context: Optional[ProtocolContext] = None,
) -> AdmissionDecision:
    """Evaluate the approved admission decision policy.

    Phase-ordered precedence (first decisive rule wins). Every input
    yields one deterministic decision or a clearly defined fail-closed
    result. Ordinary admission never bypasses receipt integrity,
    lifecycle validity, or demonstrated protocol violations.
    """
    context = protocol_context or ProtocolContext()
    codes: list[str] = []
    refs: list[str] = []

    def decide(disposition: str, *, terminal: bool,
               eligible: bool, message: str,
               provenance: Optional[str] = None,
               class_d_count: int = 0,
               affected_samples: int = 0,
               failure_classification: Optional[str] = None,
               authorization_required: bool = False,
               authorization_satisfied: bool = False,
               extra_codes: Sequence[str] = ()) -> AdmissionDecision:
        reason = tuple(dict.fromkeys([*codes, *extra_codes]))
        retry_ok, retry_reason = _retry_assessment(
            disposition, failure_classification, lifecycle_snapshot, context)
        # PENDING_UNKNOWN / blocked commitment never authorizes retry.
        if not terminal or disposition != "FAILURE":
            retry_ok, retry_reason = False, retry_reason
        if disposition == "FAILURE" and failure_classification in \
                NON_RETRYABLE_FAILURES:
            retry_ok, retry_reason = False, \
                f"non_retryable:{failure_classification}"
        auth_proc = INDETERMINATE_PROCEDURE if authorization_required else None
        decision = AdmissionDecision(
            disposition=disposition,
            terminal=terminal,
            eligible_for_commitment=eligible,
            reason_codes=reason,
            evidence_references=tuple(dict.fromkeys(refs)),
            provenance_qualification=provenance,
            class_d_conflict_count=class_d_count,
            class_d_affected_samples=affected_samples,
            retry_eligible=retry_ok,
            retry_eligibility_reason=retry_reason,
            failure_classification=failure_classification,
            authorization_required=authorization_required,
            authorization_procedure=auth_proc,
            authorization_satisfied=authorization_satisfied,
            message=message,
        )
        return AdmissionDecision(
            disposition=decision.disposition,
            terminal=decision.terminal,
            eligible_for_commitment=decision.eligible_for_commitment,
            reason_codes=decision.reason_codes,
            evidence_references=decision.evidence_references,
            provenance_qualification=decision.provenance_qualification,
            class_d_conflict_count=decision.class_d_conflict_count,
            class_d_affected_samples=decision.class_d_affected_samples,
            retry_eligible=decision.retry_eligible,
            retry_eligibility_reason=decision.retry_eligibility_reason,
            failure_classification=decision.failure_classification,
            authorization_required=decision.authorization_required,
            authorization_procedure=decision.authorization_procedure,
            authorization_satisfied=decision.authorization_satisfied,
            message=decision.message,
            public_summary=decision.to_public_dict(),
        )

    # ------------------------------------------------------------------
    # Phase 1 — Invocation identity and lifecycle state
    # ------------------------------------------------------------------
    if context.experiment_version != EXPERIMENT_VERSION:
        codes.append("CROSS_VERSION_REJECTED")
        return decide(
            "PENDING_UNKNOWN", terminal=False, eligible=False,
            message="cross-version evaluation is refused",
            extra_codes=("FAIL_CLOSED",))

    if not lifecycle_snapshot.known_slot:
        codes.append("UNKNOWN_INVOCATION")
        return decide(
            "PENDING_UNKNOWN", terminal=False, eligible=False,
            message="unknown invocation cannot receive a terminal "
                    "commitment",
            extra_codes=("NO_TERMINAL_COMMITMENT",))

    if lifecycle_snapshot.terminal_disposition in TERMINAL_DISPOSITIONS:
        codes.append("ALREADY_TERMINAL")
        # Deterministic re-evaluation of a committed terminal: report the
        # existing disposition without mutating anything.
        prior = lifecycle_snapshot.terminal_disposition
        return decide(
            prior, terminal=True, eligible=False,
            message="attempt is already terminal; decision is not mutated",
            failure_classification=(
                lifecycle_snapshot.failure_classification
                if prior == "FAILURE" else None),
            extra_codes=("IDEMPOTENT_REPLAY",))

    if lifecycle_snapshot.state in ("planned",):
        codes.append("NOT_STARTED")
        return decide(
            "PENDING_UNKNOWN", terminal=False, eligible=False,
            message="invocation has not started")

    # ------------------------------------------------------------------
    # Phase 2 — Evidence integrity and schema / receipt validity
    # ------------------------------------------------------------------
    if not receipt_integrity.intact:
        codes.extend(receipt_integrity.codes or ("RECEIPT_INTEGRITY_FAILED",))
        return decide(
            "PENDING_UNKNOWN", terminal=False, eligible=False,
            message="invalid receipt or evidence binding; never ADMIT",
            extra_codes=("NEVER_ADMIT",))

    if validated_evidence is None:
        codes.append("EVIDENCE_REPORT_MISSING")
        return decide(
            "PENDING_UNKNOWN", terminal=False, eligible=False,
            message="validated evidence report is required")

    report = validated_evidence
    refs.append(f"outcome:{report.outcome_classification}")
    refs.append(f"eligibility:{report.evidence_eligibility}")
    for q in report.q_results:
        refs.append(f"{q.check}:{'pass' if q.passed else 'fail' if q.passed is False else 'null'}")

    if report.outcome_classification == "invalid_evidence" and \
            report.errors:
        codes.append("EVIDENCE_INVALID")

    # ------------------------------------------------------------------
    # Phase 3 — Demonstrated protocol violations (before ordinary ADMIT)
    # ------------------------------------------------------------------
    violation_codes = list(context.protocol_violation_codes)
    if context.demonstrated_protocol_violation:
        codes.append("PROTOCOL_VIOLATION")
        codes.extend(violation_codes)
        return decide(
            "FAILURE", terminal=True, eligible=True,
            message="demonstrated protocol violation is non-retryable "
                    "FAILURE",
            failure_classification="protocol_violation",
            extra_codes=("NON_RETRYABLE",))

    # Multiple returned images / attachment-style signals from evidence.
    q2 = _q_map(report).get("Q2")
    if q2 is not None and "Q2_RETURNED_COUNT" in (q2.codes or ()):
        codes.append("PROTOCOL_VIOLATION")
        codes.append("Q2_RETURNED_COUNT")
        return decide(
            "FAILURE", terminal=True, eligible=True,
            message="multiple-generation / returned-count protocol "
                    "violation",
            failure_classification="protocol_violation",
            extra_codes=("NON_RETRYABLE",))

    # ------------------------------------------------------------------
    # Phase 4 — Technical-output classification
    # ------------------------------------------------------------------
    if report.technical_validation == "failed":
        codes.append("TECHNICAL_VALIDATION_FAILED")
        # Confirmed invalid raster with returned bytes → technical FAILURE.
        return decide(
            "FAILURE", terminal=True, eligible=True,
            message="confirmed invalid raster; technical FAILURE",
            failure_classification="host_technical_error",
            extra_codes=("INVALID_RASTER", "TECHNICAL_FAILURE"))

    # ------------------------------------------------------------------
    # Phase 5 — Authenticated class-C conflicts (authoritative)
    # ------------------------------------------------------------------
    if report.b_c_material_conflicts:
        codes.append("BC_MATERIAL_CONFLICT")
        codes.extend(report.b_c_material_conflicts)
        # Not eligible for ADMIT; classify through indeterminate procedure.
        auth_ok = _h3_authorization_valid(
            context.h3_authorization, lifecycle_snapshot, context)
        if context.requesting_indeterminate_closure:
            if not auth_ok:
                return decide(
                    "INDETERMINATE_FINAL", terminal=True, eligible=False,
                    message="B/C conflict eligible for INDETERMINATE_FINAL "
                            "but H3 authorization is missing or invalid",
                    authorization_required=True,
                    authorization_satisfied=False,
                    extra_codes=("AUTHORIZATION_REQUIRED",
                                 "INDETERMINATE_ELIGIBLE"))
            return decide(
                "INDETERMINATE_FINAL", terminal=True, eligible=True,
                message="authenticated B/C conflict closed under H3",
                authorization_required=True,
                authorization_satisfied=True,
                extra_codes=("INDETERMINATE_ELIGIBLE",))
        return decide(
            "PENDING_UNKNOWN", terminal=False, eligible=False,
            message="authenticated class-C conflict blocks ADMIT; "
                    "indeterminate eligibility pending H3 closure",
            authorization_required=True,
            authorization_satisfied=False,
            extra_codes=("INDETERMINATE_ELIGIBLE", "NEVER_ADMIT"))

    # ------------------------------------------------------------------
    # Phase 6 — Qualifying Q1–Q5 / ordinary ADMIT branch
    # ------------------------------------------------------------------
    class_d_count = int(report.class_d_conflict_count or 0)
    # One admitted sample may carry multiple class-D conflict *entries*.
    affected_samples = 1 if class_d_count > 0 else 0

    if report.evidence_eligible and report.technical_validation == "passed" \
            and _all_admit_q_pass(report) \
            and report.outcome_classification == "returned_evidenced":
        # Missing optional C is already non-blocking inside eligibility.
        provenance = (
            "operator_evidenced_with_class_d_conflict"
            if report.evidence_eligible_with_conflict
            else "operator_evidenced")
        if class_d_count:
            codes.append("CLASS_D_CONFLICT_PRESERVED")
        codes.append("Q1_Q5_SATISFIED")
        # Class-D never decides disposition — ADMIT stands.
        return decide(
            "ADMIT", terminal=True, eligible=True,
            message="technically valid output with qualifying Q1–Q5",
            provenance=provenance,
            class_d_count=class_d_count,
            affected_samples=affected_samples)

    # ------------------------------------------------------------------
    # Phase 7 — No-result / unknown / incomplete evidence paths
    # ------------------------------------------------------------------
    if report.outcome_classification == "no_result_evidenced":
        evidence_kind = lifecycle_snapshot.failure_evidence
        classification = lifecycle_snapshot.failure_classification
        # Safety refusal relabelled as technical failure → reject retry.
        if evidence_kind == "safety_refusal_recorded" and \
                classification in RETRYABLE_TECHNICAL_FAILURES:
            codes.append("SAFETY_REFUSAL_RELABEL_REJECTED")
            return decide(
                "FAILURE", terminal=True, eligible=True,
                message="safety refusal cannot be relabelled a technical "
                        "failure",
                failure_classification="safety_refusal",
                extra_codes=("NON_RETRYABLE",))
        if classification == "safety_refusal" or \
                evidence_kind == "safety_refusal_recorded":
            codes.append("SAFETY_REFUSAL")
            return decide(
                "FAILURE", terminal=True, eligible=True,
                message="provider safety refusal is non-retryable FAILURE",
                failure_classification="safety_refusal",
                extra_codes=("NON_RETRYABLE",))
        if classification in RETRYABLE_TECHNICAL_FAILURES or \
                evidence_kind in (
                    "host_error_recorded", "host_completed_no_image",
                    "request_not_accepted"):
            # Confirmed host error / no image with affirmative evidence.
            resolved = classification if classification in \
                RETRYABLE_TECHNICAL_FAILURES else "host_technical_error"
            codes.append("AFFIRMATIVE_NO_RESULT")
            return decide(
                "FAILURE", terminal=True, eligible=True,
                message="affirmative no-result evidence supports FAILURE",
                failure_classification=resolved,
                extra_codes=("TECHNICAL_FAILURE",))
        codes.append("NO_RESULT_WITHOUT_TECHNICAL_CLASSIFICATION")
        return decide(
            "FAILURE", terminal=True, eligible=True,
            message="no-result evidenced but classification is not a "
                    "confirmed technical failure",
            failure_classification=classification or "operator_abort",
            extra_codes=("NON_RETRYABLE",))

    if report.outcome_classification == "unknown_outcome":
        codes.append("UNKNOWN_HOST_RESULT")
        # Operator-observed absence without confirmed host failure stays
        # PENDING_UNKNOWN — never automatic technical failure.
        if context.requesting_indeterminate_closure:
            auth_ok = _h3_authorization_valid(
                context.h3_authorization, lifecycle_snapshot, context)
            if not auth_ok:
                return decide(
                    "INDETERMINATE_FINAL", terminal=True, eligible=False,
                    message="H3 indeterminate closure blocked: missing or "
                            "invalid authorization",
                    authorization_required=True,
                    authorization_satisfied=False,
                    extra_codes=("AUTHORIZATION_REQUIRED",))
            return decide(
                "INDETERMINATE_FINAL", terminal=True, eligible=True,
                message="unresolved outcome closed under H3 authorization",
                authorization_required=True,
                authorization_satisfied=True)
        return decide(
            "PENDING_UNKNOWN", terminal=False, eligible=False,
            message="unknown host result remains PENDING_UNKNOWN; never "
                    "automatic technical failure",
            extra_codes=("NEVER_AUTO_TECHNICAL_FAILURE",))

    # Incomplete Q1–Q5 / not evidence eligible with returned artifact →
    # never ADMIT; indeterminate eligibility.
    if not report.evidence_eligible:
        codes.append("INCOMPLETE_OR_DISQUALIFYING_EVIDENCE")
        if not _all_admit_q_pass(report):
            codes.append("Q1_Q5_INCOMPLETE")
        auth_ok = _h3_authorization_valid(
            context.h3_authorization, lifecycle_snapshot, context)
        if context.requesting_indeterminate_closure:
            if not auth_ok:
                return decide(
                    "INDETERMINATE_FINAL", terminal=True, eligible=False,
                    message="incomplete evidence eligible for "
                            "INDETERMINATE_FINAL but authorization missing",
                    authorization_required=True,
                    authorization_satisfied=False,
                    extra_codes=("AUTHORIZATION_REQUIRED", "NEVER_ADMIT"))
            return decide(
                "INDETERMINATE_FINAL", terminal=True, eligible=True,
                message="incomplete evidence closed under H3",
                authorization_required=True,
                authorization_satisfied=True,
                extra_codes=("NEVER_ADMIT",))
        # Mid-run: stay operational / pending review — not ADMIT.
        if lifecycle_snapshot.state == "indeterminate_pending_review":
            return decide(
                "PENDING_UNKNOWN", terminal=False, eligible=False,
                message="artifact present but contract unresolved; "
                        "never ADMIT without qualifying Q1–Q5",
                authorization_required=True,
                extra_codes=("INDETERMINATE_ELIGIBLE", "NEVER_ADMIT"))
        return decide(
            "PENDING_UNKNOWN", terminal=False, eligible=False,
            message="incomplete Q1–Q5; never ADMIT",
            extra_codes=("NEVER_ADMIT",))

    # Fail closed on any residual unclassified combination.
    codes.append("UNCLASSIFIED_INPUT")
    return decide(
        "PENDING_UNKNOWN", terminal=False, eligible=False,
        message="fail-closed: inputs did not match an approved decision "
                "branch",
        extra_codes=("FAIL_CLOSED",))


def evaluate_retry_advancement(
        prior_decision: AdmissionDecision,
        lifecycle_snapshot: LifecycleSnapshot,
        protocol_context: Optional[ProtocolContext] = None,
) -> AdmissionDecision:
    """Re-check whether lifecycle may advance a technical retry.

    Does not start a retry. Returns a decision whose ``retry_eligible``
    flag reflects budget and external-anchor requirements.
    """
    context = protocol_context or ProtocolContext()
    if not prior_decision.retry_eligible:
        return prior_decision
    if lifecycle_snapshot.retry_count >= context.max_retries:
        return AdmissionDecision(
            disposition=prior_decision.disposition,
            terminal=True,
            eligible_for_commitment=False,
            reason_codes=prior_decision.reason_codes + (
                "TECHNICAL_RETRY_BUDGET_EXHAUSTED",),
            evidence_references=prior_decision.evidence_references,
            retry_eligible=False,
            retry_eligibility_reason="technical_retry_budget_exhausted",
            failure_classification=prior_decision.failure_classification,
            message="technical retry budget exhausted",
            public_summary={},
        )
    if lifecycle_snapshot.anchor_state != ANCHOR_ANCHORED:
        return AdmissionDecision(
            disposition=prior_decision.disposition,
            terminal=True,
            eligible_for_commitment=False,
            reason_codes=prior_decision.reason_codes + (
                "PREDECESSOR_NOT_EXTERNALLY_ANCHORED",),
            evidence_references=prior_decision.evidence_references,
            retry_eligible=False,
            retry_eligibility_reason="predecessor_not_externally_anchored",
            failure_classification=prior_decision.failure_classification,
            message="previous receipt not externally anchored; no retry "
                    "advancement",
            public_summary={},
        )
    return prior_decision
