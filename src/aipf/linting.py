from __future__ import annotations
import re
from jsonschema import Draft202012Validator
from .io import load_json
from .gates import temporal_cultural_gate, art_craft_gate
from .evidence import select_evidence
from .compatibility import audit_compatibility


def _finding(level, code, message):
    return {"level":level,"code":code,"message":message}


def lint_spec(spec: dict) -> list[dict]:
    out=[]
    schema=load_json("data/schemas/request.schema.json")
    for e in sorted(Draft202012Validator(schema).iter_errors(spec), key=lambda x:list(x.path)):
        loc=".".join(str(x) for x in e.path) or "$"
        out.append(_finding("error","schema",f"{loc}: {e.message}"))
    if out:
        return out
    out.extend(temporal_cultural_gate(spec))
    out.extend(art_craft_gate(spec))
    text=spec.get("request","").casefold()
    if re.search(r"\b(8k|16k|32k)\b", text):
        out.append(_finding("info","resolution_hype","Resolution hype is low-signal unless tied to actual export requirements."))
    if any(x in text for x in ["90-60-90","perfect body","ideal body","flawless body"]):
        out.append(_finding("warning","body_measurement_ideal","Replace universal/numeric body ideals with explicit user-requested characteristics, garment silhouette, pose, or presentation."))
    if "flawless skin" in text or "perfect skin" in text:
        out.append(_finding("warning","flawless_skin","Prefer a specified retouching level with realistic skin texture."))
    if any(x in text for x in ["make face slimmer","sharpen jaw","smaller face"]) and spec.get("body_transformation",{}).get("mode") == "preserve":
        out.append(_finding("warning","unrequested_face_reshape","Face reshape language conflicts with preserve mode unless explicitly requested."))
    age_match=re.search(r"\b(1[0-7])[- ]?year[- ]?old\b", text)
    sexual=any(x in text for x in ["seductive","sexy","lingerie","bikini","cleavage","sensual"])
    if age_match and sexual:
        out.append(_finding("error","age_sexualization","Sexualized framing involving a minor is not supported."))
    refs=spec.get("references",[])
    for r in refs:
        if not r.get("roles"):
            out.append(_finding("error","missing_reference_role",f"Reference {r.get('id')} has no role."))
    if "wuxia" in spec.get("historical",{}).get("packs",[]) and len(spec.get("historical",{}).get("packs",[]))==1:
        out.append(_finding("error","genre_as_era","Wuxia needs a historical base pack or an explicit fictional setting."))
    # Evidence-backed compatibility is diagnostic, not a second hidden source of user requirements.
    try:
        audit=audit_compatibility(spec,select_evidence(spec))
        for d in audit.get("decisions",[]):
            if d["status"] in {"adapt","reject"}:
                out.append(_finding("warning","historical_evidence_conflict",f"{d['claim_id']}: {d['instruction']}"))
            elif d["status"]=="qualify" and d["compatibility"] in {"rare","unknown","interpretive","anachronistic"}:
                out.append(_finding("info","historical_evidence_qualification",f"{d['claim_id']}: {d['instruction']}"))
    except Exception as e:
        out.append(_finding("warning","evidence_retrieval_failure",f"Evidence retrieval could not complete: {e}"))
    return out


def lint_prompt(prompt: str) -> list[dict]:
    out=[]; low=prompt.casefold()
    if len(re.findall(r"\b(masterpiece|best quality|8k|16k|ultra[- ]?hd)\b", low)) >= 3:
        out.append(_finding("warning","quality_keyword_stack","Multiple low-signal quality keywords are stacked; replace them with visible requirements."))
    if low.count("avoid ") + low.count("no ") > 14:
        out.append(_finding("warning","negative_prompt_bloat","Too many negative constraints; keep only likely failure modes."))
    if "selfie" in low and re.search(r"\b(85mm|105mm|135mm)\b", low):
        out.append(_finding("warning","camera_contradiction_selfie","Arm-length selfie perspective conflicts with strongly compressed telephoto language unless a remote camera is explained."))
    return out
