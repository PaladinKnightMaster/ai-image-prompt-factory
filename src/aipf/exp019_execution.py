"""Exact, fail-closed API execution for the frozen EXP-019 protocol."""
from __future__ import annotations

import base64
import json
import os
import struct
from datetime import datetime, timezone
from pathlib import Path

from .exp019_protocol import append_attempt_event, find_slot, validate_run
from .experiment_runs import sha256_file


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json_new(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _save_run(path: Path, run: dict) -> None:
    from .experiment_execution import _write_json_atomic
    validate_run(run)
    _write_json_atomic(path, run)


def _provider_details(response) -> dict:
    item = response.data[0]
    return {
        "request_id": getattr(response, "_request_id", None),
        "provider_created": getattr(response, "created", None),
        "observed_model": getattr(response, "model", None),
        "observed_size": getattr(response, "size", None),
        "observed_quality": getattr(response, "quality", None),
        "observed_background": getattr(response, "background", None),
        "output_format": getattr(response, "output_format", None),
        "revised_prompt": getattr(item, "revised_prompt", None),
        "transport": "b64_json",
    }


def _failure_kind(exc: Exception) -> str:
    """Retry only errors that clearly precede an evaluable raster."""
    code = str(getattr(exc, "code", "") or "").lower()
    message = str(exc).lower()
    if any(term in code or term in message for term in ("content_filter", "safety", "policy_violation", "refusal")):
        return "safety_refusal"
    status_code = getattr(exc, "status_code", None)
    if isinstance(status_code, int):
        return "technical_failure" if status_code == 429 or status_code >= 500 else "provider_failure"
    if type(exc).__name__ in {"APIConnectionError", "APITimeoutError", "TimeoutError", "ConnectionError"}:
        return "technical_failure"
    return "provider_failure"


def _write_receipt(root: Path, run: dict, variant: dict, output: dict, position: int) -> None:
    events = output["attempt_events"]
    number = events[-1]["attempt_number"]
    receipt = {
        "schema_version": "1.0.0",
        "experiment_id": "EXP-019",
        "experiment_version": "1.0.0",
        "run_id": run["run_id"],
        "slot_id": output["blind_id"],
        "slot_position": position,
        "plan_commitment_sha256": run["plan_commitment_sha256"],
        "fixture_sha256": run["fixture_sha256"],
        "definition_sha256": run["experiment_definition_sha256"],
        "prompt_sha256": variant["prompt_sha256"],
        "provider": "openai",
        "requested_model": run["model"],
        "recorded_model_snapshot": run["model_snapshot"],
        "settings": run["settings"],
        "reference_inputs": [],
        "attempt_events": [dict(event) for event in events],
        "output_image_sha256": output.get("image_sha256"),
        "status": output["status"],
        "recorded_at_utc": _now(),
    }
    name = f"{output['blind_id']}.attempt-{number}.receipt.json"
    path = root / "receipts" / name
    _write_json_new(path, receipt)
    output.setdefault("receipt_history", []).append({"file": f"receipts/{name}", "sha256": sha256_file(path)})


def _slot_state(output: dict) -> tuple[int, str | None]:
    events = output["attempt_events"]
    starts = [event for event in events if event.get("event") == "started"]
    outcomes = [event for event in events if event.get("event") != "started"]
    if len(starts) != len(outcomes) or any(
        starts[index]["attempt_number"] != outcomes[index]["attempt_number"]
        for index in range(len(outcomes))
    ):
        raise ValueError("EXP-019 has an unresolved attempt; inspect before any retry")
    return len(starts), outcomes[-1]["event"] if outcomes else None


def _verify_prior_receipts(root: Path, output: dict) -> None:
    completed = sum(event.get("event") != "started" for event in output["attempt_events"])
    history = output.get("receipt_history", [])
    if len(history) != completed:
        raise ValueError("EXP-019 prior receipt history is incomplete")
    receipt_names = {binding["file"] for binding in history}
    existing_names = {f"receipts/{path.name}" for path in (root / "receipts").glob(
        f"{output['blind_id']}.attempt-*.receipt.json"
    )}
    if receipt_names != existing_names:
        raise ValueError("EXP-019 unbound or missing attempt receipt")
    for binding in history:
        path = root / binding["file"]
        if not path.is_file() or sha256_file(path) != binding["sha256"]:
            raise ValueError("EXP-019 prior receipt hash mismatch")
    image_exists = (root / "outputs" / f"{output['blind_id']}.png").exists()
    metadata_exists = (root / "outputs" / f"{output['blind_id']}.json").exists()
    if image_exists != metadata_exists or image_exists != (output.get("status") == "generated"):
        raise ValueError("EXP-019 unbound output or interrupted persistence")


def execute_exp019_run(run_file: str | Path, *, dry_run: bool = False, client=None) -> dict:
    from .experiment_execution import load_run

    path, run = load_run(run_file)
    validate_run(run)
    if dry_run:
        return {
            "run_id": run["run_id"], "dry_run": True, "generation_mode": "api",
            "model": run["model"], "settings": run["settings"],
            "slots": [{"position": s["position"], "blind_id": s["blind_id"],
                       "prompt_sha256": find_slot(run, s["blind_id"])[0]["prompt_sha256"]}
                      for s in run["invocation_order"]],
        }
    if client is None:
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is required for EXP-019 API execution")
        from openai import OpenAI
        # SDK-level automatic retries would create unrecorded invocations.
        client = OpenAI(max_retries=0)

    generated = 0
    root = path.parent
    for slot in run["invocation_order"]:
        variant, output = find_slot(run, slot["blind_id"])
        prior_count, prior_outcome = _slot_state(output)
        _verify_prior_receipts(root, output)
        if output["status"] == "generated":
            if prior_outcome != "success":
                raise ValueError("EXP-019 generated slot has no successful attempt")
            image_path = root / "outputs" / str(output.get("image"))
            if not image_path.is_file() or sha256_file(image_path) != output.get("image_sha256"):
                raise ValueError("EXP-019 prior output image hash mismatch")
            continue
        if prior_outcome in {"safety_refusal", "provider_failure", "protocol_failure"} or prior_count >= 3:
            run["status"] = "incomplete"
            _save_run(path, run)
            return {"run_id": run["run_id"], "status": "incomplete", "stopped_slot": output["blind_id"], "generated": generated}
        if prior_outcome not in {None, "technical_failure"}:
            raise ValueError("EXP-019 slot cannot be rerolled")

        for attempt_number in range(prior_count + 1, 4):
            started = {"event": "started", "attempt_number": attempt_number,
                       "at_utc": _now(), "prompt_sha256": variant["prompt_sha256"]}
            append_attempt_event(output, started)
            run["status"] = "running"
            _save_run(path, run)

            try:
                response = client.images.generate(
                    model=run["model"], prompt=variant["prompt"],
                    size=run["settings"]["size"], quality=run["settings"]["quality"],
                    background=run["settings"]["background"], n=1,
                )
            except Exception as exc:
                kind = _failure_kind(exc)
                append_attempt_event(output, {
                    "event": kind, "attempt_number": attempt_number, "at_utc": _now(),
                    "provider_request_id": getattr(exc, "request_id", None),
                    "provider_status_code": getattr(exc, "status_code", None),
                    "error_type": type(exc).__name__, "error": str(exc),
                })
                output["status"] = "failed"
                output["error"] = str(exc)
                _write_receipt(root, run, variant, output, slot["position"])
                if kind != "technical_failure" or attempt_number == 3:
                    run["status"] = "incomplete"
                    _save_run(path, run)
                    return {"run_id": run["run_id"], "status": "incomplete", "stopped_slot": output["blind_id"], "generated": generated}
                _save_run(path, run)
                continue

            data = getattr(response, "data", None)
            if not data or len(data) != 1 or not getattr(data[0], "b64_json", None):
                append_attempt_event(output, {
                    "event": "protocol_failure", "attempt_number": attempt_number,
                    "at_utc": _now(), "provider_request_id": getattr(response, "_request_id", None),
                    "error": "API returned other than exactly one base64 image",
                })
                output["status"] = "failed"
                output["error"] = "API returned other than exactly one base64 image"
                _write_receipt(root, run, variant, output, slot["position"])
                run["status"] = "incomplete"
                _save_run(path, run)
                return {"run_id": run["run_id"], "status": "incomplete", "stopped_slot": output["blind_id"], "generated": generated}

            # After a response contains an image, persistence errors are terminal:
            # the image must never be silently rerolled.
            try:
                image_bytes = base64.b64decode(data[0].b64_json, validate=True)
            except (ValueError, base64.binascii.Error) as exc:
                image_bytes = b""
            valid_raster = (
                len(image_bytes) >= 24
                and image_bytes.startswith(b"\x89PNG\r\n\x1a\n")
                and image_bytes[12:16] == b"IHDR"
                and struct.unpack(">II", image_bytes[16:24]) == (1024, 1536)
            )
            if not valid_raster:
                append_attempt_event(output, {
                    "event": "protocol_failure", "attempt_number": attempt_number,
                    "at_utc": _now(), "provider_request_id": getattr(response, "_request_id", None),
                    "error": "API response did not contain a decodable PNG raster",
                })
                output["status"] = "failed"
                output["error"] = "API response did not contain a decodable PNG raster"
                _write_receipt(root, run, variant, output, slot["position"])
                run["status"] = "incomplete"
                _save_run(path, run)
                return {"run_id": run["run_id"], "status": "incomplete", "stopped_slot": output["blind_id"], "generated": generated}
            image_path = root / "outputs" / f"{output['blind_id']}.png"
            image_path.parent.mkdir(parents=True, exist_ok=True)
            with image_path.open("xb") as handle:
                handle.write(image_bytes)
            image_hash = sha256_file(image_path)
            provider = _provider_details(response)
            metadata_name = f"{output['blind_id']}.json"
            _write_json_new(root / "outputs" / metadata_name, {
                "run_id": run["run_id"], "slot_id": output["blind_id"],
                "slot_position": slot["position"], "attempt_number": attempt_number,
                "prompt_sha256": variant["prompt_sha256"], "fixture_sha256": run["fixture_sha256"],
                "definition_sha256": run["experiment_definition_sha256"],
                "requested_model": run["model"], "recorded_model_snapshot": run["model_snapshot"],
                "settings": run["settings"], "reference_inputs": [], "provider_response": provider,
                "image_sha256": image_hash, "received_at_utc": _now(),
            })
            append_attempt_event(output, {
                "event": "success", "attempt_number": attempt_number, "at_utc": _now(),
                "prompt_sha256": variant["prompt_sha256"], "image_sha256": image_hash,
                "provider_response": provider,
            })
            output.update(status="generated", image=image_path.name,
                          image_sha256=image_hash, metadata=metadata_name,
                          metadata_sha256=sha256_file(root / "outputs" / metadata_name), error=None)
            _write_receipt(root, run, variant, output, slot["position"])
            _save_run(path, run)
            generated += 1
            break

    run["status"] = "completed"
    _save_run(path, run)
    return {"run_id": run["run_id"], "status": "completed", "generated": generated}
