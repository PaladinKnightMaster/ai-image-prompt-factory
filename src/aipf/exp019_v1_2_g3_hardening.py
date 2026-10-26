"""EXP-019 v1.2 G3 operator hardening (process-validation tooling only).

Implements run-state enforcement and contemporaneous capture controls for
human ChatGPT Images pilots. Does not contact any host, allocate treatments,
register v1.2, or reopen closed pilot evidence.

Spec: EXP019-V12-G3-HARDENING-SPEC-2026-10-26.r0
Policy: UNLOCK-AFTER-STOP=FORBID, CAPTURE_BLOCKED_POLICY=ABORT_ONLY

Timestamps recorded here are operator_observed wall clocks of local capture
commands. They do not prove authenticated host submit/response instants.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aipf.exp019_v1_2_operator import (
    ROLE_CUSTODIAN,
    ROLE_OPERATOR,
    OperatorCaptureSession,
    make_opaque_prompt_packet,
)

STATES = (
    "CREATED",
    "PREFLIGHT_READY",
    "ACTIVE",
    "CAPTURE_BLOCKED",
    "STOPPED_BY_OWNER",
    "COMPLETED",
    "CLOSED",
)

# Valid directed edges (from -> frozenset(to))
TRANSITIONS: dict[str, frozenset[str]] = {
    "CREATED": frozenset({"PREFLIGHT_READY"}),
    "PREFLIGHT_READY": frozenset({"ACTIVE"}),
    "ACTIVE": frozenset({"CAPTURE_BLOCKED", "STOPPED_BY_OWNER", "COMPLETED"}),
    "CAPTURE_BLOCKED": frozenset({"STOPPED_BY_OWNER", "COMPLETED"}),
    # UNLOCK-AFTER-STOP: FORBID - no path back to ACTIVE
    "STOPPED_BY_OWNER": frozenset({"COMPLETED"}),
    "COMPLETED": frozenset({"CLOSED"}),
    "CLOSED": frozenset(),
}

# Actions that mutate capture evidence / budget
MUTATING_CAPTURE = frozenset({
    "copy",
    "verify-clipboard",
    "pre-send",
    "submit",
    "response",
    "download",
    "attest",
    # retrospective disabled under ABORT_ONLY policy
})

DEFAULT_PILOTS = {
    "PLVA01": {
        "sha256": "7b8d2f5c74058370aa191f22faf4cd813a7de6c081748fc887c0cead7e9d786c",
        "nbytes": 328,
        "slot": "PVAMG2",
    },
    "PLVB01": {
        "sha256": "2f25bbe661eff6b3eb1a020462c854d71097f454c65d02f070f5400b2916b28e",
        "nbytes": 220,
        "slot": "PVCBX2",
    },
}


class HardeningError(Exception):
    """Explicit fail-closed error (converted to non-zero exit in main)."""


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_json(path: Path) -> Any:
    """Load JSON; tolerate UTF-8 BOM (PowerShell Set-Content -Encoding utf8)."""
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: Any) -> None:
    """Write JSON as UTF-8 without BOM (atomic replace)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, indent=2, sort_keys=True) + "\n"
    payload = text.encode("utf-8")
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(payload)
    tmp.replace(path)


def has_utf8_bom(path: Path) -> bool:
    if not path.exists():
        return False
    return path.read_bytes()[:3] == b"\xef\xbb\xbf"


def pilot_run_path(root: Path) -> Path:
    return root / "pilot-run.json"


def audit_path(root: Path) -> Path:
    return root / "audit" / "unauthorized-attempts.jsonl"


def session_path(root: Path, pilot_id: str) -> Path:
    d = root / "evidence" / pilot_id
    d.mkdir(parents=True, exist_ok=True)
    return d / "capture-session.json"


def append_audit(root: Path, event: dict) -> None:
    path = audit_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps({**event, "recorded_at_utc": utc_now()}, sort_keys=True)
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(line + "\n")


def load_pilot_run(root: Path) -> dict:
    path = pilot_run_path(root)
    if not path.exists():
        return {
            "run_state": "CREATED",
            "budget": {
                "actual_submission_count": 0,
                "max_image_generation_submissions": 2,
                "remaining": 2,
            },
            "prompt_order": ["PLVA01", "PLVB01"],
            "hardening_spec": "EXP019-V12-G3-HARDENING-SPEC-2026-10-26.r0",
            "unlock_after_stop": "FORBID",
            "capture_blocked_policy": "ABORT_ONLY",
            "state_history": [],
        }
    return read_json(path)


def save_pilot_run(root: Path, meta: dict) -> None:
    write_json(pilot_run_path(root), meta)


def get_state(meta: dict) -> str:
    return str(meta.get("run_state") or "CREATED")


def transition(root: Path, meta: dict, new_state: str, reason: str) -> dict:
    old = get_state(meta)
    if new_state not in STATES:
        raise HardeningError(f"unknown state {new_state}")
    allowed = TRANSITIONS.get(old, frozenset())
    if new_state not in allowed:
        append_audit(root, {
            "event": "invalid_transition_attempt",
            "from": old,
            "to": new_state,
            "reason": reason,
        })
        raise HardeningError(
            f"INVALID_TRANSITION {old} -> {new_state} ({reason})"
        )
    meta["run_state"] = new_state
    hist = list(meta.get("state_history") or [])
    hist.append({
        "from": old,
        "to": new_state,
        "at_utc": utc_now(),
        "reason": reason,
        "timestamp_class": "operator_observed",
    })
    meta["state_history"] = hist
    save_pilot_run(root, meta)
    return meta


def remaining_budget(meta: dict) -> int:
    b = meta.setdefault("budget", {})
    max_n = int(b.get("max_image_generation_submissions", 2))
    used = int(b.get("actual_submission_count", 0))
    rem = max(0, max_n - used)
    b["remaining"] = rem
    return rem


def require_active_for_capture(root: Path, meta: dict, action: str) -> None:
    state = get_state(meta)
    if state == "CLOSED":
        append_audit(root, {"event": "closed_mutate_attempt", "action": action})
        raise HardeningError("CLOSED_RUN: ordinary mutation forbidden")
    if state == "STOPPED_BY_OWNER":
        append_audit(root, {
            "event": "post_stop_continuation_attempt",
            "action": action,
            "note": "UNLOCK-AFTER-STOP=FORBID; local tooling refuses authorized continuation",
        })
        raise HardeningError(
            "STOPPED_BY_OWNER: further capture progression forbidden "
            "(does not control ChatGPT Images UI)"
        )
    if state == "CAPTURE_BLOCKED":
        append_audit(root, {
            "event": "capture_blocked_continuation_attempt",
            "action": action,
            "policy": "ABORT_ONLY",
        })
        raise HardeningError(
            "CAPTURE_BLOCKED: abort-only policy; no further capture "
            "(owner STOP or COMPLETE without new host capture)"
        )
    if state != "ACTIVE":
        append_audit(root, {
            "event": "capture_while_not_active",
            "action": action,
            "state": state,
        })
        raise HardeningError(f"run_state={state}; capture requires ACTIVE")


def enter_capture_blocked(root: Path, meta: dict, reason: str) -> dict:
    if get_state(meta) == "ACTIVE":
        return transition(root, meta, "CAPTURE_BLOCKED", reason)
    return meta


def resolve_pilot(root: Path, pilot_id: str) -> dict:
    packet_path = root / "packets" / pilot_id / "packet.json"
    frozen_path = root / "packets" / pilot_id / "frozen-prompt.txt"
    if not frozen_path.exists():
        raise HardeningError(f"missing frozen prompt for {pilot_id}")
    frozen = frozen_path.read_bytes()
    digest = hashlib.sha256(frozen).hexdigest()
    if packet_path.exists():
        pkt = read_json(packet_path)
        exp = pkt.get("sha256") or pkt.get("frozen_prompt_sha256")
        slot = pkt.get("tooling_slot") or pkt.get("opaque_slot_id")
        nbytes = pkt.get("nbytes") or pkt.get("frozen_prompt_nbytes")
        if exp and exp != digest:
            raise HardeningError("DIGEST_MISMATCH packet vs frozen bytes")
        if nbytes is not None and int(nbytes) != len(frozen):
            raise HardeningError("DIGEST_MISMATCH nbytes")
        if not slot:
            slot = DEFAULT_PILOTS.get(pilot_id, {}).get("slot")
        if not slot:
            raise HardeningError(f"missing tooling slot for {pilot_id}")
        return {"sha256": digest, "nbytes": len(frozen), "slot": slot, "frozen": frozen}
    if pilot_id in DEFAULT_PILOTS:
        d = DEFAULT_PILOTS[pilot_id]
        if digest != d["sha256"] or len(frozen) != d["nbytes"]:
            raise HardeningError(
                f"DIGEST_MISMATCH {pilot_id} got {digest} {len(frozen)}"
            )
        return {**d, "frozen": frozen}
    raise HardeningError(f"unknown pilot {pilot_id} without packet.json")


def load_session(root: Path, pilot_id: str) -> dict:
    path = session_path(root, pilot_id)
    if path.exists():
        return read_json(path)
    return {
        "pilot_id": pilot_id,
        "timestamp_class": "operator_observed",
        "not_authenticated_host_clock": True,
    }


def save_session(root: Path, pilot_id: str, state: dict) -> None:
    write_json(session_path(root, pilot_id), state)


def build_operator_session(
    root: Path, pilot_id: str, slot: str, frozen: bytes, conversation_ref: str,
) -> OperatorCaptureSession:
    packet = make_opaque_prompt_packet(
        opaque_slot_id=slot,
        attempt_number=1,
        frozen_prompt_bytes=frozen,
        conversation_ref=conversation_ref,
        role=ROLE_CUSTODIAN,
    )
    work = root / "evidence" / pilot_id / "session_work"
    work.mkdir(parents=True, exist_ok=True)
    return OperatorCaptureSession(
        packet=packet,
        operator_id="owner_self_human",
        role=ROLE_OPERATOR,
        work_dir=work,
    )


def action_preflight(root: Path) -> int:
    meta = load_pilot_run(root)
    state = get_state(meta)
    if state not in {"CREATED", "PREFLIGHT_READY"}:
        # idempotent read/check when already past preflight
        print(f"OK preflight skipped; run_state={state}")
        return 0
    pr = pilot_run_path(root)
    if pr.exists() and has_utf8_bom(pr):
        raise HardeningError(
            "PREFLIGHT_FAIL: pilot-run.json has UTF-8 BOM; rewrite with utf-8 no BOM"
        )
    # ensure packets exist
    order = list(meta.get("prompt_order") or ["PLVA01", "PLVB01"])
    for pid in order:
        resolve_pilot(root, pid)
    meta.setdefault("unlock_after_stop", "FORBID")
    meta.setdefault("capture_blocked_policy", "ABORT_ONLY")
    meta.setdefault(
        "hardening_spec", "EXP019-V12-G3-HARDENING-SPEC-2026-10-26.r0"
    )
    meta["preflight"] = {
        "status": "PASS",
        "bom_probe": "PASS",
        "checked_at_utc": utc_now(),
    }
    if state == "CREATED":
        transition(root, meta, "PREFLIGHT_READY", "preflight PASS")
    else:
        save_pilot_run(root, meta)
    print("OK preflight PASS (BOM probe + packet digests)")
    return 0


def action_authorize(root: Path) -> int:
    """Mark ACTIVE only from PREFLIGHT_READY (owner APPROVE EXECUTION recorded)."""
    meta = load_pilot_run(root)
    if get_state(meta) != "PREFLIGHT_READY":
        raise HardeningError("authorize requires PREFLIGHT_READY")
    meta["execution_authorized"] = True
    meta["execution_authorized_at_utc"] = utc_now()
    transition(root, meta, "ACTIVE", "owner APPROVE EXECUTION recorded locally")
    print("OK ACTIVE - local capture permitted; ChatGPT UI not controlled")
    return 0


def action_owner_stop(root: Path) -> int:
    meta = load_pilot_run(root)
    state = get_state(meta)
    if state in {"STOPPED_BY_OWNER", "CLOSED", "COMPLETED"}:
        print(f"OK already {state}")
        return 0
    if state not in {"ACTIVE", "CAPTURE_BLOCKED"}:
        raise HardeningError(f"STOP not valid from {state}")
    meta["owner_stop_decision"] = {
        "decision": "STOP",
        "at_utc": utc_now(),
        "unlock_after_stop": "FORBID",
    }
    transition(root, meta, "STOPPED_BY_OWNER", "owner STOP")
    print("OK STOPPED_BY_OWNER - local continuation forbidden")
    return 0


def action_complete(root: Path) -> int:
    meta = load_pilot_run(root)
    state = get_state(meta)
    if state == "CLOSED":
        print("OK already CLOSED")
        return 0
    if state not in {"ACTIVE", "CAPTURE_BLOCKED", "STOPPED_BY_OWNER", "COMPLETED"}:
        raise HardeningError(f"complete not valid from {state}")
    if state != "COMPLETED":
        transition(root, meta, "COMPLETED", "operator complete")
    print("OK COMPLETED - await owner disposition to CLOSED")
    return 0


def action_close(root: Path) -> int:
    meta = load_pilot_run(root)
    if get_state(meta) != "COMPLETED":
        raise HardeningError("close requires COMPLETED")
    transition(root, meta, "CLOSED", "owner disposition accepted")
    print("OK CLOSED")
    return 0


def _reject_retrospective(action: str) -> None:
    if "retrospective" in action:
        raise HardeningError(
            "RETROSPECTIVE_FORBIDDEN under CAPTURE_BLOCKED_POLICY=ABORT_ONLY"
        )


def action_pre_send(root: Path, pilot_id: str, conversation_ref: str, stamp: str) -> int:
    meta = load_pilot_run(root)
    require_active_for_capture(root, meta, "pre-send")
    info = resolve_pilot(root, pilot_id)
    state = load_session(root, pilot_id)
    try:
        session = build_operator_session(
            root, pilot_id, info["slot"], info["frozen"], conversation_ref)
        paste_sha = session.record_pre_send_paste(
            info["frozen"], rendered_request_text=None, at_utc=stamp)
        if paste_sha != info["sha256"]:
            raise HardeningError("paste digest != frozen")
        state["pre_send_at_utc"] = stamp
        state["paste_sha256"] = paste_sha
        state["pre_send_ok"] = True
        state["tooling_slot_id"] = info["slot"]
        log = session.export_action_log()
        write_json(
            root / "evidence" / pilot_id / "q3-action-log.json",
            {**log, "timestamp_class": "operator_observed"},
        )
        save_session(root, pilot_id, state)
    except Exception as exc:  # noqa: BLE001
        enter_capture_blocked(root, meta, f"pre-send failed: {exc}")
        raise HardeningError(f"pre-send failed: {exc}") from exc
    print("OK pre-send", paste_sha, "at", stamp, "(operator_observed)")
    return 0


def action_submit(root: Path, pilot_id: str, conversation_ref: str, stamp: str) -> int:
    meta = load_pilot_run(root)
    require_active_for_capture(root, meta, "submit")
    if remaining_budget(meta) <= 0:
        raise HardeningError("BUDGET_EXHAUSTED")
    info = resolve_pilot(root, pilot_id)
    state = load_session(root, pilot_id)
    if not state.get("pre_send_ok"):
        raise HardeningError("run pre-send first")
    if state.get("submit_recorded") or state.get("submit_at_utc"):
        raise HardeningError("submit already recorded; no retry")
    # Order: earlier pilots should be terminal before next (soft check)
    order = list(meta.get("prompt_order") or [])
    if pilot_id in order:
        idx = order.index(pilot_id)
        for prior in order[:idx]:
            ps = load_session(root, prior)
            if not ps.get("output_sha256"):
                raise HardeningError(
                    f"pilot order: complete download for {prior} before {pilot_id}"
                )
    try:
        session = build_operator_session(
            root, pilot_id, info["slot"], info["frozen"], conversation_ref)
        session.record_pre_send_paste(
            info["frozen"], rendered_request_text=None,
            at_utc=state["pre_send_at_utc"])
        q1 = session.record_request_capture(
            attachment_count=0, generation_request_count=1, at_utc=stamp)
        q1["timestamp_class"] = "operator_observed"
        q1["pilot_id"] = pilot_id
        q1["not_authenticated_host_clock"] = True
        q1["contemporaneous"] = True
        write_json(root / "evidence" / pilot_id / "q1-request-capture.json", q1)
        state["submit_at_utc"] = stamp
        state["submit_recorded"] = True
        state["submit_contemporaneous"] = True
        state["q1"] = q1
        log = session.export_action_log()
        write_json(
            root / "evidence" / pilot_id / "q3-action-log.json",
            {**log, "timestamp_class": "operator_observed"},
        )
        # budget only after successful Q1 write
        used = int(meta["budget"].get("actual_submission_count", 0)) + 1
        meta["budget"]["actual_submission_count"] = used
        meta["budget"]["remaining"] = max(
            0, int(meta["budget"].get("max_image_generation_submissions", 2)) - used)
        meta.setdefault("invocations", []).append({
            "pilot_id": pilot_id,
            "submitted_at_utc": stamp,
            "timestamp_class": "operator_observed",
            "contemporaneous": True,
        })
        save_session(root, pilot_id, state)
        save_pilot_run(root, meta)
    except HardeningError:
        raise
    except Exception as exc:  # noqa: BLE001
        # Do not increment budget; block further capture
        enter_capture_blocked(root, load_pilot_run(root), f"submit failed: {exc}")
        raise HardeningError(f"submit failed: {exc}") from exc
    print("BUDGET", f"{meta['budget']['actual_submission_count']}/"
          f"{meta['budget']['max_image_generation_submissions']}")
    print("OK submit Q1 captured_at_utc", stamp, "(operator_observed)")
    return 0


def action_response(
    root: Path, pilot_id: str, conversation_ref: str, stamp: str, returned: int,
) -> int:
    meta = load_pilot_run(root)
    require_active_for_capture(root, meta, "response")
    info = resolve_pilot(root, pilot_id)
    state = load_session(root, pilot_id)
    if not state.get("submit_recorded"):
        raise HardeningError("run submit first")
    if state.get("submit_contemporaneous") is False:
        raise HardeningError("retrospective submit cannot use contemporaneous response")
    if stamp < state["submit_at_utc"]:
        raise HardeningError("response time must be >= submit time")
    try:
        session = build_operator_session(
            root, pilot_id, info["slot"], info["frozen"], conversation_ref)
        session.record_pre_send_paste(
            info["frozen"], rendered_request_text=None,
            at_utc=state["pre_send_at_utc"])
        session.record_request_capture(
            attachment_count=0, generation_request_count=1,
            at_utc=state["submit_at_utc"])
        q2 = session.record_response_capture(
            image_returned=returned > 0,
            returned_image_count=returned,
            artifact_id=f"{pilot_id}-out",
            at_utc=stamp,
        )
        q2["timestamp_class"] = "operator_observed"
        q2["pilot_id"] = pilot_id
        q2["not_authenticated_host_clock"] = True
        q2["contemporaneous"] = True
        write_json(root / "evidence" / pilot_id / "q2-response-capture.json", q2)
        state["response_at_utc"] = stamp
        state["response_recorded"] = True
        state["response_contemporaneous"] = True
        state["q2"] = q2
        log = session.export_action_log()
        write_json(
            root / "evidence" / pilot_id / "q3-action-log.json",
            {**log, "timestamp_class": "operator_observed"},
        )
        save_session(root, pilot_id, state)
    except HardeningError:
        raise
    except Exception as exc:  # noqa: BLE001
        enter_capture_blocked(root, load_pilot_run(root), f"response failed: {exc}")
        raise HardeningError(f"response failed: {exc}") from exc
    print("OK response captured_at_utc", stamp, "(operator_observed)")
    return 0


def action_download(root: Path, pilot_id: str, image_path: str, stamp: str) -> int:
    meta = load_pilot_run(root)
    require_active_for_capture(root, meta, "download")
    state = load_session(root, pilot_id)
    if not state.get("response_recorded"):
        raise HardeningError("run response first")
    img_path = Path(image_path)
    if not img_path.is_file():
        raise HardeningError(f"image not found: {img_path}")
    if " " in str(img_path) and not img_path.exists():
        raise HardeningError("path with spaces must be passed as a single argument")
    try:
        data = img_path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        try:
            from io import BytesIO

            from PIL import Image
            with Image.open(BytesIO(data)) as im:
                im.load()
                raster = {
                    "technical_validation": "passed",
                    "format": im.format,
                    "dimensions": list(im.size),
                }
        except Exception as exc:  # noqa: BLE001
            raster = {"technical_validation": "failed", "error": str(exc)}
        dest_dir = root / "downloads" / pilot_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / img_path.name
        if dest.resolve() != img_path.resolve():
            dest.write_bytes(data)
        file_mtime_utc = datetime.fromtimestamp(
            img_path.stat().st_mtime, tz=timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
        q4 = {
            "pilot_id": pilot_id,
            "frozen_prompt_sha256": state.get("paste_sha256"),
            "paste_sha256": state.get("paste_sha256"),
            "output_sha256": digest,
            "output_nbytes": len(data),
            "output_path": str(dest),
            "source_path": str(img_path),
            "raster": raster,
            "associated_at_utc": stamp,
            "timestamp_class": "operator_observed",
            "file_mtime_utc": file_mtime_utc,
            "file_mtime_is_not_generation_time": True,
        }
        write_json(root / "evidence" / pilot_id / "q4-artifact-digests.json", q4)
        state["output_sha256"] = digest
        state["q4"] = q4
        save_session(root, pilot_id, state)
    except HardeningError:
        raise
    except Exception as exc:  # noqa: BLE001
        enter_capture_blocked(root, load_pilot_run(root), f"download failed: {exc}")
        raise HardeningError(f"download failed: {exc}") from exc
    print("OK download", digest, len(data), raster.get("technical_validation"))
    return 0


def action_attest(
    root: Path, pilot_id: str, signature: str, confirm: bool, stamp: str,
) -> int:
    meta = load_pilot_run(root)
    state_name = get_state(meta)
    if state_name not in {"ACTIVE", "COMPLETED"}:
        append_audit(root, {"event": "attest_blocked", "state": state_name})
        raise HardeningError(f"attest forbidden in state {state_name}")
    state = load_session(root, pilot_id)
    if "output_sha256" not in state:
        raise HardeningError("run download first")
    statements = {
        "host_ui_was_chatgpt_images": None,
        "direct_paste_no_attachment": None,
        "clipboard_matched_frozen_before_submit": None,
        "single_submission_only": None,
        "returned_exactly_one_image": None,
        "no_retry_performed": None,
        "no_edit_before_download": None,
        "downloaded_bytes_unedited": None,
    }
    unsigned = {
        "pilot_id": pilot_id,
        "attestation_status": "UNSIGNED_AWAITING_OPERATOR_CONFIRMATION",
        "attested_at_utc": None,
        "operator_signature": None,
        "output_sha256": state["output_sha256"],
        "statements_for_operator_to_confirm": statements,
        "auto_true_forbidden": True,
        "q5_does_not_cure_missing_q1_q3": True,
    }
    upath = root / "evidence" / pilot_id / "q5-operator-attestation.UNSIGNED.json"
    if not signature or not confirm:
        write_json(upath, unsigned)
        print("Q5_STATEMENTS_FOR_REVIEW (not signed; auto-true NOT applied):")
        for k in statements:
            print(f"  - {k}: ?")
        print("OUTPUT", state["output_sha256"])
        return 0
    q5 = {
        "pilot_id": pilot_id,
        "attestation_status": "OPERATOR_SIGNED",
        "attested_at_utc": stamp,
        "operator_signature": signature,
        "output_sha256": state["output_sha256"],
        "statements": {k: True for k in statements},
        "statements_explicitly_confirmed_by_operator": True,
        "timestamp_class": "operator_observed_signing_time",
        "q5_does_not_cure_missing_q1_q3": True,
        "notes": "Signing time is not a generation timestamp.",
    }
    write_json(
        root / "evidence" / pilot_id / "q5-operator-attestation.SIGNED.json", q5)
    unsigned["attestation_status"] = "SUPERSEDED_BY_SIGNED"
    unsigned["signed_file"] = "q5-operator-attestation.SIGNED.json"
    write_json(upath, unsigned)
    state["q5"] = q5
    save_session(root, pilot_id, state)
    print("OK attest", signature, stamp)
    return 0


def action_status(root: Path, pilot_id: str | None = None) -> int:
    meta = load_pilot_run(root)
    out = {
        "run_state": get_state(meta),
        "budget_remaining": remaining_budget(meta),
        "budget_used": meta.get("budget", {}).get("actual_submission_count"),
        "unlock_after_stop": meta.get("unlock_after_stop", "FORBID"),
        "capture_blocked_policy": meta.get("capture_blocked_policy", "ABORT_ONLY"),
        "trust_boundary": (
            "Local tooling enforces state/budget/evidence only; "
            "it does not control ChatGPT Images UI clicks."
        ),
    }
    if pilot_id:
        out["pilot"] = load_session(root, pilot_id)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="exp019_v1_2_g3_hardening")
    ap.add_argument("--root", required=True)
    ap.add_argument("--action", required=True)
    ap.add_argument("--pilot-id", default="")
    ap.add_argument("--conversation-ref", default="chatgpt.com/images")
    ap.add_argument("--at-utc", default="")
    ap.add_argument("--returned-count", type=int, default=1)
    ap.add_argument("--image-path", default="")
    ap.add_argument("--signature", default="")
    ap.add_argument("--confirm-all-true", action="store_true")
    args = ap.parse_args(argv)

    root = Path(args.root)
    stamp = args.at_utc or utc_now()
    action = args.action
    _reject_retrospective(action)

    try:
        if action == "preflight":
            return action_preflight(root)
        if action == "authorize":
            return action_authorize(root)
        if action == "owner-stop":
            return action_owner_stop(root)
        if action == "complete":
            return action_complete(root)
        if action == "close":
            return action_close(root)
        if action == "status":
            return action_status(root, args.pilot_id or None)
        if action in {"submit-retrospective", "response-retrospective"}:
            raise HardeningError(
                "RETROSPECTIVE_FORBIDDEN under CAPTURE_BLOCKED_POLICY=ABORT_ONLY"
            )

        if not args.pilot_id:
            raise HardeningError("--pilot-id required for this action")

        if action == "pre-send":
            return action_pre_send(root, args.pilot_id, args.conversation_ref, stamp)
        if action == "submit":
            return action_submit(root, args.pilot_id, args.conversation_ref, stamp)
        if action == "response":
            return action_response(
                root, args.pilot_id, args.conversation_ref, stamp, args.returned_count)
        if action == "download":
            if not args.image_path:
                raise HardeningError("--image-path required")
            return action_download(root, args.pilot_id, args.image_path, stamp)
        if action == "attest":
            return action_attest(
                root, args.pilot_id, args.signature, args.confirm_all_true, stamp)

        raise HardeningError(f"unknown action {action}")
    except HardeningError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        # Last-resort fail-closed
        try:
            meta = load_pilot_run(root)
            if get_state(meta) == "ACTIVE":
                enter_capture_blocked(root, meta, f"unhandled: {exc}")
        except Exception:  # noqa: BLE001
            pass
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
