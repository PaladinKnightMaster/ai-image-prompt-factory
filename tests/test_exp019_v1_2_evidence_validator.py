"""Tests for the EXP-019 v1.2 runtime evidence validator (PR-6).

Canonical Q1-Q5 semantics come from the merged G1 engineering contract
(Q1 request capture, Q2 response capture, Q3 action log, Q4 artifact
digests, Q5 operator attestation). All inputs come from the merged
synthetic fixture builders (PR-3); no experimental allocation, live host
session, external checkpoint, or real-run artifact is involved. The
validator must remain outcome-safe: it returns structured findings and an
evidence-eligibility assessment, commits no disposition, and mutates
nothing. Evidence eligibility is not scientific admission.
"""

from __future__ import annotations

import copy
import hashlib
import re
from pathlib import Path

import pytest

from aipf.exp019_protocol import frozen_protocol
from aipf import exp019_v1_2_evidence as validator
from aipf.exp019_v1_2_evidence import (
    Q_DEFINITIONS,
    canonical_artifact_digest,
    validate_evidence_bundle,
)

from exp019_v1_2_synthetic_fixtures import (
    make_evidence_bundle,
    synthetic_raster_bytes,
)

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_CONTRACT = (
    ROOT / "docs" / "drafts" / "EXP-019-v1.2.0.EVIDENCE-CONTRACT-DRAFT.md")


def _codes(report) -> set:
    return {f.code for f in report.findings}


def _q(report, name):
    return next(r for r in report.q_results if r.check == name)


def _integrity(report, field):
    return next(s for s in report.source_integrity if s.field == field)


# =============================================================================
# Canonical Q1-Q5 semantics
# =============================================================================


def test_q_identifiers_match_the_approved_contract_definitions() -> None:
    """Each Q identifier corresponds to its contract definition, verbatim."""
    normalized = " ".join(
        EVIDENCE_CONTRACT.read_text(encoding="utf-8").split())
    lines = dict(re.findall(
        r"- \*\*(Q[1-5])\*\* — (.*?)(?= - \*\*Q[1-5]\*\*| Evidence that)",
        normalized))
    assert set(lines) == {"Q1", "Q2", "Q3", "Q4", "Q5"}
    for check in ("Q1", "Q2", "Q3", "Q4"):
        assert Q_DEFINITIONS[check] in lines[check], check
    # Q5's contract line defines the attestation requirement itself.
    assert "attestation" in lines["Q5"] and "hash-bound" in lines["Q5"]
    assert Q_DEFINITIONS["Q5"] == "operator attestation"


def test_q_results_carry_canonical_definitions() -> None:
    report = validate_evidence_bundle(make_evidence_bundle("qualifying_class_b"))
    assert [(r.check, r.definition) for r in report.q_results] == [
        ("Q1", "request capture"),
        ("Q2", "response capture"),
        ("Q3", "action log"),
        ("Q4", "artifact digests"),
        ("Q5", "operator attestation"),
    ]


# =============================================================================
# Positive paths
# =============================================================================


def test_valid_qualifying_class_b_bundle_is_evidence_eligible() -> None:
    report = validate_evidence_bundle(make_evidence_bundle("qualifying_class_b"))
    assert report.evidence_eligible
    assert report.evidence_eligibility == "evidence_eligible"
    assert report.outcome_classification == "returned_evidenced"
    assert report.technical_validation == "passed"
    assert report.raster_format == "PNG"
    assert not report.errors
    for name in ("Q1", "Q2", "Q3", "Q4", "Q5"):
        assert _q(report, name).passed, name


def test_contradictory_class_d_report_remains_eligible_with_conflict() -> None:
    """A class-D conflict is disclosed, never decisive (approved policy)."""
    report = validate_evidence_bundle(
        make_evidence_bundle("contradictory_class_d"))
    assert report.evidence_eligible_with_conflict
    assert report.class_d_conflict_count == 2
    assert "CLASS_D_CONFLICT" in _codes(report)
    assert not report.errors


def test_missing_class_c_telemetry_does_not_block_eligibility() -> None:
    report = validate_evidence_bundle(make_evidence_bundle("missing_class_c"))
    assert report.evidence_eligible
    assert "CLASS_C_TELEMETRY_MISSING" in _codes(report)


# =============================================================================
# Class-C authentication boundary (A4)
# =============================================================================


def test_simulated_class_c_is_rejected_without_authentication() -> None:
    """A digest or claimed status can never forge class-C evidence."""
    report = validate_evidence_bundle(make_evidence_bundle("simulated_class_c"))
    assert not report.evidence_eligible
    assert "CLASS_C_NOT_AUTHENTICATED" in _codes(report)


def test_caller_supplied_digest_set_cannot_authenticate_class_c() -> None:
    """The removed digest-set interface stays removed: digests are data,
    not an authenticator, so an untrusted caller cannot elevate them."""
    bundle = make_evidence_bundle("simulated_class_c")
    refs = {
        f["source_ref"]
        for f in bundle["observation"]["observations"].values()
        if f["status"] == "host_observed"
    }
    with pytest.raises(TypeError, match="must be a callable"):
        validate_evidence_bundle(bundle, host_authenticator=refs)


def test_class_c_requires_the_trusted_authenticator_boundary() -> None:
    """Only a trusted-layer authenticator (stubbed here at the boundary,
    never by synthetic fixture data) can verify a host_observed field."""
    bundle = make_evidence_bundle("simulated_class_c")
    verified_refs = {
        f["source_ref"]
        for f in bundle["observation"]["observations"].values()
        if f["status"] == "host_observed"
    }

    def trusted_host_layer_stub(source_ref: str) -> bool:
        # Stands in for verification performed through an authenticated
        # host channel outside the validator; fixtures supply no such
        # channel and this stub is test scaffolding, not proof of
        # production authentication.
        return source_ref in verified_refs

    report = validate_evidence_bundle(
        bundle, host_authenticator=trusted_host_layer_stub)
    assert report.evidence_eligible
    assert "CLASS_C_NOT_AUTHENTICATED" not in _codes(report)
    assert all(s.authenticated for s in report.source_integrity
               if s.field in ("provider_generation_id", "backend_model"))


def test_authenticator_that_verifies_nothing_elevates_nothing() -> None:
    bundle = make_evidence_bundle("simulated_class_c")
    report = validate_evidence_bundle(
        bundle, host_authenticator=lambda source_ref: False)
    assert not report.evidence_eligible
    assert "CLASS_C_NOT_AUTHENTICATED" in _codes(report)


# =============================================================================
# Raster technical validation (A3)
# =============================================================================


def test_valid_png_fully_decodes() -> None:
    report = validate_evidence_bundle(make_evidence_bundle("qualifying_class_b"))
    assert report.technical_validation == "passed"
    assert report.raster_dimensions == (1, 1)


def test_truncated_png_is_not_evaluable_despite_valid_signature() -> None:
    bundle = make_evidence_bundle("qualifying_class_b")
    bundle["raster_bytes"] = synthetic_raster_bytes()[:20]
    report = validate_evidence_bundle(bundle)
    assert report.technical_validation == "failed"
    assert "INVALID_RASTER" in _codes(report)
    assert not report.evidence_eligible


def test_corrupt_png_is_not_evaluable_despite_valid_signature() -> None:
    bundle = make_evidence_bundle("qualifying_class_b")
    bundle["raster_bytes"] = b"\x89PNG\r\n\x1a\n" + b"synthetic garbage"
    report = validate_evidence_bundle(bundle)
    assert report.technical_validation == "failed"
    assert not report.evidence_eligible


def test_non_png_bytes_are_rejected() -> None:
    report = validate_evidence_bundle(make_evidence_bundle("invalid_raster"))
    assert report.technical_validation == "failed"
    assert "INVALID_RASTER" in _codes(report)
    assert not report.evidence_eligible


def test_missing_decoder_yields_pending_never_eligible(monkeypatch) -> None:
    """Without a trusted decoder, evidence is pending, not admissible."""
    monkeypatch.setattr(validator, "_PIL_Image", None)
    report = validate_evidence_bundle(make_evidence_bundle("qualifying_class_b"))
    assert report.technical_validation == "pending"
    assert "TECHNICAL_VALIDATION_PENDING" in _codes(report)
    assert not report.evidence_eligible


# =============================================================================
# Supporting-artifact integrity levels (A5)
# =============================================================================


def test_declared_digest_alone_is_not_verified_integrity() -> None:
    report = validate_evidence_bundle(make_evidence_bundle("qualifying_class_b"))
    assert _integrity(report, "conversation_ref").level == "declared_only"
    assert "SOURCE_DECLARED_ONLY" in _codes(report)


def test_recomputed_level_requires_bytes_that_hash_to_the_digest() -> None:
    bundle = make_evidence_bundle("qualifying_class_b")
    payload = b"synthetic supporting payload"
    digest = hashlib.sha256(payload).hexdigest()
    bundle["observation"]["observations"]["conversation_ref"][
        "source_ref"] = digest
    report = validate_evidence_bundle(
        bundle, supporting_artifact_bytes={digest: payload})
    assert _integrity(report, "conversation_ref").level == "recomputed"


def test_unresolved_source_ref_is_rejected_when_bytes_are_supplied() -> None:
    bundle = make_evidence_bundle("qualifying_class_b")
    report = validate_evidence_bundle(bundle, supporting_artifact_bytes={})
    assert not report.evidence_eligible
    assert "SOURCE_REF_UNRESOLVED" in _codes(report)
    assert _integrity(report, "conversation_ref").level == "unresolved"


def test_output_digest_binding_is_a_verified_binding() -> None:
    report = validate_evidence_bundle(make_evidence_bundle("qualifying_class_b"))
    assert _integrity(report, "output_sha256").level == "verified_binding"
    assert _integrity(
        report, "attestation.artifact_digest_sha256").level == \
        "verified_binding"


def test_artifact_commitments_bind_complete_serialized_artifacts() -> None:
    bundle = make_evidence_bundle("qualifying_class_b")
    commitments = {
        name: canonical_artifact_digest(bundle[name])
        for name in ("observation", "attestation", "action_log",
                     "request_capture", "response_capture")
    }
    report = validate_evidence_bundle(
        bundle, artifact_commitments=commitments)
    assert report.evidence_eligible

    bundle["action_log"]["entries"][0]["action"] = "tampered"
    report = validate_evidence_bundle(
        bundle, artifact_commitments=commitments)
    assert not report.evidence_eligible
    assert "ARTIFACT_COMMITMENT_MISMATCH" in _codes(report)


# =============================================================================
# Incomplete and violated evidence, canonical Q attribution
# =============================================================================


def test_incomplete_class_b_is_never_eligible_and_fails_q5() -> None:
    report = validate_evidence_bundle(make_evidence_bundle("incomplete_class_b"))
    assert not report.evidence_eligible
    assert _q(report, "Q5").passed is False  # Q5: operator attestation


def test_no_result_bundle_is_evidenced_failure_not_unknown() -> None:
    report = validate_evidence_bundle(make_evidence_bundle("no_output_failure"))
    assert report.outcome_classification == "no_result_evidenced"
    assert report.technical_validation == "not_applicable"
    assert not report.evidence_eligible
    assert "UNKNOWN_OUTCOME" not in _codes(report)


def test_interrupted_bundle_is_unknown_not_failure() -> None:
    report = validate_evidence_bundle(make_evidence_bundle("interrupted_unknown"))
    assert report.outcome_classification == "unknown_outcome"
    assert "UNKNOWN_OUTCOME" in _codes(report)
    assert not report.evidence_eligible


def test_digest_mismatch_bundle_fails_q4() -> None:
    report = validate_evidence_bundle(make_evidence_bundle("digest_mismatch"))
    assert not report.evidence_eligible
    assert "OUTPUT_DIGEST_MISMATCH" in _codes(report)
    assert _q(report, "Q4").passed is False  # Q4: artifact digests


def test_cross_artifact_identity_mismatch_is_rejected() -> None:
    bundle = make_evidence_bundle("qualifying_class_b")
    bundle["response_capture"]["attempt_number"] = 2
    report = validate_evidence_bundle(bundle)
    assert not report.evidence_eligible
    assert "IDENTITY_MISMATCH" in _codes(report)


def test_response_before_request_is_rejected() -> None:
    bundle = make_evidence_bundle("qualifying_class_b")
    bundle["response_capture"]["captured_at_utc"] = "2026-01-01T00:00:01+00:00"
    report = validate_evidence_bundle(bundle)
    assert not report.evidence_eligible
    assert "TEMPORAL_ORDER_VIOLATION" in _codes(report)


def test_action_log_sequence_gap_fails_q3() -> None:
    bundle = make_evidence_bundle("qualifying_class_b")
    bundle["action_log"]["entries"][3]["seq"] = 99
    report = validate_evidence_bundle(bundle)
    assert not report.evidence_eligible
    assert "ACTION_LOG_SEQUENCE" in _codes(report)
    assert _q(report, "Q3").passed is False  # Q3: action log


def test_attestation_digest_mismatch_fails_q5() -> None:
    bundle = make_evidence_bundle("qualifying_class_b")
    bundle["attestation"]["artifact_digest_sha256"] = "b" * 64
    report = validate_evidence_bundle(bundle)
    assert not report.evidence_eligible
    assert "ATTESTATION_DIGEST_MISMATCH" in _codes(report)
    assert _q(report, "Q5").passed is False  # Q5: operator attestation


def test_frozen_pasted_prompt_digest_mismatch_fails_q4() -> None:
    bundle = make_evidence_bundle("qualifying_class_b")
    bundle["observation"]["protocol_constants"]["prompt_sha256"] = "c" * 64
    report = validate_evidence_bundle(bundle)
    assert not report.evidence_eligible
    assert "PROMPT_DIGEST_MISMATCH" in _codes(report)
    assert _q(report, "Q4").passed is False


def test_rendered_textual_mismatch_is_distinct_from_byte_identity() -> None:
    bundle = make_evidence_bundle("qualifying_class_b")
    bundle["request_capture"]["rendered_request_comparison"] = "textual_mismatch"
    report = validate_evidence_bundle(bundle)
    assert not report.evidence_eligible
    assert "RENDERED_TEXTUAL_MISMATCH" in _codes(report)
    assert "PROMPT_DIGEST_MISMATCH" not in _codes(report)
    assert _q(report, "Q1").passed is False  # textual comparison is Q1


def test_no_result_with_fabricated_artifact_id_is_rejected() -> None:
    bundle = make_evidence_bundle("no_output_failure")
    bundle["response_capture"]["artifact_id"] = "invented-artifact"
    report = validate_evidence_bundle(bundle)
    assert not report.evidence_eligible
    assert "FABRICATED_ARTIFACT_ID" in _codes(report)
    assert report.outcome_classification != "no_result_evidenced"


def test_bc_material_conflict_is_reported_separately() -> None:
    bundle = make_evidence_bundle("simulated_class_c")
    field = bundle["observation"]["observations"]["returned_output_count"]
    field.update({"value": 5, "status": "host_observed", "source_class": "C",
                  "source_ref": "d" * 64})
    authenticated = {"d" * 64} | {
        f["source_ref"] for f in
        bundle["observation"]["observations"].values()
        if f["status"] == "host_observed"}
    report = validate_evidence_bundle(
        bundle, host_authenticator=authenticated.__contains__)
    assert report.b_c_material_conflicts == ("BC_RETURNED_COUNT_CONFLICT",)
    assert "BC_MATERIAL_CONFLICT" in _codes(report)
    assert not report.evidence_eligible


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
    assert not report.evidence_eligible
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
    assert report.evidence_eligible
    assert bundle["observation"]["observations"]["output_sha256"]["value"] \
        == expected
