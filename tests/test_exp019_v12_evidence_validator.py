"""Tests for the EXP-019 v1.2 runtime evidence validator (PR-6).

The validator enforces the cross-artifact rules the draft schemas reserve
for runtime validation. All inputs come from the merged synthetic fixture
builders (PR-3); no experimental allocation, live host session, external
checkpoint, or real-run artifact is involved. The validator must remain
outcome-safe: it returns structured findings and an eligibility assessment,
commits no disposition, and mutates nothing.
"""

from __future__ import annotations

import copy
import hashlib

import pytest

from aipf.exp019_protocol import frozen_protocol
from aipf.exp019_v12_evidence import validate_evidence_bundle

from exp019_v1_2_synthetic_fixtures import make_evidence_bundle


def _codes(report) -> set:
    return {f.code for f in report.findings}


def _q(report, name):
    return next(r for r in report.q_results if r.check == name)


# =============================================================================
# Positive paths
# =============================================================================


def test_valid_qualifying_class_b_bundle_is_admit_eligible() -> None:
    report = validate_evidence_bundle(make_evidence_bundle("qualifying_class_b"))
    assert report.admit_eligible
    assert report.admission_eligibility == "eligible_for_admit"
    assert report.outcome_classification == "returned_evidenced"
    assert not report.errors
    for name in ("Q1", "Q2", "Q3", "Q4", "Q5"):
        assert _q(report, name).passed, name


def test_contradictory_class_d_report_remains_admit_with_conflict() -> None:
    """A class-D conflict is disclosed, never decisive (approved policy)."""
    report = validate_evidence_bundle(
        make_evidence_bundle("contradictory_class_d"))
    assert report.admit_with_conflict
    assert report.class_d_conflict_count == 2
    assert "CLASS_D_CONFLICT" in _codes(report)
    assert not report.errors


def test_missing_class_c_telemetry_does_not_block_eligibility() -> None:
    report = validate_evidence_bundle(make_evidence_bundle("missing_class_c"))
    assert report.admit_eligible
    assert "CLASS_C_TELEMETRY_MISSING" in _codes(report)


def test_simulated_class_c_is_rejected_without_external_authentication() -> None:
    """A digest or claimed status can never forge class-C evidence."""
    report = validate_evidence_bundle(make_evidence_bundle("simulated_class_c"))
    assert not report.admit_eligible
    assert "CLASS_C_NOT_AUTHENTICATED" in _codes(report)


def test_class_c_accepted_only_with_externally_authenticated_refs() -> None:
    bundle = make_evidence_bundle("simulated_class_c")
    refs = {
        f["source_ref"]
        for f in bundle["observation"]["observations"].values()
        if f["status"] == "host_observed"
    }
    report = validate_evidence_bundle(
        bundle, authenticated_class_c_refs=refs)
    assert report.admit_eligible
    assert "CLASS_C_NOT_AUTHENTICATED" not in _codes(report)


# =============================================================================
# Incomplete and violated evidence
# =============================================================================


def test_incomplete_class_b_is_never_admit_eligible() -> None:
    report = validate_evidence_bundle(make_evidence_bundle("incomplete_class_b"))
    assert not report.admit_eligible
    assert _q(report, "Q4").passed is False


def test_no_result_bundle_is_evidenced_failure_not_unknown() -> None:
    report = validate_evidence_bundle(make_evidence_bundle("no_output_failure"))
    assert report.outcome_classification == "no_result_evidenced"
    assert not report.admit_eligible
    assert "UNKNOWN_OUTCOME" not in _codes(report)


def test_interrupted_bundle_is_unknown_not_failure() -> None:
    report = validate_evidence_bundle(make_evidence_bundle("interrupted_unknown"))
    assert report.outcome_classification == "unknown_outcome"
    assert "UNKNOWN_OUTCOME" in _codes(report)
    assert not report.admit_eligible


def test_invalid_raster_is_rejected() -> None:
    report = validate_evidence_bundle(make_evidence_bundle("invalid_raster"))
    assert not report.admit_eligible
    assert "INVALID_RASTER" in _codes(report)


def test_digest_mismatch_bundle_is_rejected() -> None:
    report = validate_evidence_bundle(make_evidence_bundle("digest_mismatch"))
    assert not report.admit_eligible
    assert "OUTPUT_DIGEST_MISMATCH" in _codes(report)
    assert _q(report, "Q3").passed is False


def test_cross_artifact_identity_mismatch_is_rejected() -> None:
    bundle = make_evidence_bundle("qualifying_class_b")
    bundle["response_capture"]["attempt_number"] = 2
    report = validate_evidence_bundle(bundle)
    assert not report.admit_eligible
    assert "IDENTITY_MISMATCH" in _codes(report)


def test_response_before_request_is_rejected() -> None:
    bundle = make_evidence_bundle("qualifying_class_b")
    bundle["response_capture"]["captured_at_utc"] = "2026-01-01T00:00:01+00:00"
    report = validate_evidence_bundle(bundle)
    assert not report.admit_eligible
    assert "TEMPORAL_ORDER_VIOLATION" in _codes(report)


def test_action_log_sequence_gap_is_rejected() -> None:
    bundle = make_evidence_bundle("qualifying_class_b")
    bundle["action_log"]["entries"][3]["seq"] = 99
    report = validate_evidence_bundle(bundle)
    assert not report.admit_eligible
    assert "ACTION_LOG_SEQUENCE" in _codes(report)
    assert _q(report, "Q5").passed is False


def test_attestation_digest_mismatch_is_rejected() -> None:
    bundle = make_evidence_bundle("qualifying_class_b")
    bundle["attestation"]["artifact_digest_sha256"] = "b" * 64
    report = validate_evidence_bundle(bundle)
    assert not report.admit_eligible
    assert "ATTESTATION_DIGEST_MISMATCH" in _codes(report)
    assert _q(report, "Q4").passed is False


def test_unresolved_source_ref_is_rejected_when_bytes_are_supplied() -> None:
    bundle = make_evidence_bundle("qualifying_class_b")
    report = validate_evidence_bundle(bundle, supporting_artifact_bytes={})
    assert not report.admit_eligible
    assert "SOURCE_REF_UNRESOLVED" in _codes(report)


def test_frozen_pasted_prompt_digest_mismatch_is_rejected() -> None:
    bundle = make_evidence_bundle("qualifying_class_b")
    bundle["observation"]["protocol_constants"]["prompt_sha256"] = "c" * 64
    report = validate_evidence_bundle(bundle)
    assert not report.admit_eligible
    assert "PROMPT_DIGEST_MISMATCH" in _codes(report)


def test_rendered_textual_mismatch_is_distinct_from_byte_identity() -> None:
    bundle = make_evidence_bundle("qualifying_class_b")
    bundle["request_capture"]["rendered_request_comparison"] = "textual_mismatch"
    report = validate_evidence_bundle(bundle)
    assert not report.admit_eligible
    assert "RENDERED_TEXTUAL_MISMATCH" in _codes(report)
    assert "PROMPT_DIGEST_MISMATCH" not in _codes(report)


def test_no_result_with_fabricated_artifact_id_is_rejected() -> None:
    bundle = make_evidence_bundle("no_output_failure")
    bundle["response_capture"]["artifact_id"] = "invented-artifact"
    report = validate_evidence_bundle(bundle)
    assert not report.admit_eligible
    assert "FABRICATED_ARTIFACT_ID" in _codes(report)
    assert report.outcome_classification != "no_result_evidenced"


def test_bc_material_conflict_is_reported_separately() -> None:
    bundle = make_evidence_bundle("simulated_class_c")
    field = bundle["observation"]["observations"]["returned_output_count"]
    field.update({"value": 5, "status": "host_observed", "source_class": "C",
                  "source_ref": "d" * 64})
    report = validate_evidence_bundle(
        bundle, authenticated_class_c_refs={"d" * 64} |
        {f["source_ref"] for f in
         bundle["observation"]["observations"].values()
         if f["status"] == "host_observed"})
    assert report.b_c_material_conflicts == ("BC_RETURNED_COUNT_CONFLICT",)
    assert "BC_MATERIAL_CONFLICT" in _codes(report)
    assert not report.admit_eligible


# =============================================================================
# Outcome safety, privacy, and the activation lockout
# =============================================================================


def test_repeated_validation_does_not_mutate_the_bundle() -> None:
    bundle = make_evidence_bundle("contradictory_class_d")
    snapshot = copy.deepcopy(bundle)
    first = validate_evidence_bundle(bundle)
    second = validate_evidence_bundle(bundle)
    assert bundle == snapshot
    assert first == second


def test_reviewer_role_cannot_access_validation_details() -> None:
    report = validate_evidence_bundle(
        make_evidence_bundle("qualifying_class_b"), requester_role="reviewer")
    assert not report.admit_eligible
    assert _codes(report) == {"ROLE_ACCESS_DENIED"}


def test_validator_output_carries_no_treatment_bearing_values() -> None:
    """Findings name fields only; no claimed values leak into the report."""
    report = validate_evidence_bundle(
        make_evidence_bundle("contradictory_class_d"))
    rendered = repr(report)
    assert "synthetic contradictory" not in rendered
    assert "model_reports" not in rendered


def test_activation_lockout_remains_effective() -> None:
    """PR-6 adds a validator only: v1.2 still cannot be activated."""
    import aipf.exp019_v12_evidence as validator

    assert not hasattr(validator, "create_run")
    assert not hasattr(validator, "generate")
    assert not hasattr(validator, "allocate")
    assert not hasattr(validator, "commit_checkpoint")
    with pytest.raises(ValueError,
                       match="unknown EXP-019 frozen protocol version"):
        frozen_protocol("1.2.0")


def test_validation_needs_no_allocation_or_checkpoint() -> None:
    """The full check runs offline on the synthetic bundle alone."""
    bundle = make_evidence_bundle("qualifying_class_b")
    expected = hashlib.sha256(bundle["raster_bytes"]).hexdigest()
    report = validate_evidence_bundle(bundle)
    assert report.admit_eligible
    assert bundle["observation"]["observations"]["output_sha256"]["value"] \
        == expected
