"""Tests for EXP-019 v1.2 terminal attempt receipts (PR-8).

Synthetic fixtures only (PR-3 builders, synthetic lifecycle stores in
temporary directories). No experimental allocation, run root, host
session, generation, or external checkpoint is involved. Legacy v1.1.1
receipt semantics are untouched; cross-version receipts are rejected.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from aipf import exp019_v1_2_receipts as receipts_module
from aipf.exp019_protocol import frozen_protocol
from aipf.exp019_v1_2_evidence import validate_evidence_bundle
from aipf.exp019_v1_2_lifecycle import (
    AttemptLifecycle,
    AuthorizationError,
    InvalidTransitionError,
    LifecycleStore,
)
from aipf.exp019_v1_2_receipts import (
    build_terminal_receipt,
    canonical_receipt_sha256,
    finalize_attempt_with_receipt,
    latest_receipt_status,
    load_stored_receipt,
    store_receipt,
    verify_terminal_receipt,
)

from exp019_v1_2_synthetic_fixtures import make_evidence_bundle

ROOT = Path(__file__).resolve().parents[1]
SLOT = "ZZZZZZ"


def _auth(slot=SLOT, attempt=1) -> dict:
    return {
        "authorization_id": "synthetic-auth-1",
        "authorized_by": "synthetic-owner",
        "reason": "synthetic unresolved outcome",
        "procedure": "H3-indeterminate-disposition",
        "action": "INDETERMINATE_FINAL",
        "run_id": "synthetic-run",
        "slot_id": slot,
        "attempt_number": attempt,
        "contract_version": "1.2.0",
    }


def _verify_anchor(record, anchor_ref) -> bool:
    return isinstance(anchor_ref, str) and "anchor" in anchor_ref


def _lifecycle(tmp_path) -> AttemptLifecycle:
    life = AttemptLifecycle(LifecycleStore(tmp_path / "store"),
                            anchor_verifier=_verify_anchor)
    life.plan_slot(SLOT)
    life.start_invocation(SLOT)
    return life


def _prompt_digest(bundle) -> str:
    return bundle["observation"]["protocol_constants"]["prompt_sha256"]


def _admitted_receipt(tmp_path, bundle=None):
    bundle = bundle or make_evidence_bundle("qualifying_class_b")
    life = _lifecycle(tmp_path)
    digest = life.record_output(SLOT, bundle["raster_bytes"])
    receipt = finalize_attempt_with_receipt(
        life, SLOT, "ADMIT", slot_position=1,
        frozen_prompt_sha256=_prompt_digest(bundle),
        evidence_bundle=bundle)
    return life, bundle, digest, receipt


# =============================================================================
# Positive outcomes
# =============================================================================


def test_successful_admitted_attempt_receipt(tmp_path) -> None:
    life, bundle, digest, receipt = _admitted_receipt(tmp_path)
    assert receipt["disposition"] == "ADMIT"
    assert receipt["experiment_version"] == "1.2.0"
    assert receipt["output"]["output_state"] == "admitted"
    assert receipt["output"]["output_sha256"] == digest
    assert receipt["output"]["admitted_output_sha256"] == digest
    assert receipt["output"]["output_location"] == "canonical_admitted"
    assert receipt["output"]["no_output_reason"] is None
    # Durable local finalization, awaiting (never claiming) anchoring.
    assert receipt["local_finalization_status"] == \
        "awaiting_external_anchor"
    assert life.external_anchor_pending()[0]["disposition"] == "ADMIT"

    result = verify_terminal_receipt(
        receipt, lifecycle=life, evidence_bundle=bundle,
        output_bytes=bundle["raster_bytes"],
        admitted_output_bytes=bundle["raster_bytes"])
    assert result.verified, result.codes


def test_receipt_binds_canonical_q1_q5_validation(tmp_path) -> None:
    _, _, _, receipt = _admitted_receipt(tmp_path)
    checks = receipt["evidence_validation"]["checks"]
    assert [(c["check"], c["definition"]) for c in checks] == [
        ("Q1", "request capture"), ("Q2", "response capture"),
        ("Q3", "action log"), ("Q4", "artifact digests"),
        ("Q5", "operator attestation")]
    assert all(c["passed"] for c in checks)


def test_multiple_class_d_conflicts_in_one_admitted_sample(tmp_path) -> None:
    bundle = make_evidence_bundle("contradictory_class_d")
    report = validate_evidence_bundle(bundle)
    assert report.class_d_conflict_count == 2
    life = _lifecycle(tmp_path)
    life.record_output(SLOT, bundle["raster_bytes"])
    receipt = finalize_attempt_with_receipt(
        life, SLOT, "ADMIT", slot_position=1,
        frozen_prompt_sha256=_prompt_digest(bundle),
        evidence_bundle=bundle, validation_report=report,
        class_d_conflict_count=report.class_d_conflict_count)
    assert receipt["class_d_conflict_count"] == 2
    assert receipt["provenance_qualification"] == \
        "operator_evidenced_with_class_d_conflict"
    assert verify_terminal_receipt(receipt, lifecycle=life).verified


def test_technical_failure_then_successful_eligible_retry(tmp_path) -> None:
    life = _lifecycle(tmp_path)
    life.confirm_no_result(SLOT, evidence="host_error_recorded",
                           failure_classification="host_technical_error")
    first = finalize_attempt_with_receipt(
        life, SLOT, "FAILURE", slot_position=1,
        frozen_prompt_sha256="a" * 64)
    assert first["output"]["output_state"] == "absent_no_output"
    assert first["output"]["output_sha256"] is None  # never invented
    assert first["output"]["no_output_reason"]
    assert verify_terminal_receipt(first, lifecycle=life).verified

    life.record_external_anchor(SLOT, 1, "anchor-1")
    life.request_retry(SLOT)
    bundle = make_evidence_bundle("qualifying_class_b")
    life.record_output(SLOT, bundle["raster_bytes"])
    second = finalize_attempt_with_receipt(
        life, SLOT, "ADMIT", slot_position=1,
        frozen_prompt_sha256=_prompt_digest(bundle),
        evidence_bundle=bundle)
    assert second["attempt_number"] == 2
    assert second["predecessor_attempt"] == 1
    assert verify_terminal_receipt(second, lifecycle=life).verified


def test_three_technical_failures_exhaust_budget_with_receipts(
        tmp_path) -> None:
    life = _lifecycle(tmp_path)
    receipts = []
    for attempt in (1, 2, 3):
        life.confirm_no_result(
            SLOT, evidence="host_error_recorded",
            failure_classification="host_timeout")
        receipts.append(finalize_attempt_with_receipt(
            life, SLOT, "FAILURE", slot_position=1,
            frozen_prompt_sha256="b" * 64))
        life.record_external_anchor(SLOT, attempt, f"anchor-{attempt}")
        if attempt < 3:
            life.request_retry(SLOT)
    with pytest.raises(InvalidTransitionError, match="exhausted"):
        life.request_retry(SLOT)
    assert [r["attempt_number"] for r in receipts] == [1, 2, 3]
    assert all(verify_terminal_receipt(r, lifecycle=life).verified
               for r in receipts)


def test_authorized_indeterminate_closure_with_retained_output(
        tmp_path) -> None:
    life = _lifecycle(tmp_path)
    digest = life.record_output(SLOT, b"retained synthetic bytes")
    life.record_contract_violation(SLOT, detail="synthetic violation")
    receipt = finalize_attempt_with_receipt(
        life, SLOT, "INDETERMINATE_FINAL", slot_position=1,
        frozen_prompt_sha256="c" * 64, authorization=_auth())
    output = receipt["output"]
    assert output["output_state"] == "retained_indeterminate"
    assert output["output_sha256"] == digest
    assert output["admitted_output_sha256"] is None  # never admitted
    assert output["output_location"] == "retained_non_admitted"
    assert receipt["authorization"]["authorization_id"] == \
        "synthetic-auth-1"
    assert verify_terminal_receipt(receipt, lifecycle=life).verified
    # Retained bytes are preserved, not discarded or admitted.
    assert life.store.read_output(digest) == b"retained synthetic bytes"


def test_technical_failure_with_retained_invalid_bytes(tmp_path) -> None:
    life = _lifecycle(tmp_path)
    record = {
        "run_id": "synthetic-run", "contract_version": "1.2.0",
        "slot_id": SLOT, "attempt_number": 1, "predecessor_attempt": None,
        "disposition": "FAILURE",
        "failure_evidence": "host_error_recorded",
        "failure_classification": "host_technical_error",
        "retained_artifact_sha256": hashlib.sha256(b"invalid").hexdigest(),
        "class_d_conflict_count": 0, "authorization": None,
    }
    receipt = build_terminal_receipt(
        terminal_record=record, slot_position=1,
        frozen_prompt_sha256="d" * 64,
        event_history=[{"seq": 1, "type": "attempt_terminal",
                        "event_id": "e" * 64}],
        no_output_reason="retained bytes are not technically evaluable")
    assert receipt["output"]["output_state"] == "retained_invalid"
    assert receipt["output"]["admitted_output_sha256"] is None
    assert receipt["output"]["output_location"] == "retained_non_admitted"
    assert verify_terminal_receipt(receipt).verified


def test_protocol_failure_with_and_without_returned_bytes(tmp_path) -> None:
    base = {
        "run_id": "synthetic-run", "contract_version": "1.2.0",
        "slot_id": SLOT, "attempt_number": 1, "predecessor_attempt": None,
        "disposition": "INDETERMINATE_FINAL",
        "failure_evidence": None, "failure_classification": None,
        "class_d_conflict_count": 0,
        "authorization": {"authorization_id": "a1",
                          "authorized_by": "synthetic-owner",
                          "reason": "protocol failure closure"},
    }
    with_bytes = build_terminal_receipt(
        terminal_record={**base, "retained_artifact_sha256": "f" * 64},
        slot_position=1, frozen_prompt_sha256="d" * 64,
        event_history=[{"seq": 1, "type": "attempt_terminal",
                        "event_id": "e" * 64}],
        output_state="retained_protocol_failure")
    assert with_bytes["output"]["output_location"] == \
        "retained_non_admitted"
    without = build_terminal_receipt(
        terminal_record={**base, "retained_artifact_sha256": None},
        slot_position=1, frozen_prompt_sha256="d" * 64,
        event_history=[{"seq": 1, "type": "attempt_terminal",
                        "event_id": "e" * 64}])
    assert without["output"]["output_state"] == "absent_no_output"
    assert without["output"]["no_output_reason"]


# =============================================================================
# Unknown outcomes, finalization, and crash recovery
# =============================================================================


def test_unknown_host_outcome_produces_no_premature_receipt(tmp_path) -> None:
    life = _lifecycle(tmp_path)
    life.mark_pending_unknown(SLOT, reason="synthetic interruption")
    with pytest.raises(AuthorizationError):
        finalize_attempt_with_receipt(
            life, SLOT, "INDETERMINATE_FINAL", slot_position=1,
            frozen_prompt_sha256="a" * 64)
    receipts_dir = tmp_path / "store" / "receipts"
    assert not receipts_dir.exists() or not list(receipts_dir.glob("*.json"))
    assert life.slot_state(SLOT)["attempts"][1]["disposition"] is None


def test_duplicate_finalization_is_idempotent(tmp_path) -> None:
    life, bundle, _, receipt = _admitted_receipt(tmp_path)
    again = finalize_attempt_with_receipt(
        life, SLOT, "ADMIT", slot_position=1,
        frozen_prompt_sha256=_prompt_digest(bundle),
        evidence_bundle=bundle)
    assert again["receipt_sha256"] == receipt["receipt_sha256"]
    stored = [p for p in (tmp_path / "store" / "receipts").glob("*.json")
              if p.name != "status-transitions.json"]
    assert len(stored) == 1
    terminal = [e for e in life.store.events
                if e["type"] == "attempt_terminal"]
    assert len(terminal) == 1


def test_interrupted_receipt_write_recovers_without_new_attempt(
        tmp_path, monkeypatch) -> None:
    life = _lifecycle(tmp_path)
    bundle = make_evidence_bundle("qualifying_class_b")
    life.record_output(SLOT, bundle["raster_bytes"])
    # Crash after the terminal event, before the receipt write lands:
    # finalize through the lifecycle alone first.
    life.finalize_attempt(SLOT, "ADMIT")
    assert load_stored_receipt(life, "0" * 64) is None

    receipt = finalize_attempt_with_receipt(
        life, SLOT, "ADMIT", slot_position=1,
        frozen_prompt_sha256=_prompt_digest(bundle),
        evidence_bundle=bundle)
    loaded = load_stored_receipt(life, receipt["receipt_sha256"])
    assert loaded["receipt_sha256"] == receipt["receipt_sha256"]
    attempts = life.slot_state(SLOT)["attempts"]
    assert sorted(attempts) == [1]  # generation attempt never duplicated
    assert verify_terminal_receipt(loaded, lifecycle=life).verified


def test_external_checkpoint_absent_after_valid_local_finalization(
        tmp_path) -> None:
    life, _, _, receipt = _admitted_receipt(tmp_path)
    assert receipt["local_finalization_status"] == \
        "awaiting_external_anchor"
    assert life.external_anchor_pending() != ()
    # Claiming external verification without anchoring is rejected.
    forged = copy.deepcopy(receipt)
    forged["local_finalization_status"] = "externally_verified"
    result = verify_terminal_receipt(forged, lifecycle=life)
    assert not result.verified
    assert "UNANCHORED_AS_VERIFIED" in result.codes


# =============================================================================
# Negative verification cases
# =============================================================================


def test_invalid_receipt_digest_is_rejected(tmp_path) -> None:
    _, _, _, receipt = _admitted_receipt(tmp_path)
    tampered = copy.deepcopy(receipt)
    tampered["class_d_conflict_count"] = 99
    result = verify_terminal_receipt(tampered)
    assert not result.verified
    assert "RECEIPT_DIGEST_MISMATCH" in result.codes


def test_substituted_evidence_is_rejected(tmp_path) -> None:
    life, bundle, _, receipt = _admitted_receipt(tmp_path)
    other = make_evidence_bundle("qualifying_class_b")
    other["action_log"]["entries"][0]["action"] = "substituted"
    result = verify_terminal_receipt(receipt, lifecycle=life,
                                     evidence_bundle=other)
    assert not result.verified
    assert "EVIDENCE_COMMITMENT_MISMATCH" in result.codes


def test_missing_evidence_is_rejected(tmp_path) -> None:
    life, bundle, _, receipt = _admitted_receipt(tmp_path)
    partial = dict(bundle)
    partial["attestation"] = None
    result = verify_terminal_receipt(receipt, lifecycle=life,
                                     evidence_bundle=partial)
    assert not result.verified
    assert "EVIDENCE_COMMITMENT_MISMATCH" in result.codes


def test_inconsistent_slot_and_attempt_identity_is_rejected(tmp_path) -> None:
    life, bundle, _, receipt = _admitted_receipt(tmp_path)
    wrong_attempt = copy.deepcopy(receipt)
    wrong_attempt["attempt_number"] = 2
    wrong_attempt["receipt_sha256"] = canonical_receipt_sha256(wrong_attempt)
    result = verify_terminal_receipt(wrong_attempt, lifecycle=life)
    assert not result.verified
    assert "IDENTITY_MISMATCH" in result.codes

    wrong_run = copy.deepcopy(receipt)
    result = verify_terminal_receipt(wrong_run, lifecycle=life,
                                     expected_run_id="another-run")
    assert "IDENTITY_MISMATCH" in result.codes


def test_substituted_output_bytes_are_rejected(tmp_path) -> None:
    _, bundle, _, receipt = _admitted_receipt(tmp_path)
    result = verify_terminal_receipt(
        receipt, output_bytes=b"substituted bytes",
        admitted_output_bytes=b"substituted bytes")
    assert not result.verified
    assert "OUTPUT_DIGEST_MISMATCH" in result.codes
    assert "ADMITTED_OUTPUT_MISMATCH" in result.codes


def test_cross_version_receipt_is_rejected() -> None:
    legacy = {
        "schema_version": "1.0.0", "experiment_id": "EXP-019",
        "experiment_version": "1.1.1", "run_id": "legacy-run",
        "receipt_type": "terminal_attempt_receipt",
    }
    result = verify_terminal_receipt(legacy)
    assert not result.verified
    assert result.codes == ("CROSS_VERSION_RECEIPT",)


def test_forbidden_legacy_and_treatment_fields_are_rejected(tmp_path) -> None:
    _, _, _, receipt = _admitted_receipt(tmp_path)
    for field in ("provider_response", "generated_file_path",
                  "metadata_recovery", "treatment"):
        forged = copy.deepcopy(receipt)
        forged[field] = "must-not-appear"
        result = verify_terminal_receipt(forged)
        assert not result.verified, field
        assert "FORBIDDEN_FIELD" in result.codes


def test_no_treatment_or_secret_leakage_in_receipt(tmp_path) -> None:
    _, _, _, receipt = _admitted_receipt(tmp_path)
    rendered = json.dumps(receipt, sort_keys=True)
    for marker in ('"treatment"', '"condition"', '"variant"',
                   '"provider_response"', '"generated_file_path"'):
        assert marker not in rendered
    assert set(receipt) == set(json.loads(
        (ROOT / "data/schemas/"
         "exp019_v1_2_terminal_attempt_receipt.schema.json")
        .read_text(encoding="utf-8"))["required"])


def test_receipt_schema_is_valid_and_version_specific() -> None:
    from jsonschema import Draft202012Validator

    schema = json.loads(
        (ROOT / "data/schemas/"
         "exp019_v1_2_terminal_attempt_receipt.schema.json")
        .read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    assert schema["properties"]["experiment_version"]["const"] == "1.2.0"


def test_missing_status_audit_is_healed_on_store_reentry(tmp_path) -> None:
    """Crash between receipt write and status transition: re-entry heals."""
    life, bundle, _, receipt = _admitted_receipt(tmp_path)
    log = tmp_path / "store" / "receipts" / "status-transitions.json"
    log.unlink()
    assert latest_receipt_status(life, receipt["receipt_sha256"]) is None
    healed = store_receipt(life, receipt)
    assert healed["receipt_sha256"] == receipt["receipt_sha256"]
    assert latest_receipt_status(life, receipt["receipt_sha256"]) == \
        "awaiting_external_anchor"
    assert verify_terminal_receipt(healed, lifecycle=life).verified


def test_missing_status_audit_fails_verification(tmp_path) -> None:
    life, _, _, receipt = _admitted_receipt(tmp_path)
    (tmp_path / "store" / "receipts" / "status-transitions.json").unlink()
    result = verify_terminal_receipt(receipt, lifecycle=life)
    assert not result.verified
    assert "STATUS_AUDIT_MISMATCH" in result.codes


def test_admit_without_evidence_validation_fails_verify(tmp_path) -> None:
    life, bundle, _, receipt = _admitted_receipt(tmp_path)
    forged = copy.deepcopy(receipt)
    forged["evidence_validation"] = None
    forged["receipt_sha256"] = canonical_receipt_sha256(forged)
    result = verify_terminal_receipt(forged, lifecycle=life)
    assert not result.verified
    assert "ADMIT_EVIDENCE_INCOMPLETE" in result.codes


def test_status_field_edit_cannot_forge_external_verification(
        tmp_path) -> None:
    """Mutable status is excluded from receipt_sha256; an attacker who
    edits only the status field still fails verification because the
    audited transition log and lifecycle anchor disagree."""
    life, _, _, receipt = _admitted_receipt(tmp_path)
    forged = copy.deepcopy(receipt)
    forged["local_finalization_status"] = "externally_verified"
    # Binding unchanged because status is outside receipt_sha256.
    assert forged["receipt_sha256"] == receipt["receipt_sha256"]
    result = verify_terminal_receipt(forged, lifecycle=life)
    assert not result.verified
    assert "UNANCHORED_AS_VERIFIED" in result.codes
    assert "STATUS_AUDIT_MISMATCH" in result.codes


def test_class_d_count_cannot_change_independently_of_records(
        tmp_path) -> None:
    bundle = make_evidence_bundle("contradictory_class_d")
    report = validate_evidence_bundle(bundle)
    life = _lifecycle(tmp_path)
    life.record_output(SLOT, bundle["raster_bytes"])
    with pytest.raises(ValueError, match="disagrees with the validated"):
        finalize_attempt_with_receipt(
            life, SLOT, "ADMIT", slot_position=1,
            frozen_prompt_sha256=_prompt_digest(bundle),
            evidence_bundle=bundle, validation_report=report,
            class_d_conflict_count=99)
    receipt = finalize_attempt_with_receipt(
        life, SLOT, "ADMIT", slot_position=1,
        frozen_prompt_sha256=_prompt_digest(bundle),
        evidence_bundle=bundle, validation_report=report,
        class_d_conflict_count=report.class_d_conflict_count)
    assert receipt["class_d_records_commitment_sha256"]
    # Substituting the underlying reports breaks the commitment.
    other = make_evidence_bundle("qualifying_class_b")
    result = verify_terminal_receipt(receipt, lifecycle=life,
                                     evidence_bundle=other)
    assert "CLASS_D_RECORDS_MISMATCH" in result.codes or \
        "EVIDENCE_COMMITMENT_MISMATCH" in result.codes


def test_admit_requires_complete_evidence_qualification(tmp_path) -> None:
    life = _lifecycle(tmp_path)
    life.record_output(SLOT, b"bytes without evidence bundle")
    with pytest.raises(ValueError, match="evidence validation"):
        finalize_attempt_with_receipt(
            life, SLOT, "ADMIT", slot_position=1,
            frozen_prompt_sha256="a" * 64)


def test_crash_at_receipt_store_boundary_recovers(tmp_path, monkeypatch
                                                  ) -> None:
    life = _lifecycle(tmp_path)
    bundle = make_evidence_bundle("qualifying_class_b")
    life.record_output(SLOT, bundle["raster_bytes"])
    life.finalize_attempt(SLOT, "ADMIT")
    real_replace = __import__("aipf.exp019_v1_2_lifecycle",
                              fromlist=["os"]).os.replace
    calls = {"n": 0}

    def boom(src, dst):
        calls["n"] += 1
        if calls["n"] == 1:
            raise OSError("synthetic crash at receipt commit")
        return real_replace(src, dst)

    monkeypatch.setattr(
        "aipf.exp019_v1_2_lifecycle.os.replace", boom)
    with pytest.raises(OSError):
        finalize_attempt_with_receipt(
            life, SLOT, "ADMIT", slot_position=1,
            frozen_prompt_sha256=_prompt_digest(bundle),
            evidence_bundle=bundle)
    monkeypatch.undo()
    receipt = finalize_attempt_with_receipt(
        life, SLOT, "ADMIT", slot_position=1,
        frozen_prompt_sha256=_prompt_digest(bundle),
        evidence_bundle=bundle)
    again = finalize_attempt_with_receipt(
        life, SLOT, "ADMIT", slot_position=1,
        frozen_prompt_sha256=_prompt_digest(bundle),
        evidence_bundle=bundle)
    assert again["receipt_sha256"] == receipt["receipt_sha256"]
    stored = list((tmp_path / "store" / "receipts").glob("*.json"))
    # One receipt + the status-transitions audit log.
    assert len([p for p in stored if p.name != "status-transitions.json"]
               ) == 1
    terminal = [e for e in life.store.events
                if e["type"] == "attempt_terminal"]
    assert len(terminal) == 1


def test_activation_lockout_remains_effective() -> None:
    public = {n for n in vars(receipts_module) if not n.startswith("_")}
    assert not {"generate", "generate_image", "allocate", "create_run",
                "commit_checkpoint", "publish_checkpoint", "reveal"} & public
    with pytest.raises(ValueError,
                       match="unknown EXP-019 frozen protocol version"):
        frozen_protocol("1.2.0")
