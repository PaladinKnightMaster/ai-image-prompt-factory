"""Validate the text-only, same-session host metadata sidecar for EXP-019 v1.1.1."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from jsonschema import Draft202012Validator

from .io import load_json


SCHEMA_PATH = "data/schemas/exp019_host_session_metadata.schema.json"
TIMESTAMP_FIELDS = ("invoked_at_utc", "generation_completed_at_utc")
QUERY_ATTESTATION = {
    "same_generation_conversation": True,
    "text_only_query": True,
    "no_additional_image_generation": True,
}


def _timestamp(value: str) -> None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValueError("EXP-019 observed host timestamp is not ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("EXP-019 observed host timestamp requires a timezone")


def load_host_session_metadata(path: str | Path) -> dict:
    source = Path(path).expanduser().resolve(strict=True)
    if source.suffix.lower() != ".json":
        raise ValueError("EXP-019 host-session metadata sidecar must be JSON")
    sidecar = json.loads(source.read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(load_json(SCHEMA_PATH)).iter_errors(sidecar))
    if errors:
        raise ValueError("EXP-019 host-session metadata sidecar schema invalid")
    for field in TIMESTAMP_FIELDS:
        if sidecar[field + "_status"] == "observed":
            _timestamp(sidecar[field])
    return sidecar


def validate_receipt_observation_fields(receipt: dict) -> None:
    for field in ("invoked_at_utc", "generation_completed_at_utc",
                  "provider_generation_id", "backend_snapshot"):
        status = receipt.get(field + "_status")
        value = receipt.get(field)
        if status == "not_observable":
            if value is not None:
                raise ValueError("EXP-019 unavailable host field must be null")
        elif status == "observed":
            if not isinstance(value, str) or not value.strip():
                raise ValueError("EXP-019 observed host field requires a value")
            if field in TIMESTAMP_FIELDS:
                _timestamp(value)
        else:
            raise ValueError("EXP-019 host observation status must be observed or not_observable")


def bind_sidecar_to_receipt(sidecar: dict, receipt: dict, *, image_present: bool) -> None:
    """Keep direct host observations distinct from operator/protocol declarations."""
    if receipt.get("metadata_query_attestation") != QUERY_ATTESTATION:
        raise ValueError("EXP-019 same-session text-only metadata attestation incomplete")
    pairs = (
        ("invoked_at_utc", "invoked_at_utc"),
        ("generation_completed_at_utc", "generation_completed_at_utc"),
        ("generation_id", "provider_generation_id"),
        ("backend_model_snapshot", "backend_snapshot"),
    )
    for host_field, receipt_field in pairs:
        if (receipt.get(receipt_field) != sidecar[host_field]
                or receipt.get(receipt_field + "_status") != sidecar[host_field + "_status"]):
            raise ValueError("EXP-019 operator receipt differs from host-session observation")
    for host_field, expected in (
        ("reference_image_count", 0),
        ("requested_output_count", 1),
        ("returned_output_count", receipt["host_returned_output_count"]),
    ):
        if sidecar[host_field + "_status"] == "observed" and sidecar[host_field] != expected:
            raise ValueError("EXP-019 host-session output/reference count mismatch")
    if (sidecar["edit_or_regeneration_used_status"] == "observed"
            and sidecar["edit_or_regeneration_used"] is not False):
        raise ValueError("EXP-019 host session reports an edit or regeneration")
    if image_present and receipt["host_returned_output_count"] != 1:
        raise ValueError("EXP-019 successful host request must return exactly one image")
