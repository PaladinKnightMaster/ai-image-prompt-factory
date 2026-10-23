"""Synthetic end-to-end integration tests for EXP-019 v1.2 PR-12.

Temporary directories and bare Git remotes only. No real generation,
allocation, or experimental provenance mutation.
"""

from __future__ import annotations

import copy
import json

import pytest

from aipf.exp019_protocol import frozen_protocol
from aipf.exp019_v1_2_admission import (
    AdmissionDecision,
    LifecycleSnapshot,
    ProtocolContext,
    ReceiptIntegrity,
    evaluate_admission,
    evaluate_retry_advancement,
)
from aipf.exp019_v1_2_checkpoints import CheckpointPublisher
from aipf.exp019_v1_2_evidence import ValidationReport, validate_evidence_bundle
from aipf.exp019_v1_2_lifecycle import (
    ANCHOR_ANCHORED,
    INDETERMINATE_PROCEDURE,
    AttemptLifecycle,
    LifecycleStore,
)
from aipf.exp019_v1_2_receipts import (
    finalize_attempt_with_receipt,
    load_stored_receipt,
    verify_terminal_receipt,
)
from aipf.exp019_v1_2_synthetic_e2e import (
    REVIEWERS,
    SYNTHETIC_SLOTS,
    assert_activation_lockout,
    build_reviewer_package,
    close_synthetic_run,
    descriptive_analysis,
    establish_synthetic_run,
    open_after_verified_freezes,
    prepare_and_freeze_reviews,
    prepare_synthetic_treatment_custody,
    run_synthetic_admitted_attempt,
)
from aipf import exp019_v1_2_synthetic_e2e as e2e_module
from exp019_v1_2_synthetic_fixtures import (
    make_evidence_bundle,
    synthetic_raster_bytes,
)

PROMPT = b"synthetic e2e frozen prompt bytes"

# Role software labels are obligations, not personal blindness claims.
ROLE_LABELS_ARE_NOT_BLINDNESS_CLAIM = True


def _unique_raster(slot: str) -> bytes:
    """Per-slot valid 1x1 PNG with distinct RGB (distinct digest per slot)."""
    import struct
    import zlib
    # Map slot chars to a stable RGB triple.
    seed = sum(ord(c) for c in slot) & 0xFFFFFF
    r, g, b = (seed >> 16) & 0xFF, (seed >> 8) & 0xFF, seed & 0xFF

    def _chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data +
                struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    raw = zlib.compress(b"\x00" + bytes((r, g, b)))
    return (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) +
            _chunk(b"IDAT", raw) + _chunk(b"IEND", b""))


def _prompt_digest(bundle) -> str:
    return bundle["observation"]["protocol_constants"]["prompt_sha256"]


def _h3(slot: str = "AAAAAA", attempt: int = 1) -> dict:
    return {
        "authorization_id": "auth-e2e-1",
        "authorized_by": "synthetic-owner",
        "reason": "closure",
        "procedure": INDETERMINATE_PROCEDURE,
        "action": "INDETERMINATE_FINAL",
        "run_id": "synthetic-e2e-001",
        "slot_id": slot,
        "attempt_number": attempt,
        "contract_version": "1.2.0",
    }


@pytest.fixture
def synth(tmp_path, monkeypatch):
    monkeypatch.setenv("AIPF_EXP019_V12_SYNTHETIC_PROVENANCE", "1")
    monkeypatch.delenv("AIPF_EXP019_PROVENANCE_REMOTE", raising=False)
    return establish_synthetic_run(tmp_path, slot_count=4)


def test_completed_synthetic_mini_run(synth) -> None:
    """Reduced completed path (4 samples) exercising the full chain."""
    for slot in SYNTHETIC_SLOTS[:4]:
        run_synthetic_admitted_attempt(
            synth, slot, prompt_bytes=PROMPT,
            raster_bytes=_unique_raster(slot))
    reviews = prepare_and_freeze_reviews(synth)
    assert set(reviews["frozen"]) == set(REVIEWERS)
    opened = open_after_verified_freezes(synth)
    assert opened["opened"] and not opened["treatment_mapping_published"]
    assert opened["analysis"]["statistical_significance_claimed"] is False
    closed = close_synthetic_run(synth, incomplete=False)
    assert closed["chain_verified"]
    types = [r["event_type"] for r in closed["public_records"]]
    assert types[0] == "run_root"
    assert types.count("attempt") == 4
    assert types.count("review_freeze") == 2
    assert types[-1] == "run_disposition"
    assert len(types) == 1 + 4 + 2 + 1
    # No treatment leakage in public records.
    blob = json.dumps(closed["public_records"])
    assert "treatment" not in blob
    assert "condition" not in blob
    for field in ("schema_version", "run_id", "sequence", "event_type",
                  "evidence_sha256", "previous_anchor_commit"):
        assert field in closed["public_records"][0]


def test_custodian_operator_reviewer_separation(synth) -> None:
    custody = synth.custody
    public = custody.public_view()
    assert "mapping" not in public
    assert public["mapping_commitment_sha256"] == \
        custody.mapping_commitment_sha256
    packet = custody.packet_for(
        SYNTHETIC_SLOTS[0], 1, PROMPT, "conv-1")
    # Packet has no treatment fields.
    assert not hasattr(packet, "treatment")
    assert not hasattr(packet, "condition")
    run_synthetic_admitted_attempt(
        synth, SYNTHETIC_SLOTS[0], prompt_bytes=PROMPT,
        raster_bytes=_unique_raster(SYNTHETIC_SLOTS[0]))
    pkg = build_reviewer_package(
        "R1", synth.admitted, rng_seed=1).to_public_dict()
    text = json.dumps(pkg).lower()
    for banned in ("treatment", "condition", "prompt", "allocation"):
        assert banned not in text


def test_incomplete_run_without_review_freezes(synth) -> None:
    run_synthetic_admitted_attempt(
        synth, SYNTHETIC_SLOTS[0], prompt_bytes=PROMPT,
        raster_bytes=_unique_raster(SYNTHETIC_SLOTS[0]))
    closed = close_synthetic_run(synth, incomplete=True)
    types = [r["event_type"] for r in closed["public_records"]]
    assert "review_freeze" not in types
    assert types[-1] == "run_disposition"
    with pytest.raises(RuntimeError, match="reviewer-freeze"):
        open_after_verified_freezes(synth)


def test_open_before_freezes_refused(synth) -> None:
    run_synthetic_admitted_attempt(
        synth, SYNTHETIC_SLOTS[0], prompt_bytes=PROMPT,
        raster_bytes=_unique_raster(SYNTHETIC_SLOTS[0]))
    with pytest.raises(RuntimeError, match="reviewer-freeze"):
        open_after_verified_freezes(synth)


def test_duplicate_finalization_idempotent(synth) -> None:
    first = run_synthetic_admitted_attempt(
        synth, SYNTHETIC_SLOTS[0], prompt_bytes=PROMPT,
        raster_bytes=_unique_raster(SYNTHETIC_SLOTS[0]))
    # Second publish of same attempt is recognized, not duplicated.
    receipt = load_stored_receipt(
        synth.lifecycle, first["receipt_sha256"])
    again = synth.publisher.publish_attempt(
        synth.run_id, SYNTHETIC_SLOTS[0], 1, receipt["receipt_sha256"])
    assert again.recognized_existing
    state = synth.publisher.load_state(synth.run_id)
    attempts = [c for c in state.checkpoints
                if c["record"]["event_type"] == "attempt"]
    assert len(attempts) == 1


def test_retry_requires_verified_anchor(synth) -> None:
    from aipf.exp019_v1_2_admission import AdmissionDecision
    prior = AdmissionDecision(
        disposition="FAILURE", terminal=True,
        eligible_for_commitment=False,
        reason_codes=("TECHNICAL_FAILURE",),
        retry_eligible=True,
        failure_classification="host_technical_error",
        message="x")
    blocked = evaluate_retry_advancement(
        prior,
        LifecycleSnapshot(
            slot_id=SYNTHETIC_SLOTS[0], attempt_number=1,
            state="FAILURE", technically_evaluable=False,
            terminal_disposition="FAILURE",
            failure_classification="host_technical_error",
            anchor_state=ANCHOR_ANCHORED, retry_count=0),
        anchor_verification=None)
    assert not blocked.retry_eligible
    assert "UNTRUSTED_ANCHOR_CLAIM" in blocked.reason_codes


def test_activation_lockout() -> None:
    assert_activation_lockout()
    with pytest.raises(ValueError,
                       match="unknown EXP-019 frozen protocol version"):
        frozen_protocol("1.2.0")
    public = {n for n in vars(e2e_module) if not n.startswith("_")}
    assert not {"generate", "generate_image", "allocate", "create_run",
                "reveal"} & public


def test_descriptive_analysis_no_significance() -> None:
    frozen = [
        {"items": [{"image_sha256": "a" * 64, "score": 3,
                    "review_id": "R1-00"}]},
        {"items": [{"image_sha256": "a" * 64, "score": 4,
                    "review_id": "R2-00"}]},
    ]
    result = descriptive_analysis(frozen)
    assert result["statistical_significance_claimed"] is False
    assert result["method"] == "descriptive_only"


def test_custodian_role_boundary() -> None:
    with pytest.raises(PermissionError):
        prepare_synthetic_treatment_custody(
            "run-x", role="operator")


def test_network_production_remote_refused(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AIPF_EXP019_V12_SYNTHETIC_PROVENANCE", "1")
    monkeypatch.setenv(
        "AIPF_EXP019_PROVENANCE_REMOTE",
        "https://github.com/example/exp019-anchors.git")
    with pytest.raises(PermissionError):
        CheckpointPublisher(
            "git@github.com:example/exp019-anchors.git",
            synthetic=True, state_dir=tmp_path)


def test_completed_12_sample_synthetic_run(tmp_path, monkeypatch) -> None:
    """Full 12-slot custody + admit + dual freeze + disposition chain."""
    monkeypatch.setenv("AIPF_EXP019_V12_SYNTHETIC_PROVENANCE", "1")
    monkeypatch.delenv("AIPF_EXP019_PROVENANCE_REMOTE", raising=False)
    synth = establish_synthetic_run(tmp_path, slot_count=12)
    assert len(synth.custody.mapping) == 12
    for slot in SYNTHETIC_SLOTS:
        run_synthetic_admitted_attempt(
            synth, slot, prompt_bytes=PROMPT,
            raster_bytes=_unique_raster(slot))
    reviews = prepare_and_freeze_reviews(synth)
    assert set(reviews["frozen"]) == set(REVIEWERS)
    opened = open_after_verified_freezes(synth)
    assert opened["opened"]
    closed = close_synthetic_run(synth, incomplete=False)
    types = [r["event_type"] for r in closed["public_records"]]
    assert types.count("attempt") == 12
    assert types.count("review_freeze") == 2
    assert types[0] == "run_root" and types[-1] == "run_disposition"
    assert len(types) == 1 + 12 + 2 + 1
    assert closed["chain_verified"]


def test_admit_preserves_class_d_conflict(synth) -> None:
    """ADMIT path retains class-D conflict count through receipt binding."""
    slot = SYNTHETIC_SLOTS[0]
    life = synth.lifecycle
    life.plan_slot(slot)
    life.start_invocation(slot)
    bundle = make_evidence_bundle("contradictory_class_d")
    report = validate_evidence_bundle(bundle)
    assert report.evidence_eligible
    assert report.class_d_conflict_count == 2
    raster = bundle["raster_bytes"]
    life.record_output(slot, raster, technically_evaluable=True)
    snap = LifecycleSnapshot(
        slot_id=slot, attempt_number=1, state="evidence_returned",
        technically_evaluable=True,
        retained_artifact_sha256=life.slot_state(slot)["attempts"][1][
            "retained_artifact_sha256"])
    decision = evaluate_admission(
        report, snap, ReceiptIntegrity.prospective())
    assert decision.disposition == "ADMIT"
    assert "CLASS_D_CONFLICT_PRESERVED" in decision.reason_codes
    receipt = finalize_attempt_with_receipt(
        life, slot, "ADMIT", slot_position=1,
        frozen_prompt_sha256=_prompt_digest(bundle),
        evidence_bundle=bundle, validation_report=report,
        class_d_conflict_count=report.class_d_conflict_count)
    assert receipt["class_d_conflict_count"] == 2
    assert verify_terminal_receipt(receipt, lifecycle=life).verified


def test_authenticated_bc_conflict_non_admission() -> None:
    """Authenticated B/C material conflict never admits."""
    base = validate_evidence_bundle(make_evidence_bundle("qualifying_class_b"))
    forged = ValidationReport(
        findings=base.findings, q_results=base.q_results,
        outcome_classification="returned_evidenced",
        evidence_eligibility="evidence_eligible",
        technical_validation="passed",
        class_d_conflict_count=0,
        b_c_material_conflicts=("BC_RETURNED_COUNT_CONFLICT",),
        source_integrity=base.source_integrity)
    snap = LifecycleSnapshot(
        slot_id="AAAAAA", attempt_number=1, state="evidence_returned",
        technically_evaluable=True, retained_artifact_sha256="a" * 64)
    decision = evaluate_admission(
        forged, snap, ReceiptIntegrity.prospective())
    assert decision.disposition != "ADMIT"
    assert "BC_MATERIAL_CONFLICT" in decision.reason_codes


def test_missing_optional_class_c_still_admits() -> None:
    report = validate_evidence_bundle(make_evidence_bundle("missing_class_c"))
    assert report.evidence_eligible
    snap = LifecycleSnapshot(
        slot_id="AAAAAA", attempt_number=1, state="evidence_returned",
        technically_evaluable=True, retained_artifact_sha256="b" * 64)
    decision = evaluate_admission(
        report, snap, ReceiptIntegrity.prospective())
    assert decision.disposition == "ADMIT"


def test_unknown_host_stays_pending_not_retry() -> None:
    report = validate_evidence_bundle(
        make_evidence_bundle("interrupted_unknown"))
    snap = LifecycleSnapshot(
        slot_id="AAAAAA", attempt_number=1, state="PENDING_UNKNOWN",
        technically_evaluable=None, retained_artifact_sha256=None)
    decision = evaluate_admission(
        report, snap, ReceiptIntegrity.prospective())
    assert decision.disposition == "PENDING_UNKNOWN"
    assert not decision.retry_eligible


def test_authorized_indeterminate_closure() -> None:
    report = validate_evidence_bundle(
        make_evidence_bundle("interrupted_unknown"))
    snap = LifecycleSnapshot(
        slot_id="AAAAAA", attempt_number=1, state="PENDING_UNKNOWN",
        technically_evaluable=None, retained_artifact_sha256=None)
    decision = evaluate_admission(
        report, snap, ReceiptIntegrity.prospective(),
        ProtocolContext(requesting_indeterminate_closure=True,
                        h3_authorization=_h3()))
    assert decision.disposition == "INDETERMINATE_FINAL"
    assert decision.eligible_for_commitment


def test_corrupted_terminal_receipt_rejected(synth) -> None:
    result = run_synthetic_admitted_attempt(
        synth, SYNTHETIC_SLOTS[0], prompt_bytes=PROMPT,
        raster_bytes=_unique_raster(SYNTHETIC_SLOTS[0]))
    receipt = load_stored_receipt(synth.lifecycle, result["receipt_sha256"])
    tampered = copy.deepcopy(receipt)
    tampered["class_d_conflict_count"] = 99
    vr = verify_terminal_receipt(tampered, lifecycle=synth.lifecycle)
    assert not vr.verified
    assert "RECEIPT_DIGEST_MISMATCH" in vr.codes


def test_corrupted_reviewer_mapping_commitment(synth) -> None:
    custody = synth.custody
    forged = copy.deepcopy(custody.mapping)
    forged[SYNTHETIC_SLOTS[0]] = "FORGED"
    import hashlib
    forged_commit = hashlib.sha256(
        (json.dumps({"run_id": custody.run_id, "mapping": forged},
                    sort_keys=True, separators=(",", ":")) + "\n"
         ).encode("utf-8")).hexdigest()
    assert forged_commit != custody.mapping_commitment_sha256
    public = custody.public_view()
    assert public["mapping_commitment_sha256"] == \
        custody.mapping_commitment_sha256


def test_crash_between_finalization_and_checkpoint(synth) -> None:
    """Local receipt survives; remote publish can resume without duplicate."""
    slot = SYNTHETIC_SLOTS[0]
    from aipf.exp019_v1_2_operator import (
        OperatorCaptureSession,
        workflow_valid_returned_image,
    )
    life = synth.lifecycle
    life.plan_slot(slot)
    life.start_invocation(slot)
    packet = synth.custody.packet_for(slot, 1, PROMPT, "conv-crash")
    session = OperatorCaptureSession(
        packet=packet, operator_id="synthetic-operator",
        work_dir=synth.root / "operator" / slot)
    raster = _unique_raster(slot)
    bundle = workflow_valid_returned_image(
        session, PROMPT, raster, artifact_id="crash-art")
    report = validate_evidence_bundle(bundle)
    life.record_output(slot, raster, technically_evaluable=True)
    snap = LifecycleSnapshot(
        slot_id=slot, attempt_number=1, state="evidence_returned",
        technically_evaluable=True,
        retained_artifact_sha256=life.slot_state(slot)["attempts"][1][
            "retained_artifact_sha256"])
    decision = evaluate_admission(
        report, snap, ReceiptIntegrity.prospective())
    assert decision.disposition == "ADMIT"
    receipt = finalize_attempt_with_receipt(
        life, slot, "ADMIT", slot_position=1,
        frozen_prompt_sha256=packet.frozen_prompt_sha256,
        evidence_bundle=bundle, validation_report=report,
        class_d_conflict_count=report.class_d_conflict_count)
    reloaded = AttemptLifecycle(
        LifecycleStore(synth.root / "lifecycle"),
        run_id=synth.run_id,
        anchor_verifier=life._anchor_verifier)
    loaded = load_stored_receipt(reloaded, receipt["receipt_sha256"])
    assert loaded["receipt_sha256"] == receipt["receipt_sha256"]
    synth.publisher.register_finalized_attempt(
        synth.run_id, slot, 1, receipt["receipt_sha256"])
    first = synth.publisher.publish_attempt(
        synth.run_id, slot, 1, receipt["receipt_sha256"])
    assert first.published
    second = synth.publisher.publish_attempt(
        synth.run_id, slot, 1, receipt["receipt_sha256"])
    assert second.recognized_existing
    attempts = [c for c in synth.publisher.load_state(synth.run_id).checkpoints
                if c["record"]["event_type"] == "attempt"]
    assert len(attempts) == 1


def test_distinct_reviewer_orderings(synth) -> None:
    for slot in SYNTHETIC_SLOTS[:4]:
        run_synthetic_admitted_attempt(
            synth, slot, prompt_bytes=PROMPT,
            raster_bytes=_unique_raster(slot))
    p1 = build_reviewer_package("R1", synth.admitted, rng_seed=1)
    p2 = build_reviewer_package("R2", synth.admitted, rng_seed=2)
    assert [i["image_sha256"] for i in p1.items] != \
        [i["image_sha256"] for i in p2.items]
    assert p1.package_sha256 != p2.package_sha256


def test_role_labels_are_not_personal_blindness() -> None:
    """Same person holding multiple role labels is not independently blinded."""
    assert ROLE_LABELS_ARE_NOT_BLINDNESS_CLAIM is True


def test_technically_evaluable_no_reroll(synth) -> None:
    """Admitted technically-evaluable image is not eligible for regeneration."""
    result = run_synthetic_admitted_attempt(
        synth, SYNTHETIC_SLOTS[0], prompt_bytes=PROMPT,
        raster_bytes=_unique_raster(SYNTHETIC_SLOTS[0]))
    prior = AdmissionDecision(
        disposition="ADMIT", terminal=True,
        eligible_for_commitment=True, reason_codes=(),
        retry_eligible=False, message="admitted")
    blocked = evaluate_retry_advancement(
        prior,
        LifecycleSnapshot(
            slot_id=SYNTHETIC_SLOTS[0], attempt_number=1,
            state="ADMIT", technically_evaluable=True,
            terminal_disposition="ADMIT",
            retained_artifact_sha256=result["output_sha256"],
            anchor_state=ANCHOR_ANCHORED, retry_count=0),
        anchor_verification=None)
    assert not blocked.retry_eligible
