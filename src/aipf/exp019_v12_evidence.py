"""EXP-019 v1.2 runtime evidence validator (PR-6, Stage 2).

This module validates evidence bundles against the approved v1.2
engineering contract (gate G1). It is a *validator only*:

* it performs no generation, creates no attempt event, commits no
  disposition, writes no checkpoint, and creates no run root;
* EXP-019 v1.2 remains unregistered in ``frozen_protocol()`` and cannot be
  activated through this module — there is deliberately no run, allocation,
  generation, or checkpoint API here;
* it never mutates the evidence it is given and never overwrites any
  artifact; findings reference artifacts and fields by name, never by
  treatment-bearing value.

The cross-artifact rules enforced here are exactly the ones the draft
schemas reserve for runtime validation: digest recomputation, class-C
authentication, attested-vs-recorded source resolution, cross-artifact
identity binding, temporal ordering, action-log integrity, and
returned-count agreement.

Q1–Q5 in this module follow the PR-6 specification, which subsumes the
merged evidence contract's qualifying requirements:

* Q1 contemporaneous request capture (contract Q1);
* Q2 contemporaneous response capture (contract Q2);
* Q3 downloaded artifact identity and digest association (contract Q4,
  with Q2's artifact association);
* Q4 hash-bound operator attestation (contract Q5 for attested claims);
* Q5 completed action log and prompt-integrity evidence (contract Q3,
  plus frozen/pasted prompt-digest consistency and the separate
  rendered-request textual comparison).

A SHA-256 digest alone never establishes class-C evidence: a
``host_observed`` field is accepted as authenticated only when its
``source_ref`` appears in ``authenticated_class_c_refs``, the set of
references the caller has verified through an authenticated host channel
outside this validator. Screenshots, clipboard evidence, and model
statements can never supply that set.
"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field as dataclass_field
from datetime import datetime
from pathlib import Path
from typing import AbstractSet, Mapping, Optional

from jsonschema import Draft202012Validator

_SCHEMA_FILES = {
    "observation": "exp019_v1_2_observation.schema.json",
    "attestation": "exp019_v1_2_attestation.schema.json",
    "action_log": "exp019_v1_2_action_log.schema.json",
    "request_capture": "exp019_v1_2_request_capture.schema.json",
    "response_capture": "exp019_v1_2_response_capture.schema.json",
}

_DENIED_ROLES = {"reviewer", "public"}
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


@dataclass(frozen=True)
class Finding:
    """One validation finding. Messages name fields, never private values."""

    code: str
    severity: str  # "error" | "warning" | "info"
    artifact: str
    field: str
    message: str


@dataclass(frozen=True)
class QResult:
    """Outcome of one Q1–Q5 check (``passed=None`` means not applicable)."""

    check: str
    passed: Optional[bool]
    codes: tuple = ()


@dataclass(frozen=True)
class ValidationReport:
    """Structured, outcome-safe validation result.

    ``admission_eligibility`` is an eligibility assessment only; this
    validator commits no disposition.
    """

    findings: tuple
    q_results: tuple
    outcome_classification: str  # returned_evidenced | no_result_evidenced |
    #                              unknown_outcome | invalid_evidence
    admission_eligibility: str  # eligible_for_admit |
    #                             eligible_for_admit_with_conflict |
    #                             not_eligible_for_admit
    class_d_conflict_count: int = 0
    b_c_material_conflicts: tuple = ()

    @property
    def errors(self) -> tuple:
        return tuple(f for f in self.findings if f.severity == "error")

    @property
    def admit_eligible(self) -> bool:
        return self.admission_eligibility in (
            "eligible_for_admit", "eligible_for_admit_with_conflict")

    @property
    def admit_with_conflict(self) -> bool:
        return self.admission_eligibility == "eligible_for_admit_with_conflict"


def _default_schema_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "schemas"


def _parse_time(value) -> Optional[datetime]:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class _Collector:
    def __init__(self) -> None:
        self.findings: list = []

    def add(self, code, severity, artifact, field, message) -> None:
        self.findings.append(Finding(code, severity, artifact, field, message))

    def error(self, code, artifact, field, message) -> None:
        self.add(code, "error", artifact, field, message)

    def codes_for(self, artifact=None) -> set:
        return {f.code for f in self.findings
                if artifact is None or f.artifact == artifact}


def validate_evidence_bundle(
    bundle: Mapping,
    *,
    authenticated_class_c_refs: AbstractSet = frozenset(),
    supporting_artifact_bytes: Optional[Mapping] = None,
    requester_role: str = "operator",
    schema_dir: Optional[Path] = None,
) -> ValidationReport:
    """Validate one synthetic-or-real evidence bundle, without side effects.

    ``bundle`` maps artifact names (``observation``, ``attestation``,
    ``action_log``, ``request_capture``, ``response_capture``) to parsed
    JSON objects (or ``None`` where an artifact legitimately does not
    exist) and ``raster_bytes`` to the downloaded bytes or ``None``.

    ``authenticated_class_c_refs`` is the set of ``source_ref`` digests the
    caller has verified through an authenticated host channel *outside*
    this validator; a digest by itself authenticates nothing.

    ``supporting_artifact_bytes``, when supplied, maps ``source_ref``
    digests to the supporting artifact bytes so source references can be
    recomputed and resolved; unresolved references then fail.
    """
    work = copy.deepcopy(dict(bundle))
    out = _Collector()

    if requester_role in _DENIED_ROLES:
        out.error("ROLE_ACCESS_DENIED", "bundle", "requester_role",
                  "this role may not access private evidence validation")
        return _report(out, {}, "invalid_evidence", 0, ())

    # ---- schema integrity -------------------------------------------------
    schema_path = Path(schema_dir) if schema_dir else _default_schema_dir()
    artifacts = {}
    for name, filename in _SCHEMA_FILES.items():
        artifact = work.get(name)
        artifacts[name] = artifact
        if artifact is None:
            continue
        schema = json.loads((schema_path / filename).read_text(
            encoding="utf-8"))
        validator = Draft202012Validator(schema)
        for err in validator.iter_errors(artifact):
            out.error("SCHEMA_INVALID", name,
                      ".".join(str(p) for p in err.absolute_path) or "(root)",
                      "artifact does not satisfy its v1.2 draft schema")

    observation = artifacts.get("observation") or {}
    obs_fields = observation.get("observations", {}) if observation else {}
    attestation = artifacts.get("attestation")
    action_log = artifacts.get("action_log")
    request_capture = artifacts.get("request_capture")
    response_capture = artifacts.get("response_capture")
    raster = work.get("raster_bytes")

    # ---- cross-artifact identity -------------------------------------------
    identities = {
        (a.get("opaque_slot_id"), a.get("attempt_number"))
        for a in artifacts.values() if a is not None
    }
    if len(identities) > 1:
        out.error("IDENTITY_MISMATCH", "bundle", "opaque_slot_id/attempt_number",
                  "artifacts do not share one opaque identity and attempt")

    # ---- field authority ----------------------------------------------------
    authenticated = set(authenticated_class_c_refs or ())
    attested_field_names = []
    for name, fld in obs_fields.items():
        status, ref = fld.get("status"), fld.get("source_ref")
        if status == "host_observed" and ref not in authenticated:
            out.error("CLASS_C_NOT_AUTHENTICATED", "observation", name,
                      "host_observed claim is not backed by an authenticated "
                      "host source; a digest alone does not authenticate")
        if status == "operator_attested":
            attested_field_names.append(name)
        if status in ("not_observable", "not_applicable"):
            if fld.get("value") is not None or ref is not None:
                out.error("UNAVAILABLE_FIELD_NOT_NULL", "observation", name,
                          "unavailable fields must carry null value and ref")
        if supporting_artifact_bytes is not None and ref is not None:
            supplied = supporting_artifact_bytes.get(ref)
            if supplied is None:
                out.error("SOURCE_REF_UNRESOLVED", "observation", name,
                          "source_ref does not resolve to supplied evidence")
            elif _sha256(supplied) != ref:
                out.error("SOURCE_REF_DIGEST_MISMATCH", "observation", name,
                          "supporting bytes do not recompute to source_ref")

    # Missing class-C telemetry is expected and informational only.
    if any(f.get("status") == "not_observable" for f in obs_fields.values()):
        out.add("CLASS_C_TELEMETRY_MISSING", "info", "observation",
                "host_telemetry", "some host telemetry is not observable")

    # ---- class-D conflicts ---------------------------------------------------
    class_d_conflicts = 0
    for report_entry in observation.get("model_reports", []) or []:
        fld_name = report_entry.get("field")
        authoritative = obs_fields.get(fld_name)
        if authoritative is not None and (
                authoritative.get("value") != report_entry.get("claimed_value")):
            class_d_conflicts += 1
            out.add("CLASS_D_CONFLICT", "warning", "observation", fld_name,
                    "model report conflicts with authoritative evidence; "
                    "authoritative evidence is unchanged")

    # ---- timestamps and log integrity ---------------------------------------
    request_time = _parse_time((request_capture or {}).get("captured_at_utc"))
    response_time = _parse_time((response_capture or {}).get("captured_at_utc"))
    if request_capture is not None and request_time is None:
        out.error("TIMESTAMP_UNPARSEABLE", "request_capture", "captured_at_utc",
                  "capture timestamp cannot be parsed")
    if response_capture is not None and response_time is None:
        out.error("TIMESTAMP_UNPARSEABLE", "response_capture", "captured_at_utc",
                  "capture timestamp cannot be parsed")
    if (request_time is not None and response_time is not None
            and response_time < request_time):
        out.error("TEMPORAL_ORDER_VIOLATION", "response_capture",
                  "captured_at_utc", "response capture precedes request capture")

    log_entries = (action_log or {}).get("entries", []) if action_log else []
    log_times = []
    if action_log is not None:
        seqs = [e.get("seq") for e in log_entries]
        if seqs != list(range(1, len(seqs) + 1)):
            out.error("ACTION_LOG_SEQUENCE", "action_log", "entries.seq",
                      "action log sequence is not contiguous from 1")
        log_times = [_parse_time(e.get("at_utc")) for e in log_entries]
        if any(t is None for t in log_times):
            out.error("TIMESTAMP_UNPARSEABLE", "action_log", "entries.at_utc",
                      "an action log timestamp cannot be parsed")
        elif any(b < a for a, b in zip(log_times, log_times[1:])):
            out.error("ACTION_LOG_ORDER", "action_log", "entries.at_utc",
                      "action log timestamps are not monotonically ordered")
        closed = _parse_time(action_log.get("closed_at_utc"))
        if closed is not None and log_times and log_times[-1] is not None \
                and closed < log_times[-1]:
            out.error("ACTION_LOG_ORDER", "action_log", "closed_at_utc",
                      "log closes before its last entry")

    # ---- Q1: contemporaneous request capture --------------------------------
    q: dict = {}
    q1_codes = []
    if request_capture is None:
        q1_codes.append("Q1_MISSING_REQUEST_CAPTURE")
    else:
        if "SCHEMA_INVALID" in out.codes_for("request_capture"):
            q1_codes.append("Q1_REQUEST_SCHEMA_INVALID")
        if request_capture.get("attachment_count") != 0:
            q1_codes.append("Q1_ATTACHMENT_PRESENT")
        if request_capture.get("generation_request_count") != 1:
            q1_codes.append("Q1_REQUEST_COUNT")
        submitted = next((e for e in log_entries
                          if e.get("action") == "generation_request_submitted"),
                         None)
        if submitted is not None and request_time is not None:
            if _parse_time(submitted.get("at_utc")) != request_time:
                q1_codes.append("Q1_NOT_CONTEMPORANEOUS")
    q["Q1"] = QResult("Q1", not q1_codes, tuple(q1_codes))

    # ---- Q2: contemporaneous response capture --------------------------------
    image_returned = (response_capture or {}).get("image_returned")
    q2_codes = []
    if response_capture is None:
        q2_codes.append("Q2_MISSING_RESPONSE_CAPTURE")
    else:
        if "SCHEMA_INVALID" in out.codes_for("response_capture"):
            q2_codes.append("Q2_RESPONSE_SCHEMA_INVALID")
        if image_returned is True:
            if response_capture.get("returned_image_count", 0) < 1:
                q2_codes.append("Q2_RETURNED_COUNT")
            if not response_capture.get("artifact_id"):
                q2_codes.append("Q2_MISSING_ARTIFACT_ID")
        elif image_returned is False:
            if response_capture.get("artifact_id") is not None:
                q2_codes.append("Q2_FABRICATED_ARTIFACT_ID")
                out.error("FABRICATED_ARTIFACT_ID", "response_capture",
                          "artifact_id",
                          "a no-result capture must not carry an artifact id")
            if not response_capture.get("no_result_evidence"):
                q2_codes.append("Q2_NO_RESULT_WITHOUT_EVIDENCE")
    q["Q2"] = QResult("Q2", not q2_codes if response_capture is not None else None,
                      tuple(q2_codes))

    # ---- Q3: downloaded artifact identity and digest association -------------
    raster_sha = _sha256(raster) if isinstance(raster, (bytes, bytearray)) else None
    q3_codes = []
    output_field = obs_fields.get("output_sha256", {})
    if image_returned is True:
        if raster_sha is None:
            q3_codes.append("Q3_RASTER_MISSING")
        else:
            if not bytes(raster).startswith(_PNG_SIGNATURE):
                q3_codes.append("Q3_INVALID_RASTER")
                out.error("INVALID_RASTER", "raster_bytes", "bytes",
                          "downloaded bytes are not a PNG raster")
            if output_field.get("value") != raster_sha:
                q3_codes.append("Q3_OUTPUT_DIGEST_MISMATCH")
                out.error("OUTPUT_DIGEST_MISMATCH", "observation",
                          "output_sha256",
                          "observation digest does not recompute from bytes")
            artifact_field = obs_fields.get("output_artifact_id", {})
            if response_capture.get("artifact_id") != artifact_field.get("value"):
                q3_codes.append("Q3_ARTIFACT_ID_MISMATCH")
                out.error("ARTIFACT_ID_MISMATCH", "response_capture",
                          "artifact_id", "capture and observation disagree")
            for entry in log_entries:
                if entry.get("action") in ("artifact_downloaded",
                                           "artifact_hashed"):
                    if entry.get("artifact_sha256") != raster_sha:
                        q3_codes.append("Q3_LOG_DIGEST_MISMATCH")
                        out.error("LOG_DIGEST_MISMATCH", "action_log",
                                  entry.get("action"),
                                  "log digest does not recompute from bytes")
    q["Q3"] = QResult("Q3", not q3_codes if image_returned is True else None,
                      tuple(q3_codes))

    # ---- Q4: hash-bound operator attestation ----------------------------------
    q4_codes = []
    if attested_field_names or image_returned is True:
        if attestation is None:
            q4_codes.append("Q4_ATTESTATION_MISSING")
            out.error("ATTESTATION_MISSING", "attestation", "artifact",
                      "a returned attempt has no hash-bound operator "
                      "attestation")
        else:
            if "SCHEMA_INVALID" in out.codes_for("attestation"):
                q4_codes.append("Q4_ATTESTATION_SCHEMA_INVALID")
            if raster_sha is not None and \
                    attestation.get("artifact_digest_sha256") != raster_sha:
                q4_codes.append("Q4_ATTESTATION_DIGEST_MISMATCH")
                out.error("ATTESTATION_DIGEST_MISMATCH", "attestation",
                          "artifact_digest_sha256",
                          "attestation is not hash-bound to the artifact")
    if attestation is not None and image_returned is False:
        q4_codes.append("Q4_ATTESTATION_WITHOUT_ARTIFACT")
        out.error("ATTESTATION_WITHOUT_ARTIFACT", "attestation", "artifact",
                  "an attestation exists for an attempt with no artifact")
    q["Q4"] = QResult("Q4", not q4_codes if (attested_field_names or
                                             attestation is not None or
                                             image_returned is True) else None,
                      tuple(q4_codes))

    # ---- Q5: completed action log and prompt integrity -------------------------
    q5_codes = []
    if action_log is None:
        q5_codes.append("Q5_ACTION_LOG_MISSING")
    else:
        if "SCHEMA_INVALID" in out.codes_for("action_log"):
            q5_codes.append("Q5_ACTION_LOG_SCHEMA_INVALID")
        if "ACTION_LOG_SEQUENCE" in out.codes_for("action_log") or \
                "ACTION_LOG_ORDER" in out.codes_for("action_log"):
            q5_codes.append("Q5_ACTION_LOG_INTEGRITY")
        actions = [e.get("action") for e in log_entries]
        required = ["conversation_created", "prompt_pasted",
                    "generation_request_submitted"]
        if image_returned is True:
            required += ["response_captured", "artifact_downloaded",
                         "artifact_hashed", "slot_closed"]
        elif image_returned is False:
            required += ["response_captured", "slot_closed"]
        if any(a not in actions for a in required):
            q5_codes.append("Q5_ACTION_LOG_INCOMPLETE")
    # Prompt integrity: frozen vs pasted is a byte-digest equality;
    # rendered text is a separate textual comparison, never byte equality
    # against the frozen prompt digest.
    constants = observation.get("protocol_constants", {}) if observation else {}
    pasted = obs_fields.get("prompt_bytes_pasted_sha256", {}).get("value")
    rendered = obs_fields.get("prompt_text_rendered_sha256", {}).get("value")
    if constants:
        if pasted != constants.get("prompt_sha256"):
            q5_codes.append("Q5_FROZEN_PASTED_DIGEST_MISMATCH")
            out.error("PROMPT_DIGEST_MISMATCH", "observation",
                      "prompt_bytes_pasted_sha256",
                      "pasted bytes do not match the frozen prompt digest")
        if request_capture is not None:
            if request_capture.get("paste_sha256") != pasted:
                q5_codes.append("Q5_PASTE_BINDING_MISMATCH")
            if request_capture.get("rendered_request_text_sha256") != rendered:
                q5_codes.append("Q5_RENDERED_BINDING_MISMATCH")
            if request_capture.get("rendered_request_comparison") != \
                    "textual_match":
                q5_codes.append("Q5_RENDERED_TEXTUAL_MISMATCH")
                out.error("RENDERED_TEXTUAL_MISMATCH", "request_capture",
                          "rendered_request_comparison",
                          "rendered request text does not textually match")
    q["Q5"] = QResult("Q5", not q5_codes, tuple(q5_codes))

    # ---- B/C material conflicts ------------------------------------------------
    b_c_conflicts = []
    returned_field = obs_fields.get("returned_output_count", {})
    if (returned_field.get("status") == "host_observed"
            and returned_field.get("source_ref") in authenticated
            and response_capture is not None
            and returned_field.get("value") !=
            response_capture.get("returned_image_count")):
        b_c_conflicts.append("BC_RETURNED_COUNT_CONFLICT")
        out.error("BC_MATERIAL_CONFLICT", "observation",
                  "returned_output_count",
                  "authenticated class-C evidence conflicts with class-B "
                  "capture evidence")

    # ---- outcome classification and eligibility ----------------------------------
    has_errors = any(f.severity == "error" for f in out.findings)
    if response_capture is None:
        outcome = "unknown_outcome"
        out.add("UNKNOWN_OUTCOME", "warning", "response_capture", "artifact",
                "no response capture exists; the host outcome is unknown, "
                "not a confirmed failure")
    elif image_returned is False:
        outcome = ("no_result_evidenced"
                   if response_capture.get("no_result_evidence")
                   and not has_errors
                   and not q["Q1"].codes and not q5_codes else "invalid_evidence")
    elif image_returned is True:
        outcome = "returned_evidenced" if not has_errors else "invalid_evidence"
    else:
        outcome = "invalid_evidence"

    all_q_pass = all(r.passed for r in q.values() if r.passed is not None) \
        and q["Q1"].passed and q["Q2"].passed and q["Q3"].passed \
        and q["Q5"].passed
    if outcome == "returned_evidenced" and all_q_pass and not has_errors:
        eligibility = ("eligible_for_admit_with_conflict"
                       if class_d_conflicts else "eligible_for_admit")
    else:
        eligibility = "not_eligible_for_admit"

    return _report(out, q, outcome, class_d_conflicts, tuple(b_c_conflicts),
                   eligibility)


def _report(out, q, outcome, class_d_conflicts, b_c_conflicts,
            eligibility="not_eligible_for_admit") -> ValidationReport:
    return ValidationReport(
        findings=tuple(out.findings),
        q_results=tuple(q[k] for k in ("Q1", "Q2", "Q3", "Q4", "Q5")
                        if k in q),
        outcome_classification=outcome,
        admission_eligibility=eligibility,
        class_d_conflict_count=class_d_conflicts,
        b_c_material_conflicts=tuple(b_c_conflicts),
    )
