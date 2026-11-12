"""PCC-02 Attribute Preservation/Change Contract (APCC) — slice 1.

Opt-in structured preserve/change validation and deterministic prompt emission.
Absent ``attribute_contract`` leaves the legacy compiler path unchanged.
"""
from __future__ import annotations

ATTRIBUTE_ORDER = ("identity.face", "wardrobe.garment")
SUPPORTED_ATTRIBUTES = frozenset(ATTRIBUTE_ORDER)
IDENTITY_INTENTS = frozenset({"preserve", "unconstrained"})
WARDROBE_INTENTS = frozenset({"preserve", "change", "unconstrained"})
ATTRIBUTE_ROLE = {
    "identity.face": "identity",
    "wardrobe.garment": "outfit",
}
COMPATIBLE_IDENTITY_MODES = frozenset({"strict_identity", "recognizable_identity"})
SUPPORTED_ROUTES = frozenset({"reference_transform"})
TEXT_TARGET_MAX_LEN = 500
OUTFIT_PRESERVE_LOCK_KEYS = frozenset({
    "preserve_source_outfit",
    "preserve_outfit",
    "forbid_wardrobe_change",
})


def _finding_local(level: str, code: str, message: str) -> dict:
    return {"level": level, "code": code, "message": message}


def _refs_by_id(spec: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for ref in spec.get("references") or []:
        rid = ref.get("id")
        if isinstance(rid, str) and rid:
            out[rid] = ref
    return out


def _normalized_rows(contract: dict) -> list[dict]:
    rows = list(contract.get("attributes") or [])
    # Stable emission / comparison order by ATTRIBUTE_ORDER; unknown kept last.
    rank = {name: i for i, name in enumerate(ATTRIBUTE_ORDER)}
    return sorted(rows, key=lambda r: (rank.get(r.get("attribute"), 999), str(r.get("attribute"))))


def attribute_contract_findings(spec: dict) -> list[dict]:
    """Return lint findings for an opt-in attribute_contract.

    Schema structural checks still run first in lint_spec. This function covers
    semantic ownership, intent legality, route/context, and typed conflicts.
    """
    contract = spec.get("attribute_contract")
    if contract is None:
        return []

    out: list[dict] = []
    if spec.get("version") != "3.5":
        out.append(_finding_local(
            "error",
            "attribute_contract_version",
            "attribute_contract requires request version 3.5.",
        ))
        return out

    if not isinstance(contract, dict):
        out.append(_finding_local(
            "error",
            "attribute_contract_shape",
            "attribute_contract must be an object.",
        ))
        return out

    rows = contract.get("attributes")
    if not isinstance(rows, list) or not rows:
        out.append(_finding_local(
            "error",
            "attribute_contract_shape",
            "attribute_contract.attributes must be a nonempty array.",
        ))
        return out

    # Slice-1 context gates (fail closed).
    if spec.get("route") not in SUPPORTED_ROUTES:
        out.append(_finding_local(
            "error",
            "attribute_unsupported_context",
            "PCC-02 attribute_contract supports route reference_transform only.",
        ))
    if spec.get("transformation"):
        out.append(_finding_local(
            "error",
            "attribute_unsupported_context",
            "PCC-02 attribute_contract does not support Representation TransformationPacks.",
        ))
    art = spec.get("art") or {}
    if art.get("method") or art.get("artifact_form") or art.get("artifact_state"):
        out.append(_finding_local(
            "error",
            "attribute_unsupported_context",
            "PCC-02 attribute_contract does not support art method/form/state transforms.",
        ))
    hist = spec.get("historical") or {}
    if hist.get("strictness") == "strict_reconstruction":
        out.append(_finding_local(
            "error",
            "attribute_unsupported_context",
            "PCC-02 attribute_contract fails closed under strict_reconstruction.",
        ))

    seen: set[str] = set()
    refs = _refs_by_id(spec)
    locks = spec.get("locks") or {}
    identity_mode = (spec.get("identity") or {}).get("mode")

    for row in rows:
        if not isinstance(row, dict):
            out.append(_finding_local(
                "error",
                "attribute_contract_shape",
                "Each attribute_contract entry must be an object.",
            ))
            continue
        attr = row.get("attribute")
        intent = row.get("intent")
        if attr not in SUPPORTED_ATTRIBUTES:
            out.append(_finding_local(
                "error",
                "attribute_unknown",
                f"Unsupported APCC attribute: {attr!r}.",
            ))
            continue
        if attr in seen:
            out.append(_finding_local(
                "error",
                "attribute_duplicate_declaration",
                f"Duplicate attribute_contract declaration for {attr}.",
            ))
            continue
        seen.add(attr)

        allowed = IDENTITY_INTENTS if attr == "identity.face" else WARDROBE_INTENTS
        if intent not in allowed:
            out.append(_finding_local(
                "error",
                "attribute_unsupported_intent",
                f"Unsupported intent {intent!r} for {attr}.",
            ))
            continue

        required_role = ATTRIBUTE_ROLE[attr]
        source_id = row.get("source_reference_id")
        target = row.get("target")

        if intent == "preserve":
            if not isinstance(source_id, str) or not source_id.strip():
                out.append(_finding_local(
                    "error",
                    "attribute_source_missing",
                    f"{attr} preserve requires source_reference_id.",
                ))
            elif source_id not in refs:
                out.append(_finding_local(
                    "error",
                    "attribute_unknown_source",
                    f"{attr} preserve source_reference_id {source_id!r} is not in references.",
                ))
            elif required_role not in (refs[source_id].get("roles") or []):
                out.append(_finding_local(
                    "error",
                    "attribute_source_role_mismatch",
                    f"{attr} preserve source {source_id!r} lacks required role {required_role!r}.",
                ))
            if attr == "identity.face" and identity_mode not in COMPATIBLE_IDENTITY_MODES:
                out.append(_finding_local(
                    "error",
                    "attribute_identity_mode_conflict",
                    "identity.face preserve requires identity.mode "
                    "strict_identity or recognizable_identity.",
                ))

        elif intent == "change":
            if attr != "wardrobe.garment":
                out.append(_finding_local(
                    "error",
                    "attribute_unsupported_intent",
                    f"Intent change is not supported for {attr} in PCC-02.",
                ))
                continue
            if target is None:
                out.append(_finding_local(
                    "error",
                    "attribute_change_target_missing",
                    "wardrobe.garment change requires a target.",
                ))
                continue
            if not isinstance(target, dict):
                out.append(_finding_local(
                    "error",
                    "attribute_change_target_missing",
                    "wardrobe.garment change target must be an object.",
                ))
                continue
            has_text = "text" in target and target.get("text") is not None
            has_ref = "reference_id" in target and target.get("reference_id") is not None
            if has_text and has_ref:
                out.append(_finding_local(
                    "error",
                    "attribute_change_target_ambiguous",
                    "wardrobe.garment change target must use exactly one of text or reference_id.",
                ))
            elif has_text:
                text = target.get("text")
                if not isinstance(text, str) or not text.strip():
                    out.append(_finding_local(
                        "error",
                        "attribute_change_target_missing",
                        "wardrobe.garment change text target must be a nonempty string.",
                    ))
                elif len(text) > TEXT_TARGET_MAX_LEN:
                    out.append(_finding_local(
                        "error",
                        "attribute_change_target_missing",
                        f"wardrobe.garment change text exceeds {TEXT_TARGET_MAX_LEN} characters.",
                    ))
            elif has_ref:
                rid = target.get("reference_id")
                if not isinstance(rid, str) or not rid.strip():
                    out.append(_finding_local(
                        "error",
                        "attribute_change_target_missing",
                        "wardrobe.garment change reference_id must be a nonempty string.",
                    ))
                elif rid not in refs:
                    out.append(_finding_local(
                        "error",
                        "attribute_unknown_source",
                        f"wardrobe.garment change target reference_id {rid!r} is not in references.",
                    ))
                elif "outfit" not in (refs[rid].get("roles") or []):
                    out.append(_finding_local(
                        "error",
                        "attribute_source_role_mismatch",
                        f"wardrobe.garment change target {rid!r} lacks required role 'outfit'.",
                    ))
            else:
                out.append(_finding_local(
                    "error",
                    "attribute_change_target_missing",
                    "wardrobe.garment change requires target.text or target.reference_id.",
                ))

            for key in OUTFIT_PRESERVE_LOCK_KEYS:
                if locks.get(key) is True:
                    out.append(_finding_local(
                        "error",
                        "attribute_lock_conflict",
                        f"locks.{key}=true conflicts with wardrobe.garment change.",
                    ))
                    break

        # unconstrained: no source/target required; reject leftover preserve/change fields lightly
        elif intent == "unconstrained":
            if source_id:
                out.append(_finding_local(
                    "error",
                    "attribute_contract_shape",
                    f"{attr} unconstrained must not declare source_reference_id.",
                ))
            if target is not None:
                out.append(_finding_local(
                    "error",
                    "attribute_contract_shape",
                    f"{attr} unconstrained must not declare target.",
                ))

    return out


def attribute_contract_prompt_clauses(spec: dict) -> tuple[str | None, str | None]:
    """Return (preserve_clause, change_clause) for valid APCC requests.

    Caller must lint first; this assumes a valid contract when present.
    """
    contract = spec.get("attribute_contract")
    if not contract:
        return None, None
    preserve_bits: list[str] = []
    change_bits: list[str] = []
    for row in _normalized_rows(contract):
        attr = row["attribute"]
        intent = row["intent"]
        if intent == "preserve":
            source = row["source_reference_id"]
            role = ATTRIBUTE_ROLE[attr]
            if attr == "identity.face":
                preserve_bits.append(
                    f"Preserve attribute identity.face from reference {source} "
                    f"(role identity only): keep recognizable facial identity and "
                    f"distinctive stable features consistent with that source. "
                    f"Do not import outfit, pose, environment, or hairstyle from "
                    f"{source} unless those roles are also explicitly assigned. "
                    f"This is a semantic preservation instruction, not a pixel-perfect "
                    f"identity or masked local-edit guarantee."
                )
            elif attr == "wardrobe.garment":
                preserve_bits.append(
                    f"Preserve attribute wardrobe.garment from reference {source} "
                    f"(role outfit only): keep garment category, silhouette, "
                    f"construction, and material logic consistent with that source. "
                    f"Do not import identity, body anatomy, or pose from {source} "
                    f"unless those roles are also explicitly assigned. "
                    f"Exact fold geometry from a particular pose is not required."
                )
        elif intent == "change" and attr == "wardrobe.garment":
            target = row["target"]
            if "text" in target:
                change_bits.append(
                    f"Change attribute wardrobe.garment: replace the original garment "
                    f"design rather than lightly recoloring or restyling it. Target "
                    f"wardrobe: {target['text'].strip()}. Do not treat this wardrobe "
                    f"change as authorization for facial redesign or identity drift. "
                    f"No outfit identity may be inferred from an identity-only reference."
                )
            else:
                rid = target["reference_id"]
                change_bits.append(
                    f"Change attribute wardrobe.garment using reference {rid} "
                    f"(role outfit only): replace the original garment with the "
                    f"garment silhouette, construction, layering, and material cues "
                    f"from {rid}. Do not import facial identity, body anatomy, pose, "
                    f"or unrelated environment from {rid}. This wardrobe change does "
                    f"not authorize a facial redesign."
                )
    preserve = " ".join(preserve_bits) if preserve_bits else None
    change = " ".join(change_bits) if change_bits else None
    return preserve, change
