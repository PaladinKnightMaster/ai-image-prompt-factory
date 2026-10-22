"""Schema-level tests for the DRAFT EXP-019 v1.2 evidence contract.

These schemas are **drafts and non-executable**. v1.2 is not registered in
``frozen_protocol()``, and no runtime code reads these files. The tests below
therefore assert only that the draft schemas are internally consistent and that
they encode the proposed A/B/C/D source-class and observation-status
constraints correctly.

They deliberately do NOT create a v1.2 experiment, register a v1.2 protocol, or
authorize any generation, metadata query, or recovery replay. They use only
synthetic in-memory objects; no real-run artifact is read or copied.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "data/schemas"

OBSERVATION_SCHEMA = SCHEMA_DIR / "exp019_v1_2_observation.schema.json"
ATTESTATION_SCHEMA = SCHEMA_DIR / "exp019_v1_2_attestation.schema.json"
ACTION_LOG_SCHEMA = SCHEMA_DIR / "exp019_v1_2_action_log.schema.json"
REQUEST_CAPTURE_SCHEMA = SCHEMA_DIR / "exp019_v1_2_request_capture.schema.json"
RESPONSE_CAPTURE_SCHEMA = SCHEMA_DIR / "exp019_v1_2_response_capture.schema.json"

ALL_DRAFT_SCHEMAS = (
    OBSERVATION_SCHEMA, ATTESTATION_SCHEMA, ACTION_LOG_SCHEMA,
    REQUEST_CAPTURE_SCHEMA, RESPONSE_CAPTURE_SCHEMA,
)

SHA = "a" * 64
# A synthetic opaque slot id. Real run slot identifiers are never used here:
# naming one in a public file would let a reader reconstruct the
# blind-id-to-treatment mapping, because the frozen definition already fixes
# the condition at each invocation position.
SLOT = "ZZZZZZ"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _validator(path: Path) -> Draft202012Validator:
    return Draft202012Validator(_load(path))


def _field(value=None, status: str = "operator_recorded",
           source_class: str = "B", source_ref: str | None = SHA) -> dict:
    return {"value": value, "status": status,
            "source_class": source_class, "source_ref": source_ref}


def _observation() -> dict:
    return {
        "schema_version": "1.2.0-draft",
        "status": "draft",
        "executable": False,
        "opaque_slot_id": SLOT,
        "attempt_number": 1,
        "recorded_at_utc": "2026-01-01T00:00:00+00:00",
        "protocol_constants": {
            "experiment_id": "EXP-019",
            "experiment_version": "1.2.0",
            "prompt_sha256": SHA,
            "requested_reference_count": 0,
            "requested_output_count": 1,
            "aspect_ratio_request": "2:3",
            "delivery_mode": "direct_paste_no_attachment",
        },
        "observations": {
            "output_sha256": _field(SHA),
            "output_artifact_id": _field("artifact-1"),
            "attachment_count_at_request": _field(0),
            "generation_request_count": _field(1),
            "returned_output_count": _field(1),
            "edit_or_regeneration_used": _field(False),
            "conversation_ref": _field("conversation-1"),
            "prompt_bytes_pasted_sha256": _field(SHA),
            "prompt_text_rendered_sha256": _field(SHA),
        },
        "model_reports": [],
    }


# =============================================================================
# Draft / non-executable markers
# =============================================================================


@pytest.mark.parametrize("path", ALL_DRAFT_SCHEMAS, ids=lambda p: p.name)
def test_every_v1_2_schema_is_marked_draft_and_non_executable(path: Path) -> None:
    """No v1.2 schema may look frozen or executable."""
    schema = _load(path)
    assert schema["properties"]["status"]["const"] == "draft"
    assert schema["properties"]["executable"]["const"] is False
    assert "DRAFT" in schema["title"]
    assert "NOT a frozen protocol" in schema["description"]


@pytest.mark.parametrize("path", ALL_DRAFT_SCHEMAS, ids=lambda p: p.name)
def test_v1_2_schemas_are_valid_json_schema(path: Path) -> None:
    """Each draft must be a well-formed JSON Schema document."""
    Draft202012Validator.check_schema(_load(path))


def test_v1_2_is_not_registered_as_an_executable_protocol() -> None:
    """The runtime must not recognise v1.2 while the schemas are drafts."""
    from aipf.exp019_protocol import frozen_protocol

    with pytest.raises(ValueError, match="unknown EXP-019 frozen protocol version"):
        frozen_protocol("1.2.0")


def test_no_v1_2_runtime_module_exists() -> None:
    """v1.2 runtime implementation must not be present yet."""
    package = ROOT / "src" / "aipf"
    assert not (package / "exp019_v12").exists()
    assert not list(package.glob("exp019_v1_2*.py"))


# =============================================================================
# Observation artifact: source classes and statuses
# =============================================================================


def test_valid_observation_artifact_is_accepted() -> None:
    errors = list(_validator(OBSERVATION_SCHEMA).iter_errors(_observation()))
    assert not errors, [e.message for e in errors]


@pytest.mark.parametrize("status,source_class", [
    ("host_observed", "C"),
    ("operator_recorded", "B"),
    ("operator_attested", "B"),
])
def test_each_status_requires_its_matching_source_class(status: str, source_class: str) -> None:
    """A status may only be paired with its own source class."""
    observation = _observation()
    observation["observations"]["output_sha256"] = _field(
        "x", status=status, source_class=source_class)
    errors = list(_validator(OBSERVATION_SCHEMA).iter_errors(observation))
    assert not errors, [e.message for e in errors]


@pytest.mark.parametrize("status,source_class", [
    ("host_observed", "B"),   # class B must never be elevated to host-observed
    ("host_observed", "D"),   # class D must never impersonate telemetry
    ("operator_recorded", "C"),
    ("operator_recorded", "D"),
    ("model_reported", "B"),
    ("model_reported", "C"),
])
def test_mismatched_status_and_source_class_is_rejected(status: str, source_class: str) -> None:
    """The A/B/C/D distinction must be enforced, not decorative."""
    observation = _observation()
    observation["observations"]["output_sha256"] = _field(
        "x", status=status, source_class=source_class)
    errors = list(_validator(OBSERVATION_SCHEMA).iter_errors(observation))
    assert errors, f"{status} with class {source_class} should be rejected"


@pytest.mark.parametrize("status", ["not_observable", "not_applicable"])
def test_unavailable_status_requires_null_value_and_null_source_ref(status: str) -> None:
    """not_observable / not_applicable mean no value and no source artifact."""
    observation = _observation()
    observation["observations"]["backend_model"] = _field(
        None, status=status, source_class="C", source_ref=None)
    assert not list(_validator(OBSERVATION_SCHEMA).iter_errors(observation))

    observation["observations"]["backend_model"] = _field(
        "DALL-E", status=status, source_class="C", source_ref=None)
    errors = list(_validator(OBSERVATION_SCHEMA).iter_errors(observation))
    assert errors, "a non-null value with an unavailable status must be rejected"

    observation["observations"]["backend_model"] = _field(
        None, status=status, source_class="C", source_ref=SHA)
    errors = list(_validator(OBSERVATION_SCHEMA).iter_errors(observation))
    assert errors, "an unavailable status must not carry a source_ref"


@pytest.mark.parametrize("status", ["host_observed", "operator_recorded", "operator_attested"])
def test_available_status_requires_a_source_ref_digest(status: str) -> None:
    """An available observation must name the artifact that supports it."""
    observation = _observation()
    observation["observations"]["output_sha256"] = _field(
        "x", status=status, source_class="B" if status != "host_observed" else "C",
        source_ref=None)
    errors = list(_validator(OBSERVATION_SCHEMA).iter_errors(observation))
    assert errors, f"{status} without a source_ref must be rejected"


def test_model_reports_are_isolated_and_preserve_original_bytes() -> None:
    """Model claims live in their own namespace and keep the original bytes."""
    observation = _observation()
    observation["model_reports"] = [{
        "source": "model",
        "field": "host_output_path",
        "claimed_value": "/mnt/data/example.png",
        "claimed_status": "model_reported",
        "raw_bytes_sha256": SHA,
        "raw_bytes_base64": "eyJhIjoxfQ==",
        "captured_at_utc": "2026-01-01T00:00:01+00:00",
    }]
    assert not list(_validator(OBSERVATION_SCHEMA).iter_errors(observation))

    # A model report may never claim an authoritative status.
    observation["model_reports"][0]["claimed_status"] = "host_observed"
    errors = list(_validator(OBSERVATION_SCHEMA).iter_errors(observation))
    assert errors, "a model report must not be able to claim host_observed"

    # A model report may never be presented as coming from the host.
    observation["model_reports"][0]["claimed_status"] = "model_reported"
    observation["model_reports"][0]["source"] = "host"
    errors = list(_validator(OBSERVATION_SCHEMA).iter_errors(observation))
    assert errors, "a model report must not be able to claim a host source"


def test_model_report_cannot_overwrite_an_authoritative_observation() -> None:
    """The model namespace is additive only; it cannot shadow class A/B/C."""
    observation = _observation()
    observation["observations"]["output_sha256"] = _field(SHA)
    observation["model_reports"] = [{
        "source": "model",
        "field": "output_sha256",
        "claimed_value": "b" * 64,
        "claimed_status": "model_reported",
        "raw_bytes_sha256": SHA,
        "raw_bytes_base64": "e30=",
        "captured_at_utc": "2026-01-01T00:00:01+00:00",
    }]
    # The schema permits recording the conflict; it must not silently replace
    # the authoritative observation, which is still present and unchanged.
    assert observation["observations"]["output_sha256"]["value"] == SHA
    assert not list(_validator(OBSERVATION_SCHEMA).iter_errors(observation))


def test_unknown_observation_field_is_rejected() -> None:
    """Observation artifacts must not carry undeclared fields."""
    observation = _observation()
    observation["observations"]["secret_extra_field"] = _field("x")
    errors = list(_validator(OBSERVATION_SCHEMA).iter_errors(observation))
    assert errors


def test_protocol_constants_are_not_observations() -> None:
    """Protocol constants are frozen labels and carry no observation status."""
    constants = _load(OBSERVATION_SCHEMA)["properties"]["protocol_constants"]
    for name, spec in constants["properties"].items():
        assert "status" not in spec, f"{name} must not carry an observation status"


# =============================================================================
# Attestation artifact
# =============================================================================


def _attestation() -> dict:
    return {
        "schema_version": "1.2.0-draft",
        "status": "draft",
        "executable": False,
        "opaque_slot_id": SLOT,
        "attempt_number": 1,
        "attested_by": "operator-1",
        "attested_at_utc": "2026-01-01T00:00:00+00:00",
        "artifact_digest_sha256": SHA,
        "assertions": {
            "no_edit_or_regeneration_performed": True,
            "first_returned_image_retained": True,
            "no_subsequent_generation_in_conversation": True,
            "artifact_is_fresh_host_output_for_slot": True,
        },
    }


def test_valid_attestation_is_accepted() -> None:
    assert not list(_validator(ATTESTATION_SCHEMA).iter_errors(_attestation()))


@pytest.mark.parametrize("assertion", [
    "no_edit_or_regeneration_performed",
    "first_returned_image_retained",
    "no_subsequent_generation_in_conversation",
    "artifact_is_fresh_host_output_for_slot",
])
def test_required_attestation_must_be_true(assertion: str) -> None:
    """A required operator assertion may not be false or absent."""
    attestation = _attestation()
    attestation["assertions"][assertion] = False
    errors = list(_validator(ATTESTATION_SCHEMA).iter_errors(attestation))
    assert errors, f"{assertion} must be true"

    attestation = _attestation()
    del attestation["assertions"][assertion]
    errors = list(_validator(ATTESTATION_SCHEMA).iter_errors(attestation))
    assert errors, f"{assertion} must be required"


def test_attestation_requires_a_hash_bound_digest() -> None:
    """The attestation artifact must carry its own binding digest."""
    attestation = _attestation()
    del attestation["artifact_digest_sha256"]
    errors = list(_validator(ATTESTATION_SCHEMA).iter_errors(attestation))
    assert errors, "the attestation must carry a digest"

    attestation = _attestation()
    attestation["artifact_digest_sha256"] = "not-a-digest"
    errors = list(_validator(ATTESTATION_SCHEMA).iter_errors(attestation))
    assert errors, "the attestation digest must be a sha256"


# =============================================================================
# Action log
# =============================================================================


def _action_log() -> dict:
    return {
        "schema_version": "1.2.0-draft",
        "status": "draft",
        "executable": False,
        "opaque_slot_id": SLOT,
        "attempt_number": 1,
        "closed_at_utc": "2026-01-01T00:01:00+00:00",
        "log_digest_sha256": SHA,
        "entries": [
            {"seq": 1, "at_utc": "2026-01-01T00:00:01+00:00",
             "action": "conversation_created"},
            {"seq": 2, "at_utc": "2026-01-01T00:00:02+00:00",
             "action": "prompt_pasted", "artifact_sha256": SHA},
            {"seq": 3, "at_utc": "2026-01-01T00:00:03+00:00",
             "action": "generation_request_submitted"},
            {"seq": 4, "at_utc": "2026-01-01T00:00:04+00:00",
             "action": "response_captured"},
            {"seq": 5, "at_utc": "2026-01-01T00:00:05+00:00",
             "action": "artifact_downloaded", "artifact_sha256": SHA},
            {"seq": 6, "at_utc": "2026-01-01T00:00:06+00:00",
             "action": "artifact_hashed", "artifact_sha256": SHA},
            {"seq": 7, "at_utc": "2026-01-01T00:00:07+00:00",
             "action": "no_edit_or_regeneration_performed"},
            {"seq": 8, "at_utc": "2026-01-01T00:00:08+00:00",
             "action": "slot_closed"},
        ],
    }


def test_valid_action_log_is_accepted() -> None:
    assert not list(_validator(ACTION_LOG_SCHEMA).iter_errors(_action_log()))


def test_action_log_rejects_unknown_action() -> None:
    """Only the declared operator actions may be recorded."""
    log = _action_log()
    log["entries"][2]["action"] = "regenerated_the_image"
    errors = list(_validator(ACTION_LOG_SCHEMA).iter_errors(log))
    assert errors, "an undeclared action must be rejected"


def test_action_log_rejects_empty_entries() -> None:
    log = _action_log()
    log["entries"] = []
    errors = list(_validator(ACTION_LOG_SCHEMA).iter_errors(log))
    assert errors


# =============================================================================
# Request and response captures
# =============================================================================


def _request_capture() -> dict:
    return {
        "schema_version": "1.2.0-draft",
        "status": "draft",
        "executable": False,
        "opaque_slot_id": SLOT,
        "attempt_number": 1,
        "captured_at_utc": "2026-01-01T00:00:02+00:00",
        "capture_digest_sha256": SHA,
        "attachment_count": 0,
        "generation_request_count": 1,
        "paste_sha256": SHA,
        "rendered_request_text_sha256": SHA,
        "rendered_request_comparison": "textual_match",
        "host_authenticated_request_bytes": None,
    }


def _response_capture() -> dict:
    return {
        "schema_version": "1.2.0-draft",
        "status": "draft",
        "executable": False,
        "opaque_slot_id": SLOT,
        "attempt_number": 1,
        "captured_at_utc": "2026-01-01T00:00:04+00:00",
        "capture_digest_sha256": SHA,
        "image_returned": True,
        "returned_image_count": 1,
        "artifact_id": "artifact-1",
    }


def test_valid_captures_are_accepted() -> None:
    assert not list(_validator(REQUEST_CAPTURE_SCHEMA).iter_errors(_request_capture()))
    assert not list(_validator(RESPONSE_CAPTURE_SCHEMA).iter_errors(_response_capture()))


def test_request_capture_records_a_textual_comparison_not_byte_identity() -> None:
    """The achievable comparison is textual; byte identity is not claimed."""
    schema = _load(REQUEST_CAPTURE_SCHEMA)
    comparison = schema["properties"]["rendered_request_comparison"]
    assert set(comparison["enum"]) == {"textual_match", "textual_mismatch", "not_compared"}
    assert "byte-identity" in comparison["description"]
    assert "NOT available" in comparison["description"]


def test_request_capture_may_not_claim_authenticated_host_bytes() -> None:
    """host_authenticated_request_bytes is optional and only a digest."""
    capture = _request_capture()
    capture["host_authenticated_request_bytes"] = "not-a-digest"
    errors = list(_validator(REQUEST_CAPTURE_SCHEMA).iter_errors(capture))
    assert errors


def test_response_capture_distinguishes_no_result_from_unknown() -> None:
    """A no-result outcome needs affirmative evidence, not an operator belief."""
    capture = _response_capture()
    capture["image_returned"] = False
    capture["returned_image_count"] = 0
    capture["artifact_id"] = None
    capture["no_result_evidence"] = "host_error_recorded"
    assert not list(_validator(RESPONSE_CAPTURE_SCHEMA).iter_errors(capture))

    # No affirmative evidence recorded: the artifact must still be rejected,
    # so an operator statement alone cannot manufacture a no-result outcome.
    capture["no_result_evidence"] = None
    errors = list(_validator(RESPONSE_CAPTURE_SCHEMA).iter_errors(capture))
    assert errors, "a no-result capture requires affirmative no-result evidence"

    capture["no_result_evidence"] = "operator_saw_no_image"
    errors = list(_validator(RESPONSE_CAPTURE_SCHEMA).iter_errors(capture))
    assert errors, "an operator belief is not affirmative no-result evidence"


def test_returned_image_requires_a_positive_count() -> None:
    """A capture that says an image was returned must record at least one."""
    capture = _response_capture()
    capture["returned_image_count"] = 0
    errors = list(_validator(RESPONSE_CAPTURE_SCHEMA).iter_errors(capture))
    assert errors, "image_returned=true requires returned_image_count >= 1"


@pytest.mark.parametrize("status,source_class", [
    ("host_observed", "C"),
    ("operator_recorded", "B"),
    ("operator_attested", "B"),
])
def test_available_status_requires_a_non_null_value(status: str, source_class: str) -> None:
    """An available observation carrying null is missing telemetry in disguise."""
    observation = _observation()
    observation["observations"]["backend_model"] = _field(
        None, status=status, source_class=source_class)
    errors = list(_validator(OBSERVATION_SCHEMA).iter_errors(observation))
    assert errors, f"{status} with a null value must be rejected"


def test_model_reported_may_not_occupy_an_authoritative_field() -> None:
    """Class-D claims live only in model_reports, never in observations."""
    for source_ref in (SHA, None):
        observation = _observation()
        observation["observations"]["backend_model"] = _field(
            "some-model", status="model_reported", source_class="D",
            source_ref=source_ref)
        errors = list(_validator(OBSERVATION_SCHEMA).iter_errors(observation))
        assert errors, "model_reported in an authoritative field must be rejected"


@pytest.mark.parametrize("source_class", ["A", "D"])
def test_unavailable_status_may_not_use_protocol_or_model_class(source_class: str) -> None:
    """not_observable describes authoritative B/C evidence, never A or D."""
    observation = _observation()
    observation["observations"]["backend_model"] = _field(
        None, status="not_observable", source_class=source_class, source_ref=None)
    errors = list(_validator(OBSERVATION_SCHEMA).iter_errors(observation))
    assert errors, f"not_observable with class {source_class} must be rejected"


def test_no_result_capture_must_not_invent_an_artifact_id() -> None:
    """A no-result capture has no artifact; its handle must be null."""
    capture = _response_capture()
    capture["image_returned"] = False
    capture["returned_image_count"] = 0
    capture["no_result_evidence"] = "host_error_recorded"
    # artifact_id still carries the returned-image handle from the fixture.
    errors = list(_validator(RESPONSE_CAPTURE_SCHEMA).iter_errors(capture))
    assert errors, "a no-result capture must not carry an artifact_id"

    capture["artifact_id"] = None
    assert not list(_validator(RESPONSE_CAPTURE_SCHEMA).iter_errors(capture))


def test_every_schema_reserves_cross_artifact_checks_for_runtime() -> None:
    """Checks JSON Schema cannot enforce must be explicitly runtime-reserved."""
    for path in ALL_DRAFT_SCHEMAS:
        comment = _load(path).get("$comment", "")
        assert "RESERVED FOR RUNTIME VALIDATION" in comment, path.name
        assert "JSON Schema cannot enforce" in comment, path.name


def test_request_and_response_captures_are_distinct_artifacts() -> None:
    """A request capture cannot stand in for a response capture."""
    request = _load(REQUEST_CAPTURE_SCHEMA)
    response = _load(RESPONSE_CAPTURE_SCHEMA)
    assert "image_returned" not in request["properties"]
    assert "attachment_count" not in response["properties"]
    assert "no_result_evidence" not in request["properties"]
