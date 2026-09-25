"""Host-native EXP-019 v1.1 attempt capture around the shared frozen plan."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from PIL import Image

from .exp019_protocol import append_attempt_event, find_slot, validate_run
from .experiment_runs import sha256_file


ATTESTATIONS = (
    "fresh_chat", "exact_prompt_unchanged", "zero_uploaded_images",
    "zero_reference_images", "no_prior_exp019_prompt", "no_prior_exp019_output",
    "no_edit", "no_follow_up_repair", "one_generation_request",
)
RECEIPT_DIR = Path("provenance-freeze/execution-receipts")
RUN_RECEIPT = Path("provenance-freeze/EXP-019.provenance-ledger.json")


def _write_new(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _timestamp(value: str) -> None:
    if not isinstance(value, str):
        raise ValueError("host attempt requires an operator invocation timestamp")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("host attempt timestamp requires timezone")


def _raster(source: Path) -> dict:
    with Image.open(source) as image:
        image.verify()
    with Image.open(source) as image:
        image.load()
        if image.format not in {"PNG", "JPEG", "WEBP"}:
            raise ValueError("host output must be a fully decodable PNG, JPEG, or WEBP")
        has_alpha = "A" in image.getbands() or "transparency" in image.info
        return {"width": image.width, "height": image.height,
                "format": image.format, "has_alpha": has_alpha,
                "opaque": not has_alpha or image.convert("RGBA").getchannel("A").getextrema() == (255, 255)}


def _receipt_payload(path: Path, run: dict, slot: dict, variant: dict, attempt: int,
                     image_hash: str | None, failure: str | None) -> dict:
    receipt = json.loads(path.read_text(encoding="utf-8"))
    expected = {"experiment_id": "EXP-019", "experiment_version": "1.1.0",
                "run_id": run["run_id"], "slot_id": slot["blind_id"],
                "attempt_number": attempt, "prompt_sha256": variant["prompt_sha256"],
                "generation_mode": "host_native", "host_product": "ChatGPT Images",
                "reference_count": 0, "requested_aspect_ratio": "2:3",
                "requested_dimensions": None, "generation_request_count": 1,
                "output_count": 1 if image_hash else 0,
                "outcome": failure or "success", "output_sha256": image_hash}
    if any(receipt.get(k) != v for k, v in expected.items()):
        raise ValueError("EXP-019 host attempt differs from frozen slot or invocation")
    if receipt.get("fresh_chat_attestation") != {name: True for name in ATTESTATIONS}:
        raise ValueError("EXP-019 fresh-conversation attestation incomplete")
    returned = receipt.get("host_returned_output_count")
    if (type(returned) is not int or returned < 0
            or (image_hash is not None and returned != 1)
            or (failure != "protocol_failure" and image_hash is None and returned != 0)):
        raise ValueError("EXP-019 host return count is invalid; multiple candidates cannot be selected")
    _timestamp(receipt.get("invoked_at_utc"))
    if receipt.get("backend_snapshot", "unknown") != "unknown" and not receipt.get("backend_snapshot_exposed_by_host"):
        raise ValueError("EXP-019 backend snapshot cannot be inferred")
    if receipt.get("provider_generation_id") is not None and not receipt.get("provider_id_exposed_by_host"):
        raise ValueError("EXP-019 provider ID cannot be inferred")
    if receipt.get("api_request_metadata") is not None:
        raise ValueError("EXP-019 host-native attempt has no API request metadata")
    return receipt


def export_host_package(run_file: str | Path, *, output: str | Path | None = None) -> dict:
    """Anchor the run before releasing ordered, treatment-opaque tasks."""
    from .experiment_execution import load_run
    from .exp019_anchor import ensure_run_root
    path, run = load_run(run_file)
    if run["experiment_version"] != "1.1.0" or run["status"] != "planned":
        raise ValueError("EXP-019 host export requires a fresh v1.1.0 plan")
    root = path.parent
    destination = root / "packages" / "generation-inputs"
    if output is not None and Path(output).expanduser().resolve() != destination.resolve():
        raise ValueError("EXP-019 generation package must use its private canonical path")
    ensure_run_root(path, run)
    if destination.exists():
        raise FileExistsError(destination)
    destination.mkdir(parents=True)
    templates = destination / "operator-receipt-templates"
    templates.mkdir()
    tasks = []
    for slot in run["invocation_order"]:
        variant, _item = find_slot(run, slot["blind_id"])
        prompt = variant["prompt"]
        prompt_path = root / "generation-inputs" / "prompts" / f"{slot['blind_id']}.txt"
        if not prompt_path.is_file() or prompt_path.read_bytes() != prompt.encode("utf-8"):
            raise ValueError("EXP-019 exported prompt bytes differ from frozen plan")
        tasks.append({"ordinal": slot["position"], "opaque_slot_id": slot["blind_id"],
                      "prompt": prompt, "prompt_sha256": variant["prompt_sha256"],
                      "host_product": "ChatGPT Images", "requested_aspect_ratio": "2:3",
                      "reference_count": 0, "requested_outputs": 1,
                      "operator_receipt_template": f"operator-receipt-templates/{slot['blind_id']}.json"})
        _write_new(templates / f"{slot['blind_id']}.json", {
            "experiment_id": "EXP-019", "experiment_version": "1.1.0", "run_id": run["run_id"],
            "slot_id": slot["blind_id"], "attempt_number": 1, "prompt_sha256": variant["prompt_sha256"],
            "generation_mode": "host_native", "host_product": "ChatGPT Images",
            "observed_host_label": None, "backend_snapshot": "unknown", "provider_generation_id": None,
            "reference_count": 0, "requested_aspect_ratio": "2:3", "requested_dimensions": None,
            "generation_request_count": 1, "host_returned_output_count": None,
            "output_count": None, "outcome": None, "output_sha256": None,
            "fresh_chat_attestation": {name: False for name in ATTESTATIONS},
            "invoked_at_utc": None, "api_request_metadata": None,
        })
    _write_new(destination / "manifest.json", {"experiment_id": "EXP-019",
               "experiment_version": "1.1.0", "tasks": tasks})
    (destination / "README.md").write_text(
        "Use a fresh ChatGPT Images conversation for each task, in manifest order. "
        "Paste only its exact prompt. Upload no images; do not edit, repair, or reroll a decodable result. "
        "Keep this generation package away from reviewers.\n", encoding="utf-8")
    return {"run_id": run["run_id"], "task_count": 12, "reference_count": 0,
            "output": str(destination), "manifest": str(destination / "manifest.json")}


def _next_slot(run: dict) -> tuple[dict, dict, dict]:
    for slot in run["invocation_order"]:
        variant, output = find_slot(run, slot["blind_id"])
        if output["status"] == "generated":
            continue
        events = output["attempt_events"]
        outcomes = events[1::2]
        if outcomes and (outcomes[-1]["event"] != "technical_failure" or len(outcomes) >= 3):
            raise ValueError("EXP-019 run stopped at a terminal attempt")
        if len(events) % 2:
            raise ValueError("EXP-019 unresolved host attempt")
        return slot, variant, output
    raise ValueError("EXP-019 run already completed")


def verify_host_attempts(root: Path, run: dict, output: dict, position: int) -> None:
    """Rebind every host receipt and raster to the append-only ledger."""
    variant, _ = find_slot(run, output["blind_id"])
    history = output.get("receipt_history", [])
    events = output["attempt_events"]
    if len(history) != len(events) // 2:
        raise ValueError("EXP-019 host attempt history incomplete")
    for index, binding in enumerate(history, 1):
        path = root / binding["file"]
        if not path.is_file() or sha256_file(path) != binding["sha256"]:
            raise ValueError("EXP-019 host attempt receipt changed")
        record = json.loads(path.read_text(encoding="utf-8"))
        operator_path = root / binding["operator_file"]
        if (not operator_path.is_file() or sha256_file(operator_path) != binding["operator_sha256"]
                or record.get("operator_receipt_sha256") != binding["operator_sha256"]):
            raise ValueError("EXP-019 host operator attestation changed")
        outcome = events[index * 2 - 1]
        _receipt_payload(operator_path, run,
                         next(s for s in run["invocation_order"] if s["blind_id"] == output["blind_id"]),
                         variant, index, outcome.get("image_sha256"),
                         None if outcome["event"] == "success" else outcome["event"])
        if (record.get("experiment_id") != "EXP-019" or record.get("experiment_version") != "1.1.0"
                or record.get("run_id") != run["run_id"]
                or record.get("slot_id") != output["blind_id"] or record.get("slot_position") != position
                or record.get("prompt_sha256") != variant["prompt_sha256"]
                or record.get("attempt_events") != events[:index * 2]
                or record.get("output_image_sha256") != outcome.get("image_sha256")
                or record.get("attempt_number") != index
                or record.get("status") != ("generated" if outcome["event"] == "success" else "failed")):
            raise ValueError("EXP-019 host receipt differs from attempt ledger")
        if outcome["event"] == "success":
            metadata_path = root / "outputs" / str(output.get("metadata"))
            if (record.get("output_metadata_sha256") != output.get("metadata_sha256")
                    or record.get("imported_raster_path") != (Path("outputs") / str(output.get("image"))).as_posix()
                    or not metadata_path.is_file() or record.get("actual_raster") != json.loads(metadata_path.read_text(encoding="utf-8")).get("actual_raster")):
                raise ValueError("EXP-019 host metadata binding differs")
    if output["status"] == "generated":
        image = root / "outputs" / str(output.get("image"))
        metadata = root / "outputs" / str(output.get("metadata"))
        if (not image.is_file() or sha256_file(image) != output.get("image_sha256")
                or not metadata.is_file() or sha256_file(metadata) != output.get("metadata_sha256")):
            raise ValueError("EXP-019 host output or metadata changed")


def host_receipt_from_run(run: dict, root: Path) -> dict:
    """Derive the private terminal ledger from run state and externally anchored evidence."""
    from .exp019_anchor import run_receipt_provenance
    validate_run(run)
    slots = []
    stopped = False
    for slot in run["invocation_order"]:
        variant, output = find_slot(run, slot["blind_id"])
        verify_host_attempts(root, run, output, slot["position"])
        events = output["attempt_events"]
        if len(events) % 2 or (stopped and events):
            raise ValueError("EXP-019 host ledger has unresolved or post-terminal attempt")
        outcomes = events[1::2]
        last = outcomes[-1]["event"] if outcomes else None
        if output["status"] == "generated":
            if last != "success" or output["image_sha256"] != outcomes[-1]["image_sha256"]:
                raise ValueError("EXP-019 host generated slot mismatch")
        elif output["status"] == "failed":
            if last not in {"technical_failure", "safety_refusal", "provider_failure", "protocol_failure"}:
                raise ValueError("EXP-019 host failed slot mismatch")
            stopped = last != "technical_failure" or len(outcomes) == 3
            if not stopped:
                raise ValueError("EXP-019 host receipt requires terminal state")
        elif output["status"] != "planned" or events:
            raise ValueError("EXP-019 host slot state mismatch")
        slots.append({"position": slot["position"], "slot_id": slot["blind_id"],
                      "condition": slot["variant_id"], "replicate": slot["replicate"],
                      "prompt_sha256": variant["prompt_sha256"], "status": output["status"],
                      "attempt_events": events, "receipt_history": output.get("receipt_history", []),
                      "output_image_sha256": output.get("image_sha256"),
                      "output_metadata_sha256": output.get("metadata_sha256")})
    derived = "completed" if all(s["status"] == "generated" for s in slots) else "incomplete" if stopped else None
    if derived is None or run["status"] != derived:
        raise ValueError("EXP-019 host terminal status differs from attempt ledger")
    from .exp019_protocol import _canonical_sha256
    core = {"schema_version": "1.1.0", "experiment_id": "EXP-019", "experiment_version": "1.1.0",
            "run_id": run["run_id"], "definition_sha256": run["experiment_definition_sha256"],
            "fixture_sha256": run["fixture_sha256"], "plan_commitment_sha256": run["plan_commitment_sha256"],
            "generation_mode": "host_native", "host_product": "ChatGPT Images",
            "backend_snapshot": "unknown", "settings": run["settings"], "reference_inputs": [],
            "ordered_slots": slots, "derived_run_status": derived,
            "external_provenance": run_receipt_provenance(root / "run-private.json", run)}
    return {**core, "evidence_sha256": _canonical_sha256(core)}


def record_attempt(run_file: str | Path, *, blind_id: str, receipt: str | Path,
                   image: str | Path | None = None, failure: str | None = None) -> dict:
    from .experiment_execution import _write_json_atomic, load_run
    from .exp019_anchor import append_attempt_checkpoint, verify_external
    from .exp019_receipt import write_run_receipt
    path, run = load_run(run_file)
    if run["experiment_version"] != "1.1.0":
        raise ValueError("host attempt requires EXP-019 v1.1.0")
    verify_external(path, run)
    slot, variant, output = _next_slot(run)
    if blind_id != slot["blind_id"]:
        raise ValueError("EXP-019 host attempt violates frozen invocation order")
    if failure not in {None, "technical_failure", "safety_refusal", "provider_failure", "protocol_failure"}:
        raise ValueError("EXP-019 invalid host failure type")
    if (image is None) == (failure is None):
        raise ValueError("provide exactly one image or one classified failure")
    root = path.parent
    verify_host_attempts(root, run, output, slot["position"])
    source = Path(image).expanduser().resolve() if image is not None else None
    raster = _raster(source) if source else None
    image_hash = sha256_file(source) if source else None
    attempt = len(output["attempt_events"]) // 2 + 1
    operator_receipt = _receipt_payload(Path(receipt).expanduser().resolve(), run, slot, variant,
                                        attempt, image_hash, failure)
    started = {"event": "started", "attempt_number": attempt,
               "at_utc": operator_receipt["invoked_at_utc"], "prompt_sha256": variant["prompt_sha256"]}
    append_attempt_event(output, started)
    outcome = {"event": failure or "success", "attempt_number": attempt,
               "at_utc": operator_receipt["invoked_at_utc"], "prompt_sha256": variant["prompt_sha256"],
               "image_sha256": image_hash, "host_product": "ChatGPT Images",
               "backend_snapshot": operator_receipt.get("backend_snapshot", "unknown"),
               "provider_generation_id": operator_receipt.get("provider_generation_id")}
    append_attempt_event(output, outcome)
    if source:
        ext = {"PNG": ".png", "JPEG": ".jpg", "WEBP": ".webp"}[raster["format"]]
        image_path = root / "outputs" / f"{blind_id}{ext}"
        image_path.parent.mkdir(parents=True, exist_ok=True)
        with image_path.open("xb") as handle:
            handle.write(source.read_bytes())
        if sha256_file(image_path) != image_hash:
            raise ValueError("EXP-019 imported raster hash changed")
        metadata_path = root / "outputs" / "metadata" / f"{blind_id}.json"
        metadata = {"slot_id": blind_id, "attempt_number": attempt,
                    "prompt_sha256": variant["prompt_sha256"], "image_sha256": image_hash,
                    "actual_raster": raster, "imported_at_utc": datetime.now().astimezone().isoformat(),
                    "host_product": "ChatGPT Images", "backend_snapshot": outcome["backend_snapshot"],
                    "provider_generation_id": outcome["provider_generation_id"]}
        _write_new(metadata_path, metadata)
        output.update(status="generated", image=image_path.name, image_sha256=image_hash,
                      metadata=f"metadata/{metadata_path.name}", metadata_sha256=sha256_file(metadata_path), error=None)
    else:
        output.update(status="failed", error=operator_receipt.get("failure_detail"))
    operator_path = root / RECEIPT_DIR / f"{blind_id}.attempt-{attempt}.operator.json"
    _write_new(operator_path, operator_receipt)
    record = {"experiment_id": "EXP-019", "experiment_version": "1.1.0",
              "run_id": run["run_id"], "slot_id": blind_id, "slot_position": slot["position"],
              "attempt_number": attempt, "prompt_sha256": variant["prompt_sha256"],
              "operator_receipt_sha256": sha256_file(operator_path),
              "attempt_events": output["attempt_events"], "output_image_sha256": image_hash,
              "output_metadata_sha256": output.get("metadata_sha256"),
              "imported_raster_path": image_path.relative_to(root).as_posix() if source else None,
              "imported_at_utc": metadata["imported_at_utc"] if source else None,
              "actual_raster": raster, "status": output["status"]}
    canonical_path = root / RECEIPT_DIR / f"{blind_id}.attempt-{attempt}.receipt.json"
    _write_new(canonical_path, record)
    output.setdefault("receipt_history", []).append({"file": canonical_path.relative_to(root).as_posix(),
                                                       "sha256": sha256_file(canonical_path),
                                                       "operator_file": operator_path.relative_to(root).as_posix(),
                                                       "operator_sha256": sha256_file(operator_path)})
    run["status"] = ("completed" if all(o["status"] == "generated" for v in run["variants"] for o in v["outputs"])
                     else "incomplete" if failure is not None and (failure != "technical_failure" or attempt == 3)
                     else "partial")
    _write_json_atomic(path, run)
    append_attempt_checkpoint(path, run, blind_id, attempt)
    if run["status"] in {"completed", "incomplete"}:
        write_run_receipt(path, run)
    return {"run_id": run["run_id"], "slot_id": blind_id, "attempt_number": attempt,
            "status": run["status"], "image_sha256": image_hash}
