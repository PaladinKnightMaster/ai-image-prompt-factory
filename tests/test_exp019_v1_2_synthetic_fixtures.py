"""Tests for the synthetic EXP-019 v1.2 fixture builders.

The builders in ``exp019_v1_2_synthetic_fixtures`` produce only synthetic,
in-memory artifacts for the DRAFT, non-executable v1.2 schemas. These tests
assert that each scenario is schema-valid (or schema-invalid, where the
fixture is deliberately malformed) and that the fixture's stated property
actually holds (e.g. a digest mismatch really mismatches).

They do NOT implement any v1.2 runtime validation: cross-artifact, temporal,
digest-recomputation, and authentication checks remain reserved for a future
runtime validator, exactly as the draft schemas state. They create no
experiment, register no protocol, and read no real-run artifact.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from exp019_v1_2_synthetic_fixtures import (
    SLOT,
    invalid_raster_bytes,
    make_action_log,
    make_attestation,
    make_evidence_bundle,
    make_invalid_request_capture,
    make_invalid_response_capture,
    make_observation,
    make_request_capture,
    make_response_capture,
    make_reviewer_artifact,
    make_status_violation,
    synthetic_raster_bytes,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "data/schemas"


def _validator(name: str) -> Draft202012Validator:
    schema = json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


OBSERVATION = _validator("exp019_v1_2_observation.schema.json")
ATTESTATION = _validator("exp019_v1_2_attestation.schema.json")
ACTION_LOG = _validator("exp019_v1_2_action_log.schema.json")
REQUEST = _validator("exp019_v1_2_request_capture.schema.json")
RESPONSE = _validator("exp019_v1_2_response_capture.schema.json")

ARTIFACT_VALIDATORS = {
    "observation": OBSERVATION,
    "attestation": ATTESTATION,
    "action_log": ACTION_LOG,
    "request_capture": REQUEST,
    "response_capture": RESPONSE,
}


def _assert_bundle_schema_valid(bundle: dict) -> None:
    for key, validator in ARTIFACT_VALIDATORS.items():
        artifact = bundle[key]
        if artifact is None:
            continue
        errors = list(validator.iter_errors(artifact))
        assert not errors, (key, [e.message for e in errors])


# =============================================================================
# Qualifying and incomplete class-B evidence
# =============================================================================


def test_qualifying_class_b_bundle_is_schema_valid() -> None:
    bundle = make_evidence_bundle("qualifying_class_b")
    _assert_bundle_schema_valid(bundle)
    fields = bundle["observation"]["observations"]
    assert fields["edit_or_regeneration_used"]["status"] == "operator_attested"
    assert bundle["attestation"] is not None


def test_incomplete_class_b_bundle_has_no_attested_claims() -> None:
    """Without an attestation, nothing may claim operator_attested."""
    bundle = make_evidence_bundle("incomplete_class_b")
    _assert_bundle_schema_valid(bundle)
    assert bundle["attestation"] is None
    for field in bundle["observation"]["observations"].values():
        assert field["status"] != "operator_attested"


def test_attestation_and_action_log_builders_are_schema_valid() -> None:
    assert not list(ATTESTATION.iter_errors(make_attestation()))
    assert not list(ACTION_LOG.iter_errors(make_action_log()))


def test_incomplete_attestation_is_schema_invalid() -> None:
    """A missing required assertion cannot be attested around."""
    attestation = make_attestation()
    del attestation["assertions"]["first_returned_image_retained"]
    assert list(ATTESTATION.iter_errors(attestation))


# =============================================================================
# Class-C: simulated presence and genuine absence
# =============================================================================


def test_simulated_class_c_bundle_is_schema_valid_but_only_simulated() -> None:
    bundle = make_evidence_bundle("simulated_class_c")
    _assert_bundle_schema_valid(bundle)
    backend = bundle["observation"]["observations"]["backend_model"]
    assert backend["status"] == "host_observed"
    assert backend["source_class"] == "C"
    # The fixture label itself records that this is a simulation, so the
    # synthetic digest can never be mistaken for authenticated telemetry.
    assert bundle["scenario"] == "simulated_class_c"


def test_missing_class_c_telemetry_uses_null_unavailable_fields() -> None:
    bundle = make_evidence_bundle("missing_class_c")
    _assert_bundle_schema_valid(bundle)
    for name in ("backend_model", "provider_generation_id"):
        field = bundle["observation"]["observations"][name]
        assert field["status"] == "not_observable"
        assert field["value"] is None
        assert field["source_ref"] is None


# =============================================================================
# Contradictory class-D reports
# =============================================================================


def test_contradictory_class_d_reports_do_not_touch_observations() -> None:
    bundle = make_evidence_bundle("contradictory_class_d")
    _assert_bundle_schema_valid(bundle)
    observation = bundle["observation"]
    reports = observation["model_reports"]
    assert reports, "the fixture must actually contain model reports"
    for report in reports:
        assert report["source"] == "model"
        assert report["claimed_status"] == "model_reported"
        authoritative = observation["observations"][report["field"]]
        assert authoritative["value"] != report["claimed_value"]


# =============================================================================
# Request and response captures
# =============================================================================


def test_valid_captures_are_schema_valid_and_temporally_ordered() -> None:
    request = make_request_capture()
    response = make_response_capture()
    assert not list(REQUEST.iter_errors(request))
    assert not list(RESPONSE.iter_errors(response))
    # Lexicographic order matches chronological order for these ISO stamps;
    # real ordering remains a runtime-reserved check.
    assert request["captured_at_utc"] < response["captured_at_utc"]


@pytest.mark.parametrize("kind", [
    "bad_paste_digest",
    "zero_generation_requests",
    "authenticated_bytes_not_a_digest",
    "missing_rendered_digest",
])
def test_invalid_request_captures_are_rejected(kind: str) -> None:
    assert list(REQUEST.iter_errors(make_invalid_request_capture(kind)))


@pytest.mark.parametrize("kind", [
    "no_result_without_evidence",
    "no_result_operator_belief",
    "no_result_with_artifact_id",
    "returned_with_zero_count",
])
def test_invalid_response_captures_are_rejected(kind: str) -> None:
    assert list(RESPONSE.iter_errors(make_invalid_response_capture(kind)))


# =============================================================================
# Failure and unknown outcomes (distinct dispositions)
# =============================================================================


def test_no_output_failure_bundle() -> None:
    """An affirmative no-result is a recorded failure, with no raster."""
    bundle = make_evidence_bundle("no_output_failure")
    _assert_bundle_schema_valid(bundle)
    assert bundle["raster_bytes"] is None
    response = bundle["response_capture"]
    assert response["image_returned"] is False
    assert response["no_result_evidence"] == "host_error_recorded"
    assert response["artifact_id"] is None


def test_interrupted_unknown_bundle_is_not_a_failure() -> None:
    """An interrupted invocation is unknown: no response capture exists."""
    bundle = make_evidence_bundle("interrupted_unknown")
    _assert_bundle_schema_valid(bundle)
    assert bundle["response_capture"] is None
    actions = [e["action"] for e in bundle["action_log"]["entries"]]
    assert "generation_request_submitted" in actions
    assert "response_captured" not in actions
    assert "slot_closed" not in actions


# =============================================================================
# Raster bytes and digests
# =============================================================================


def test_synthetic_raster_is_a_real_png() -> None:
    raster = synthetic_raster_bytes()
    assert raster.startswith(b"\x89PNG\r\n\x1a\n")


def test_invalid_raster_is_not_a_png() -> None:
    bundle = make_evidence_bundle("invalid_raster")
    _assert_bundle_schema_valid(bundle)
    assert not bundle["raster_bytes"].startswith(b"\x89PNG")


def test_digest_mismatch_bundle_really_mismatches() -> None:
    bundle = make_evidence_bundle("digest_mismatch")
    _assert_bundle_schema_valid(bundle)
    claimed = bundle["observation"]["observations"]["output_sha256"]["value"]
    actual = hashlib.sha256(bundle["raster_bytes"]).hexdigest()
    assert claimed != actual


def test_qualifying_bundle_digest_matches_raster() -> None:
    bundle = make_evidence_bundle("qualifying_class_b")
    claimed = bundle["observation"]["observations"]["output_sha256"]["value"]
    actual = hashlib.sha256(bundle["raster_bytes"]).hexdigest()
    assert claimed == actual


# =============================================================================
# Schema/status violations
# =============================================================================


@pytest.mark.parametrize("kind", [
    "model_reported_in_authoritative_field",
    "host_observed_with_operator_class",
    "unavailable_with_a_value",
    "available_with_null_value",
    "unavailable_with_model_class",
])
def test_status_violations_are_rejected(kind: str) -> None:
    assert list(OBSERVATION.iter_errors(make_status_violation(kind)))


# =============================================================================
# Treatment-free reviewer-facing artifacts
# =============================================================================


_FORBIDDEN_REVIEWER_KEYS = {
    "condition", "conditions", "treatment", "variant", "arm",
    "prompt", "prompt_text", "prompt_sha256", "mapping",
    "condition_id", "treatment_id", "expected_score",
}


def _all_keys(obj) -> set:
    keys = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            keys.add(key)
            keys |= _all_keys(value)
    elif isinstance(obj, list):
        for item in obj:
            keys |= _all_keys(item)
    return keys


def test_reviewer_artifact_is_treatment_free() -> None:
    artifact = make_reviewer_artifact()
    assert not (_all_keys(artifact) & _FORBIDDEN_REVIEWER_KEYS)
    assert artifact["opaque_slot_id"] == SLOT


def test_builders_use_only_the_synthetic_slot() -> None:
    """No builder may emit an identifier other than the synthetic one."""
    bundle = make_evidence_bundle("qualifying_class_b")
    for key in ARTIFACT_VALIDATORS:
        assert bundle[key]["opaque_slot_id"] == SLOT
    assert make_reviewer_artifact()["opaque_slot_id"] == SLOT


def test_observation_builder_defaults_to_missing_class_c() -> None:
    """The plain builder must not silently invent host telemetry."""
    fields = make_observation()["observations"]
    assert fields["backend_model"]["status"] == "not_observable"
