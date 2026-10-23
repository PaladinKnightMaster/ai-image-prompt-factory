"""EXP-019 v1.2 operator evidence-capture workflow and tooling (PR-11).

Implements the operator-side preparation, capture, and closure tools
required by the approved evidence contract. Outputs conform to the
merged v1.2 evidence schemas and are intended for the PR-6 validator.

Canonical Q1–Q5 meanings are preserved exactly:

* Q1 — request capture (direct-paste, no-attachment, one generation)
* Q2 — response capture (separate response-time artifact)
* Q3 — append-only action log
* Q4 — artifact digests (frozen/paste/output; rendered text ≠ byte equality)
* Q5 — hash-bound operator attestation (not host-authenticated truth)

This module does **not** invoke a generation host, create allocations or
run roots, publish external checkpoints, finalize experimental attempts,
register v1.2, or reveal treatment assignments. The operator receives
only an opaque-labelled prompt packet; the allocation custodian retains
treatment mapping privately outside this module.

Attestation and digests bind bytes; they never prove host-side factual
claims. Failed or absent captures are never silently converted into
affirmative statements. Model metadata is never solicited to fill gaps.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Optional, Sequence

SCHEMA_VERSION = "1.2.0-draft"
EXPERIMENT_VERSION = "1.2.0"

#: Opaque slot id pattern (base32 Crockford, six chars) — schema contract.
_SLOT_PATTERN = re.compile(r"^[A-HJ-NP-Z2-9]{6}$")

AFFIRMATIVE_NO_RESULT = frozenset({
    "host_error_recorded",
    "host_completed_no_image",
    "request_not_accepted",
    "safety_refusal_recorded",
})

#: Operator-belief labels that must never become affirmative failure.
NON_AFFIRMATIVE_ABSENCE = frozenset({
    "operator_saw_no_image",
    "operator_believes_no_image",
})

ROLE_OPERATOR = "operator"
ROLE_CUSTODIAN = "allocation_custodian"


class OperatorCaptureError(ValueError):
    """Operator workflow violation or incomplete capture."""


class RoleBoundaryError(PermissionError):
    """Role-specific access or action denied."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Mapping) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False,
                       separators=(",", ":")) + "\n").encode("utf-8")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _field(value, status="operator_recorded", source_class="B",
           source_ref=None):
    return {
        "value": value,
        "status": status,
        "source_class": source_class,
        "source_ref": source_ref,
    }


def _unavailable(source_class="B"):
    return _field(None, status="not_observable", source_class=source_class,
                  source_ref=None)


@dataclass(frozen=True)
class OpaquePromptPacket:
    """Operator-visible prompt packet (no treatment / allocation mapping).

    Prepared by the allocation custodian; the operator sees only the
    opaque slot identity, attempt number, and frozen prompt bytes.
    """

    opaque_slot_id: str
    attempt_number: int
    frozen_prompt_bytes: bytes
    frozen_prompt_sha256: str
    conversation_ref: str
    aspect_ratio_request: str = "2:3"
    delivery_mode: str = "direct_paste_no_attachment"

    def __post_init__(self) -> None:
        if not _SLOT_PATTERN.match(self.opaque_slot_id):
            raise OperatorCaptureError("opaque_slot_id fails schema pattern")
        if self.attempt_number < 1:
            raise OperatorCaptureError("attempt_number must be >= 1")
        if _sha256(self.frozen_prompt_bytes) != self.frozen_prompt_sha256:
            raise OperatorCaptureError(
                "frozen_prompt_sha256 does not match frozen prompt bytes")
        if self.delivery_mode != "direct_paste_no_attachment":
            raise OperatorCaptureError(
                "v1.2 requires direct_paste_no_attachment delivery")


def make_opaque_prompt_packet(
        *, opaque_slot_id: str, attempt_number: int,
        frozen_prompt_bytes: bytes, conversation_ref: str,
        role: str = ROLE_CUSTODIAN) -> OpaquePromptPacket:
    """Custodian-only packet construction (no treatment fields exposed)."""
    if role != ROLE_CUSTODIAN:
        raise RoleBoundaryError(
            "only the allocation custodian may prepare prompt packets")
    return OpaquePromptPacket(
        opaque_slot_id=opaque_slot_id,
        attempt_number=attempt_number,
        frozen_prompt_bytes=bytes(frozen_prompt_bytes),
        frozen_prompt_sha256=_sha256(bytes(frozen_prompt_bytes)),
        conversation_ref=conversation_ref,
    )


@dataclass
class OperatorCaptureSession:
    """Auditable operator workflow for one opaque invocation attempt.

    Supports the Phase B2 sequence without invoking a generation host.
    """

    packet: OpaquePromptPacket
    operator_id: str
    role: str = ROLE_OPERATOR
    work_dir: Optional[Path] = None
    _paste_sha256: Optional[str] = field(default=None, init=False, repr=False)
    _rendered_text_sha256: Optional[str] = field(
        default=None, init=False, repr=False)
    _rendered_comparison: Optional[str] = field(
        default=None, init=False, repr=False)
    _request_capture: Optional[dict] = field(
        default=None, init=False, repr=False)
    _response_capture: Optional[dict] = field(
        default=None, init=False, repr=False)
    _output_bytes: Optional[bytes] = field(
        default=None, init=False, repr=False)
    _output_sha256: Optional[str] = field(
        default=None, init=False, repr=False)
    _artifact_id: Optional[str] = field(
        default=None, init=False, repr=False)
    _attestation: Optional[dict] = field(
        default=None, init=False, repr=False)
    _entries: list = field(default_factory=list, init=False, repr=False)
    _closed: bool = field(default=False, init=False, repr=False)
    _interrupted: bool = field(default=False, init=False, repr=False)
    _protocol_violation: Optional[str] = field(
        default=None, init=False, repr=False)
    _outcome_kind: Optional[str] = field(
        default=None, init=False, repr=False)
    _no_result_evidence: Optional[str] = field(
        default=None, init=False, repr=False)
    _log: list = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.role != ROLE_OPERATOR:
            raise RoleBoundaryError(
                "OperatorCaptureSession requires the operator role")
        if self.work_dir is not None:
            self.work_dir = Path(self.work_dir)
            self.work_dir.mkdir(parents=True, exist_ok=True)

    # -- internal helpers -----------------------------------------------------

    def _require_open(self) -> None:
        if self._closed:
            raise OperatorCaptureError(
                "session is closed; duplicate closure is refused")

    def _append(self, action: str, *, at_utc: Optional[str] = None,
                artifact_sha256: Optional[str] = None) -> None:
        self._require_open()
        entry = {
            "seq": len(self._entries) + 1,
            "at_utc": at_utc or _utc_now(),
            "action": action,
        }
        if artifact_sha256 is not None:
            entry["artifact_sha256"] = artifact_sha256
        if self._entries:
            prev = self._entries[-1]["at_utc"]
            if entry["at_utc"] < prev:
                raise OperatorCaptureError(
                    "action-log timestamps must be monotonic")
        self._entries.append(entry)
        self._log.append({"role": ROLE_OPERATOR, "action": action,
                          "at_utc": entry["at_utc"]})

    def _artifact_digest(self, artifact: Mapping) -> str:
        body = {k: v for k, v in artifact.items()
                if k != "capture_digest_sha256"}
        return _sha256(_canonical(body))

    # -- B2 workflow steps ----------------------------------------------------

    def verify_frozen_prompt_bytes(self, presented_bytes: bytes) -> bool:
        """Verify operator-held bytes match the frozen packet digest."""
        match = _sha256(bytes(presented_bytes)) == \
            self.packet.frozen_prompt_sha256
        self._log.append({
            "role": ROLE_OPERATOR,
            "action": "verify_frozen_prompt",
            "match": match,
        })
        return match

    def record_pre_send_paste(self, pasted_bytes: bytes, *,
                              rendered_request_text: Optional[str] = None,
                              at_utc: Optional[str] = None) -> str:
        """Record clipboard paste digest before submission (Q4 paste)."""
        self._require_open()
        if self._paste_sha256 is not None:
            raise OperatorCaptureError("duplicate pre-send paste refused")
        pasted = bytes(pasted_bytes)
        self._paste_sha256 = _sha256(pasted)
        if rendered_request_text is None:
            self._rendered_text_sha256 = self._paste_sha256
            self._rendered_comparison = (
                "textual_match"
                if self._paste_sha256 == self.packet.frozen_prompt_sha256
                else "textual_mismatch")
        else:
            self._rendered_text_sha256 = _sha256(
                rendered_request_text.encode("utf-8"))
            # Rendered text comparison is textual, never byte equality
            # against the frozen prompt digest.
            self._rendered_comparison = (
                "textual_match"
                if rendered_request_text == pasted.decode("utf-8", "replace")
                else "textual_mismatch")
        if not self._entries:
            self._append("conversation_created", at_utc=at_utc)
        self._append("prompt_pasted", at_utc=at_utc,
                     artifact_sha256=self._paste_sha256)
        return self._paste_sha256

    def record_request_capture(self, *, attachment_count: int = 0,
                               generation_request_count: int = 1,
                               at_utc: Optional[str] = None) -> dict:
        """Q1 — contemporaneous request capture at submission."""
        self._require_open()
        if self._request_capture is not None:
            raise OperatorCaptureError("duplicate request capture refused")
        if self._paste_sha256 is None:
            raise OperatorCaptureError(
                "pre-send paste digest required before request capture")
        if attachment_count != 0:
            self._protocol_violation = "attachment_used"
        if generation_request_count != 1:
            self._protocol_violation = (
                self._protocol_violation or "generation_request_count")
        stamp = at_utc or _utc_now()
        capture = {
            "schema_version": SCHEMA_VERSION,
            "status": "draft",
            "executable": False,
            "opaque_slot_id": self.packet.opaque_slot_id,
            "attempt_number": self.packet.attempt_number,
            "captured_at_utc": stamp,
            "attachment_count": int(attachment_count),
            "generation_request_count": int(generation_request_count),
            "paste_sha256": self._paste_sha256,
            "rendered_request_text_sha256": self._rendered_text_sha256,
            "rendered_request_comparison": self._rendered_comparison,
            "host_authenticated_request_bytes": None,
        }
        capture["capture_digest_sha256"] = self._artifact_digest(capture)
        self._request_capture = capture
        self._append("generation_request_submitted", at_utc=stamp)
        return copy.deepcopy(capture)

    def record_response_capture(
            self, *, image_returned: bool,
            returned_image_count: int,
            artifact_id: Optional[str] = None,
            no_result_evidence: Optional[str] = None,
            at_utc: Optional[str] = None) -> dict:
        """Q2 — separate response-time capture."""
        self._require_open()
        if self._request_capture is None:
            raise OperatorCaptureError(
                "request capture required before response capture")
        if self._response_capture is not None:
            raise OperatorCaptureError("duplicate response capture refused")
        stamp = at_utc or _utc_now()
        if stamp < self._request_capture["captured_at_utc"]:
            raise OperatorCaptureError(
                "response capture must not precede request capture")
        if image_returned:
            if no_result_evidence is not None:
                raise OperatorCaptureError(
                    "returned-image capture must not carry no_result_evidence")
            if returned_image_count != 1:
                self._protocol_violation = (
                    self._protocol_violation or "returned_image_count")
            if not artifact_id:
                raise OperatorCaptureError(
                    "returned image requires an artifact_id; do not fabricate")
            self._outcome_kind = "returned"
            self._artifact_id = artifact_id
        else:
            if artifact_id is not None:
                raise OperatorCaptureError(
                    "no-result capture must not carry an artifact_id")
            if no_result_evidence in NON_AFFIRMATIVE_ABSENCE:
                # Operator belief ≠ affirmative failure.
                self._outcome_kind = "unknown"
                no_result_evidence = None
            elif no_result_evidence in AFFIRMATIVE_NO_RESULT:
                self._outcome_kind = "no_result"
                self._no_result_evidence = no_result_evidence
            elif no_result_evidence is None:
                self._outcome_kind = "unknown"
            else:
                raise OperatorCaptureError(
                    "unrecognized no_result_evidence label")
            if returned_image_count != 0:
                raise OperatorCaptureError(
                    "no-result returned_image_count must be 0")
        capture = {
            "schema_version": SCHEMA_VERSION,
            "status": "draft",
            "executable": False,
            "opaque_slot_id": self.packet.opaque_slot_id,
            "attempt_number": self.packet.attempt_number,
            "captured_at_utc": stamp,
            "image_returned": bool(image_returned),
            "returned_image_count": int(returned_image_count),
            "artifact_id": artifact_id,
        }
        if not image_returned and self._no_result_evidence:
            capture["no_result_evidence"] = self._no_result_evidence
        elif not image_returned:
            # Unknown outcome: do not invent affirmative evidence.
            capture["no_result_evidence"] = None
        capture["capture_digest_sha256"] = self._artifact_digest(capture)
        self._response_capture = capture
        self._append("response_captured", at_utc=stamp)
        return copy.deepcopy(capture)

    def associate_downloaded_artifact(
            self, output_bytes: bytes, *,
            expected_artifact_id: Optional[str] = None,
            at_utc: Optional[str] = None) -> str:
        """Associate downloaded bytes with the observed response (Q4)."""
        self._require_open()
        if self._response_capture is None:
            raise OperatorCaptureError(
                "response capture required before artifact association")
        if not self._response_capture.get("image_returned"):
            raise OperatorCaptureError(
                "no-output scenarios must leave output digest null")
        if self._output_bytes is not None:
            raise OperatorCaptureError("duplicate artifact association refused")
        expected = expected_artifact_id or self._artifact_id
        if expected != self._response_capture.get("artifact_id"):
            raise OperatorCaptureError(
                "downloaded artifact does not match response association")
        data = bytes(output_bytes)
        digest = _sha256(data)
        stamp = at_utc or _utc_now()
        self._output_bytes = data
        self._output_sha256 = digest
        self._append("artifact_downloaded", at_utc=stamp,
                     artifact_sha256=digest)
        self._append("artifact_hashed", at_utc=stamp, artifact_sha256=digest)
        if self.work_dir is not None:
            path = self.work_dir / f"{digest}.bin"
            path.write_bytes(data)
        return digest

    def mark_interrupted(self, *, at_utc: Optional[str] = None) -> None:
        """Record an interrupted attempt; remains identifiable as incomplete.

        Interruption is session metadata — the action-log schema enum does
        not include a separate interrupt action — so the exported log stays
        truncated at the last schema-valid entry.
        """
        self._require_open()
        self._interrupted = True
        self._outcome_kind = self._outcome_kind or "unknown"
        self._log.append({
            "role": ROLE_OPERATOR,
            "action": "invocation_interrupted",
            "at_utc": at_utc or _utc_now(),
        })

    def resume_same_invocation(self, *, at_utc: Optional[str] = None) -> None:
        """Resume the same attempt after interruption (no new attempt)."""
        self._require_open()
        if not self._interrupted:
            raise OperatorCaptureError(
                "resume requires a prior interruption of this invocation")
        self._interrupted = False
        self._log.append({
            "role": ROLE_OPERATOR,
            "action": "invocation_resumed",
            "at_utc": at_utc or _utc_now(),
        })

    def record_protocol_violation(self, detail: str, *,
                                  at_utc: Optional[str] = None) -> None:
        """Record a protocol violation without inventing schema-invalid log actions."""
        self._require_open()
        self._protocol_violation = detail
        self._log.append({
            "role": ROLE_OPERATOR,
            "action": "protocol_violation_recorded",
            "detail": detail,
            "at_utc": at_utc or _utc_now(),
        })

    def produce_attestation(self, *, at_utc: Optional[str] = None) -> dict:
        """Q5 — hash-bound attestation when a returned artifact exists."""
        self._require_open()
        if self._attestation is not None:
            raise OperatorCaptureError("duplicate attestation refused")
        if self._output_sha256 is None:
            raise OperatorCaptureError(
                "attestation requires associated output bytes; do not "
                "attest an absent artifact")
        stamp = at_utc or _utc_now()
        attestation = {
            "schema_version": SCHEMA_VERSION,
            "status": "draft",
            "executable": False,
            "opaque_slot_id": self.packet.opaque_slot_id,
            "attempt_number": self.packet.attempt_number,
            "attested_by": self.operator_id,
            "attested_at_utc": stamp,
            "artifact_digest_sha256": self._output_sha256,
            "assertions": {
                "no_edit_or_regeneration_performed": True,
                "first_returned_image_retained": True,
                "no_subsequent_generation_in_conversation": True,
                "artifact_is_fresh_host_output_for_slot": True,
            },
        }
        self._attestation = attestation
        self._append("no_edit_or_regeneration_performed", at_utc=stamp)
        return copy.deepcopy(attestation)

    def close_invocation(self, *, at_utc: Optional[str] = None) -> dict:
        """Close the action log for this attempt."""
        self._require_open()
        stamp = at_utc or _utc_now()
        self._append("slot_closed", at_utc=stamp)
        self._closed = True
        return self.export_action_log()

    # -- export ----------------------------------------------------------------

    def export_action_log(self) -> dict:
        if not self._entries:
            raise OperatorCaptureError("action log is empty")
        closed_at = self._entries[-1]["at_utc"]
        body = {
            "schema_version": SCHEMA_VERSION,
            "status": "draft",
            "executable": False,
            "opaque_slot_id": self.packet.opaque_slot_id,
            "attempt_number": self.packet.attempt_number,
            "closed_at_utc": closed_at,
            "entries": copy.deepcopy(self._entries),
        }
        body["log_digest_sha256"] = _sha256(_canonical(
            {k: v for k, v in body.items() if k != "log_digest_sha256"}))
        return body

    def export_observation(self) -> dict:
        paste = self._paste_sha256
        rendered = self._rendered_text_sha256
        if self._outcome_kind == "returned" and self._output_sha256:
            observations = {
                "output_sha256": _field(self._output_sha256,
                                        source_ref=self._response_capture and
                                        self._response_capture.get(
                                            "capture_digest_sha256")),
                "output_artifact_id": _field(self._artifact_id),
                "attachment_count_at_request": _field(
                    (self._request_capture or {}).get("attachment_count", 0)),
                "generation_request_count": _field(
                    (self._request_capture or {}).get(
                        "generation_request_count", 1)),
                "returned_output_count": _field(
                    (self._response_capture or {}).get(
                        "returned_image_count", 0)),
                "edit_or_regeneration_used": _field(
                    False, status="operator_attested",
                    source_ref=None),
                "conversation_ref": _field(self.packet.conversation_ref),
                "prompt_bytes_pasted_sha256": _field(paste),
                "prompt_text_rendered_sha256": _field(rendered),
            }
        else:
            observations = {
                "output_sha256": _unavailable("B"),
                "output_artifact_id": _unavailable("B"),
                "attachment_count_at_request": _field(
                    (self._request_capture or {}).get("attachment_count", 0)),
                "generation_request_count": _field(
                    (self._request_capture or {}).get(
                        "generation_request_count", 1)),
                "returned_output_count": _field(
                    (self._response_capture or {}).get(
                        "returned_image_count", 0)
                    if self._response_capture else 0),
                "edit_or_regeneration_used": _unavailable("B"),
                "conversation_ref": _field(self.packet.conversation_ref),
                "prompt_bytes_pasted_sha256": _field(paste) if paste else
                _unavailable("B"),
                "prompt_text_rendered_sha256": _field(rendered) if rendered
                else _unavailable("B"),
            }
        # Missing optional class-C telemetry — non-blocking.
        observations["provider_generation_id"] = _unavailable("C")
        observations["backend_model"] = _unavailable("C")
        # Resolve attested source_ref after attestation exists.
        if self._attestation is not None:
            from .exp019_v1_2_evidence import canonical_artifact_digest
            att_digest = canonical_artifact_digest(self._attestation)
            observations["edit_or_regeneration_used"] = _field(
                False, status="operator_attested", source_ref=att_digest)
        # Bind recorded fields to contemporaneous capture digests when present.
        if self._request_capture is not None:
            req_digest = self._request_capture["capture_digest_sha256"]
            for name in ("attachment_count_at_request",
                         "generation_request_count",
                         "prompt_bytes_pasted_sha256",
                         "prompt_text_rendered_sha256",
                         "conversation_ref"):
                if name in observations and \
                        observations[name].get("status") == "operator_recorded":
                    observations[name] = dict(observations[name])
                    observations[name]["source_ref"] = req_digest
        if self._response_capture is not None and \
                observations.get("returned_output_count", {}).get(
                    "status") == "operator_recorded":
            observations["returned_output_count"] = dict(
                observations["returned_output_count"])
            observations["returned_output_count"]["source_ref"] = \
                self._response_capture["capture_digest_sha256"]
        if self._output_sha256 and observations.get("output_sha256", {}).get(
                "status") == "operator_recorded":
            observations["output_sha256"] = dict(observations["output_sha256"])
            observations["output_sha256"]["source_ref"] = \
                self._response_capture["capture_digest_sha256"]
            observations["output_artifact_id"] = dict(
                observations["output_artifact_id"])
            observations["output_artifact_id"]["source_ref"] = \
                self._response_capture["capture_digest_sha256"]
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "draft",
            "executable": False,
            "opaque_slot_id": self.packet.opaque_slot_id,
            "attempt_number": self.packet.attempt_number,
            "recorded_at_utc": (self._entries[-1]["at_utc"]
                                if self._entries else _utc_now()),
            "protocol_constants": {
                "experiment_id": "EXP-019",
                "experiment_version": EXPERIMENT_VERSION,
                "prompt_sha256": self.packet.frozen_prompt_sha256,
                "requested_reference_count": 0,
                "requested_output_count": 1,
                "aspect_ratio_request": self.packet.aspect_ratio_request,
                "delivery_mode": self.packet.delivery_mode,
            },
            "observations": observations,
            "model_reports": [],
        }

    def export_evidence_bundle(self) -> dict:
        """Export a complete evidence bundle for PR-6 validation."""
        if not self._closed and not self._interrupted:
            raise OperatorCaptureError(
                "export requires closure or an explicit interruption")
        # Never solicit model metadata to fill gaps.
        bundle = {
            "scenario": self._outcome_kind or "incomplete",
            "observation": self.export_observation(),
            "attestation": copy.deepcopy(self._attestation),
            "action_log": self.export_action_log(),
            "request_capture": copy.deepcopy(self._request_capture),
            "response_capture": copy.deepcopy(self._response_capture),
            "raster_bytes": self._output_bytes,
            "protocol_violation": self._protocol_violation,
            "interrupted": self._interrupted,
            "operator_role_log": copy.deepcopy(self._log),
        }
        return bundle

    def frozen_vs_paste_match(self) -> Optional[bool]:
        if self._paste_sha256 is None:
            return None
        return self._paste_sha256 == self.packet.frozen_prompt_sha256

    @property
    def protocol_violation(self) -> Optional[str]:
        return self._protocol_violation

    @property
    def outcome_kind(self) -> Optional[str]:
        return self._outcome_kind


# -- Distinct outcome workflows (B3) -----------------------------------------


def workflow_valid_returned_image(
        session: OperatorCaptureSession, pasted_bytes: bytes,
        output_bytes: bytes, *, artifact_id: str,
        rendered_request_text: Optional[str] = None) -> dict:
    session.record_pre_send_paste(
        pasted_bytes, rendered_request_text=rendered_request_text)
    session.record_request_capture()
    session.record_response_capture(
        image_returned=True, returned_image_count=1, artifact_id=artifact_id)
    session.associate_downloaded_artifact(
        output_bytes, expected_artifact_id=artifact_id)
    session.produce_attestation()
    session.close_invocation()
    return session.export_evidence_bundle()


def workflow_confirmed_no_result(
        session: OperatorCaptureSession, pasted_bytes: bytes, *,
        evidence: str) -> dict:
    if evidence not in AFFIRMATIVE_NO_RESULT:
        raise OperatorCaptureError(
            "confirmed no-result requires affirmative evidence")
    session.record_pre_send_paste(pasted_bytes)
    session.record_request_capture()
    session.record_response_capture(
        image_returned=False, returned_image_count=0,
        no_result_evidence=evidence)
    session.close_invocation()
    return session.export_evidence_bundle()


def workflow_technically_invalid_file(
        session: OperatorCaptureSession, pasted_bytes: bytes,
        invalid_bytes: bytes, *, artifact_id: str) -> dict:
    return workflow_valid_returned_image(
        session, pasted_bytes, invalid_bytes, artifact_id=artifact_id)


def workflow_interrupted_unknown(
        session: OperatorCaptureSession, pasted_bytes: bytes) -> dict:
    session.record_pre_send_paste(pasted_bytes)
    session.record_request_capture()
    session.mark_interrupted()
    # Interrupted export without inventing a response capture.
    return session.export_evidence_bundle()


def workflow_unknown_host_result(
        session: OperatorCaptureSession, pasted_bytes: bytes) -> dict:
    session.record_pre_send_paste(pasted_bytes)
    session.record_request_capture()
    # Operator non-observation must not become affirmative failure.
    session.record_response_capture(
        image_returned=False, returned_image_count=0,
        no_result_evidence="operator_saw_no_image")
    session.close_invocation()
    return session.export_evidence_bundle()


def workflow_multiple_returned_candidates(
        session: OperatorCaptureSession, pasted_bytes: bytes, *,
        artifact_id: str) -> dict:
    session.record_pre_send_paste(pasted_bytes)
    session.record_request_capture()
    session.record_response_capture(
        image_returned=True, returned_image_count=2, artifact_id=artifact_id)
    session.close_invocation()
    return session.export_evidence_bundle()


def workflow_accidental_attachment(
        session: OperatorCaptureSession, pasted_bytes: bytes) -> dict:
    session.record_pre_send_paste(pasted_bytes)
    session.record_request_capture(attachment_count=1)
    session.record_protocol_violation("attachment_used")
    session.close_invocation()
    return session.export_evidence_bundle()
