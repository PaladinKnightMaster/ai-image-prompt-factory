"""Deterministic run-level receipt for the frozen EXP-019 execution ledger."""
from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from .exp019_protocol import _canonical_sha256, find_slot, validate_run
from .experiment_runs import sha256_file
from .io import load_json


RECEIPT_NAME = "exp019.run.receipt.json"


def _receipt_location(path: Path, run: dict) -> tuple[Path, str | None]:
    if run["experiment_version"] == "1.1.0":
        from .exp019_host import RUN_RECEIPT
        return path.parent / RUN_RECEIPT, "data/schemas/exp019_host_run_receipt.schema.json"
    return path.parent / "receipts" / RECEIPT_NAME, "data/schemas/exp019_run_receipt.schema.json"


def receipt_from_run(run: dict, root: Path) -> dict:
    """Derive evidence and completeness from the ledger, never from a caller's conclusion."""
    if run["experiment_version"] == "1.1.0":
        from .exp019_host import host_receipt_from_run
        return host_receipt_from_run(run, root)
    from .exp019_execution import _verify_prior_receipts
    from .exp019_anchor import run_receipt_provenance

    validate_run(run)
    slots = []
    terminal_failure_seen = False
    for position in run["invocation_order"]:
        variant, output = find_slot(run, position["blind_id"])
        _verify_prior_receipts(root, run, variant, output, position["position"])
        events = output["attempt_events"]
        if len(events) % 2:
            raise ValueError("EXP-019 run receipt requires resolved attempts")
        if terminal_failure_seen and events:
            raise ValueError("EXP-019 attempted a later slot after terminal failure")
        outcomes = [event for event in events if event["event"] != "started"]
        last = outcomes[-1]["event"] if outcomes else None
        if output["status"] == "generated":
            if last != "success" or output.get("image_sha256") != outcomes[-1].get("image_sha256"):
                raise ValueError("EXP-019 generated slot/attempt mismatch")
            image_path = root / "outputs" / str(output.get("image"))
            metadata_path = root / "outputs" / str(output.get("metadata"))
            if (not image_path.is_file() or sha256_file(image_path) != output["image_sha256"]
                    or not metadata_path.is_file() or sha256_file(metadata_path) != output.get("metadata_sha256")):
                raise ValueError("EXP-019 run receipt output or metadata hash mismatch")
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            expected_metadata = {
                "run_id": run["run_id"], "slot_id": output["blind_id"],
                "slot_position": position["position"],
                "attempt_number": outcomes[-1]["attempt_number"],
                "prompt_sha256": variant["prompt_sha256"],
                "fixture_sha256": run["fixture_sha256"],
                "definition_sha256": run["experiment_definition_sha256"],
                "requested_model": run["model"],
                "recorded_model_snapshot": run["model_snapshot"],
                "settings": run["settings"], "reference_inputs": [],
                "provider_response": outcomes[-1]["provider_response"],
                "image_sha256": output["image_sha256"],
            }
            if any(metadata.get(key) != value for key, value in expected_metadata.items()):
                raise ValueError("EXP-019 provider metadata differs from execution ledger")
            if not metadata.get("received_at_utc") or metadata.get("decoded_format") not in {"PNG", "JPEG"}:
                raise ValueError("EXP-019 provider metadata incomplete")
        elif output["status"] == "failed":
            if last not in {"technical_failure", "provider_failure", "protocol_failure", "safety_refusal"}:
                raise ValueError("EXP-019 failed slot lacks failure outcome")
            if last != "technical_failure" or len(outcomes) == 3:
                terminal_failure_seen = True
        elif output["status"] != "planned" or events:
            raise ValueError("EXP-019 run receipt has unresolved slot")
        slots.append({
            "position": position["position"], "slot_id": output["blind_id"],
            "condition": position["variant_id"], "replicate": position["replicate"],
            "prompt_sha256": variant["prompt_sha256"], "status": output["status"],
            "attempt_events": events, "receipt_history": output.get("receipt_history", []),
            "output_image_sha256": output.get("image_sha256"),
            "output_metadata_sha256": output.get("metadata_sha256"),
        })
    if all(slot["status"] == "generated" for slot in slots):
        derived_status = "completed"
    elif terminal_failure_seen:
        derived_status = "incomplete"
    else:
        raise ValueError("EXP-019 run receipt requires terminal run state")
    if run.get("status") != derived_status:
        raise ValueError("EXP-019 declared completeness disagrees with ledger")
    core = {
        "schema_version": "1.0.0", "experiment_id": "EXP-019",
        "experiment_version": "1.0.0", "run_id": run["run_id"],
        "definition_sha256": run["experiment_definition_sha256"],
        "fixture_sha256": run["fixture_sha256"],
        "plan_commitment_sha256": run["plan_commitment_sha256"],
        "requested_model": run["model"],
        "recorded_model_snapshot": run["model_snapshot"],
        "settings": run["settings"], "reference_inputs": [],
        "ordered_slots": slots, "derived_run_status": derived_status,
        "external_provenance": run_receipt_provenance(root / "run.json", run),
    }
    return {**core, "evidence_sha256": _canonical_sha256(core)}


def validate_run_receipt(run_file: str | Path, run: dict | None = None) -> dict:
    path = Path(run_file).expanduser().resolve()
    if run is None:
        from .experiment_execution import load_run
        _path, run = load_run(path)
    receipt_path, schema_name = _receipt_location(path, run)
    if not receipt_path.is_file():
        raise ValueError("EXP-019 run-level execution receipt missing")
    actual = json.loads(receipt_path.read_text(encoding="utf-8"))
    schema = load_json(schema_name)
    if list(Draft202012Validator(schema).iter_errors(actual)):
        raise ValueError("EXP-019 run-level receipt schema invalid")
    expected = receipt_from_run(run, path.parent)
    if actual != expected:
        raise ValueError("EXP-019 run-level receipt differs from canonical ledger")
    return actual


def write_run_receipt(run_file: str | Path, run: dict) -> dict:
    path = Path(run_file).expanduser().resolve()
    receipt = receipt_from_run(run, path.parent)
    destination, _schema_name = _receipt_location(path, run)
    if destination.exists():
        return validate_run_receipt(path, run)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(receipt, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return validate_run_receipt(path, run)
