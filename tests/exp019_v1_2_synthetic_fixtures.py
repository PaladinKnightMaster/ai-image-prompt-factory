"""Synthetic fixture builders for the DRAFT EXP-019 v1.2 evidence contract.

These builders exist only so the draft v1.2 schemas (PR-2) can be exercised
by future tests without touching any real experiment. Everything produced
here is synthetic and in-memory:

* no historical image, metadata, receipt, prompt, or mapping is copied;
* opaque identifiers are synthetic placeholders, never real run identifiers;
* class-C ("host_observed") fixtures are *simulated*: they demonstrate the
  schema shape only and are never authenticated host telemetry;
* no builder registers, freezes, or executes EXP-019 v1.2, and no runtime
  code reads this module.

Builders return fresh objects on every call so tests may mutate them freely.
"""

from __future__ import annotations

import base64
import hashlib

# Synthetic opaque placeholder. It satisfies the draft schema pattern but is
# deliberately not a real identifier from any run.
SLOT = "ZZZZZZ"
ATTEMPT = 1
OPERATOR = "synthetic-operator"
ARTIFACT_ID = "synthetic-artifact-1"
CONVERSATION_REF = "synthetic-conversation-1"

T_SUBMIT = "2026-01-01T00:00:02+00:00"
T_RETURN = "2026-01-01T00:00:04+00:00"
T_CLOSE = "2026-01-01T00:01:00+00:00"

# A generic 1x1 PNG, generated synthetically for fixture use only.
_RASTER_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8"
    "/x8AAwMCAO+ip1sAAAAASUVORK5CYII="
)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def synthetic_raster_bytes() -> bytes:
    """Valid, fully synthetic raster bytes (a 1x1 PNG)."""
    return base64.b64decode(_RASTER_B64)


def invalid_raster_bytes() -> bytes:
    """Bytes that are not a raster image at all."""
    return b"this is not a raster image, synthetically speaking"


def _digest(label: str) -> str:
    """Deterministic synthetic supporting-artifact digest."""
    return sha256_hex(f"synthetic:{label}".encode("utf-8"))


def _field(value, status="operator_recorded", source_class="B", source_ref=None):
    if source_ref is None and status not in ("not_observable", "not_applicable"):
        source_ref = _digest(f"{status}:{value!r}")
    return {
        "value": value,
        "status": status,
        "source_class": source_class,
        "source_ref": source_ref,
    }


def _unavailable(source_class="C"):
    return _field(None, status="not_observable", source_class=source_class,
                  source_ref=None)


# ---------------------------------------------------------------------------
# Individual artifact builders
# ---------------------------------------------------------------------------


def make_observation(*, raster: bytes | None = None,
                     simulated_class_c: bool = False,
                     missing_class_c: bool = True,
                     contradictory_model_reports: bool = False,
                     digest_mismatch: bool = False,
                     no_output: bool = False) -> dict:
    """Synthetic observation artifact (draft schema shape).

    With ``simulated_class_c=True`` the class-C fields are a *simulation of
    shape only*: detached from the labelled bundle they are indistinguishable
    in form from class-C fields, but their synthetic digests authenticate
    nothing and can never satisfy production authentication, which the draft
    schemas reserve for runtime validation. Use them only inside a bundle
    whose scenario label records the simulation.
    """
    if raster is None:
        raster = synthetic_raster_bytes()
    output_digest = sha256_hex(b"different synthetic bytes" if digest_mismatch
                               else raster)
    observations = {
        "output_sha256": _field(output_digest),
        "output_artifact_id": _field(ARTIFACT_ID),
        "attachment_count_at_request": _field(0),
        "generation_request_count": _field(1),
        "returned_output_count": _field(1),
        "edit_or_regeneration_used": _field(False, status="operator_attested"),
        "conversation_ref": _field(CONVERSATION_REF),
        "prompt_bytes_pasted_sha256": _field(_digest("prompt-paste")),
        "prompt_text_rendered_sha256": _field(_digest("prompt-rendered")),
    }
    if no_output:
        observations["output_sha256"] = _unavailable("B")
        observations["output_artifact_id"] = _unavailable("B")
        observations["returned_output_count"] = _field(0)
    if simulated_class_c:
        # Simulated only: demonstrates the class-C shape. A digest here does
        # not authenticate anything; real class-C evidence would require a
        # genuinely authenticated host source, which fixtures cannot supply.
        observations["provider_generation_id"] = _field(
            "synthetic-generation-1", status="host_observed", source_class="C")
        observations["backend_model"] = _field(
            "synthetic-backend", status="host_observed", source_class="C")
    elif missing_class_c:
        observations["provider_generation_id"] = _unavailable("C")
        observations["backend_model"] = _unavailable("C")
    model_reports = []
    if contradictory_model_reports:
        model_reports = [{
            "source": "model",
            "field": "returned_output_count",
            "claimed_value": 3,
            "claimed_status": "model_reported",
            "raw_bytes_sha256": _digest("model-report-bytes"),
            "raw_bytes_base64": base64.b64encode(
                b"synthetic contradictory model claim").decode("ascii"),
            "captured_at_utc": T_RETURN,
        }, {
            "source": "model",
            "field": "edit_or_regeneration_used",
            "claimed_value": True,
            "claimed_status": "model_reported",
            "raw_bytes_sha256": _digest("model-report-bytes-2"),
            "raw_bytes_base64": base64.b64encode(
                b"synthetic contradictory model claim 2").decode("ascii"),
            "captured_at_utc": T_RETURN,
        }]
    return {
        "schema_version": "1.2.0-draft",
        "status": "draft",
        "executable": False,
        "opaque_slot_id": SLOT,
        "attempt_number": ATTEMPT,
        "recorded_at_utc": T_CLOSE,
        "protocol_constants": {
            "experiment_id": "EXP-019",
            "experiment_version": "1.2.0",
            "prompt_sha256": _digest("prompt-paste"),
            "requested_reference_count": 0,
            "requested_output_count": 1,
            "aspect_ratio_request": "2:3",
            "delivery_mode": "direct_paste_no_attachment",
        },
        "observations": observations,
        "model_reports": model_reports,
    }


def make_attestation() -> dict:
    """Complete synthetic operator attestation (all assertions true)."""
    return {
        "schema_version": "1.2.0-draft",
        "status": "draft",
        "executable": False,
        "opaque_slot_id": SLOT,
        "attempt_number": ATTEMPT,
        "attested_by": OPERATOR,
        "attested_at_utc": T_CLOSE,
        "artifact_digest_sha256": sha256_hex(synthetic_raster_bytes()),
        "assertions": {
            "no_edit_or_regeneration_performed": True,
            "first_returned_image_retained": True,
            "no_subsequent_generation_in_conversation": True,
            "artifact_is_fresh_host_output_for_slot": True,
        },
    }


def make_action_log(*, interrupted: bool = False) -> dict:
    """Synthetic operator action log; optionally truncated mid-invocation."""
    entries = [
        {"seq": 1, "at_utc": "2026-01-01T00:00:01+00:00",
         "action": "conversation_created"},
        {"seq": 2, "at_utc": T_SUBMIT, "action": "prompt_pasted",
         "artifact_sha256": _digest("prompt-paste")},
        {"seq": 3, "at_utc": T_SUBMIT,
         "action": "generation_request_submitted"},
    ]
    if not interrupted:
        entries += [
            {"seq": 4, "at_utc": T_RETURN, "action": "response_captured"},
            {"seq": 5, "at_utc": T_RETURN, "action": "artifact_downloaded",
             "artifact_sha256": sha256_hex(synthetic_raster_bytes())},
            {"seq": 6, "at_utc": T_RETURN, "action": "artifact_hashed",
             "artifact_sha256": sha256_hex(synthetic_raster_bytes())},
            {"seq": 7, "at_utc": T_CLOSE,
             "action": "no_edit_or_regeneration_performed"},
            {"seq": 8, "at_utc": T_CLOSE, "action": "slot_closed"},
        ]
    return {
        "schema_version": "1.2.0-draft",
        "status": "draft",
        "executable": False,
        "opaque_slot_id": SLOT,
        "attempt_number": ATTEMPT,
        # An interrupted log was never closed at slot close; its closed_at
        # is the last recorded action rather than a closure time.
        "closed_at_utc": T_SUBMIT if interrupted else T_CLOSE,
        "log_digest_sha256": _digest("action-log"),
        "entries": entries,
    }


def make_request_capture() -> dict:
    """Valid synthetic request capture (taken at submission)."""
    return {
        "schema_version": "1.2.0-draft",
        "status": "draft",
        "executable": False,
        "opaque_slot_id": SLOT,
        "attempt_number": ATTEMPT,
        "captured_at_utc": T_SUBMIT,
        "capture_digest_sha256": _digest("request-capture"),
        "attachment_count": 0,
        "generation_request_count": 1,
        "paste_sha256": _digest("prompt-paste"),
        "rendered_request_text_sha256": _digest("prompt-rendered"),
        "rendered_request_comparison": "textual_match",
        "host_authenticated_request_bytes": None,
    }


def make_invalid_request_capture(kind: str) -> dict:
    """Request captures that the draft schema must reject."""
    capture = make_request_capture()
    if kind == "bad_paste_digest":
        capture["paste_sha256"] = "not-a-digest"
    elif kind == "zero_generation_requests":
        capture["generation_request_count"] = 0
    elif kind == "authenticated_bytes_not_a_digest":
        capture["host_authenticated_request_bytes"] = "claimed-bytes"
    elif kind == "missing_rendered_digest":
        del capture["rendered_request_text_sha256"]
    else:  # pragma: no cover - guard against typo'd kinds in tests
        raise ValueError(f"unknown invalid request capture kind: {kind}")
    return capture


def make_response_capture(*, no_result: bool = False) -> dict:
    """Synthetic response capture (taken when the image appears)."""
    capture = {
        "schema_version": "1.2.0-draft",
        "status": "draft",
        "executable": False,
        "opaque_slot_id": SLOT,
        "attempt_number": ATTEMPT,
        "captured_at_utc": T_RETURN,
        "capture_digest_sha256": _digest("response-capture"),
        "image_returned": True,
        "returned_image_count": 1,
        "artifact_id": ARTIFACT_ID,
    }
    if no_result:
        capture.update({
            "image_returned": False,
            "returned_image_count": 0,
            "artifact_id": None,
            "no_result_evidence": "host_error_recorded",
        })
    return capture


def make_invalid_response_capture(kind: str) -> dict:
    """Response captures that the draft schema must reject."""
    capture = make_response_capture()
    if kind == "no_result_without_evidence":
        capture.update({"image_returned": False, "returned_image_count": 0,
                        "artifact_id": None, "no_result_evidence": None})
    elif kind == "no_result_operator_belief":
        capture.update({"image_returned": False, "returned_image_count": 0,
                        "artifact_id": None,
                        "no_result_evidence": "operator_saw_no_image"})
    elif kind == "no_result_with_artifact_id":
        capture.update({"image_returned": False, "returned_image_count": 0,
                        "no_result_evidence": "host_error_recorded"})
        # artifact_id deliberately left as the returned-image handle.
    elif kind == "returned_with_zero_count":
        capture["returned_image_count"] = 0
    else:  # pragma: no cover - guard against typo'd kinds in tests
        raise ValueError(f"unknown invalid response capture kind: {kind}")
    return capture


def make_status_violation(kind: str) -> dict:
    """Observation artifacts violating the status/source-class contract."""
    observation = make_observation()
    fields = observation["observations"]
    if kind == "model_reported_in_authoritative_field":
        fields["backend_model"] = _field(
            "synthetic-backend", status="model_reported", source_class="D")
    elif kind == "host_observed_with_operator_class":
        fields["backend_model"] = _field(
            "synthetic-backend", status="host_observed", source_class="B")
    elif kind == "unavailable_with_a_value":
        fields["backend_model"] = _field(
            "synthetic-backend", status="not_observable", source_class="C",
            source_ref=None)
    elif kind == "available_with_null_value":
        fields["backend_model"] = _field(
            None, status="host_observed", source_class="C",
            source_ref=_digest("backend"))
    elif kind == "unavailable_with_model_class":
        fields["backend_model"] = _field(
            None, status="not_observable", source_class="D", source_ref=None)
    else:  # pragma: no cover - guard against typo'd kinds in tests
        raise ValueError(f"unknown status violation kind: {kind}")
    return observation


def make_reviewer_artifact() -> dict:
    """Treatment-free synthetic artifact as shown to a blind reviewer.

    Contains only an opaque identifier and raster descriptors: no condition,
    treatment, variant, prompt, or mapping material of any kind.
    """
    return {
        "opaque_slot_id": SLOT,
        "artifact_sha256": sha256_hex(synthetic_raster_bytes()),
        "raster_format": "PNG",
        "width_px": 1,
        "height_px": 1,
    }


# ---------------------------------------------------------------------------
# Whole-bundle scenarios
# ---------------------------------------------------------------------------


def make_evidence_bundle(scenario: str = "qualifying_class_b") -> dict:
    """A coherent synthetic evidence bundle for one scenario.

    ``response_capture``/``attestation``/``raster_bytes`` may be ``None`` for
    scenarios where that artifact legitimately does not exist. ``scenario``
    is a fixture label only; it is not a protocol disposition.
    """
    bundle = {
        "scenario": scenario,
        "observation": make_observation(),
        "attestation": make_attestation(),
        "action_log": make_action_log(),
        "request_capture": make_request_capture(),
        "response_capture": make_response_capture(),
        "raster_bytes": synthetic_raster_bytes(),
    }
    if scenario == "qualifying_class_b":
        pass
    elif scenario == "incomplete_class_b":
        # No attestation was made, so nothing may claim operator_attested.
        bundle["attestation"] = None
        bundle["observation"]["observations"]["edit_or_regeneration_used"] = (
            _unavailable("B"))
    elif scenario == "simulated_class_c":
        bundle["observation"] = make_observation(simulated_class_c=True)
    elif scenario == "missing_class_c":
        bundle["observation"] = make_observation(missing_class_c=True)
    elif scenario == "contradictory_class_d":
        bundle["observation"] = make_observation(
            contradictory_model_reports=True)
    elif scenario == "no_output_failure":
        bundle["observation"] = make_observation(no_output=True)
        bundle["response_capture"] = make_response_capture(no_result=True)
        bundle["raster_bytes"] = None
        # Nothing was returned, so there is no artifact to attest about:
        # no attestation exists and nothing may claim operator_attested.
        bundle["attestation"] = None
        bundle["observation"]["observations"]["edit_or_regeneration_used"] = (
            _unavailable("B"))
        # The action log for a no-output invocation records the submission
        # and the no-result response capture, but no download or hashing of
        # an artifact that does not exist.
        bundle["action_log"]["entries"] = [
            {"seq": 1, "at_utc": "2026-01-01T00:00:01+00:00",
             "action": "conversation_created"},
            {"seq": 2, "at_utc": T_SUBMIT, "action": "prompt_pasted",
             "artifact_sha256": _digest("prompt-paste")},
            {"seq": 3, "at_utc": T_SUBMIT,
             "action": "generation_request_submitted"},
            {"seq": 4, "at_utc": T_RETURN, "action": "response_captured"},
            {"seq": 5, "at_utc": T_CLOSE, "action": "slot_closed"},
        ]
    elif scenario == "invalid_raster":
        bundle["raster_bytes"] = invalid_raster_bytes()
        bundle["observation"] = make_observation(
            raster=invalid_raster_bytes())
        # Isolate raster-format invalidity as the sole defect: every digest
        # that refers to the returned artifact must digest the invalid
        # bytes, exactly as in the qualifying bundle.
        invalid_digest = sha256_hex(invalid_raster_bytes())
        bundle["attestation"]["artifact_digest_sha256"] = invalid_digest
        for entry in bundle["action_log"]["entries"]:
            if entry["action"] in ("artifact_downloaded", "artifact_hashed"):
                entry["artifact_sha256"] = invalid_digest
    elif scenario == "interrupted_unknown":
        # The invocation was interrupted: no response was ever captured and
        # the log stops after submission. Outcome is unknown, not a failure.
        bundle["response_capture"] = None
        bundle["action_log"] = make_action_log(interrupted=True)
        bundle["observation"]["observations"]["returned_output_count"] = (
            _unavailable("B"))
        bundle["observation"]["observations"]["output_sha256"] = (
            _unavailable("B"))
        bundle["observation"]["observations"]["output_artifact_id"] = (
            _unavailable("B"))
        # No artifact arrived and no attestation was made for an invocation
        # whose outcome is unknown.
        bundle["attestation"] = None
        bundle["raster_bytes"] = None
        bundle["observation"]["observations"]["edit_or_regeneration_used"] = (
            _unavailable("B"))
    elif scenario == "digest_mismatch":
        bundle["observation"] = make_observation(digest_mismatch=True)
    else:  # pragma: no cover - guard against typo'd scenarios in tests
        raise ValueError(f"unknown synthetic scenario: {scenario}")
    return bundle
