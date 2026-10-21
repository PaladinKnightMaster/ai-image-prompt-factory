"""Historical-preservation regression tests for EXP-019 v1.1.1 and its predecessors.

These tests are the PR-1 foundation for the prospective EXP-019 v1.2 work. They
assert that the frozen historical evidence of already-executed EXP-019 runs is
unchanged, that the two post-start procedural amendments remain byte-frozen, and
that the public (repository) EXP-019 artifacts are still internally consistent.

Two kinds of checks live here:

* **Public checks** -- read only repository-tracked files (frozen definitions,
  the frozen preregistration, the byte-frozen amendments). These always run.
* **Private checks** -- read a real private experiment run that exists only on a
  configured workstation. They are strictly opt-in and are SKIPPED (never
  reported as passing) when the private evidence is unavailable.

The private checks are guarded by the ``private_evidence`` marker and are
skipped unless the opt-in environment variable
``AIPF_EXP019_PRIVATE_PRESERVATION`` is set to a truthy value. They never embed,
print, or publish private paths, images, prompt text, treatment mappings,
credentials, or private evidence artifacts; every assertion is expressed as a
digest or a count.

**No opaque slot identifier appears in this file.** The private checks derive
every slot it needs from the run's own evidence -- the run ledger, the bounded
recovery disposition records, and the degraded-host evidence -- rather than
naming slots. Naming them would let a reader of this public repository
reconstruct the blind-id-to-treatment mapping, because the frozen definition
already fixes the condition at each invocation position. The run has not been
reviewed, so that mapping is still sealed.

No real-run image, sidecar, or receipt is copied into this repository, and no
real-run artifact is used as a pytest fixture. The private checks only ever
*read* the private run and compare it against digests it computes at run time.
"""

from __future__ import annotations

import json
import os
from hashlib import sha256
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# --- Frozen public artifacts (all repository-tracked) ------------------------
DEFINITION_PATH = ROOT / "experiments/definitions/EXP-019.json"
HOST_V110_PATH = ROOT / "experiments/archive/EXP-019-v1.1.0.json"
LEGACY_PATH = ROOT / "experiments/archive/EXP-019-v1.0.0.json"
HOST_V110_PREREG_PATH = ROOT / "experiments/archive/EXP-019-v1.1.0.PREREGISTRATION.md"
PREREG_PATH = ROOT / "experiments/preregistrations/EXP-019.PREREGISTRATION.md"
FIXTURE_PATH = ROOT / "experiments/fixtures/EXP-019/EXP-019-BOKASHI-01.fixture.json"
MR_AMENDMENT_PATH = ROOT / "experiments/amendments/EXP-019.v1.1.1.METADATA-RECOVERY-01.md"
DHP_AMENDMENT_PATH = ROOT / "experiments/amendments/EXP-019.v1.1.1.DEGRADED-HOST-PROVENANCE-01.md"

# Digests pinned by the merged implementation for the two byte-frozen amendments.
MR_AMENDMENT_SHA256 = "b061e5ab023684df102b029d1ed1c319b0cddf24579c51215030be354730512a"
DHP_AMENDMENT_SHA256 = "9d6fb9e7ba6e8f38729d980cb04f612957b26c42518d27f9ff781d03a0f7dc91"

# The predecessor v1.1.0 run identifier is public: it is named in the frozen
# v1.1.1 preregistration and carries no slot-level information.
PRIVATE_V110_RUN_ID = "EXP-019-1.1.0-20260925T171442Z-GZ8Y"

PRIVATE_OPT_IN_ENV = "AIPF_EXP019_PRIVATE_PRESERVATION"
_TRUTHY = {"1", "true", "yes", "on"}


def _opt_in_requested() -> bool:
    return os.environ.get(PRIVATE_OPT_IN_ENV, "").strip().lower() in _TRUTHY


def _private_runs_root() -> Path | None:
    """Locate the private experiment runs root without embedding a private path.

    The root is resolved from the already-configured private output location
    (``AIPF_EXPERIMENT_OUTPUT_PATH``) rather than hard-coded, so nothing private
    is stored in this repository. Returns ``None`` when the private evidence is
    not configured on this machine.
    """
    # Imported eagerly so the dotenv-loaded configuration is applied regardless
    # of which other test modules happen to be collected first.
    from aipf.config import experiment_output_path

    base = experiment_output_path()
    return Path(base) if base is not None else None


def _sha256_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _sha256_dir(root: Path) -> str:
    """Order-independent digest over a directory tree's relative paths + bytes."""
    entries = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        entries.append(f"{path.relative_to(root).as_posix()}:{_sha256_file(path)}")
    return sha256("\n".join(entries).encode("utf-8")).hexdigest()


# =============================================================================
# Public checks: byte-frozen amendments
# =============================================================================


def test_metadata_recovery_amendment_is_byte_frozen() -> None:
    """The MR addendum must remain byte-identical to its implementation pin."""
    assert MR_AMENDMENT_PATH.is_file()
    assert _sha256_file(MR_AMENDMENT_PATH) == MR_AMENDMENT_SHA256


def test_degraded_host_amendment_is_byte_frozen() -> None:
    """The DHP addendum must remain byte-identical to its implementation pin."""
    assert DHP_AMENDMENT_PATH.is_file()
    assert _sha256_file(DHP_AMENDMENT_PATH) == DHP_AMENDMENT_SHA256


def test_amendment_pins_match_the_merged_implementation() -> None:
    """The pins asserted above must equal the constants the runtime enforces.

    Using the canonical ``frozen_amendment()`` helpers means a change to either
    amendment or to its implementation pin fails here rather than silently
    weakening the guarantee.
    """
    from aipf.exp019_degraded_host import frozen_amendment as dhp_amendment
    from aipf.exp019_metadata_recovery import frozen_amendment as mr_amendment

    assert mr_amendment() == {
        "id": "EXP-019-MR-20260928-01",
        "file": "experiments/amendments/EXP-019.v1.1.1.METADATA-RECOVERY-01.md",
        "sha256": MR_AMENDMENT_SHA256,
    }
    assert dhp_amendment() == {
        "id": "EXP-019-DHP-20260928-01",
        "file": "experiments/amendments/EXP-019.v1.1.1.DEGRADED-HOST-PROVENANCE-01.md",
        "sha256": DHP_AMENDMENT_SHA256,
    }


def test_amendments_are_distinct_documents() -> None:
    """The two addenda must not have been collapsed into one another."""
    mr_bytes = MR_AMENDMENT_PATH.read_bytes()
    dhp_bytes = DHP_AMENDMENT_PATH.read_bytes()
    assert mr_bytes != dhp_bytes
    assert sha256(mr_bytes).hexdigest() != sha256(dhp_bytes).hexdigest()


# =============================================================================
# Public checks: frozen definitions and preregistration remain intact
# =============================================================================


def test_exp019_definitions_remain_byte_frozen() -> None:
    """The active and archived EXP-019 definitions must stay byte-identical.

    The digests are the ones the runtime itself pins, so a byte change to any
    frozen definition or to the fixture fails here.
    """
    from aipf.exp019_protocol import (
        DEFINITION_SHA256, FIXTURE_SHA256,
        HOST_V110_DEFINITION_SHA256, LEGACY_DEFINITION_SHA256,
    )

    assert _sha256_file(DEFINITION_PATH) == DEFINITION_SHA256
    assert _sha256_file(HOST_V110_PATH) == HOST_V110_DEFINITION_SHA256
    assert _sha256_file(LEGACY_PATH) == LEGACY_DEFINITION_SHA256
    assert _sha256_file(FIXTURE_PATH) == FIXTURE_SHA256


def test_exp019_active_definition_is_still_v1_1_1_and_planned() -> None:
    """The active definition must remain the v1.1.1 planned definition."""
    definition = json.loads(DEFINITION_PATH.read_text(encoding="utf-8"))
    assert definition["experiment_id"] == "EXP-019"
    assert definition["version"] == "1.1.1"
    assert definition["status"] == "planned"


def test_exp019_preregistration_files_remain_present() -> None:
    """Both preregistration documents must remain present and non-empty."""
    for path in (PREREG_PATH, HOST_V110_PREREG_PATH, FIXTURE_PATH):
        assert path.is_file()
        assert path.stat().st_size > 0


def test_exp019_result_schema_still_declares_host_provenance() -> None:
    """The public v1.1.1 result schema must still require a provenance object.

    A future v1.2 schema is additive; it must not remove the v1.1.1
    requirement, which is what keeps the historical result contract stable.
    """
    schema_path = ROOT / "data/schemas/exp019_public_result_v1_1_1.schema.json"
    assert schema_path.is_file()
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    assert "host_provenance" in schema["required"]
    assert schema["properties"]["host_provenance"]["properties"]["state"]["enum"] == [
        "normal_host_provenance",
        "degraded_host_provenance",
    ]


def test_no_operational_v1_2_protocol_is_registered_yet() -> None:
    """v1.2 must not be executable until its approved protocol artifacts exist.

    PR-1 lands before any v1.2 protocol approval, so the runtime must not yet
    recognise a "1.2.0" experiment version. This guards against registering an
    operational version against placeholder definition/preregistration stubs.

    The error message is matched precisely: a bare ``pytest.raises(ValueError)``
    would still pass if "1.2.0" were later added to the allowed set and the
    function then failed for some unrelated reason.
    """
    from aipf.exp019_protocol import frozen_protocol

    with pytest.raises(ValueError, match="unknown EXP-019 frozen protocol version"):
        frozen_protocol("1.2.0")


# =============================================================================
# Private checks: opt-in, read-only, digest-based
# =============================================================================


@pytest.fixture(scope="module")
def private_run() -> Path:
    """The private v1.1.1 run root, or a skip explaining why it is unavailable."""
    if not _opt_in_requested():
        pytest.skip(
            f"private-evidence verification not requested; set {PRIVATE_OPT_IN_ENV}=1 to enable"
        )
    base = _private_runs_root()
    if base is None:
        pytest.skip(
            "private EXP-019 run evidence is not available on this machine; "
            "configure AIPF_EXPERIMENT_OUTPUT_PATH and set "
            f"{PRIVATE_OPT_IN_ENV}=1 to enable"
        )
    # The v1.1.1 run is the only run holding a bounded-recovery record and an
    # eight-sample import history; identify it by that structure rather than by
    # naming it, so no private identifier is written into this repository.
    candidates = []
    v111_runs = []
    for candidate in sorted(base.iterdir() if base.is_dir() else []):
        if not candidate.is_dir():
            continue
        # Detect the run by its private evidence layout, so that a deleted or
        # corrupted ledger is still recognised as evidence loss rather than
        # being mistaken for "this machine has no private evidence".
        if not (candidate / ".metadata-recovery-private").is_dir():
            continue
        run_file = candidate / "run-private.json"
        if not run_file.is_file():
            v111_runs.append(candidate)
            continue
        try:
            run = json.loads(run_file.read_text(encoding="utf-8"))
        except (ValueError, UnicodeError):
            v111_runs.append(candidate)
            continue
        if run.get("experiment_id") != "EXP-019" or run.get("experiment_version") != "1.1.1":
            continue
        v111_runs.append(candidate)
        candidates.append(candidate)
    if not candidates:
        if v111_runs:
            # The run exists but its ledger is missing, unreadable, or its
            # bounded-recovery evidence is gone. That is evidence loss, not an
            # unavailable machine: skipping here would make destruction
            # indistinguishable from "no private evidence", which is the wrong
            # failure mode for a preservation suite.
            pytest.fail(
                "a private EXP-019 v1.1.1 run with recovery-evidence layout was "
                "found but its ledger or bounded-recovery evidence is missing or "
                "unreadable; the private evidence appears to have been removed "
                "rather than merely unavailable"
            )
        pytest.skip("no private EXP-019 v1.1.1 run was found on this machine")
    if len(candidates) > 1:
        pytest.fail(
            "multiple private EXP-019 v1.1.1 runs with recovery evidence were "
            "found; refusing to guess which run to verify"
        )
    return candidates[0]


def _load_private_run(private_run: Path):
    from aipf.experiment_execution import load_run

    return load_run(private_run / "run-private.json")


def _outputs_by_slot(run: dict) -> dict:
    return {o["blind_id"]: o for v in run["variants"] for o in v["outputs"]}


def _finalized_slots(run: dict) -> list[str]:
    return [sid for sid, o in _outputs_by_slot(run).items() if o["status"] == "generated"]


def _unfinalized_slots(run: dict) -> list[str]:
    return [sid for sid, o in _outputs_by_slot(run).items() if o["status"] != "generated"]


def _recovery_areas(private_run: Path) -> dict:
    """Map slot -> the bounded-recovery disposition recorded for it."""
    area_root = private_run / ".metadata-recovery-private"
    if not area_root.is_dir():
        return {}
    found = {}
    for area in sorted(area_root.iterdir()):
        record = area / "response.json"
        if not area.is_dir() or not record.is_file():
            continue
        found[area.name] = json.loads(record.read_text(encoding="utf-8"))
    return found


def _degraded_areas(private_run: Path) -> dict:
    """Map slot -> the degraded-host evidence recorded for it."""
    area_root = private_run / ".degraded-host-private"
    if not area_root.is_dir():
        return {}
    found = {}
    for area in sorted(area_root.iterdir()):
        wrapper = area / "degraded-evidence.json"
        if not area.is_dir() or not wrapper.is_file():
            continue
        found[area.name] = json.loads(wrapper.read_text(encoding="utf-8"))
    return found


@pytest.mark.private_evidence
def test_private_run_ledger_reports_eight_finalized_slots(private_run: Path) -> None:
    """Exactly eight slots must be finalized and four must remain unfinalized."""
    _path, run = _load_private_run(private_run)
    outputs = [o for v in run["variants"] for o in v["outputs"]]

    assert len(outputs) == 12
    assert len(_finalized_slots(run)) == 8
    assert len(_unfinalized_slots(run)) == 4
    assert run["status"] == "partial"


@pytest.mark.private_evidence
def test_private_run_receipts_and_host_sessions_verify(private_run: Path) -> None:
    """Every finalized slot's receipt, operator record and host session must verify.

    ``verify_host_attempts`` is the canonical verifier: it rebinds each attempt
    receipt, operator attestation, frozen metadata query and host-session
    sidecar to the append-only ledger. Using it means this test cannot drift
    away from the behaviour the runtime actually enforces.
    """
    from aipf.exp019_host import verify_host_attempts
    from aipf.exp019_protocol import find_slot

    _path, run = _load_private_run(private_run)
    for position, entry in enumerate(run["invocation_order"], 1):
        _variant, output = find_slot(run, entry["blind_id"])
        if output["status"] == "generated":
            verify_host_attempts(private_run, run, output, position)


@pytest.mark.private_evidence
def test_private_finalized_images_match_their_recorded_digests(private_run: Path) -> None:
    """Each finalized canonical image must still hash to its recorded digest."""
    _path, run = _load_private_run(private_run)
    finalized = _finalized_slots(run)
    assert finalized, "no finalized slots were found"
    for slot_id in finalized:
        output = _outputs_by_slot(run)[slot_id]
        image = private_run / "outputs" / output["image"]
        assert image.is_file()
        assert _sha256_file(image) == output["image_sha256"]


@pytest.mark.private_evidence
def test_private_blocked_recovery_disposition_is_preserved(private_run: Path) -> None:
    """The blocked metadata recovery must remain recorded and unpromoted.

    The blocked slot's disposition record, the preserved rejected response, the
    frozen recovery response and the completed attestations must all still be
    present and internally consistent, and the active staged sidecar must still
    be the original rejected response (never the conflicting recovery reply).
    """
    blocked = {sid: rec for sid, rec in _recovery_areas(private_run).items()
               if rec.get("status") == "blocked"}
    assert len(blocked) == 1, "expected exactly one blocked recovery record"
    slot_id, disposition = next(iter(blocked.items()))

    assert disposition["slot_id"] == slot_id
    assert disposition["recovery_responses_consumed"] == 1
    assert disposition["generation_attempts_consumed"] == 0
    assert disposition["rejection_reason"]

    area = private_run / ".metadata-recovery-private" / slot_id
    for name in ("prepare.json", "rejected.host-session.json", "recovery-query.txt",
                 "response.host-session.json", "response.attestations.json"):
        assert (area / name).is_file()

    # The frozen response is the conflicting reply; the rejected original is
    # preserved separately and must differ from it.
    rejected = (area / "rejected.host-session.json").read_bytes()
    response = (area / "response.host-session.json").read_bytes()
    assert rejected != response

    # The active staged sidecar must still be the rejected original.
    staged = private_run / "host-import-staging" / slot_id / "host-session.json"
    assert staged.is_file()
    assert staged.read_bytes() == rejected


@pytest.mark.private_evidence
def test_private_blocked_slot_consumed_no_attempt(private_run: Path) -> None:
    """A blocked recovery must not have created a canonical attempt or output."""
    from aipf.exp019_protocol import find_slot

    blocked = {sid for sid, rec in _recovery_areas(private_run).items()
               if rec.get("status") == "blocked"}
    assert len(blocked) == 1
    slot_id = next(iter(blocked))

    _path, run = _load_private_run(private_run)
    _variant, output = find_slot(run, slot_id)
    assert output["status"] == "planned"
    assert output["attempt_events"] == []
    assert "receipt_history" not in output
    assert output["image"] is None
    assert not list((private_run / "outputs").glob(f"**/{slot_id}*"))
    assert not list((private_run / "provenance-freeze").glob(f"**/{slot_id}*"))


@pytest.mark.private_evidence
def test_private_accepted_recovery_records_are_preserved(private_run: Path) -> None:
    """All accepted bounded recoveries must remain accepted and intact."""
    accepted = {sid: rec for sid, rec in _recovery_areas(private_run).items()
                if rec.get("status") == "accepted"}
    assert len(accepted) == 5, (
        f"expected five accepted bounded-recovery records, found {len(accepted)}"
    )
    for slot_id, result in accepted.items():
        area = private_run / ".metadata-recovery-private" / slot_id
        assert area.is_dir(), slot_id
        assert result["slot_id"] == slot_id
        assert result["recovery_responses_consumed"] == 1
        assert result["generation_attempts_consumed"] == 0
        assert result["rejection_reason"] is None
        for name in ("prepare.json", "rejected.host-session.json", "recovery-query.txt",
                     "response.host-session.json", "response.attestations.json"):
            assert (area / name).is_file(), f"{slot_id}/{name}"


@pytest.mark.private_evidence
def test_private_accepted_recoveries_are_bound_into_their_receipts(private_run: Path) -> None:
    """Each accepted recovery must remain bound into its canonical attempt receipt."""
    from aipf.exp019_protocol import find_slot

    accepted = {sid for sid, rec in _recovery_areas(private_run).items()
                if rec.get("status") == "accepted"}
    assert accepted
    _path, run = _load_private_run(private_run)
    for slot_id in accepted:
        _variant, output = find_slot(run, slot_id)
        assert output["status"] == "generated"
        binding = output["receipt_history"][0]
        receipt = json.loads((private_run / binding["file"]).read_text(encoding="utf-8"))
        recovery = receipt.get("metadata_recovery")
        assert recovery is not None, slot_id
        assert recovery["amendment"]["sha256"] == MR_AMENDMENT_SHA256
        for name, digest in recovery["files"].items():
            assert (private_run / name).is_file(), name
            assert _sha256_file(private_run / name) == digest, name


@pytest.mark.private_evidence
def test_private_degraded_host_provenance_is_preserved(private_run: Path) -> None:
    """The degraded-host slot must retain its qualification and evidence."""
    from aipf.exp019_degraded_host import STATE

    degraded = _degraded_areas(private_run)
    assert len(degraded) == 1, "expected exactly one degraded-host evidence record"
    slot_id, wrapper = next(iter(degraded.items()))

    area = private_run / ".degraded-host-private" / slot_id
    for name in ("attestations.json", "degraded-evidence.json", "finalization.json",
                 "metadata-query.txt", "raw.host-session.json", "rejection.json"):
        assert (area / name).is_file(), name

    assert wrapper["slot_id"] == slot_id
    assert wrapper["host_provenance_state"] == STATE
    assert wrapper["raw_sidecar_schema_valid"] is False
    assert wrapper["scientific_bindings_valid"] is True
    assert wrapper["amendment"]["sha256"] == DHP_AMENDMENT_SHA256

    finalization = json.loads((area / "finalization.json").read_text(encoding="utf-8"))
    assert finalization["wrapper_sha256"] == _sha256_file(area / "degraded-evidence.json")
    receipt = private_run / finalization["receipt_file"]
    assert receipt.is_file()
    assert _sha256_file(receipt) == finalization["receipt_sha256"]

    record = json.loads(receipt.read_text(encoding="utf-8"))
    assert record["host_provenance_state"] == STATE


@pytest.mark.private_evidence
def test_private_external_provenance_chain_verifies(private_run: Path) -> None:
    """The remote provenance chain must still verify end to end.

    ``verify_external`` re-fetches the remote ref and rebinds every local
    checkpoint to the current evidence, so this exercises the real external
    chain rather than a local approximation. It requires the configured
    provenance remote; without one the check is skipped rather than faked.
    """
    if not os.environ.get("AIPF_EXP019_PROVENANCE_REMOTE"):
        pytest.skip(
            "AIPF_EXP019_PROVENANCE_REMOTE is not configured; "
            "external chain verification needs the configured provenance remote"
        )
    from aipf.exp019_anchor import verify_external

    _path, run = _load_private_run(private_run)
    state = verify_external(private_run / "run-private.json", run)
    checkpoints = state["checkpoints"]
    assert checkpoints[0]["record"]["event_type"] == "run_root"
    attempts = [c for c in checkpoints if c["record"]["event_type"] == "attempt"]
    assert len(attempts) == len(_finalized_slots(run))
    assert state["head_commit"] == checkpoints[-1]["commit"]


@pytest.mark.private_evidence
def test_private_checkpoint_count_and_types(private_run: Path) -> None:
    """The local checkpoint index must hold one root plus one per finalized slot.

    The blocked slot must not have an external attempt checkpoint.
    """
    state = json.loads(
        (private_run / ".provenance-private" / "anchor-state.json").read_text(encoding="utf-8")
    )
    checkpoints = state["checkpoints"]
    _path, run = _load_private_run(private_run)

    assert len(checkpoints) == 1 + len(_finalized_slots(run))
    assert checkpoints[0]["record"]["event_type"] == "run_root"
    assert all(c["record"]["event_type"] == "attempt" for c in checkpoints[1:])

    blocked = {sid for sid, rec in _recovery_areas(private_run).items()
               if rec.get("status") == "blocked"}
    for slot_id in blocked:
        assert not [
            c for c in checkpoints
            if c.get("private_binding", {}).get("slot_id") == slot_id
        ]


@pytest.mark.private_evidence
def test_private_no_reviewer_or_analysis_artifacts_exist(private_run: Path) -> None:
    """No review, reveal or analysis artifact may exist for the v1.1.1 run.

    The run was never reviewed or analyzed, and the v1.2 work must not change
    that: producing reviewer packages, a reveal, or an analysis for this run is
    prohibited.
    """
    for name in ("blind-review", ".review-private", "analysis-private"):
        assert not (private_run / name).exists(), name


@pytest.mark.private_evidence
def test_private_historical_v1_1_0_run_is_untouched(private_run: Path) -> None:
    """The predecessor v1.1.0 run must remain present and unpromoted.

    The v1.1.0 run stopped before its first import; it must not be reopened,
    imported, or reused. It must hold no canonical outputs at all, so the
    canonical output directory must be absent rather than merely empty.
    """
    historical = private_run.parent / PRIVATE_V110_RUN_ID
    assert historical.is_dir()
    assert not (historical / "outputs").exists()
    assert not (historical / "blind-review").exists()

    # Its root checkpoint must still be its only attempt-level anchor.
    state_path = historical / ".provenance-private" / "anchor-state.json"
    assert state_path.is_file()
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["checkpoints"][0]["record"]["event_type"] == "run_root"
    assert not [
        c for c in state["checkpoints"] if c["record"]["event_type"] == "attempt"
    ]


@pytest.mark.private_evidence
def test_private_tree_digest_is_deterministic_and_corruption_sensitive(private_run: Path) -> None:
    """The private tree digest must be deterministic and change when bytes change.

    The tree digest is what makes the whole-run preservation check above
    meaningful: it must be stable across repeated computation, and a single
    altered byte anywhere in the run must change it. It deliberately does not
    pin a fixed expected digest, because doing so would publish private
    evidence bytes into this repository.
    """
    first = _sha256_dir(private_run)
    assert first == _sha256_dir(private_run)

    # Corrupting a single byte of one real artifact must change the tree
    # digest. The file is restored immediately afterwards, so the private
    # evidence is left exactly as it was found.
    probe = private_run / "run-private.json"
    original = probe.read_bytes()
    try:
        mutated = bytearray(original)
        mutated[0] ^= 0x01
        probe.write_bytes(bytes(mutated))
        assert _sha256_dir(private_run) != first
    finally:
        # Restore unconditionally, and do not let a restore failure mask the
        # original error: report both, but preserve the first exception.
        try:
            probe.write_bytes(original)
        except OSError as restore_error:  # pragma: no cover - defensive
            # Chain, do not suppress: the original failure must stay visible.
            raise AssertionError(
                f"the probe file could not be restored: {restore_error}"
            ) from restore_error
        assert probe.read_bytes() == original, "the probe file was not restored"
        assert _sha256_dir(private_run) == first, "the private run was not restored"
