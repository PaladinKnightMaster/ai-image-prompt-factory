"""EXP-019 v1.2 terminal attempt receipts: construction and verification (PR-8).

Exactly one terminal attempt receipt is built per terminal attempt,
against the v1.2 receipt schema
(``data/schemas/exp019_v1_2_terminal_attempt_receipt.schema.json``).
The receipt binds the experiment and version, the run and opaque slot
identity, slot position and attempt number, the frozen prompt digest,
the attempt event history and terminal outcome, the available evidence
artifacts and their canonical commitments, the original output bytes
digest or an explicit no-output reason, operator observations and the
attestation commitment, captured class-D conflicts, the provenance
qualification, and the local finalization status.

Cryptographic integrity is SHA-256 over deterministic canonical
serializations. ``receipt_sha256`` binds the receipt core and excludes
both itself and ``local_finalization_status`` (a mutable lifecycle
state), so the binding is never self-referential. Status transitions
are recorded in a separate, chained audit log under the store
(``receipts/status-transitions.json``); verification requires the
claimed status to match that log and, for ``externally_verified``, the
durable lifecycle anchor state. An attacker who edits only the status
field on a stored receipt cannot make an unanchored receipt verify as
externally verified. Evidence integrity is kept separate from evidence
truth and from authenticated host provenance: a commitment proves
bytes are unchanged, never that their claims are true or class-C
authentic. The class-D conflict count is bound to a commitment over
the isolated ``model_reports`` records and cannot be changed
independently of those records.

Outcome-dependent output handling uses ``output_state`` with nullable
digests and a mandatory no-output reason where no artifact exists; a
digest is never invented for an absent artifact, and only an ``ADMIT``
receipt may place output in the canonical admitted location.

Lifecycle integration uses the PR-7 durable state machine — there is no
competing lifecycle here. Receipt preparation, durable local
finalization, awaiting external anchoring, and externally verified
finalization (a PR-9 responsibility) are distinct states; an unanchored
receipt is never represented as externally verified, and no experimental
checkpoint is created. Cross-version receipts (any legacy EXP-019
version) are rejected by explicit version dispatch.

This module registers nothing in ``frozen_protocol()``, creates no run
root, allocation, or checkpoint, and issues no host request.
"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional

from jsonschema import Draft202012Validator

from .exp019_v1_2_evidence import (
    canonical_artifact_digest,
    validate_evidence_bundle,
)

SCHEMA_VERSION = "1.2.0-draft"
EXPERIMENT_VERSION = "1.2.0"
EVIDENCE_CONTRACT_VERSION = "1.2.0"
RECEIPT_SCHEMA_FILE = "exp019_v1_2_terminal_attempt_receipt.schema.json"

TERMINAL_DISPOSITIONS = ("ADMIT", "FAILURE", "INDETERMINATE_FINAL")

#: Keys that must never appear in a v1.2 receipt: legacy model
#: metadata-query / metadata-recovery material (abolished by H2) and
#: any treatment-bearing field.
FORBIDDEN_RECEIPT_FIELDS = frozenset({
    "model_metadata", "metadata_query", "provider_response",
    "generated_file_path", "metadata_recovery", "recorded_model_snapshot",
    "requested_model", "condition", "condition_id", "treatment",
    "treatment_id", "variant", "variant_id",
})

_OUTPUT_STATES_BY_DISPOSITION = {
    "ADMIT": {"admitted"},
    "FAILURE": {"absent_no_output", "retained_invalid"},
    "INDETERMINATE_FINAL": {
        "absent_no_output", "retained_indeterminate",
        "retained_protocol_failure"},
}

_EVIDENCE_KINDS = ("observation", "attestation", "action_log",
                   "request_capture", "response_capture")

_STATUS_ORDER = ("prepared", "locally_finalized", "awaiting_external_anchor",
                 "externally_verified")
STATUS_TRANSITIONS_NAME = "status-transitions.json"


@dataclass(frozen=True)
class ReceiptFinding:
    """One receipt-verification finding; fields are named, never valued."""

    code: str
    field: str
    message: str


@dataclass(frozen=True)
class ReceiptVerification:
    findings: tuple = ()

    @property
    def verified(self) -> bool:
        return not self.findings

    @property
    def codes(self) -> tuple:
        return tuple(f.code for f in self.findings)


def _canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _receipt_core(receipt: Mapping) -> dict:
    """The cryptographically bound core: everything except the binding
    itself and the mutable local-finalization status."""
    return {key: value for key, value in receipt.items()
            if key not in ("receipt_sha256", "local_finalization_status")}


def canonical_receipt_sha256(receipt: Mapping) -> str:
    """Recompute the receipt binding. Never self-referential."""
    return _sha256(_canonical(_receipt_core(receipt)))


def _check_output_matrix(disposition, output) -> list:
    """The outcome/output-state matrix shared by builder and verifier."""
    codes = []
    state = output.get("output_state")
    digest = output.get("output_sha256")
    admitted = output.get("admitted_output_sha256")
    reason = output.get("no_output_reason")
    location = output.get("output_location")
    if state not in _OUTPUT_STATES_BY_DISPOSITION.get(disposition, set()):
        codes.append("OUTPUT_STATE_INCONSISTENT")
    if state == "admitted":
        if digest is None or admitted != digest or reason is not None:
            codes.append("OUTPUT_STATE_INCONSISTENT")
        if location != "canonical_admitted":
            codes.append("OUTPUT_STATE_INCONSISTENT")
    elif state == "absent_no_output":
        if digest is not None or admitted is not None or not reason:
            codes.append("OUTPUT_STATE_INCONSISTENT")
        if location != "none":
            codes.append("OUTPUT_STATE_INCONSISTENT")
    else:  # retained but not admitted
        if digest is None or admitted is not None:
            codes.append("OUTPUT_STATE_INCONSISTENT")
        if location != "retained_non_admitted":
            codes.append("OUTPUT_STATE_INCONSISTENT")
        if state == "retained_invalid" and not reason:
            codes.append("OUTPUT_STATE_INCONSISTENT")
    if disposition != "ADMIT" and admitted is not None:
        codes.append("OUTPUT_STATE_INCONSISTENT")
    return sorted(set(codes))


def _derive_output_state(disposition, retained_sha256, explicit):
    if explicit is not None:
        return explicit
    if disposition == "ADMIT":
        return "admitted"
    if retained_sha256 is None:
        return "absent_no_output"
    return "retained_invalid" if disposition == "FAILURE" \
        else "retained_indeterminate"


def build_terminal_receipt(*, terminal_record: Mapping, slot_position: int,
                           frozen_prompt_sha256: str,
                           event_history, evidence_bundle=None,
                           validation_report=None, output_state=None,
                           no_output_reason=None,
                           local_finalization_status: str = "prepared"
                           ) -> dict:
    """Build one terminal attempt receipt from a PR-7 terminal record.

    The receipt is ``prepared`` when returned; durable local
    finalization happens only through
    :func:`finalize_attempt_with_receipt`. No digest is invented for an
    absent artifact, and no legacy metadata or treatment field is
    emitted.
    """
    disposition = terminal_record.get("disposition")
    if disposition not in TERMINAL_DISPOSITIONS:
        raise ValueError("a receipt requires a terminal disposition")
    retained = terminal_record.get("retained_artifact_sha256")
    state = _derive_output_state(disposition, retained, output_state)
    if state == "absent_no_output" and not no_output_reason:
        if disposition == "FAILURE":
            no_output_reason = "{}:{}".format(
                terminal_record.get("failure_evidence"),
                terminal_record.get("failure_classification"))
            if no_output_reason.startswith("None"):
                raise ValueError(
                    "a no-output FAILURE receipt requires an explicit "
                    "no-output reason")
        elif disposition == "INDETERMINATE_FINAL":
            no_output_reason = "unresolved_no_output"
    if state == "retained_invalid" and not no_output_reason:
        raise ValueError(
            "retained invalid bytes require an explicit reason")
    output = {
        "output_state": state,
        "output_sha256": retained,
        "admitted_output_sha256": retained if disposition == "ADMIT"
            else None,
        "no_output_reason": no_output_reason
            if state != "admitted" else None,
        "output_location": (
            "canonical_admitted" if state == "admitted"
            else "none" if state == "absent_no_output"
            else "retained_non_admitted"),
    }
    matrix_codes = _check_output_matrix(disposition, output)
    if matrix_codes:
        raise ValueError(
            "receipt output state is inconsistent with its disposition: "
            + ", ".join(matrix_codes))
    if disposition == "INDETERMINATE_FINAL" and \
            not terminal_record.get("authorization"):
        raise ValueError(
            "an INDETERMINATE_FINAL receipt requires the persisted H3 "
            "authorization summary from the terminal record")

    report = validation_report
    if report is None and evidence_bundle is not None:
        report = validate_evidence_bundle(evidence_bundle)
    if disposition == "ADMIT":
        if report is None:
            raise ValueError(
                "ADMIT requires a completed evidence validation report")
        if not report.evidence_eligible or \
                report.technical_validation != "passed":
            raise ValueError(
                "ADMIT requires complete evidence qualification and "
                "technical validation; a digest alone is never "
                "scientific admission")
    evidence_artifacts = []
    attested_fields, recorded_fields = [], []
    attestation_commitment = None
    model_reports = []
    if evidence_bundle is not None:
        for kind in _EVIDENCE_KINDS:
            artifact = evidence_bundle.get(kind)
            if artifact is not None:
                evidence_artifacts.append({
                    "kind": kind,
                    "commitment_sha256": canonical_artifact_digest(
                        artifact)})
        attestation = evidence_bundle.get("attestation")
        if attestation is not None:
            attestation_commitment = canonical_artifact_digest(attestation)
        observation = evidence_bundle.get("observation") or {}
        model_reports = list(observation.get("model_reports") or [])
        for name, fld in (observation.get("observations") or {}).items():
            if fld.get("status") == "operator_attested":
                attested_fields.append(name)
            elif fld.get("status") == "operator_recorded":
                recorded_fields.append(name)
    if report is not None:
        class_d_count = int(report.class_d_conflict_count)
        authenticated = any(s.authenticated
                            for s in report.source_integrity)
        evidence_validation = {
            "outcome_classification": report.outcome_classification,
            "evidence_eligibility": report.evidence_eligibility,
            "technical_validation": report.technical_validation,
            "checks": [
                {"check": r.check, "definition": r.definition,
                 "passed": r.passed} for r in report.q_results],
        }
    else:
        class_d_count = int(terminal_record.get("class_d_conflict_count")
                            or 0)
        authenticated = False
        evidence_validation = None
    record_conflict_count = int(
        terminal_record.get("class_d_conflict_count") or 0)
    # The conflict count cannot be changed independently of the
    # validated records: a caller-supplied count must agree with the
    # report when both are present.
    if report is not None and record_conflict_count and \
            record_conflict_count != class_d_count:
        raise ValueError(
            "class_d_conflict_count disagrees with the validated "
            "conflict records and cannot be altered independently")
    if class_d_count and not model_reports:
        raise ValueError(
            "a non-zero class-D conflict count requires the isolated "
            "model_reports records whose commitment it represents")
    class_d_records_commitment = (
        _sha256(_canonical(model_reports)) if class_d_count else None)
    provenance = (
        "authenticated_class_c_supported" if authenticated
        else "operator_evidenced_with_class_d_conflict" if class_d_count
        else "operator_evidenced")
    authorization = copy.deepcopy(terminal_record.get("authorization"))
    if authorization is not None:
        authorization.setdefault("procedure",
                                 "H3-indeterminate-disposition")
        authorization.setdefault("action", "INDETERMINATE_FINAL")

    receipt = {
        "schema_version": SCHEMA_VERSION,
        "receipt_type": "terminal_attempt_receipt",
        "experiment_id": "EXP-019",
        "experiment_version": EXPERIMENT_VERSION,
        "evidence_contract_version": EVIDENCE_CONTRACT_VERSION,
        "run_id": terminal_record.get("run_id"),
        "opaque_slot_id": terminal_record.get("slot_id"),
        "slot_position": int(slot_position),
        "attempt_number": int(terminal_record.get("attempt_number")),
        "predecessor_attempt": terminal_record.get("predecessor_attempt"),
        "frozen_prompt_sha256": frozen_prompt_sha256,
        "disposition": disposition,
        "failure_evidence": terminal_record.get("failure_evidence"),
        "failure_classification": terminal_record.get(
            "failure_classification"),
        "authorization": authorization,
        "attempt_event_history": [
            {"seq": int(e["seq"]), "event_type": e["type"],
             "event_id": e["event_id"]} for e in event_history],
        "evidence_artifacts": evidence_artifacts,
        "evidence_validation": evidence_validation,
        "operator_observations": {
            "operator_attested_fields": sorted(attested_fields),
            "operator_recorded_fields": sorted(recorded_fields)},
        "attestation_commitment_sha256": attestation_commitment,
        "class_d_conflict_count": class_d_count,
        "class_d_records_commitment_sha256": class_d_records_commitment,
        "provenance_qualification": provenance,
        "output": output,
        "local_finalization_status": local_finalization_status,
    }
    receipt["receipt_sha256"] = canonical_receipt_sha256(receipt)
    return receipt


def verify_terminal_receipt(receipt: Mapping, *, lifecycle=None,
                            evidence_bundle=None, output_bytes=None,
                            admitted_output_bytes=None,
                            expected_run_id=None,
                            schema_dir: Optional[Path] = None
                            ) -> ReceiptVerification:
    """Verify a v1.2 terminal attempt receipt. Purely read-only.

    Cross-version receipts are rejected by explicit version dispatch
    before any other check. Where the durable ``lifecycle``, the
    ``evidence_bundle``, or the actual output bytes are supplied, the
    receipt is verified against them; integrity findings never assert
    evidence truth or authenticated host provenance.
    """
    findings = []

    def add(code, field, message):
        findings.append(ReceiptFinding(code, field, message))

    # Explicit version dispatch: legacy receipts are not v1.2 receipts.
    if receipt.get("experiment_version") != EXPERIMENT_VERSION or \
            receipt.get("schema_version") != SCHEMA_VERSION or \
            receipt.get("receipt_type") != "terminal_attempt_receipt":
        add("CROSS_VERSION_RECEIPT", "experiment_version",
            "only EXP-019 v1.2 terminal attempt receipts are accepted "
            "here; legacy-version receipts are rejected")
        return ReceiptVerification(tuple(findings))

    for key in sorted(set(receipt) & FORBIDDEN_RECEIPT_FIELDS):
        add("FORBIDDEN_FIELD", key,
            "legacy metadata or treatment-bearing fields are forbidden")

    base = Path(schema_dir) if schema_dir else \
        Path(__file__).resolve().parents[2] / "data" / "schemas"
    schema = json.loads((base / RECEIPT_SCHEMA_FILE).read_text(
        encoding="utf-8"))
    for _err in Draft202012Validator(schema).iter_errors(receipt):
        add("SCHEMA_INVALID", "receipt",
            "receipt does not satisfy the v1.2 receipt schema")
        break

    if receipt.get("receipt_sha256") != canonical_receipt_sha256(receipt):
        add("RECEIPT_DIGEST_MISMATCH", "receipt_sha256",
            "receipt binding does not recompute from the receipt core")

    for code in _check_output_matrix(receipt.get("disposition"),
                                     receipt.get("output") or {}):
        add(code, "output",
            "output state is inconsistent with the terminal disposition")

    if receipt.get("disposition") == "INDETERMINATE_FINAL" and \
            not receipt.get("authorization"):
        add("AUTHORIZATION_MISSING", "authorization",
            "INDETERMINATE_FINAL requires the authorized record summary")

    if receipt.get("disposition") == "ADMIT":
        evidence_validation = receipt.get("evidence_validation") or {}
        if not evidence_validation:
            add("ADMIT_EVIDENCE_INCOMPLETE", "evidence_validation",
                "ADMIT requires a bound evidence validation summary")
        else:
            if evidence_validation.get("technical_validation") != "passed":
                add("ADMIT_EVIDENCE_INCOMPLETE", "technical_validation",
                    "ADMIT requires technical_validation=passed")
            if evidence_validation.get("evidence_eligibility") not in (
                    "evidence_eligible",
                    "evidence_eligible_with_conflict"):
                add("ADMIT_EVIDENCE_INCOMPLETE", "evidence_eligibility",
                    "ADMIT requires complete evidence qualification")
            checks = {c.get("check"): c for c in
                      evidence_validation.get("checks") or []}
            # Match evidence-eligibility: Q1/Q2/Q3/Q5 must be True.
            # Q4 may be null when no image was returned; False always fails.
            for name in ("Q1", "Q2", "Q3", "Q5"):
                if name not in checks or \
                        checks[name].get("passed") is not True:
                    add("ADMIT_EVIDENCE_INCOMPLETE", name,
                        "ADMIT requires Q1/Q2/Q3/Q5 passed=true "
                        "(null is not success)")
            if "Q4" not in checks or \
                    checks["Q4"].get("passed") is False:
                add("ADMIT_EVIDENCE_INCOMPLETE", "Q4",
                    "ADMIT rejects Q4 failure; null is only allowed "
                    "when no image was returned")

    if expected_run_id is not None and \
            receipt.get("run_id") != expected_run_id:
        add("IDENTITY_MISMATCH", "run_id",
            "receipt does not belong to the expected run")

    if output_bytes is not None and receipt.get("output", {}).get(
            "output_sha256") != _sha256(bytes(output_bytes)):
        add("OUTPUT_DIGEST_MISMATCH", "output.output_sha256",
            "retained output bytes do not recompute to the receipt "
            "digest")
    if admitted_output_bytes is not None and receipt.get(
            "output", {}).get("admitted_output_sha256") != _sha256(
            bytes(admitted_output_bytes)):
        add("ADMITTED_OUTPUT_MISMATCH", "output.admitted_output_sha256",
            "canonical admitted output bytes do not recompute to the "
            "receipt digest")

    if evidence_bundle is not None:
        expected_commitments = {
            kind: canonical_artifact_digest(evidence_bundle[kind])
            for kind in _EVIDENCE_KINDS
            if evidence_bundle.get(kind) is not None}
        actual_commitments = {
            entry["kind"]: entry["commitment_sha256"]
            for entry in receipt.get("evidence_artifacts") or []}
        if actual_commitments != expected_commitments:
            add("EVIDENCE_COMMITMENT_MISMATCH", "evidence_artifacts",
                "evidence commitments do not recompute from the "
                "supplied artifacts; an artifact is missing or "
                "substituted")
        if receipt.get("disposition") == "ADMIT":
            report = validate_evidence_bundle(evidence_bundle)
            if not report.evidence_eligible or \
                    report.technical_validation != "passed":
                add("ADMIT_EVIDENCE_INCOMPLETE", "evidence_bundle",
                    "supplied evidence does not qualify for ADMIT")
            if report.class_d_conflict_count != \
                    receipt.get("class_d_conflict_count"):
                add("CLASS_D_RECORDS_MISMATCH", "class_d_conflict_count",
                    "bound conflict count disagrees with revalidated "
                    "evidence")
            bound = {(c.get("check"), c.get("passed"))
                     for c in (receipt.get("evidence_validation") or
                               {}).get("checks") or []}
            actual = {(r.check, r.passed) for r in report.q_results}
            if bound != actual:
                add("ADMIT_EVIDENCE_INCOMPLETE", "evidence_validation",
                    "bound Q1-Q5 findings disagree with revalidated "
                    "evidence")
        attestation = evidence_bundle.get("attestation")
        expected_attestation = canonical_artifact_digest(attestation) \
            if attestation is not None else None
        if receipt.get("attestation_commitment_sha256") != \
                expected_attestation:
            add("ATTESTATION_COMMITMENT_MISMATCH",
                "attestation_commitment_sha256",
                "attestation commitment does not recompute from the "
                "supplied attestation")
        observation = evidence_bundle.get("observation") or {}
        constants = observation.get("protocol_constants") or {}
        if constants and receipt.get("frozen_prompt_sha256") != \
                constants.get("prompt_sha256"):
            add("FROZEN_PROMPT_MISMATCH", "frozen_prompt_sha256",
                "receipt prompt digest does not match the frozen "
                "prompt digest in the evidence")
        reports = list(observation.get("model_reports") or [])
        expected_cd = (_sha256(_canonical(reports))
                       if receipt.get("class_d_conflict_count") else None)
        if receipt.get("class_d_records_commitment_sha256") != expected_cd:
            add("CLASS_D_RECORDS_MISMATCH",
                "class_d_records_commitment_sha256",
                "class-D conflict count is not bound to the supplied "
                "model_reports records")
        if receipt.get("class_d_conflict_count") and not reports:
            add("CLASS_D_RECORDS_MISMATCH", "class_d_conflict_count",
                "a non-zero conflict count has no underlying records")

    if receipt.get("class_d_conflict_count") and \
            not receipt.get("class_d_records_commitment_sha256"):
        add("CLASS_D_RECORDS_MISMATCH",
            "class_d_records_commitment_sha256",
            "conflict count cannot stand without a records commitment")
    if not receipt.get("class_d_conflict_count") and \
            receipt.get("class_d_records_commitment_sha256"):
        add("CLASS_D_RECORDS_MISMATCH",
            "class_d_records_commitment_sha256",
            "a records commitment requires a non-zero conflict count")

    if lifecycle is not None:
        try:
            state = lifecycle.slot_state(receipt.get("opaque_slot_id"))
            attempt = state["attempts"].get(receipt.get("attempt_number"))
        except Exception:
            attempt = None
        if attempt is None:
            add("IDENTITY_MISMATCH", "opaque_slot_id/attempt_number",
                "no such attempt exists in the durable lifecycle")
        else:
            if attempt.get("disposition") != receipt.get("disposition"):
                add("TERMINAL_RECORD_MISMATCH", "disposition",
                    "receipt disposition disagrees with the durable "
                    "terminal record; dispositions are never silently "
                    "changed")
            # The receipt binds the attempt's history up to and
            # including its terminal event; later events (anchoring,
            # retries) belong to subsequent states, not this receipt.
            terminal_seqs = [
                e["seq"] for e in lifecycle.store.events
                if e.get("type") == "attempt_terminal"
                and e.get("slot_id") == receipt.get("opaque_slot_id")
                and e.get("attempt_number") == receipt.get(
                    "attempt_number")]
            cutoff = terminal_seqs[0] if terminal_seqs else -1
            expected_history = [
                {"seq": e["seq"], "event_type": e["type"],
                 "event_id": e["event_id"]}
                for e in lifecycle.store.events
                if e.get("slot_id") == receipt.get("opaque_slot_id")
                and e.get("attempt_number") in (
                    None, receipt.get("attempt_number"))
                and e["seq"] <= cutoff]
            if receipt.get("attempt_event_history") != expected_history:
                add("EVENT_HISTORY_MISMATCH", "attempt_event_history",
                    "attempt event history does not pair with the "
                    "durable lifecycle events")
            status = receipt.get("local_finalization_status")
            anchored = attempt.get("anchor_state") == \
                "externally-anchored"
            audited = latest_receipt_status(
                lifecycle, receipt.get("receipt_sha256"))
            if status != "prepared":
                if audited != status:
                    add("STATUS_AUDIT_MISMATCH",
                        "local_finalization_status",
                        "claimed status must match the durable status-"
                        "transition audit log; missing audit fails "
                        "closed")
            elif audited is not None and audited != status:
                add("STATUS_AUDIT_MISMATCH", "local_finalization_status",
                    "claimed status disagrees with the durable status-"
                    "transition audit log")
            if status == "externally_verified":
                if not anchored:
                    add("UNANCHORED_AS_VERIFIED",
                        "local_finalization_status",
                        "an unanchored receipt must not be represented "
                        "as externally verified")

    return ReceiptVerification(tuple(findings))


# =============================================================================
# Durable lifecycle integration (PR-7 state machine; no competing lifecycle)
# =============================================================================


def _receipts_dir(lifecycle) -> Path:
    directory = lifecycle.store.root / "receipts"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _status_log_path(lifecycle) -> Path:
    return _receipts_dir(lifecycle) / STATUS_TRANSITIONS_NAME


def _load_status_log(lifecycle) -> list:
    path = _status_log_path(lifecycle)
    if not path.is_file():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _save_status_log(lifecycle, entries: list) -> None:
    """Persist the status-transition audit log via staged atomic write."""
    path = _status_log_path(lifecycle)
    lifecycle.store._stage_and_commit(
        lifecycle.store.staging_dir, path, _canonical(entries))


def latest_receipt_status(lifecycle, receipt_sha256) -> Optional[str]:
    """Return the latest audited status for a receipt, or None."""
    for entry in reversed(_load_status_log(lifecycle)):
        if entry.get("receipt_sha256") == receipt_sha256:
            return entry.get("to_status")
    return None


def record_status_transition(lifecycle, receipt_sha256: str, *,
                             from_status: str, to_status: str) -> dict:
    """Append one auditable status transition for a receipt binding.

    Transitions must advance along ``_STATUS_ORDER`` (or be an
    idempotent repeat of the current status). The chain is hashed so
    an edited or reordered log fails closed. This is the only
    permitted mechanism for changing ``local_finalization_status``.
    """
    if from_status not in _STATUS_ORDER or to_status not in _STATUS_ORDER:
        raise ValueError("unknown receipt finalization status")
    from_idx = _STATUS_ORDER.index(from_status)
    to_idx = _STATUS_ORDER.index(to_status)
    if to_idx < from_idx:
        raise ValueError("receipt status transitions are monotonic")
    # Adjacent advance, or prepared -> awaiting_external_anchor (the
    # durable local-finalization write collapses prepared and
    # locally_finalized into one audited step).
    permitted = to_idx == from_idx or to_idx == from_idx + 1 or (
        from_status == "prepared" and
        to_status == "awaiting_external_anchor")
    if not permitted:
        raise ValueError("receipt status transition is not adjacent")
    current = latest_receipt_status(lifecycle, receipt_sha256)
    if current == to_status:
        for entry in reversed(_load_status_log(lifecycle)):
            if entry.get("receipt_sha256") == receipt_sha256 and \
                    entry.get("to_status") == to_status:
                return entry
    if current is not None and current != from_status:
        raise ValueError(
            "status transition does not continue the audited chain")
    entries = _load_status_log(lifecycle)
    previous = entries[-1]["entry_sha256"] if entries else None
    entry = {
        "receipt_sha256": receipt_sha256,
        "from_status": from_status,
        "to_status": to_status,
        "previous_entry_sha256": previous,
    }
    entry["entry_sha256"] = _sha256(_canonical(entry))
    entries.append(entry)
    _save_status_log(lifecycle, entries)
    return entry


def store_receipt(lifecycle, receipt: Mapping) -> dict:
    """Durably store a prepared receipt (staged atomic write).

    Idempotent: an already-stored receipt with the same binding is
    returned unchanged. The stored copy is marked
    ``awaiting_external_anchor`` — locally finalized, externally
    pending — and that transition is recorded in the status audit
    log. It is never marked externally verified here.
    """
    directory = _receipts_dir(lifecycle)
    binding = receipt["receipt_sha256"]
    final_path = directory / f"{binding}.json"
    if final_path.is_file():
        stored = json.loads(final_path.read_text(encoding="utf-8"))
        # Heal a missing status-audit entry after a crash between the
        # receipt write and the transition write; never invent a
        # different binding or status. If audit already reached
        # awaiting_external_anchor or later, return idempotently.
        if stored.get("receipt_sha256") != binding:
            raise ValueError(
                "stored receipt binding disagrees with the requested "
                "binding; recovery fails closed")
        audited = latest_receipt_status(lifecycle, binding)
        if audited is None:
            record_status_transition(
                lifecycle, binding, from_status="prepared",
                to_status="awaiting_external_anchor")
        return stored
    stored = copy.deepcopy(dict(receipt))
    stored["local_finalization_status"] = "awaiting_external_anchor"
    # Receipt first, then the status transition: a crash between them
    # recovers by re-invoking store_receipt, which sees the file and
    # records the missing transition.
    lifecycle.store._stage_and_commit(
        lifecycle.store.staging_dir, final_path, _canonical(stored))
    audited = latest_receipt_status(lifecycle, binding)
    if audited is None:
        record_status_transition(
            lifecycle, binding, from_status="prepared",
            to_status="awaiting_external_anchor")
    return stored


def mark_receipt_externally_verified(lifecycle, receipt_sha256: str,
                                     *, verified_anchor: bool) -> dict:
    """Record the audited transition to externally_verified (PR-9).

    Requires ``verified_anchor=True`` from a trusted anchoring
    verification — a caller boolean alone is never accepted as proof.
    """
    if not verified_anchor:
        raise ValueError(
            "externally_verified requires a trusted anchoring "
            "verification result, not a caller assertion")
    current = latest_receipt_status(lifecycle, receipt_sha256)
    if current != "awaiting_external_anchor" and \
            current != "externally_verified":
        raise ValueError(
            "only a locally finalized, awaiting receipt may be marked "
            "externally verified")
    entry = record_status_transition(
        lifecycle, receipt_sha256,
        from_status="awaiting_external_anchor",
        to_status="externally_verified")
    stored = load_stored_receipt(lifecycle, receipt_sha256)
    if stored is None:
        raise ValueError("receipt is absent from durable storage")
    stored = copy.deepcopy(stored)
    stored["local_finalization_status"] = "externally_verified"
    path = _receipts_dir(lifecycle) / f"{receipt_sha256}.json"
    lifecycle.store._stage_and_commit(
        lifecycle.store.staging_dir, path, _canonical(stored))
    return entry


def load_stored_receipt(lifecycle, receipt_sha256: str) -> Optional[dict]:
    path = _receipts_dir(lifecycle) / f"{receipt_sha256}.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def finalize_attempt_with_receipt(lifecycle, slot_id, disposition, *,
                                  slot_position: int,
                                  frozen_prompt_sha256: str,
                                  evidence_bundle=None,
                                  validation_report=None,
                                  authorization=None,
                                  class_d_conflict_count: int = 0,
                                  output_state=None,
                                  no_output_reason=None) -> dict:
    """Finalize an attempt through PR-7 and durably store its receipt.

    Exactly-once: an already-finalized attempt is recognized through
    the lifecycle's idempotent finalization, the receipt is rebuilt
    deterministically (identical binding), and the stored receipt is
    returned without duplication. A crash between the terminal event
    and the receipt write therefore recovers by simply calling this
    again — the generation attempt is never duplicated and existing
    evidence is never overwritten. If recovery cannot prove the
    existing terminal state, the call fails closed.
    """
    # Validate the receipt payload against evidence *before* committing
    # a terminal disposition, so a rejected conflict count or missing
    # ADMIT qualification cannot leave a durable terminal record that
    # disagrees with the evidence.
    report = validation_report
    if report is None and evidence_bundle is not None:
        report = validate_evidence_bundle(evidence_bundle)
    if disposition == "ADMIT":
        if report is None:
            raise ValueError(
                "ADMIT requires a completed evidence validation report")
        if not report.evidence_eligible or \
                report.technical_validation != "passed":
            raise ValueError(
                "ADMIT requires complete evidence qualification and "
                "technical validation")
        if class_d_conflict_count and report.class_d_conflict_count != \
                class_d_conflict_count:
            raise ValueError(
                "class_d_conflict_count disagrees with the validated "
                "conflict records and cannot be altered independently")
        if not class_d_conflict_count:
            class_d_conflict_count = report.class_d_conflict_count

    record = lifecycle.finalize_attempt(
        slot_id, disposition, authorization=authorization,
        class_d_conflict_count=class_d_conflict_count)
    if record.get("disposition") != disposition:
        raise ValueError(
            "durable terminal disposition disagrees with the requested "
            "finalization; recovery fails closed")
    terminal_seqs = [
        e["seq"] for e in lifecycle.store.events
        if e.get("type") == "attempt_terminal"
        and e.get("slot_id") == slot_id
        and e.get("attempt_number") == record["attempt_number"]]
    if not terminal_seqs:
        raise ValueError(
            "no durable terminal event exists for this attempt; "
            "recovery fails closed")
    cutoff = terminal_seqs[0]
    history = [
        e for e in lifecycle.store.events
        if e.get("slot_id") == slot_id
        and e.get("attempt_number") in (None, record["attempt_number"])
        and e["seq"] <= cutoff]
    receipt = build_terminal_receipt(
        terminal_record=record, slot_position=slot_position,
        frozen_prompt_sha256=frozen_prompt_sha256,
        event_history=history, evidence_bundle=evidence_bundle,
        validation_report=report, output_state=output_state,
        no_output_reason=no_output_reason)
    return store_receipt(lifecycle, receipt)
