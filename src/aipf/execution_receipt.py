from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from .experiment_runs import sha256_file

RECEIPT_SCHEMA_VERSION = "1.0.0"
TASK_COMMITMENT_SCHEMA_VERSION = "1.0.0"


def receipt_required(run: dict) -> bool:
    provenance = run.get("execution_provenance") or {}
    if not isinstance(provenance, dict):
        raise ValueError("execution_provenance must be an object")
    return bool(provenance.get("receipt_required", False))


def normalized_reference_inputs(run: dict) -> list[dict]:
    result: list[dict] = []
    for reference in run.get("reference_inputs") or []:
        result.append(
            {
                "slot": reference["slot"],
                "role": reference["role"],
                "fixture_id": reference["fixture_id"],
                "fixture_version": reference["fixture_version"],
                "fixture_sha256": str(reference["fixture_sha256"]).lower(),
            }
        )
    return result


def task_commitment_payload(run: dict, variant: dict, output: dict) -> dict:
    return {
        "schema_version": TASK_COMMITMENT_SCHEMA_VERSION,
        "run_id": run["run_id"],
        "experiment_id": run["experiment_id"],
        "experiment_version": run["experiment_version"],
        "blind_id": output["blind_id"],
        "replicate": output["replicate"],
        "prompt_sha256": variant["prompt_sha256"],
        "reference_inputs": normalized_reference_inputs(run),
        "generation_mode": run["generation_mode"],
        "model": run["model"],
        "model_snapshot": run["model_snapshot"],
        "settings": {
            "size": run["settings"]["size"],
            "quality": run["settings"]["quality"],
            "background": run["settings"].get("background"),
        },
    }


def canonical_sha256(payload: dict) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def task_commitment_sha256(run: dict, variant: dict, output: dict) -> str:
    return canonical_sha256(task_commitment_payload(run, variant, output))


def receipt_template(
    run: dict,
    variant: dict,
    output: dict,
    *,
    provider: str = "chatgpt",
) -> dict:
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "run_id": run["run_id"],
        "blind_id": output["blind_id"],
        "task_commitment_sha256": task_commitment_sha256(
            run, variant, output
        ),
        "prompt_sha256": variant["prompt_sha256"],
        "reference_inputs": normalized_reference_inputs(run),
        "generation_mode": run["generation_mode"],
        "provider": provider,
        "model": run["model"],
        "model_snapshot": run["model_snapshot"],
        "settings": {
            "size": run["settings"]["size"],
            "quality": run["settings"]["quality"],
            "background": run["settings"].get("background"),
        },
        "invocation": {
            "mode": "single_sample",
            "host_generation_id": "",
            "generated_at_utc": "",
            "image_count": 1,
        },
        "image_sha256": "",
    }


def _normalize_receipt_references(value) -> list[dict]:
    if not isinstance(value, list):
        raise ValueError(
            "execution receipt reference_inputs must be an array"
        )

    required = (
        "slot",
        "role",
        "fixture_id",
        "fixture_version",
        "fixture_sha256",
    )
    normalized: list[dict] = []

    for item in value:
        if not isinstance(item, dict):
            raise ValueError(
                "execution receipt reference input must be an object"
            )
        missing = [key for key in required if not item.get(key)]
        if missing:
            raise ValueError(
                "execution receipt reference input is missing: "
                + ", ".join(missing)
            )
        normalized.append(
            {
                "slot": item["slot"],
                "role": item["role"],
                "fixture_id": item["fixture_id"],
                "fixture_version": item["fixture_version"],
                "fixture_sha256": str(item["fixture_sha256"]).lower(),
            }
        )

    return normalized


def validate_execution_receipt(
    *,
    receipt: str | Path,
    run: dict,
    variant: dict,
    output: dict,
    image_sha256: str,
    provider: str,
    model: str,
    model_snapshot: str,
) -> tuple[Path, dict, str]:
    receipt_path = Path(receipt).expanduser().resolve()
    if not receipt_path.is_file():
        raise FileNotFoundError(receipt_path)

    try:
        payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("execution receipt is not valid JSON") from exc

    if not isinstance(payload, dict):
        raise ValueError("execution receipt must be an object")

    required = (
        "schema_version",
        "run_id",
        "blind_id",
        "task_commitment_sha256",
        "prompt_sha256",
        "reference_inputs",
        "generation_mode",
        "provider",
        "model",
        "model_snapshot",
        "settings",
        "invocation",
        "image_sha256",
    )
    missing = [key for key in required if key not in payload]
    if missing:
        raise ValueError(
            "execution receipt is missing required fields: "
            + ", ".join(missing)
        )

    provenance = run.get("execution_provenance") or {}
    expected_schema = provenance.get(
        "receipt_schema_version", RECEIPT_SCHEMA_VERSION
    )

    if payload["schema_version"] != expected_schema:
        raise ValueError("execution receipt schema version mismatch")
    if payload["run_id"] != run["run_id"]:
        raise ValueError("execution receipt run_id mismatch")
    if str(payload["blind_id"]).upper() != str(output["blind_id"]).upper():
        raise ValueError("execution receipt blind_id mismatch")

    expected_commitment = task_commitment_sha256(run, variant, output)
    if str(payload["task_commitment_sha256"]).lower() != expected_commitment:
        raise ValueError("execution receipt task commitment mismatch")

    if str(payload["prompt_sha256"]).lower() != str(
        variant["prompt_sha256"]
    ).lower():
        raise ValueError("execution receipt prompt SHA-256 mismatch")

    if _normalize_receipt_references(
        payload["reference_inputs"]
    ) != normalized_reference_inputs(run):
        raise ValueError("execution receipt reference bindings mismatch")

    if payload["generation_mode"] != run["generation_mode"]:
        raise ValueError("execution receipt generation mode mismatch")
    if payload["provider"] != provider:
        raise ValueError("execution receipt provider mismatch")
    if payload["model"] != model:
        raise ValueError("execution receipt model mismatch")
    if payload["model_snapshot"] != model_snapshot:
        raise ValueError("execution receipt model snapshot mismatch")

    expected_settings = {
        "size": run["settings"]["size"],
        "quality": run["settings"]["quality"],
        "background": run["settings"].get("background"),
    }
    if payload["settings"] != expected_settings:
        raise ValueError("execution receipt settings mismatch")

    if str(payload["image_sha256"]).lower() != image_sha256.lower():
        raise ValueError("execution receipt image SHA-256 mismatch")

    invocation = payload["invocation"]
    if not isinstance(invocation, dict):
        raise ValueError("execution receipt invocation must be an object")
    if invocation.get("mode") != "single_sample":
        raise ValueError(
            "execution receipt invocation mode must be single_sample"
        )
    if invocation.get("image_count") != 1:
        raise ValueError("execution receipt image_count must equal 1")

    host_generation_id = str(
        invocation.get("host_generation_id", "")
    ).strip()
    if not host_generation_id:
        raise ValueError(
            "execution receipt host_generation_id must not be empty"
        )

    generated_at = str(invocation.get("generated_at_utc", "")).strip()
    if not generated_at:
        raise ValueError(
            "execution receipt generated_at_utc must not be empty"
        )
    try:
        parsed = datetime.fromisoformat(
            generated_at.replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise ValueError(
            "execution receipt generated_at_utc is not ISO-8601"
        ) from exc
    if parsed.tzinfo is None:
        raise ValueError(
            "execution receipt generated_at_utc must include timezone"
        )

    if provenance.get("unique_host_generation_id_required", True):
        for candidate_variant in run.get("variants", []):
            for candidate in candidate_variant.get("outputs", []):
                if candidate is output:
                    continue
                if candidate.get("host_generation_id") == host_generation_id:
                    raise ValueError(
                        "execution receipt host_generation_id already "
                        "used by another sample"
                    )

    return receipt_path, payload, sha256_file(receipt_path)
