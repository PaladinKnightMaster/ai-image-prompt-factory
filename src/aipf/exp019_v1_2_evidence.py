"""EXP-019 v1.2 runtime evidence validator (PR-6).

This module is authorized, non-executing evidence-validation code. It:

* performs no generation, creates no attempt event, commits no
  disposition, writes no checkpoint, creates no run root, and allocates
  no treatment;
* leaves EXP-019 v1.2 unregistered in ``frozen_protocol()`` — there is
  deliberately no run, allocation, generation, or checkpoint API here;
* never mutates the evidence it is given and never overwrites any
  artifact; findings reference artifacts and fields by name, never by
  treatment-bearing value.

Canonical Q1-Q5 semantics (merged G1 engineering contract; the contract
is normative and this module follows it, not the reverse):

* Q1 — request capture: a request capture taken at submission;
* Q2 — response capture: a response capture taken when the image
  appears, a distinct later artifact;
* Q3 — action log: an action log whose sequence and timing the runtime
  can verify;
* Q4 — artifact digests: artifact digests recomputed by the runtime
  against the actual bytes (including frozen/pasted prompt-digest
  consistency as digest recomputation, with the rendered-request
  *textual* comparison kept under Q1 as a property of the capture);
* Q5 — operator attestation: where a field claims ``operator_attested``,
  a hash-bound attestation made for that invocation, and where a field
  claims ``operator_recorded``, a contemporaneous record created at
  action time.

Evidence eligibility is not scientific admission. This validator reports
whether evidence is *eligible* for the admission rules; the admission
decision itself belongs to the later attempt lifecycle. In particular, a
raster is never treated as technically evaluable on a file signature
alone: raster bytes are fully decoded (see ``technical_validation`` in
the report), and if no trusted decoder is available the technical state
is ``pending`` and the evidence is not eligible.

Class-C boundary. A SHA-256 digest alone never establishes class-C
evidence, and neither do screenshots, clipboard evidence, model
statements, or a caller-supplied collection of digests. ``host_observed``
fields are treated as authenticated only when the caller supplies a
``host_authenticator``: a callable, provided by a trusted host-integration
layer that itself obtained the reference through an authenticated host
channel, which returns ``True`` for a verified ``source_ref``. Production
code paths without such a layer must pass no authenticator, in which case
no ``host_observed`` claim is elevated. This repository contains no
authenticated host channel, so nothing here can manufacture class-C
evidence.

Artifact integrity is reported in explicit levels (``source_integrity``),
distinguishing a merely *declared* digest (a digest string is present but
its bytes were never supplied), a *recomputed* digest (supplied bytes hash
to the declared digest), a *verified binding* (a recomputed digest that
also matches the cross-artifact binding, e.g. the raster or the
attestation), and an *authenticated source* (class-C verification through
the boundary above). Required evidence whose original bytes are
unavailable therefore never receives a verified-integrity level merely
because a digest string is present. Complete serialized artifacts may be
bound without any recursive self-hashing by supplying
``artifact_commitments``: externally computed SHA-256 digests of each
artifact's canonical serialization (see ``canonical_artifact_digest``).
"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Callable, Mapping, Optional

from jsonschema import Draft202012Validator

try:  # Pillow is the repository's existing raster decoder (see
    # ``aipf.exp019_host._raster`` / ``aipf.exp019_execution``).
    from PIL import Image as _PIL_Image
except ImportError:  # pragma: no cover - decoder absence is a state, not a crash
    _PIL_Image = None

_SCHEMA_FILES = {
    "observation": "exp019_v1_2_observation.schema.json",
    "attestation": "exp019_v1_2_attestation.schema.json",
    "action_log": "exp019_v1_2_action_log.schema.json",
    "request_capture": "exp019_v1_2_request_capture.schema.json",
    "response_capture": "exp019_v1_2_response_capture.schema.json",
}

_DENIED_ROLES = {"reviewer", "public"}
_DECODABLE_FORMATS = {"PNG", "JPEG", "WEBP"}

#: Canonical Q1-Q5 definitions from the merged G1 engineering contract
#: (docs/drafts/EXP-019-v1.2.0.EVIDENCE-CONTRACT-DRAFT.md, section 4).
Q_DEFINITIONS = {
    "Q1": "request capture",
    "Q2": "response capture",
    "Q3": "action log",
    "Q4": "artifact digests",
    "Q5": "operator attestation",
}


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
    """Outcome of one canonical Q1-Q5 check (``passed=None``: not applicable)."""

    check: str
    definition: str
    passed: Optional[bool]
    codes: tuple = ()


@dataclass(frozen=True)
class SourceIntegrity:
    """Integrity level for one source reference.

    ``level`` is one of ``not_applicable`` (no digest declared),
    ``declared_only`` (digest string present, bytes never supplied),
    ``unresolved`` (bytes were supplied for verification but this
    reference was not among them), ``mismatch`` (supplied bytes do not
    recompute to the declared digest), ``recomputed`` (supplied bytes
    recompute to the declared digest), or ``verified_binding`` (a
    recomputed digest that also matches its cross-artifact binding).
    ``authenticated`` is true only for class-C references verified
    through the trusted host-authenticator boundary.
    """

    field: str
    level: str
    authenticated: bool = False


@dataclass(frozen=True)
class ValidationReport:
    """Structured, outcome-safe validation result.

    ``evidence_eligibility`` assesses eligibility for the admission
    rules only; this validator commits no disposition and performs no
    scientific admission. ``technical_validation`` is ``passed``,
    ``failed``, ``pending`` (no trusted decoder available), or
    ``not_applicable`` (no raster was returned).
    """

    findings: tuple
    q_results: tuple
    outcome_classification: str  # returned_evidenced | no_result_evidenced |
    #                              unknown_outcome | invalid_evidence
    evidence_eligibility: str  # evidence_eligible |
    #                            evidence_eligible_with_conflict |
    #                            not_evidence_eligible
    technical_validation: str = "not_applicable"
    raster_format: Optional[str] = None
    raster_dimensions: Optional[tuple] = None
    class_d_conflict_count: int = 0
    b_c_material_conflicts: tuple = ()
    source_integrity: tuple = ()

    @property
    def errors(self) -> tuple:
        return tuple(f for f in self.findings if f.severity == "error")

    @property
    def evidence_eligible(self) -> bool:
        return self.evidence_eligibility in (
            "evidence_eligible", "evidence_eligible_with_conflict")

    @property
    def evidence_eligible_with_conflict(self) -> bool:
        return self.evidence_eligibility == "evidence_eligible_with_conflict"

    # Backwards-compatible aliases: these describe *evidence* eligibility
    # for admission, never an admission decision.
    @property
    def admit_eligible(self) -> bool:
        return self.evidence_eligible

    @property
    def admit_with_conflict(self) -> bool:
        return self.evidence_eligible_with_conflict

    @property
    def admission_eligibility(self) -> str:
        return {
            "evidence_eligible": "eligible_for_admit",
            "evidence_eligible_with_conflict":
                "eligible_for_admit_with_conflict",
            "not_evidence_eligible": "not_eligible_for_admit",
        }[self.evidence_eligibility]


def canonical_artifact_digest(artifact: Mapping) -> str:
    """SHA-256 of an artifact's canonical JSON serialization.

    This binds a complete serialized artifact from outside it; it is not
    a self-hash and involves no recursion into embedded digest fields
    beyond their serialized bytes.
    """
    canonical = json.dumps(artifact, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


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


def _decode_raster(data: bytes):
    """Fully decode raster bytes with the repository's decoder (Pillow).

    Returns ``(status, format, dimensions)`` where status is ``passed``
    (the entire raster decodes and has a decodable format), ``failed``
    (bytes were supplied but do not fully decode — a plausible header is
    not an evaluable image), or ``pending`` (no trusted decoder is
    available, so technical validation cannot be performed here).
    """
    if _PIL_Image is None:
        return ("pending", None, None)
    try:
        with _PIL_Image.open(BytesIO(data)) as image:
            image.verify()
        with _PIL_Image.open(BytesIO(data)) as image:
            image.load()
            if image.format not in _DECODABLE_FORMATS:
                return ("failed", image.format, None)
            return ("passed", image.format, (image.width, image.height))
    except (OSError, ValueError, SyntaxError):
        return ("failed", None, None)


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
    host_authenticator: Optional[Callable[[str], bool]] = None,
    supporting_artifact_bytes: Optional[Mapping] = None,
    artifact_commitments: Optional[Mapping] = None,
    requester_role: str = "operator",
    schema_dir: Optional[Path] = None,
) -> ValidationReport:
    """Validate one evidence bundle, without side effects.

    ``bundle`` maps artifact names (``observation``, ``attestation``,
    ``action_log``, ``request_capture``, ``response_capture``) to parsed
    JSON objects (or ``None`` where an artifact legitimately does not
    exist) and ``raster_bytes`` to the downloaded bytes or ``None``.

    ``host_authenticator`` is the trusted class-C boundary described in
    the module docstring: a callable from a trusted host-integration
    layer returning ``True`` only for ``source_ref`` values it verified
    through an authenticated host channel. A collection of digests is
    not an authenticator and is rejected; a digest by itself
    authenticates nothing.

    ``supporting_artifact_bytes``, when supplied, maps ``source_ref``
    digests to the supporting artifact bytes so declared digests can be
    recomputed; unresolved references then fail. When it is not
    supplied, digests remain at the ``declared_only`` integrity level.

    ``artifact_commitments``, when supplied, maps artifact names to
    externally computed canonical-serialization digests (see
    ``canonical_artifact_digest``) binding each complete artifact.
    """
    if host_authenticator is not None and not callable(host_authenticator):
        raise TypeError(
            "host_authenticator must be a callable from a trusted "
            "host-integration layer; a collection of digests cannot "
            "authenticate class-C evidence")
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

    # ---- external artifact commitments -------------------------------------
    for name, expected in (artifact_commitments or {}).items():
        artifact = artifacts.get(name)
        if artifact is None:
            out.error("ARTIFACT_COMMITMENT_UNRESOLVED", "bundle", name,
                      "a commitment was supplied for a missing artifact")
        elif canonical_artifact_digest(artifact) != expected:
            out.error("ARTIFACT_COMMITMENT_MISMATCH", "bundle", name,
                      "artifact bytes do not match the external commitment")

    # ---- cross-artifact identity -------------------------------------------
    identities = {
        (a.get("opaque_slot_id"), a.get("attempt_number"))
        for a in artifacts.values() if a is not None
    }
    if len(identities) > 1:
        out.error("IDENTITY_MISMATCH", "bundle", "opaque_slot_id/attempt_number",
                  "artifacts do not share one opaque identity and attempt")

    # ---- field authority and source integrity -------------------------------
    def _authenticated(ref) -> bool:
        return bool(host_authenticator is not None and ref is not None
                    and host_authenticator(ref))

    integrity: list = []
    attested_field_names = []
    recorded_field_names = []
    for name, fld in obs_fields.items():
        status, ref = fld.get("status"), fld.get("source_ref")
        authenticated = status == "host_observed" and _authenticated(ref)
        if status == "host_observed" and not authenticated:
            out.error("CLASS_C_NOT_AUTHENTICATED", "observation", name,
                      "host_observed claim is not verified through the "
                      "trusted host-authenticator boundary; a digest or "
                      "claimed status alone does not authenticate")
        if status == "operator_attested":
            attested_field_names.append(name)
        if status == "operator_recorded":
            recorded_field_names.append(name)
        if status in ("not_observable", "not_applicable"):
            if fld.get("value") is not None or ref is not None:
                out.error("UNAVAILABLE_FIELD_NOT_NULL", "observation", name,
                          "unavailable fields must carry null value and ref")
        if ref is None:
            level = "not_applicable"
        elif supporting_artifact_bytes is not None:
            supplied = supporting_artifact_bytes.get(ref)
            if supplied is None:
                level = "unresolved"
                out.error("SOURCE_REF_UNRESOLVED", "observation", name,
                          "source_ref does not resolve to supplied evidence")
            elif _sha256(supplied) != ref:
                level = "mismatch"
                out.error("SOURCE_REF_DIGEST_MISMATCH", "observation", name,
                          "supporting bytes do not recompute to source_ref")
            else:
                level = "recomputed"
        else:
            level = "declared_only"
            out.add("SOURCE_DECLARED_ONLY", "info", "observation", name,
                    "digest is declared but its bytes were not supplied, "
                    "so integrity is declared only, not verified")
        integrity.append(SourceIntegrity(name, level, authenticated))

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

    # ---- timestamps -----------------------------------------------------------
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

    q: dict = {}

    # ---- Q1: request capture --------------------------------------------------
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
        # The rendered request is compared textually; this is a property
        # of the capture, never byte equality against the frozen prompt.
        if request_capture.get("rendered_request_comparison") != \
                "textual_match":
            q1_codes.append("Q1_RENDERED_TEXTUAL_MISMATCH")
            out.error("RENDERED_TEXTUAL_MISMATCH", "request_capture",
                      "rendered_request_comparison",
                      "rendered request text does not textually match")
    q["Q1"] = QResult("Q1", Q_DEFINITIONS["Q1"], not q1_codes,
                      tuple(q1_codes))

    # ---- Q2: response capture --------------------------------------------------
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
    q["Q2"] = QResult("Q2", Q_DEFINITIONS["Q2"],
                      not q2_codes if response_capture is not None else None,
                      tuple(q2_codes))

    # ---- Q3: action log ---------------------------------------------------------
    q3_codes = []
    if action_log is None:
        q3_codes.append("Q3_ACTION_LOG_MISSING")
    else:
        if "SCHEMA_INVALID" in out.codes_for("action_log"):
            q3_codes.append("Q3_ACTION_LOG_SCHEMA_INVALID")
        if "ACTION_LOG_SEQUENCE" in out.codes_for("action_log") or \
                "ACTION_LOG_ORDER" in out.codes_for("action_log"):
            q3_codes.append("Q3_ACTION_LOG_INTEGRITY")
        actions = [e.get("action") for e in log_entries]
        required = ["conversation_created", "prompt_pasted",
                    "generation_request_submitted"]
        if image_returned is True:
            required += ["response_captured", "artifact_downloaded",
                         "artifact_hashed", "slot_closed"]
        elif image_returned is False:
            required += ["response_captured", "slot_closed"]
        if any(a not in actions for a in required):
            q3_codes.append("Q3_ACTION_LOG_INCOMPLETE")
    q["Q3"] = QResult("Q3", Q_DEFINITIONS["Q3"], not q3_codes,
                      tuple(q3_codes))

    # ---- technical raster validation (distinct from Q4 digest checks) ----------
    raster_sha = _sha256(raster) if isinstance(raster, (bytes, bytearray)) else None
    if image_returned is True and raster_sha is not None:
        technical, raster_format, raster_dimensions = _decode_raster(bytes(raster))
        if technical == "failed":
            out.error("INVALID_RASTER", "raster_bytes", "bytes",
                      "downloaded bytes do not fully decode as a raster; "
                      "a plausible header is not an evaluable image")
        elif technical == "pending":
            out.add("TECHNICAL_VALIDATION_PENDING", "warning", "raster_bytes",
                    "bytes", "no trusted raster decoder is available, so "
                    "technical validation is pending and the evidence is "
                    "not eligible")
    else:
        technical, raster_format, raster_dimensions = \
            "not_applicable", None, None

    # ---- Q4: artifact digests ----------------------------------------------------
    q4_codes = []
    output_field = obs_fields.get("output_sha256", {})
    if image_returned is True:
        if raster_sha is None:
            q4_codes.append("Q4_RASTER_MISSING")
        else:
            if output_field.get("value") != raster_sha:
                q4_codes.append("Q4_OUTPUT_DIGEST_MISMATCH")
                out.error("OUTPUT_DIGEST_MISMATCH", "observation",
                          "output_sha256",
                          "observation digest does not recompute from bytes")
            else:
                # Recomputed digest that also matches the declared
                # observation binding is a verified binding.
                integrity = [SourceIntegrity(
                    s.field,
                    "verified_binding" if s.field == "output_sha256"
                    else s.level, s.authenticated) for s in integrity]
            artifact_field = obs_fields.get("output_artifact_id", {})
            if response_capture.get("artifact_id") != artifact_field.get("value"):
                q4_codes.append("Q4_ARTIFACT_ID_MISMATCH")
                out.error("ARTIFACT_ID_MISMATCH", "response_capture",
                          "artifact_id", "capture and observation disagree")
            for entry in log_entries:
                if entry.get("action") in ("artifact_downloaded",
                                           "artifact_hashed"):
                    if entry.get("artifact_sha256") != raster_sha:
                        q4_codes.append("Q4_LOG_DIGEST_MISMATCH")
                        out.error("LOG_DIGEST_MISMATCH", "action_log",
                                  entry.get("action"),
                                  "log digest does not recompute from bytes")
    # Frozen/pasted prompt integrity is digest recomputation (Q4). Frozen
    # vs pasted is a byte-digest equality; the rendered-request textual
    # comparison lives under Q1 and is never byte equality against the
    # frozen prompt digest.
    constants = observation.get("protocol_constants", {}) if observation else {}
    pasted = obs_fields.get("prompt_bytes_pasted_sha256", {}).get("value")
    rendered = obs_fields.get("prompt_text_rendered_sha256", {}).get("value")
    if constants:
        if pasted != constants.get("prompt_sha256"):
            q4_codes.append("Q4_FROZEN_PASTED_DIGEST_MISMATCH")
            out.error("PROMPT_DIGEST_MISMATCH", "observation",
                      "prompt_bytes_pasted_sha256",
                      "pasted bytes do not match the frozen prompt digest")
        if request_capture is not None:
            if request_capture.get("paste_sha256") != pasted:
                q4_codes.append("Q4_PASTE_BINDING_MISMATCH")
            if request_capture.get("rendered_request_text_sha256") != rendered:
                q4_codes.append("Q4_RENDERED_BINDING_MISMATCH")
    q["Q4"] = QResult("Q4", Q_DEFINITIONS["Q4"],
                      not q4_codes if image_returned is True else None,
                      tuple(q4_codes))

    # ---- Q5: operator attestation -------------------------------------------------
    q5_codes = []
    if attested_field_names or image_returned is True:
        if attestation is None:
            q5_codes.append("Q5_ATTESTATION_MISSING")
            out.error("ATTESTATION_MISSING", "attestation", "artifact",
                      "a returned attempt has no hash-bound operator "
                      "attestation")
        else:
            if "SCHEMA_INVALID" in out.codes_for("attestation"):
                q5_codes.append("Q5_ATTESTATION_SCHEMA_INVALID")
            if raster_sha is not None and \
                    attestation.get("artifact_digest_sha256") != raster_sha:
                q5_codes.append("Q5_ATTESTATION_DIGEST_MISMATCH")
                out.error("ATTESTATION_DIGEST_MISMATCH", "attestation",
                          "artifact_digest_sha256",
                          "attestation is not hash-bound to the artifact")
            elif raster_sha is not None:
                integrity.append(SourceIntegrity(
                    "attestation.artifact_digest_sha256",
                    "verified_binding", False))
    if attestation is not None and image_returned is False:
        q5_codes.append("Q5_ATTESTATION_WITHOUT_ARTIFACT")
        out.error("ATTESTATION_WITHOUT_ARTIFACT", "attestation", "artifact",
                  "an attestation exists for an attempt with no artifact")
    # Where fields claim operator_recorded, the contemporaneous records
    # are the captures and the action log evaluated under Q1-Q3; a claim
    # with none of those present cannot be satisfied here either.
    if recorded_field_names and request_capture is None and action_log is None:
        q5_codes.append("Q5_CONTEMPORANEOUS_RECORD_MISSING")
    q["Q5"] = QResult("Q5", Q_DEFINITIONS["Q5"],
                      not q5_codes if (attested_field_names or
                                       attestation is not None or
                                       image_returned is True) else None,
                      tuple(q5_codes))

    # ---- B/C material conflicts ------------------------------------------------
    b_c_conflicts = []
    returned_field = obs_fields.get("returned_output_count", {})
    if (returned_field.get("status") == "host_observed"
            and _authenticated(returned_field.get("source_ref"))
            and response_capture is not None
            and returned_field.get("value") !=
            response_capture.get("returned_image_count")):
        b_c_conflicts.append("BC_RETURNED_COUNT_CONFLICT")
        out.error("BC_MATERIAL_CONFLICT", "observation",
                  "returned_output_count",
                  "authenticated class-C evidence conflicts with class-B "
                  "capture evidence")

    # ---- outcome classification and evidence eligibility -------------------------
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
                   and not q["Q1"].codes and not q3_codes else "invalid_evidence")
    elif image_returned is True:
        outcome = "returned_evidenced" if not has_errors else "invalid_evidence"
    else:
        outcome = "invalid_evidence"

    all_q_pass = all(r.passed for r in q.values() if r.passed is not None) \
        and q["Q1"].passed and q["Q2"].passed and q["Q3"].passed \
        and q["Q5"].passed
    if outcome == "returned_evidenced" and all_q_pass and not has_errors \
            and technical == "passed":
        eligibility = ("evidence_eligible_with_conflict"
                       if class_d_conflicts else "evidence_eligible")
    else:
        eligibility = "not_evidence_eligible"

    return _report(out, q, outcome, class_d_conflicts, tuple(b_c_conflicts),
                   eligibility, technical, raster_format, raster_dimensions,
                   tuple(integrity))


def _report(out, q, outcome, class_d_conflicts, b_c_conflicts,
            eligibility="not_evidence_eligible", technical="not_applicable",
            raster_format=None, raster_dimensions=None, integrity=()):
    return ValidationReport(
        findings=tuple(out.findings),
        q_results=tuple(
            r for r in (q.get(k) for k in ("Q1", "Q2", "Q3", "Q4", "Q5"))
            if r is not None),
        outcome_classification=outcome,
        evidence_eligibility=eligibility,
        technical_validation=technical,
        raster_format=raster_format,
        raster_dimensions=raster_dimensions,
        class_d_conflict_count=class_d_conflicts,
        b_c_material_conflicts=tuple(b_c_conflicts),
        source_integrity=tuple(integrity),
    )
