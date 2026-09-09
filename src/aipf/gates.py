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


def art_craft_gate(spec: dict) -> list[dict]:
    findings=[]
    art=spec.get("art", {})
    mid=art.get("method")
    form=art.get("artifact_form")
    state=art.get("artifact_state")
    if not mid:
        if form or state:
            findings.append({"level":"error","code":"artifact_without_method","message":"Artifact form/state is set but no art method is selected."})
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
    return findings
