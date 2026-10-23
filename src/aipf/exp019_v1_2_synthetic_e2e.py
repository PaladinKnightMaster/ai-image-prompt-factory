"""EXP-019 v1.2 synthetic end-to-end integration harness (PR-12).

Wires the merged PR-6 through PR-11 components into an isolated synthetic
workflow for G2 engineering-integration evidence. This module:

* never registers v1.2 in ``frozen_protocol()``;
* never invokes a real generation host;
* never publishes to a production provenance remote;
* uses temporary local bare Git remotes only;
* keeps treatment mappings in a private custodian store that reviewers
  and coordinators never receive.

Role labels are software obligations, not personal blindness claims: the
same person holding multiple roles is never represented as independently
blinded merely because labels differ.

Descriptive analysis on synthetic scores only — no statistical
significance claims.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Optional, Sequence

from .exp019_v1_2_admission import (
    LifecycleSnapshot,
    ProtocolContext,
    ReceiptIntegrity,
    evaluate_admission,
    evaluate_retry_advancement,
)
from .exp019_v1_2_checkpoints import (
    SYNTHETIC_ENV,
    CheckpointPublisher,
    CheckpointVerifier,
)
from .exp019_v1_2_evidence import validate_evidence_bundle
from .exp019_v1_2_lifecycle import (
    ANCHOR_ANCHORED,
    AttemptLifecycle,
    LifecycleStore,
)
from .exp019_v1_2_operator import (
    ROLE_CUSTODIAN,
    ROLE_OPERATOR,
    OperatorCaptureSession,
    make_opaque_prompt_packet,
    workflow_valid_returned_image,
)
from .exp019_v1_2_receipts import (
    finalize_attempt_with_receipt,
    mark_receipt_externally_verified,
    verify_terminal_receipt,
)

EXPERIMENT_VERSION = "1.2.0"
REVIEWERS = ("R1", "R2")

# Synthetic opaque slot ids (Crockford base32, six chars) — not real run ids.
SYNTHETIC_SLOTS = (
    "AAAAAA", "BBBBBB", "CCCCCC", "DDDDDD",
    "EEEEEE", "FFFFFF", "GGGGGG", "HHHHHH",
    "JJJJJJ", "KKKKKK", "LLLLLL", "MMMMMM",
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Mapping) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False,
                       separators=(",", ":")) + "\n").encode("utf-8")


@dataclass
class PrivateTreatmentCustody:
    """Custodian-only synthetic treatment map (never given to reviewers).

    Test-only. Does not create a scientific allocation or register v1.2.
    """

    run_id: str
    mapping: dict  # opaque_slot_id -> condition label (private)
    mapping_commitment_sha256: str
    role: str = ROLE_CUSTODIAN

    def packet_for(self, opaque_slot_id: str, attempt_number: int,
                   prompt_bytes: bytes, conversation_ref: str):
        if opaque_slot_id not in self.mapping:
            raise KeyError("unknown opaque slot for this custody record")
        # Operator receives prompt bytes + opaque id only — never the map.
        return make_opaque_prompt_packet(
            opaque_slot_id=opaque_slot_id,
            attempt_number=attempt_number,
            frozen_prompt_bytes=prompt_bytes,
            conversation_ref=conversation_ref,
            role=ROLE_CUSTODIAN,
        )

    def public_view(self) -> dict:
        """What may leave custodian custody: commitment only."""
        return {
            "run_id": self.run_id,
            "mapping_commitment_sha256": self.mapping_commitment_sha256,
            "slot_count": len(self.mapping),
        }


def prepare_synthetic_treatment_custody(
        run_id: str, *,
        slots: Sequence[str] = SYNTHETIC_SLOTS,
        conditions: Sequence[str] = ("A", "B"),
        role: str = ROLE_CUSTODIAN) -> PrivateTreatmentCustody:
    """Create a synthetic private mapping (custodian only)."""
    if role != ROLE_CUSTODIAN:
        raise PermissionError(
            "only the allocation custodian may prepare treatment custody; "
            "this is a role-label check, not personal blindness")
    if len(slots) % len(conditions) != 0:
        raise ValueError("slot count must divide evenly across conditions")
    mapping = {}
    per = len(slots) // len(conditions)
    for i, slot in enumerate(slots):
        mapping[slot] = conditions[i // per]
    commitment = _sha256(_canonical({"run_id": run_id, "mapping": mapping}))
    return PrivateTreatmentCustody(
        run_id=run_id, mapping=mapping,
        mapping_commitment_sha256=commitment)


@dataclass
class ReviewerPackage:
    """Treatment-free reviewer package (mapping + content blindness)."""

    reviewer_id: str
    items: list  # [{review_id, image_sha256, order}]
    package_sha256: str

    def to_public_dict(self) -> dict:
        text = json.dumps(self.items, sort_keys=True)
        for banned in ("treatment", "condition", "prompt", "variant",
                       "allocation", "provenance_conflict"):
            if banned in text.lower():
                raise ValueError(
                    "reviewer package must not contain treatment-bearing "
                    "terminology")
        return {
            "reviewer_id": self.reviewer_id,
            "items": copy.deepcopy(self.items),
            "package_sha256": self.package_sha256,
        }


@dataclass
class PrivateReviewerImageBinding:
    """Custodian-held binding: canonical output ↔ reviewer PNG digest."""

    bindings: dict  # output_sha256 -> reviewer_png_sha256
    commitment_sha256: str


def build_reviewer_package(
        reviewer_id: str,
        admitted_output_digests: Sequence[str],
        *,
        rng_seed: int) -> ReviewerPackage:
    """Coordinator-distributable package: digests + randomized order only."""
    if reviewer_id not in REVIEWERS:
        raise ValueError("unknown reviewer identity")
    # Deterministic shuffle from seed (no treatment labels).
    ordered = list(admitted_output_digests)
    # Simple deterministic permutation.
    n = len(ordered)
    idx = list(range(n))
    state = rng_seed
    for i in range(n - 1, 0, -1):
        state = (state * 1103515245 + 12345) & 0x7FFFFFFF
        j = state % (i + 1)
        idx[i], idx[j] = idx[j], idx[i]
    items = []
    for order, i in enumerate(idx):
        items.append({
            "review_id": f"{reviewer_id}-{order:02d}",
            "image_sha256": ordered[i],
            "order": order,
        })
    package = {"reviewer_id": reviewer_id, "items": items}
    digest = _sha256(_canonical(package))
    return ReviewerPackage(
        reviewer_id=reviewer_id, items=items, package_sha256=digest)


def freeze_reviewer_record(package: ReviewerPackage,
                           scores: Mapping[str, int]) -> dict:
    """Freeze independent reviewer scores (synthetic)."""
    items = []
    for entry in package.items:
        rid = entry["review_id"]
        if rid not in scores:
            raise ValueError("missing score for review item")
        items.append({
            "review_id": rid,
            "image_sha256": entry["image_sha256"],
            "score": int(scores[rid]),
        })
    frozen = {
        "reviewer_id": package.reviewer_id,
        "package_sha256": package.package_sha256,
        "items": items,
    }
    frozen["freeze_commitment_sha256"] = _sha256(_canonical(frozen))
    return frozen


def descriptive_analysis(frozen_reviews: Sequence[Mapping]) -> dict:
    """Apply frozen descriptive analysis to synthetic scores only.

    No statistical significance claims.
    """
    by_image: dict = {}
    for frozen in frozen_reviews:
        for item in frozen["items"]:
            by_image.setdefault(item["image_sha256"], []).append(
                item["score"])
    rows = []
    for digest, scores in sorted(by_image.items()):
        rows.append({
            "image_sha256": digest,
            "scores": scores,
            "mean": sum(scores) / len(scores) if scores else None,
            "agree": len(set(scores)) == 1,
        })
    return {
        "method": "descriptive_only",
        "statistical_significance_claimed": False,
        "n_images": len(rows),
        "rows": rows,
    }


@dataclass
class SyntheticRunContext:
    """Isolated synthetic run workspace (scientifically inactive)."""

    run_id: str
    root: Path
    remote: Path
    publisher: CheckpointPublisher
    verifier: CheckpointVerifier
    lifecycle: AttemptLifecycle
    custody: PrivateTreatmentCustody
    plan_commitment_sha256: str
    admitted: list = field(default_factory=list)
    receipts: dict = field(default_factory=dict)
    reviewer_packages: dict = field(default_factory=dict)
    frozen_reviews: dict = field(default_factory=dict)
    closed: bool = False
    incomplete: bool = False


def establish_synthetic_run(
        root: Path, *, run_id: str = "synthetic-e2e-001",
        slot_count: int = 12) -> SyntheticRunContext:
    """Establish a synthetic run context without activating science."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    remote = root / "remote.git"
    if not remote.exists():
        import subprocess
        subprocess.run(
            ["git", "init", "--bare", "-q", str(remote)], check=True)
    os.environ[SYNTHETIC_ENV] = "1"
    os.environ.pop("AIPF_EXP019_PROVENANCE_REMOTE", None)
    publisher = CheckpointPublisher(
        str(remote), synthetic=True, state_dir=root / "private")
    verifier = CheckpointVerifier(publisher)

    def _anchor_verifier(terminal_record, anchor_ref) -> bool:
        """PR-9 authority: match slot/attempt binding, then verify remote."""
        state = publisher.load_state(run_id)
        if state is None or not terminal_record:
            return False
        slot_id = terminal_record.get("slot_id")
        attempt_number = terminal_record.get("attempt_number")
        for entry in state.checkpoints:
            binding = entry.get("private_binding") or {}
            if (entry.get("commit") == anchor_ref and
                    entry["record"]["event_type"] == "attempt" and
                    binding.get("slot_id") == slot_id and
                    binding.get("attempt_number") == attempt_number):
                result = verifier.verify_attempt_anchor(
                    run_id, binding["receipt_sha256"], anchor_ref)
                return bool(result.verified)
        return False

    store = LifecycleStore(root / "lifecycle")
    life = AttemptLifecycle(
        store, run_id=run_id, anchor_verifier=_anchor_verifier)
    slots = SYNTHETIC_SLOTS[:slot_count]
    custody = prepare_synthetic_treatment_custody(run_id, slots=slots)
    plan = {
        "run_id": run_id,
        "slots": list(slots),
        "mapping_commitment_sha256": custody.mapping_commitment_sha256,
        "scientifically_active": False,
    }
    plan_digest = _sha256(_canonical(plan))
    pub = publisher.publish_run_root(run_id, plan_digest)
    if not pub.published:
        raise RuntimeError(f"run_root publish failed: {pub.message}")
    return SyntheticRunContext(
        run_id=run_id, root=root, remote=remote,
        publisher=publisher, verifier=verifier, lifecycle=life,
        custody=custody, plan_commitment_sha256=plan_digest)


def run_synthetic_admitted_attempt(
        ctx: SyntheticRunContext, opaque_slot_id: str, *,
        prompt_bytes: bytes, raster_bytes: bytes,
        artifact_id: str = "synthetic-artifact-1",
        attempt_number: int = 1) -> dict:
    """Operator capture → validate → admit → receipt → checkpoint."""
    if ctx.closed:
        raise RuntimeError("run is closed")
    life = ctx.lifecycle
    from .exp019_v1_2_lifecycle import InvalidTransitionError
    if opaque_slot_id not in life._slots:
        life.plan_slot(opaque_slot_id)
    try:
        life.start_invocation(opaque_slot_id)
    except InvalidTransitionError:
        # Already started for this attempt — continue.
        pass

    packet = ctx.custody.packet_for(
        opaque_slot_id, attempt_number, prompt_bytes,
        conversation_ref=f"conv-{opaque_slot_id}-{attempt_number}")
    session = OperatorCaptureSession(
        packet=packet, operator_id="synthetic-operator",
        work_dir=ctx.root / "operator" / opaque_slot_id)
    bundle = workflow_valid_returned_image(
        session, prompt_bytes, raster_bytes, artifact_id=artifact_id)
    report = validate_evidence_bundle(bundle)
    if not report.evidence_eligible:
        raise RuntimeError(
            f"evidence not eligible: {[f.code for f in report.findings]}")

    life.record_output(opaque_slot_id, raster_bytes, technically_evaluable=True)
    snap = LifecycleSnapshot(
        slot_id=opaque_slot_id, attempt_number=attempt_number,
        state="evidence_returned", technically_evaluable=True,
        retained_artifact_sha256=life.slot_state(opaque_slot_id)[
            "attempts"][attempt_number]["retained_artifact_sha256"])
    decision = evaluate_admission(
        report, snap, ReceiptIntegrity.prospective())
    if decision.disposition != "ADMIT" or not decision.eligible_for_commitment:
        raise RuntimeError(f"expected ADMIT, got {decision.disposition}")

    receipt = finalize_attempt_with_receipt(
        life, opaque_slot_id, "ADMIT",
        slot_position=list(SYNTHETIC_SLOTS).index(opaque_slot_id) + 1
        if opaque_slot_id in SYNTHETIC_SLOTS else 1,
        frozen_prompt_sha256=packet.frozen_prompt_sha256,
        evidence_bundle=bundle,
        validation_report=report,
        class_d_conflict_count=report.class_d_conflict_count)
    vr = verify_terminal_receipt(receipt, lifecycle=life)
    if not vr.verified:
        raise RuntimeError(f"receipt verify failed: {vr.codes}")

    ctx.publisher.register_finalized_attempt(
        ctx.run_id, opaque_slot_id, attempt_number, receipt["receipt_sha256"])
    pub = ctx.publisher.publish_attempt(
        ctx.run_id, opaque_slot_id, attempt_number, receipt["receipt_sha256"])
    if not pub.published:
        raise RuntimeError(f"attempt checkpoint failed: {pub.message}")
    anchor = ctx.verifier.verify_attempt_anchor(
        ctx.run_id, receipt["receipt_sha256"], pub.commit)
    if not anchor.verified:
        raise RuntimeError(f"anchor verify failed: {anchor.codes}")
    life.record_external_anchor(
        opaque_slot_id, attempt_number, pub.commit)
    mark_receipt_externally_verified(
        life, receipt["receipt_sha256"], verified_anchor=True)

    output_sha = receipt["output"]["output_sha256"]
    ctx.admitted.append(output_sha)
    ctx.receipts[opaque_slot_id] = receipt
    return {
        "decision": decision.to_public_dict(),
        "receipt_sha256": receipt["receipt_sha256"],
        "checkpoint_commit": pub.commit,
        "output_sha256": output_sha,
    }


def prepare_and_freeze_reviews(
        ctx: SyntheticRunContext, *,
        score_fn=None) -> dict:
    """Build treatment-free packages and freeze two independent reviews."""
    if not ctx.admitted:
        raise RuntimeError("no admitted samples for review")
    # Private reviewer-image binding (pixel-equivalent digests in synthetic
    # tests: same digest stands in for a metadata-stripped PNG).
    bindings = {d: d for d in ctx.admitted}
    private_binding = PrivateReviewerImageBinding(
        bindings=bindings,
        commitment_sha256=_sha256(_canonical(bindings)))
    (ctx.root / "custodian").mkdir(parents=True, exist_ok=True)
    (ctx.root / "custodian" / "reviewer-image-bindings.json").write_text(
        json.dumps({"commitment": private_binding.commitment_sha256,
                    "n": len(bindings)}, indent=2),
        encoding="utf-8")

    packages = {}
    frozen = {}
    for i, reviewer_id in enumerate(REVIEWERS):
        pkg = build_reviewer_package(
            reviewer_id, ctx.admitted, rng_seed=1000 + i)
        # Coordinator may distribute packages — never the custody map.
        packages[reviewer_id] = pkg.to_public_dict()
        scores = {}
        for item in pkg.items:
            if score_fn:
                scores[item["review_id"]] = score_fn(reviewer_id, item)
            else:
                scores[item["review_id"]] = 3 + (i % 2)
        fr = freeze_reviewer_record(pkg, scores)
        frozen[reviewer_id] = fr
        pub = ctx.publisher.publish_review_freeze(
            ctx.run_id, reviewer_id, fr["freeze_commitment_sha256"])
        if not pub.published:
            raise RuntimeError(
                f"review freeze checkpoint failed: {pub.message}")
    ctx.reviewer_packages = packages
    ctx.frozen_reviews = frozen
    # Verify both freezes before any open-after-freeze.
    chain = ctx.verifier.verify_run(ctx.run_id)
    if not chain.verified:
        raise RuntimeError(f"chain verify failed after freezes: {chain.codes}")
    return {
        "packages": packages,
        "frozen": {k: {"freeze_commitment_sha256": v[
            "freeze_commitment_sha256"], "n": len(v["items"])}
            for k, v in frozen.items()},
        "binding_commitment": private_binding.commitment_sha256,
    }


def open_after_verified_freezes(ctx: SyntheticRunContext) -> dict:
    """Post-freeze opening of private bindings (not a scientific reveal API).

    Refused unless both reviewer-freeze checkpoints are present and the
    remote chain verifies. Does not publish treatment mappings.
    """
    state = ctx.publisher.load_state(ctx.run_id)
    if state is None:
        raise RuntimeError("missing checkpoint state")
    if set(state.review_freeze_reviewers) != set(REVIEWERS):
        raise RuntimeError(
            "both reviewer-freeze checkpoints must be verified before opening")
    chain = ctx.verifier.verify_run(ctx.run_id)
    if not chain.verified:
        raise RuntimeError("remote chain not verified")
    analysis = descriptive_analysis(list(ctx.frozen_reviews.values()))
    return {
        "opened": True,
        "treatment_mapping_published": False,
        "analysis": analysis,
    }


def close_synthetic_run(ctx: SyntheticRunContext, *,
                        incomplete: bool = False) -> dict:
    disposition = "incomplete" if incomplete else "completed"
    closure = _sha256(_canonical({
        "run_id": ctx.run_id,
        "disposition": disposition,
        "admitted_count": len(ctx.admitted),
    }))
    pub = ctx.publisher.publish_run_disposition(
        ctx.run_id, disposition, closure, incomplete=incomplete)
    if not pub.published:
        raise RuntimeError(f"run_disposition failed: {pub.message}")
    ctx.closed = True
    ctx.incomplete = incomplete
    chain = ctx.verifier.verify_run(ctx.run_id)
    return {
        "disposition": disposition,
        "commit": pub.commit,
        "chain_verified": chain.verified,
        "public_records": [
            c["record"] for c in
            (ctx.publisher.load_state(ctx.run_id).checkpoints or [])],
    }


def assert_activation_lockout() -> None:
    from .exp019_protocol import frozen_protocol
    try:
        frozen_protocol("1.2.0")
        raise AssertionError("v1.2 must remain unregistered")
    except ValueError:
        pass
