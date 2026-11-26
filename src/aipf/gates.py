from __future__ import annotations
from .io import load_json


def temporal_cultural_gate(spec: dict) -> list[dict]:
    findings = []
    hist = spec.get("historical", {})
    strictness = hist.get("strictness", "historically_informed")
    packs = hist.get("packs", [])
    registry = load_json("references/eras/registry.json")
    known = {x["id"]: x for x in registry["packs"]}
    loaded = []
    for pid in packs:
        if pid not in known:
            findings.append({"level":"error","code":"unknown_era_pack","message":f"Unknown era/site/overlay pack: {pid}"})
            continue
        p = load_json(known[pid]["path"])
        loaded.append(p)
    overlays = [p for p in loaded if p.get("pack_type") in {"genre_overlay", "fantasy_overlay"}]
    bases = [p for p in loaded if p.get("pack_type") in {"historical_era", "site_tradition"}]
    for p in overlays:
        if not bases and not hist.get("region"):
            findings.append({"level":"error","code":"genre_as_era","message":f"{p['name']} is an overlay, not a historical era; add a base setting or explicit fictional world."})
    if "dunhuang" in packs and strictness == "strict_reconstruction" and not hist.get("subperiod"):
        findings.append({"level":"error","code":"dunhuang_strict_narrowing","message":"Strict Dunhuang reconstruction requires a cave/subperiod or tightly bounded evidence family."})
    intentional = hist.get("intentional_hybrids", [])
    if intentional and strictness == "strict_reconstruction":
        findings.append({"level":"warning","code":"strict_hybrid_conflict","message":"Intentional hybrid declared under strict_reconstruction; consider historically_informed/period_drama/fantasy_hybrid."})
    return findings


_STATE_AWARE_REQUIRED_OVERLAY_STATES = (
    "in_period",
    "aged",
    "damaged",
    "excavated",
    "partially_restored",
    "museum_conserved",
)
_STATE_AWARE_NULL_OVERLAY_STATES = (
    "newly_created",
    "modern_reconstruction",
    "replica",
    "fantasy_artifact",
)


def art_method_emission_contract_gate(spec: dict) -> list[dict]:
    """Validate explicit ArtMethod emission-contract selection (CR-017).

    Absent selector means legacy and is not an error. Explicit state_aware_v1
    fails closed when capability, state, technique/overlays, or route are invalid.
    """
    findings = []
    art = spec.get("art") or {}
    if "art_method_emission_contract" not in art:
        return findings
    contract = art.get("art_method_emission_contract")
    # Null/invalid enum are primarily schema errors; still fail closed if reached.
    if contract is None:
        findings.append(
            {
                "level": "error",
                "code": "art_method_emission_contract_null",
                "message": "art_method_emission_contract must not be null; omit the field for legacy or set legacy|state_aware_v1.",
            }
        )
        return findings
    if contract not in {"legacy", "state_aware_v1"}:
        findings.append(
            {
                "level": "error",
                "code": "art_method_emission_contract_invalid",
                "message": f"Unknown art_method_emission_contract: {contract}",
            }
        )
        return findings
    if contract != "state_aware_v1":
        return findings

    if spec.get("transformation"):
        findings.append(
            {
                "level": "error",
                "code": "state_aware_incompatible_with_transformation",
                "message": "art_method_emission_contract=state_aware_v1 is incompatible with transformation routes.",
            }
        )
        return findings

    state = art.get("artifact_state")
    if "artifact_state" not in art or state is None:
        findings.append(
            {
                "level": "error",
                "code": "state_aware_requires_artifact_state",
                "message": "art_method_emission_contract=state_aware_v1 requires a non-null registry artifact_state.",
            }
        )
        return findings

    states = load_json("references/artifacts/states.json")["states"]
    if state not in states:
        findings.append(
            {
                "level": "error",
                "code": "unknown_artifact_state",
                "message": f"Unknown artifact state: {state}",
            }
        )
        return findings

    mid = art.get("method")
    if not mid:
        findings.append(
            {
                "level": "error",
                "code": "state_aware_requires_art_method",
                "message": "art_method_emission_contract=state_aware_v1 requires an art method.",
            }
        )
        return findings
    registry = load_json("references/art-methods/registry.json")
    known = {x["id"]: x for x in registry["methods"]}
    if mid not in known:
        findings.append(
            {
                "level": "error",
                "code": "unknown_art_method",
                "message": f"Unknown art method: {mid}",
            }
        )
        return findings
    method = load_json(known[mid]["path"])
    supported = method.get("supported_art_method_emission_contracts") or []
    if "state_aware_v1" not in supported:
        findings.append(
            {
                "level": "error",
                "code": "state_aware_pack_capability_missing",
                "message": f"{mid} does not declare supported_art_method_emission_contracts including state_aware_v1.",
            }
        )
        return findings

    technique = method.get("technique")
    if not isinstance(technique, dict) or any(
        not isinstance(technique.get(k), str) or not technique.get(k)
        for k in ("prompt_core", "surface", "edge")
    ):
        findings.append(
            {
                "level": "error",
                "code": "state_aware_technique_incomplete",
                "message": f"{mid} is missing required technique.prompt_core/surface/edge for state_aware_v1.",
            }
        )
        return findings

    overlays = method.get("condition_overlays")
    if not isinstance(overlays, dict):
        findings.append(
            {
                "level": "error",
                "code": "state_aware_overlays_malformed",
                "message": f"{mid} condition_overlays must be an object keyed by registry artifact states.",
            }
        )
        return findings
    required_keys = set(states)
    if set(overlays) != required_keys:
        findings.append(
            {
                "level": "error",
                "code": "state_aware_overlays_incomplete",
                "message": f"{mid} condition_overlays must include exactly the ten registry artifact states.",
            }
        )
        return findings
    for key in _STATE_AWARE_NULL_OVERLAY_STATES:
        val = overlays.get(key)
        # null or empty string permitted for fresh-like defaults
        if not (val is None or (isinstance(val, str) and not val.strip())):
            findings.append(
                {
                    "level": "error",
                    "code": "state_aware_fresh_overlay_not_null",
                    "message": f"{mid} condition_overlays.{key} must be null/empty for fresh-like defaults.",
                }
            )
    for key in _STATE_AWARE_REQUIRED_OVERLAY_STATES:
        val = overlays.get(key)
        if not isinstance(val, str) or not val.strip():
            findings.append(
                {
                    "level": "error",
                    "code": "state_aware_overlay_missing",
                    "message": f"{mid} condition_overlays.{key} must be a non-empty string for state_aware_v1.",
                }
            )
    return findings


def art_craft_gate(spec: dict) -> list[dict]:
    findings=[]
    art=spec.get("art", {})
    mid=art.get("method")
    form=art.get("artifact_form")
    state=art.get("artifact_state")
    if not mid:
        if form or state:
            findings.append({"level":"error","code":"artifact_without_method","message":"Artifact form/state is set but no art method is selected."})
        findings.extend(art_method_emission_contract_gate(spec))
        return findings
    registry=load_json("references/art-methods/registry.json")
    known={x["id"]:x for x in registry["methods"]}
    if mid not in known:
        return [{"level":"error","code":"unknown_art_method","message":f"Unknown art method: {mid}"}]
    method=load_json(known[mid]["path"])
    if form and form not in method.get("artifact_compatibility",[]):
        findings.append({"level":"error","code":"art_form_incompatible","message":f"{mid} does not declare compatibility with artifact form {form}."})
    if form:
        forms=load_json("references/artifacts/forms.json")["forms"]
        if form not in forms:
            findings.append({"level":"error","code":"unknown_artifact_form","message":f"Unknown artifact form: {form}"})
    if state:
        states=load_json("references/artifacts/states.json")["states"]
        if state not in states:
            findings.append({"level":"error","code":"unknown_artifact_state","message":f"Unknown artifact state: {state}"})
    findings.extend(art_method_emission_contract_gate(spec))
    return findings


def transformation_art_gate(spec: dict) -> list[dict]:
    """Compatibility authority for representation targets; packs do not choose methods."""
    request = spec.get("transformation")
    if not request:
        return []
    from .transformations import transformation_packs

    pack = transformation_packs().get(request["pack_id"])
    method_id = spec.get("art", {}).get("method")
    if not pack or not method_id:
        return []
    method_paths = {row["id"]: row["path"] for row in load_json("references/art-methods/registry.json")["methods"]}
    if method_id not in method_paths:
        return []
    family = load_json(method_paths[method_id])["family"]
    accepted = {
        "volumetric_sculpture": {"sculpture"},
        "architectural_mural": {"painting_on_wall"},
        "relief_print": {"printmaking"},
        "decorated_artifact": {"ceramic_decoration"},
    }
    if family not in accepted[pack["target_representation"]]:
        return [{"level": "error", "code": "transformation_method_incompatible", "message": f"{method_id} cannot realize {pack['target_representation']}."}]
    return []


def resolved_concept_plan(spec: dict, method_doc: dict, era_docs: list[dict], audit: dict) -> tuple[list[dict], list[dict]]:
    """Authorize concept IDs from selected semantic packs and explicit selections.

    Lexicon text and retrieval terms are not consulted for semantic selection.
    """
    if not spec.get("transformation"):
        return [], []
    from .lexicon import concepts

    records = concepts()
    refs: list[tuple[str, dict]] = [("art_method", method_doc.get("concept_refs", {}))]
    form_id = spec["art"].get("artifact_form")
    if form_id:
        form = load_json("references/artifacts/forms.json")["forms"].get(form_id, {})
        refs.append(("artifact_form", form.get("concept_refs", {})))
    refs.extend((f"era_pack:{pack['id']}", pack.get("concept_refs", {})) for pack in era_docs)
    core: dict[str, str] = {}
    conditional: dict[str, str] = {}
    for source, group in refs:
        for cid in group.get("core", []):
            core.setdefault(cid, source)
        for cid in group.get("conditional", []):
            conditional.setdefault(cid, source)
    request = spec["transformation"]
    selected = request.get("selected_concepts", [])
    findings = []
    authorized = dict(core)
    decisions = {d["claim_id"]: d for d in audit.get("decisions", [])}
    explicit_claims = set(spec.get("evidence", {}).get("claim_ids", []))
    for cid in selected:
        if cid not in core and cid not in conditional:
            findings.append({"level": "error", "code": "unavailable_concept", "message": f"{cid} is not available from the selected semantic packs."})
            continue
        if cid == "pose.contrapposto" and (form_id != "free_standing_statue" or not spec.get("director", {}).get("body_weight")):
            findings.append({"level": "error", "code": "pose_geometry_incompatible", "message": "Contrapposto requires a resolved standing artifact and weight-bearing pose."})
            continue
        if cid == "sculpture.polychromy" and ("classical_greek" not in spec["historical"]["packs"] or "greek-marble-polychromy-001" not in explicit_claims):
            findings.append({"level": "error", "code": "polychromy_unresolved", "message": "Polychromy requires explicit compatible historical evidence."})
            continue
        subperiod = (spec["historical"].get("subperiod") or "").casefold().replace("-", " ")
        if cid == "mural.pouncing_transfer" and ("dunhuang" not in spec["historical"]["packs"] or "mogao-pouncing-v34-001" not in explicit_claims or not any(token in subperiod for token in ("10th century", "tenth century"))):
            findings.append({"level": "error", "code": "pouncing_unresolved", "message": "Pouncing requires explicit context-bound transfer evidence."})
            continue
        claim_ids = records[cid].get("evidence_refs", {}).get("claim_ids", [])
        if any(claim_id in decisions and decisions[claim_id]["status"] in {"reject", "adapt"} for claim_id in claim_ids):
            findings.append({"level": "error", "code": "concept_evidence_rejected", "message": f"{cid} conflicts with the evidence gate."})
            continue
        authorized[cid] = core.get(cid) or conditional[cid]
    modifiers = request.get("signature_atoms", {})
    for cid, atoms in modifiers.items():
        if cid not in authorized:
            findings.append({"level": "error", "code": "unresolved_concept_modifier", "message": f"Signature atoms for unresolved concept {cid}."})
        elif any(atom not in records[cid].get("visual_signature", []) for atom in atoms):
            findings.append({"level": "error", "code": "unauthorized_signature_atom", "message": f"Signature atom not registered for {cid}."})
    resolved = []
    for cid, source in authorized.items():
        record = records[cid]
        resolved.append({
            "concept_id": cid,
            "source_component": source,
            "resolved_modifiers": {"signature_atoms": modifiers.get(cid, [])},
            "evidence_refs": record["evidence_refs"],
            "compatibility_status": "gated",
        })
    return resolved, findings
