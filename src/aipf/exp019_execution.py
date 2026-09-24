"""Exact, fail-closed API execution for the frozen EXP-019 protocol."""
from __future__ import annotations

import base64
from io import BytesIO
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

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


def _finish_run(path: Path, run: dict, status: str) -> None:
    from .exp019_receipt import write_run_receipt

    run["status"] = status
    _save_run(path, run)
    write_run_receipt(path, run)


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


def _decoded_raster_format(image_bytes: bytes) -> str | None:
    """Read the entire raster; a plausible header is not an evaluable image."""
    try:
        with Image.open(BytesIO(image_bytes)) as image:
            image.verify()
        with Image.open(BytesIO(image_bytes)) as image:
            image.load()
            if image.size != (1024, 1536) or image.format not in {"PNG", "JPEG"}:
                return None
            return image.format
    except (OSError, ValueError, SyntaxError):
        return None


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
    receipt_hash = sha256_file(path)
    commitment_name = f"{output['blind_id']}.attempt-{number}.commitment.json"
    commitment_path = root / "receipts" / commitment_name
    _write_json_new(commitment_path, {
        "run_id": run["run_id"], "slot_id": output["blind_id"],
        "attempt_number": number, "plan_commitment_sha256": run["plan_commitment_sha256"],
        "event_chain_sha256": events[-1]["event_sha256"],
        "receipt_sha256": receipt_hash,
    })
    output.setdefault("receipt_history", []).append({
        "file": f"receipts/{name}", "sha256": receipt_hash,
        "commitment_file": f"receipts/{commitment_name}",
        "commitment_sha256": sha256_file(commitment_path),
    })


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


def _verify_prior_receipts(root: Path, run: dict, variant: dict, output: dict, position: int) -> None:
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
    commitment_names = {binding.get("commitment_file") for binding in history}
    existing_commitments = {f"receipts/{path.name}" for path in (root / "receipts").glob(
        f"{output['blind_id']}.attempt-*.commitment.json"
    )}
    if commitment_names != existing_commitments:
        raise ValueError("EXP-019 unbound or missing attempt commitment")
    for index, binding in enumerate(history, start=1):
        path = root / binding["file"]
        if not path.is_file() or sha256_file(path) != binding["sha256"]:
            raise ValueError("EXP-019 prior receipt hash mismatch")
        commitment_path = root / binding["commitment_file"]
        if not commitment_path.is_file() or sha256_file(commitment_path) != binding["commitment_sha256"]:
            raise ValueError("EXP-019 prior attempt commitment hash mismatch")
        commitment = json.loads(commitment_path.read_text(encoding="utf-8"))
        expected_commitment = {
            "run_id": run["run_id"], "slot_id": output["blind_id"],
            "attempt_number": index, "plan_commitment_sha256": run["plan_commitment_sha256"],
            "event_chain_sha256": output["attempt_events"][index * 2 - 1]["event_sha256"],
            "receipt_sha256": binding["sha256"],
        }
        if commitment != expected_commitment:
            raise ValueError("EXP-019 prior attempt commitment differs from ledger")
        receipt = json.loads(path.read_text(encoding="utf-8"))
        expected_events = output["attempt_events"][:index * 2]
        expected_outcome = expected_events[-1]["event"]
        if (receipt.get("run_id") != run["run_id"]
                or receipt.get("slot_id") != output["blind_id"]
                or receipt.get("slot_position") != position
                or receipt.get("plan_commitment_sha256") != run["plan_commitment_sha256"]
                or receipt.get("fixture_sha256") != run["fixture_sha256"]
                or receipt.get("definition_sha256") != run["experiment_definition_sha256"]
                or receipt.get("prompt_sha256") != variant["prompt_sha256"]
                or receipt.get("requested_model") != run["model"]
                or receipt.get("recorded_model_snapshot") != run["model_snapshot"]
                or receipt.get("settings") != run["settings"]
                or receipt.get("reference_inputs") != []
                or receipt.get("attempt_events") != expected_events
                or receipt.get("status") != ("generated" if expected_outcome == "success" else "failed")
                or receipt.get("output_image_sha256") != (
                    expected_events[-1].get("image_sha256") if expected_outcome == "success" else None
                )):
            raise ValueError("EXP-019 prior receipt differs from canonical attempt ledger")
    image_exists = any((root / "outputs" / f"{output['blind_id']}{suffix}").exists()
                       for suffix in (".png", ".jpg"))
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
        _verify_prior_receipts(root, run, variant, output, slot["position"])
        if output["status"] == "generated":
            if prior_outcome != "success":
                raise ValueError("EXP-019 generated slot has no successful attempt")
            image_path = root / "outputs" / str(output.get("image"))
            if not image_path.is_file() or sha256_file(image_path) != output.get("image_sha256"):
                raise ValueError("EXP-019 prior output image hash mismatch")
            continue
        if prior_outcome in {"safety_refusal", "provider_failure", "protocol_failure"} or prior_count >= 3:
            _finish_run(path, run, "incomplete")
            return {"run_id": run["run_id"], "status": "incomplete", "stopped_slot": output["blind_id"], "generated": generated}
        if prior_outcome not in {None, "technical_failure"}:
            raise ValueError("EXP-019 slot cannot be rerolled")

        for attempt_number in range(prior_count + 1, 4):
            if attempt_number > 1:
                _verify_prior_receipts(root, run, variant, output, slot["position"])
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
                    _finish_run(path, run, "incomplete")
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
                _finish_run(path, run, "incomplete")
                return {"run_id": run["run_id"], "status": "incomplete", "stopped_slot": output["blind_id"], "generated": generated}

            # After a response contains an image, persistence errors are terminal:
            # the image must never be silently rerolled.
            try:
                image_bytes = base64.b64decode(data[0].b64_json, validate=True)
            except (ValueError, base64.binascii.Error) as exc:
                image_bytes = b""
            decoded_format = _decoded_raster_format(image_bytes)
            if decoded_format is None:
                append_attempt_event(output, {
                    "event": "technical_failure", "attempt_number": attempt_number,
                    "at_utc": _now(), "provider_request_id": getattr(response, "_request_id", None),
                    "error": "API response did not contain a fully decodable 1024x1536 raster",
                })
                output["status"] = "failed"
                output["error"] = "API response did not contain a fully decodable 1024x1536 raster"
                _write_receipt(root, run, variant, output, slot["position"])
                if attempt_number == 3:
                    _finish_run(path, run, "incomplete")
                    return {"run_id": run["run_id"], "status": "incomplete", "stopped_slot": output["blind_id"], "generated": generated}
                _save_run(path, run)
                continue
            suffix = ".png" if decoded_format == "PNG" else ".jpg"
            image_path = root / "outputs" / f"{output['blind_id']}{suffix}"
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
                "decoded_format": decoded_format,
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

    _finish_run(path, run, "completed")
    return {"run_id": run["run_id"], "status": "completed", "generated": generated}
