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
state), so the binding is never self-referential; the status is instead
verified against the durable lifecycle record. Evidence integrity is
kept separate from evidence truth and from authenticated host
provenance: a commitment proves bytes are unchanged, never that their
claims are true or class-C authentic.

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
    evidence_artifacts = []
    attested_fields, recorded_fields = [], []
    attestation_commitment = None
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
        for name, fld in (observation.get("observations") or {}).items():
            if fld.get("status") == "operator_attested":
                attested_fields.append(name)
            elif fld.get("status") == "operator_recorded":
                recorded_fields.append(name)
    if report is not None:
        class_d_count = report.class_d_conflict_count
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
        class_d_count = int(terminal_record.get("class_d_conflict_count", 0))
        authenticated = False
        evidence_validation = None
    record_conflict_count = int(
        terminal_record.get("class_d_conflict_count") or 0)
    if record_conflict_count:
        class_d_count = record_conflict_count
    provenance = (
        "authenticated_class_c_supported" if authenticated
        else "operator_evidenced_with_class_d_conflict" if class_d_count
        else "operator_evidenced")

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
        "authorization": copy.deepcopy(
            terminal_record.get("authorization")),
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
            if status == "externally_verified" and not anchored:
                add("UNANCHORED_AS_VERIFIED", "local_finalization_status",
                    "an unanchored receipt must not be represented as "
                    "externally verified")

    return ReceiptVerification(tuple(findings))


# =============================================================================
# Durable lifecycle integration (PR-7 state machine; no competing lifecycle)
# =============================================================================


def _receipts_dir(lifecycle) -> Path:
    directory = lifecycle.store.root / "receipts"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def store_receipt(lifecycle, receipt: Mapping) -> dict:
    """Durably store a prepared receipt (staged atomic write).

    Idempotent: an already-stored receipt with the same binding is
    returned unchanged. The stored copy is marked
    ``awaiting_external_anchor`` — locally finalized, externally
    pending; it is never marked externally verified here.
    """
    directory = _receipts_dir(lifecycle)
    final_path = directory / f"{receipt['receipt_sha256']}.json"
    if final_path.is_file():
        return json.loads(final_path.read_text(encoding="utf-8"))
    stored = copy.deepcopy(dict(receipt))
    stored["local_finalization_status"] = "awaiting_external_anchor"
    lifecycle.store._stage_and_commit(
        lifecycle.store.staging_dir, final_path, _canonical(stored))
    return stored


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
    evidence is never overwritten.
    """
    record = lifecycle.finalize_attempt(
        slot_id, disposition, authorization=authorization,
        class_d_conflict_count=class_d_conflict_count)
    terminal_seqs = [
        e["seq"] for e in lifecycle.store.events
        if e.get("type") == "attempt_terminal"
        and e.get("slot_id") == slot_id
        and e.get("attempt_number") == record["attempt_number"]]
    cutoff = terminal_seqs[0] if terminal_seqs else -1
    history = [
        e for e in lifecycle.store.events
        if e.get("slot_id") == slot_id
        and e.get("attempt_number") in (None, record["attempt_number"])
        and e["seq"] <= cutoff]
    receipt = build_terminal_receipt(
        terminal_record=record, slot_position=slot_position,
        frozen_prompt_sha256=frozen_prompt_sha256,
        event_history=history, evidence_bundle=evidence_bundle,
        validation_report=validation_report, output_state=output_state,
        no_output_reason=no_output_reason)
    return store_receipt(lifecycle, receipt)
