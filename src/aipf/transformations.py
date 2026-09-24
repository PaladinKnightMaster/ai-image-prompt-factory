"""Data-driven representation changes. Historical and material authority live elsewhere."""
from __future__ import annotations

from .io import load_json


def transformation_packs() -> dict[str, dict]:
    registry = load_json("references/transformations/registry.json")
    return {row["id"]: load_json(row["path"]) for row in registry["packs"]}


def resolve_transformation(spec: dict) -> dict | None:
    request = spec.get("transformation")
    if not request:
        return None
    pack = transformation_packs()[request["pack_id"]]
    if request.get("source_representation", "portrait") != pack["source_representation"]:
        raise ValueError("Transformation source representation does not match the pack")
    return {
        "pack_id": pack["id"],
        "source_component": "transformation_pack",
        "source_representation": pack["source_representation"],
        "target_representation": pack["target_representation"],
        "representation_delta": dict(pack["representation_delta"]),
        "failure_modes": list(pack["failure_modes"]),
    }


def transformation_findings(spec: dict) -> list[dict]:
    request = spec.get("transformation")
    if not request:
        return []
    findings = []
    if request["pack_id"] not in transformation_packs():
        findings.append({"level": "error", "code": "unknown_transformation_pack", "message": f"Unknown transformation pack: {request['pack_id']}"})
    if not spec.get("art", {}).get("method") or not spec.get("art", {}).get("artifact_form"):
        findings.append({"level": "error", "code": "transformation_requires_artifact", "message": "V3.4 transformations require an explicit art method and artifact form."})
    return findings
