"""One prospective, text-only metadata recovery; never generate an image or anchor it."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator

from .experiment_runs import sha256_file
from .exp019_host_metadata import (
    QUERY_ATTESTATION, SCHEMA_PATH, bind_sidecar_to_receipt, load_host_session_metadata,
    validate_run_timestamp_plausibility,
)

AMENDMENT_ID = "EXP-019-MR-20260928-01"
AMENDMENT_PATH = "experiments/amendments/EXP-019.v1.1.1.METADATA-RECOVERY-01.md"
AMENDMENT_SHA256 = "b061e5ab023684df102b029d1ed1c319b0cddf24579c51215030be354730512a"
RECOVERY_DIR = Path(".metadata-recovery-private")
ATTESTATION_SCHEMA = "data/schemas/exp019_metadata_recovery_attestation.schema.json"


def frozen_amendment() -> dict:
    from .io import repo_root
    if sha256_file(repo_root() / AMENDMENT_PATH) != AMENDMENT_SHA256:
        raise ValueError("EXP-019 metadata recovery amendment is not byte-frozen")
    return {"id": AMENDMENT_ID, "file": AMENDMENT_PATH, "sha256": AMENDMENT_SHA256}


def _regular(path: Path, root: Path, *, directory: bool = False) -> Path:
    """Reject symlinks/junctions in every component below the canonical run."""
    lexical = Path(os.path.abspath(path))
    if ".." in path.parts or not lexical.is_relative_to(root):
        raise ValueError("EXP-019 recovery path escapes its run")
    for component in [lexical, *lexical.parents]:
        if component.is_symlink() or getattr(component, "is_junction", lambda: False)():
            raise ValueError("EXP-019 recovery path is redirected")
        if component == root:
            break
    if lexical.resolve(strict=True) != lexical or not (lexical.is_dir() if directory else lexical.is_file()):
        raise ValueError("EXP-019 recovery requires a canonical regular path")
    return lexical


def _write_new(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _evidence_error(path: Path, run: dict, slot_id: str,
                    recorded_at: str | None = None) -> str | None:
    """Apply the existing schema, slot, observation, count and lifecycle gates."""
    try:
        sidecar = load_host_session_metadata(path)
        receipt = {"metadata_query_attestation": QUERY_ATTESTATION.copy(),
                   "host_returned_output_count": 1}
        for host, operator in (("invoked_at_utc", "invoked_at_utc"),
                               ("generation_completed_at_utc", "generation_completed_at_utc"),
                               ("generation_id", "provider_generation_id"),
                               ("backend_model_snapshot", "backend_snapshot")):
            receipt[operator] = sidecar[host]
            receipt[operator + "_status"] = sidecar[host + "_status"]
        bind_sidecar_to_receipt(sidecar, receipt, opaque_slot_id=slot_id, image_present=True)
        validate_run_timestamp_plausibility(receipt, run["created_at_utc"],
                                            recorded_at or datetime.now(timezone.utc).isoformat())
    except (ValueError, KeyError, UnicodeError) as exc:
        # Canonical errors do not echo host-private field values into public output.
        return str(exc)
    return None


def _schema_errors(path: Path) -> list[dict]:
    from .io import load_json
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError):
        return [{"field": "$", "reason": "response is not valid UTF-8 JSON"}]
    return [{"field": ".".join(map(str, error.absolute_path)), "reason": error.message}
            for error in Draft202012Validator(load_json(SCHEMA_PATH)).iter_errors(payload)]


def _reject_generation_conflicts(path: Path) -> None:
    """Do not use capture recovery to erase a directly reported generation violation."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError):
        return
    if not isinstance(payload, dict):
        return
    for field, expected in (("reference_image_count", 0), ("requested_output_count", 1),
                            ("returned_output_count", 1), ("edit_or_regeneration_used", False)):
        value = payload.get(field)
        known_type = type(value) is bool if field == "edit_or_regeneration_used" else type(value) is int
        if payload.get(field + "_status") == "observed" and known_type and value != expected:
            raise ValueError("EXP-019 host-reported generation conflict requires protocol review, not metadata recovery")


def _eligible(run_file: str | Path, slot_id: str) -> tuple[Path, dict, Path, Path]:
    from .experiment_execution import load_run
    from .exp019_anchor import verify_external
    from .exp019_host import _next_slot, _raster, _staged_source
    path, run = load_run(run_file)
    if run["experiment_version"] != "1.1.1" or run["generation_mode"] != "host_native":
        raise ValueError("EXP-019 recovery applies only to v1.1.1 host-native execution")
    slot, _, output = _next_slot(run)
    if (slot["blind_id"] != slot_id or output["status"] != "planned"
            or output["attempt_events"] or output.get("receipt_history")
            or output.get("image") or output.get("metadata")):
        raise ValueError("EXP-019 recovery requires the current unimported slot with zero attempts")
    root = path.parent
    if (list((root / "outputs").glob(f"**/{slot_id}*"))
            or list((root / "provenance-freeze").glob(f"**/{slot_id}*"))):
        raise ValueError("EXP-019 recovery cannot reopen canonical slot evidence")
    state = verify_external(path, run)
    if any(c.get("private_binding", {}).get("slot_id") == slot_id for c in state["checkpoints"]):
        raise ValueError("EXP-019 recovery slot already has an external attempt checkpoint")
    staging = root / "host-import-staging" / slot_id
    _regular(staging, root, directory=True)
    sidecar = staging / "host-session.json"
    entries = list(staging.iterdir())
    images = [p for p in entries if p.name != sidecar.name]
    if len(entries) != 2 or len(images) != 1 or not sidecar.is_file():
        raise ValueError("EXP-019 recovery staging must contain exactly image and sidecar")
    image = images[0]
    _regular(image, root); _regular(sidecar, root)
    _staged_source(root, slot_id, image); _staged_source(root, slot_id, sidecar)
    _raster(image)
    return root, run, image, sidecar


def prepare_metadata_recovery(run_file: str | Path, *, blind_id: str,
                              original_conversation_available: bool = False,
                              no_image_change: bool = False) -> dict:
    """Preserve the rejected reply and reserve exactly one replay; no ledger mutation."""
    from .exp019_host import _packaged_query
    amendment = frozen_amendment()
    if original_conversation_available is not True or no_image_change is not True:
        raise ValueError("EXP-019 recovery requires original-conversation and unchanged-image attestations")
    root, run, image, sidecar = _eligible(run_file, blind_id)
    from .exp019_degraded_host import DEGRADED_DIR
    if (root / DEGRADED_DIR / blind_id).exists():
        raise ValueError("EXP-019 degraded evidence already reserved; no metadata path switching")
    area = root / RECOVERY_DIR / blind_id
    if area.exists() or area.is_symlink():
        raise ValueError("EXP-019 metadata recovery was already reserved; no additional replay")
    _reject_generation_conflicts(sidecar)
    prepared_at = datetime.now(timezone.utc).isoformat()
    rejection = _evidence_error(sidecar, run, blind_id, prepared_at)
    if rejection is None:
        raise ValueError("EXP-019 metadata recovery cannot replace valid metadata")
    query, query_hash = _packaged_query(root, run, blind_id)
    if (root / RECOVERY_DIR).exists():
        _regular(root / RECOVERY_DIR, root, directory=True)
    area.mkdir(parents=True)
    (area / "incoming").mkdir()
    (area / "rejected.host-session.json").write_bytes(sidecar.read_bytes())
    (area / "recovery-query.txt").write_bytes(query)
    record = {"amendment": amendment, "run_id": run["run_id"], "slot_id": blind_id,
              "prepared_at_utc": prepared_at,
              "image_sha256": sha256_file(image), "rejected_sha256": sha256_file(sidecar),
              "rejection_reason": rejection, "query_sha256": query_hash,
              "validator_failures": _schema_errors(sidecar),
              "generation_attempts_consumed": 0, "recovery_replays_reserved": 1,
              "original_conversation_available": True, "no_image_change": True}
    _write_new(area / "prepare.json", record)
    _write_new(area / "incoming" / "attestations.json", {
        "opaque_slot_id": blind_id, "replayed_query_sha256": query_hash,
        **{key: False for key in ("same_original_conversation", "same_original_image",
                                  "no_subsequent_image_generation", "no_image_modification",
                                  "exact_query_unchanged", "no_coaching_or_error_disclosure",
                                  "first_and_only_recovery_response")}})
    return {"slot_id": blind_id, "amendment_id": AMENDMENT_ID, "replay_budget": 1,
            "query": str(area / "recovery-query.txt"),
            "response_destination": str(area / "incoming" / "host-session.json"),
            "attestations": str(area / "incoming" / "attestations.json"),
            "attempts_consumed": 0, "checkpoint_created": False}


def _prepared(root: Path, run: dict, slot_id: str, image_hash: str) -> tuple[Path, dict]:
    from .exp019_host import _expected_query
    area = root / RECOVERY_DIR / slot_id
    _regular(area, root, directory=True)
    prepared = json.loads(_regular(area / "prepare.json", root).read_text(encoding="utf-8"))
    if (prepared.get("amendment") != frozen_amendment() or prepared.get("run_id") != run["run_id"]
            or prepared.get("slot_id") != slot_id or prepared.get("image_sha256") != image_hash
            or prepared.get("generation_attempts_consumed") != 0
            or prepared.get("recovery_replays_reserved") != 1
            or prepared.get("original_conversation_available") is not True
            or prepared.get("no_image_change") is not True):
        raise ValueError("EXP-019 prepared metadata recovery binding changed")
    rejected = _regular(area / "rejected.host-session.json", root)
    query = _regular(area / "recovery-query.txt", root)
    expected, expected_hash = _expected_query(slot_id)
    if (sha256_file(rejected) != prepared["rejected_sha256"]
            or query.read_bytes() != expected or prepared["query_sha256"] != expected_hash
            or not prepared.get("rejection_reason")
            or _evidence_error(rejected, run, slot_id, prepared["prepared_at_utc"]) != prepared["rejection_reason"]
            or _schema_errors(rejected) != prepared["validator_failures"]):
        raise ValueError("EXP-019 rejected metadata or recovery query evidence changed")
    return area, prepared


def stage_metadata_recovery(run_file: str | Path, *, blind_id: str) -> dict:
    """Consume the sole metadata response, including invalid replies; never retry it."""
    from .exp019_host import _packaged_query
    from .io import load_json
    root, run, image, sidecar = _eligible(run_file, blind_id)
    area, prepared = _prepared(root, run, blind_id, sha256_file(image))
    if ((area / "response.json").exists() or (area / "response.host-session.json").exists()
            or (area / "response-reserved").exists()):
        raise ValueError("EXP-019 recovery response already consumed; no third metadata response")
    if sha256_file(sidecar) != prepared["rejected_sha256"]:
        raise ValueError("EXP-019 active rejected sidecar was manually changed")
    _, query_hash = _packaged_query(root, run, blind_id)
    incoming = _regular(area / "incoming", root, directory=True)
    if {p.name for p in incoming.iterdir()} != {"host-session.json", "attestations.json"}:
        raise ValueError("EXP-019 recovery incoming area requires exactly response and attestations")
    candidate = _regular(incoming / "host-session.json", root)
    attestation_path = _regular(incoming / "attestations.json", root)
    # Exclusive reservation also prevents concurrent stage calls from consuming two replies.
    (area / "response-reserved").mkdir()
    # Freeze the first supplied response before judging it. A failed response exhausts the budget.
    candidate.rename(area / "response.host-session.json")
    attestation_path.rename(area / "response.attestations.json")
    error = None
    try:
        attestations = json.loads((area / "response.attestations.json").read_text(encoding="utf-8"))
        if (list(Draft202012Validator(load_json(ATTESTATION_SCHEMA)).iter_errors(attestations))
                or attestations["opaque_slot_id"] != blind_id
                or attestations["replayed_query_sha256"] != query_hash):
            error = "recovery execution attestations or replayed query binding invalid"
    except (ValueError, KeyError):
        error = "recovery execution attestations invalid"
    recorded_at = datetime.now(timezone.utc).isoformat()
    error = error or _evidence_error(area / "response.host-session.json", run, blind_id, recorded_at)
    result = {"run_id": run["run_id"], "slot_id": blind_id,
              "prepare_sha256": sha256_file(area / "prepare.json"),
              "response_sha256": sha256_file(area / "response.host-session.json"),
              "attestations_sha256": sha256_file(area / "response.attestations.json"),
              "recorded_at_utc": recorded_at,
              "status": "blocked" if error else "accepted", "rejection_reason": error,
              "recovery_responses_consumed": 1, "generation_attempts_consumed": 0}
    _write_new(area / "response.json", result)
    if error is None:
        temporary = area / "promote.host-session.json"
        temporary.write_bytes((area / "response.host-session.json").read_bytes())
        temporary.replace(sidecar)
    return {"slot_id": blind_id, "status": result["status"],
            "attempts_consumed": 0, "checkpoint_created": False,
            "additional_metadata_replay_allowed": False}


def recovery_binding(root: Path, run: dict, slot_id: str, image_hash: str,
                     sidecar_hash: str) -> dict | None:
    """Bind prospective recovery evidence into the existing canonical attempt receipt."""
    from .io import load_json
    area = root / RECOVERY_DIR / slot_id
    if not area.exists() and not area.is_symlink():
        return None
    area, prepared = _prepared(root, run, slot_id, image_hash)
    result = json.loads(_regular(area / "response.json", root).read_text(encoding="utf-8"))
    response = _regular(area / "response.host-session.json", root)
    attestation_path = _regular(area / "response.attestations.json", root)
    attestations = json.loads(attestation_path.read_text(encoding="utf-8"))
    if (result.get("status") != "accepted" or result.get("run_id") != run["run_id"]
            or result.get("slot_id") != slot_id or result.get("recovery_responses_consumed") != 1
            or result.get("generation_attempts_consumed") != 0
            or result.get("prepare_sha256") != sha256_file(area / "prepare.json")
            or result.get("response_sha256") != sha256_file(response)
            or result.get("attestations_sha256") != sha256_file(attestation_path)
            or sha256_file(response) != sidecar_hash
            or list(Draft202012Validator(load_json(ATTESTATION_SCHEMA)).iter_errors(attestations))
            or attestations.get("opaque_slot_id") != slot_id
            or attestations.get("replayed_query_sha256") != prepared["query_sha256"]
            or _evidence_error(response, run, slot_id, result["recorded_at_utc"]) is not None):
        raise ValueError("EXP-019 recovery response or immutable evidence binding invalid")
    return {"amendment": prepared["amendment"], "files": {
        (area / name).relative_to(root).as_posix(): sha256_file(area / name)
        for name in ("prepare.json", "rejected.host-session.json", "recovery-query.txt",
                     "response.json", "response.host-session.json", "response.attestations.json")}}


def verify_recovery_receipt(root: Path, run: dict, slot_id: str, record: dict) -> None:
    binding = record.get("metadata_recovery")
    if binding is not None and binding != recovery_binding(
            root, run, slot_id, record["output_image_sha256"], record["host_session_metadata_sha256"]):
        raise ValueError("EXP-019 finalized metadata recovery evidence changed")
