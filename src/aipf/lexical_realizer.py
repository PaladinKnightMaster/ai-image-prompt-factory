"""Deterministic wording for concept IDs already accepted by semantic authorities."""
from __future__ import annotations

from .lexicon import concepts


PROFILES = {"compact", "descriptive", "historical_precision", "artifact_technical"}


def realize_concept(resolved: dict, profile: str, registry: dict[str, dict] | None = None, budget: int | None = None) -> tuple[str, dict, list[str]]:
    if profile not in PROFILES:
        raise ValueError(f"Unresolved lexical profile: {profile}")
    registry = registry if registry is not None else concepts()
    record = registry[resolved["concept_id"]]
    modifiers = resolved.get("resolved_modifiers", {})
    term = record["preferred_term"]
    if modifiers.get("material"):
        term = f"{modifiers['material']} {term}"
    required = f"{term}, {record['visible_gloss']}"
    atoms = modifiers.get("signature_atoms", [])
    for atom in atoms:
        if atom not in record.get("visual_signature", []):
            raise ValueError(f"Unresolved signature atom for {record['id']}: {atom}")
    count = {"compact": 0, "descriptive": 1, "historical_precision": 2, "artifact_technical": 2}[profile]
    applicable = [atom for atom in atoms if atom.casefold() not in required.casefold()]
    chosen = applicable[:count]
    if budget is not None:
        while chosen and len(required) + len("; ".join(chosen)) + 2 > budget:
            chosen.pop()
    realized = required + ("; " + "; ".join(chosen) if chosen else "")
    trace = {
        "concept_id": record["id"],
        "source_component": resolved["source_component"],
        "lexical_profile": profile,
        "preferred_term": record["preferred_term"],
        "realized_text": realized,
        "evidence_refs": resolved.get("evidence_refs", record["evidence_refs"]),
        "omitted_signature_atoms": [atom for atom in atoms if atom not in chosen and atom.casefold() not in required.casefold()],
    }
    return realized, trace, record.get("avoid_realizations", [])


def realize_concepts(resolved: list[dict], profile: str, budget: int | None = None) -> dict:
    registry = concepts()
    grouped: dict[str, list[str]] = {}
    trace = []
    avoid = []
    seen = set()
    unique = []
    for item in resolved:
        cid = item["concept_id"]
        if cid in seen:
            continue
        seen.add(cid)
        unique.append(item)
    minimum = {item["concept_id"]: realize_concept(item, "compact", registry)[0] for item in unique}
    optional_remaining = None if budget is None else max(0, budget - sum(len(text) + 2 for text in minimum.values()))
    for item in unique:
        cid = item["concept_id"]
        local_budget = None if optional_remaining is None else len(minimum[cid]) + optional_remaining
        text, row, anti_patterns = realize_concept(item, profile, registry, local_budget)
        if optional_remaining is not None:
            optional_remaining = max(0, optional_remaining - (len(text) - len(minimum[cid])))
        group = registry[cid].get("coalesce_group") or cid
        grouped.setdefault(group, []).append(text)
        trace.append(row)
        avoid.extend(anti_patterns)
    return {
        "clauses": ["; ".join(parts) + "." for parts in grouped.values()],
        "lexical_trace": trace,
        "avoid_realizations": list(dict.fromkeys(avoid)),
    }
