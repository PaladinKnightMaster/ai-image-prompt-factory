# -*- coding: utf-8 -*-
"""L/S/V/C regression for Bronze sculpture art_method_emission_contract."""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from aipf import gates as gates_mod
from aipf.compiler import compile_result
from aipf.io import load_json
from aipf.linting import lint_spec

ROOT = Path(__file__).resolve().parents[1]

# Portable Stage 0 legacy prompt-byte baselines (UTF-8 digest + length; no private paths).
STAGE0_BRONZE = {
    "newly_created": ("a07f2d6516ff328530bfc93c1a94f125652bf66f5cfdaaeec26c213e967221d6", 4010),
    "in_period": ("0d5912004404ab2225adfb20932b8b9fc9b64a0ee540019d07495478bc26cce1", 4035),
    "aged": ("5194f919e692216daaa510b59d1536e5d5498077da1a90d703cf0f775a6edb5f", 4008),
    "damaged": ("0ad955dd7e1ec3392a052aeb7ec25649f7dfc04d5f8ed10910f1fd18046091be", 4012),
    "excavated": ("816839f0a68e6cd0fa43628a4b366ee696a87670b281f5edc5d6d382f159281f", 4011),
    "partially_restored": ("d165cea2eddaac980d829e1e072587e05672f1e6378bcf1f4575c9803776c229", 4042),
    "museum_conserved": ("0ee93b89009eaeffee03d5f5a8521f6d58017731484eab8166adac13785977e6", 4044),
    "modern_reconstruction": ("e6470e0def9db2d3467720b19467033b33632670222cf8da6a1dda0d8676a5a3", 4042),
    "replica": ("3daf381efe5301d361ff420da3f997b77799675535ffd93f1a3fae5396ee82ea", 4018),
    "fantasy_artifact": ("a6439f1568f753e61e4acb34d1d233b7ea1de7ba0af4395ebd47d93d556c877b", 3999),
}
STAGE0_XF_NEW = ("bd0943f2f9c36662fcf5939a07881eb2d552b7b8c049cbf4467ed6b9e71f43f3", 3017)
STAGE0_XF_AGED = ("832bc5e734d54ba7233bf5c57e7b071087162b495d3f3a5518b74da74dfa93db", 3015)

# Legacy emission-field digests preserved from bronze_sculpture v1.1.0.
LEGACY_CORE_DIGEST = "e2e45489560d9b10264d964c734a202d80872624258aee28a3a2e02fbac5d87a"
LEGACY_SURFACE_DIGEST = "3e4f47965eb0a3ffa1e2b213ed4028857dfe9b402b10a837ce120f1a6e979f9c"
LEGACY_EDGE_DIGEST = "c25540161486a78045247fd38ebfb6cfd902df718dbfcc4de63e5ce6397a5bc2"

# Positive deterioration/aging imperatives forbidden in technique (negations OK).
FORBIDDEN_TECHNIQUE_DETERIORATION = (
    "aged patina",
    "localized corrosion",
)

STATES = list(STAGE0_BRONZE)
FRESH_STATES = {"newly_created", "modern_reconstruction", "replica", "fantasy_artifact"}


def _sha(prompt: str) -> tuple[str, int]:
    raw = prompt.encode("utf-8")
    return hashlib.sha256(raw).hexdigest(), len(raw)


def _stage0_spec(state: str, **art_overrides) -> dict:
    """Rebuild the Stage 0 Bronze legacy fixture without private filesystem paths."""
    art = {
        "method": "bronze_sculpture",
        "artifact_form": "bust",
        "artifact_state": state,
        "variant": "individualized rather than emperor-like idealization",
    }
    art.update(art_overrides)
    return {
        "version": "3.1",
        "id": f"bronze-stage0-legacy-{state}",
        "request": (
            "Create a Roman Imperial bronze portrait bust for Stage 0 legacy baseline "
            f"capture with artifact_state={state}."
        ),
        "route": "artifact_transform",
        "locks": {
            "adult_subject": True,
            "primary_subject": "same adult subject across transformations",
            "do_not_silently_add_rank_or_sacred_status": True,
        },
        "references": [
            {
                "id": "ref-identity-01",
                "roles": ["identity"],
                "notes": "Stage 0 placeholder identity reference; not a recipe mutation.",
            }
        ],
        "identity": {
            "mode": "strict_identity",
            "locked_features": ["recognizable facial structure"],
        },
        "body_transformation": {
            "mode": "artistic_stylization",
            "anatomy_change": "none unless explicitly stated in request",
            "pose_change": "allowed as director choice",
            "camera_presentation": "allowed",
            "garment_shaping": "allowed when route requires it",
            "artistic_stylization": "only when selected by body mode/art method",
        },
        "historical": {
            "strictness": "historically_informed",
            "packs": ["roman_imperial"],
            "subperiod": "2nd century CE-inspired",
            "region": "Roman Mediterranean",
            "role": "private elite portrait",
            "occasion": "portrait display",
            "intentional_hybrids": ["modern sitter mapped to Roman portrait convention"],
        },
        "art": art,
        "requested_elements": [],
        "director": {
            "moment": "studio capture of a finished bronze bust",
            "action": "frontal-three-quarter bust with subtle head turn",
            "gaze": "focused slightly off-axis",
            "body_weight": "not applicable beyond stable bust support",
            "hand_logic": "no hands in crop",
            "foreground": "dark bronze mount edge",
            "midground": "head, neck, shoulders and deliberate bust termination",
            "background": "neutral studio wall with soft falloff",
            "camera": "close portrait at eye level",
            "light_source": "controlled warm side key with cooler ambient fill",
            "material_response": "true metallic reflection of copper-alloy casting",
            "micro_story": "Stage 0 legacy ArtMethod emission baseline for bronze_sculpture",
        },
        "output": {
            "profile": "standard",
            "aspect_ratio": "4:5",
            "text_in_image": [],
            "generation_requested": False,
        },
    }


def _xf_spec(state: str) -> dict:
    spec = _stage0_spec(state)
    spec["id"] = f"bronze-stage0-xf-portrait_to_volumetric_sculpture-{state}"
    spec["request"] = (
        "Stage 0 transformation compatibility capture: portrait to volumetric sculpture "
        f"using bronze_sculpture {state}."
    )
    spec["transformation"] = {
        "pack_id": "portrait_to_volumetric_sculpture",
        "selected_concepts": [],
    }
    return spec


def _errors(spec: dict) -> list[dict]:
    return [f for f in lint_spec(spec) if f["level"] == "error"]


def _bronze_pack_path(path: str | Path) -> bool:
    return Path(str(path)).as_posix().endswith("references/art-methods/bronze_sculpture.json")


def _patch_bronze_pack(monkeypatch, mutator):
    real = gates_mod.load_json

    def fake_load_json(path):
        data = real(path)
        if _bronze_pack_path(path):
            data = copy.deepcopy(data)
            mutator(data)
        return data

    monkeypatch.setattr(gates_mod, "load_json", fake_load_json)


def _assert_public_entry_rejects(spec: dict, code: str) -> None:
    findings = lint_spec(spec)
    err_codes = [f["code"] for f in findings if f.get("level") == "error"]
    assert code in err_codes, f"expected {code} in {err_codes}"
    with pytest.raises(ValueError) as raised:
        compile_result(spec)
    assert "Cannot compile invalid spec" in str(raised.value)


# ---------------------------------------------------------------------------
# L — Legacy parity
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("state", STATES)
def test_l_absent_selector_matches_stage0_bronze_bytes(state: str):
    prompt = compile_result(_stage0_spec(state))["prompt"]
    assert _sha(prompt) == STAGE0_BRONZE[state]


def test_l_explicit_legacy_equals_absent_newly_created():
    absent = compile_result(_stage0_spec("newly_created"))
    explicit = compile_result(_stage0_spec("newly_created", art_method_emission_contract="legacy"))
    assert absent["prompt"] == explicit["prompt"]
    assert _sha(absent["prompt"]) == _sha(explicit["prompt"])


def test_l_legacy_pack_field_digests_unchanged():
    pack = load_json("references/art-methods/bronze_sculpture.json")
    assert hashlib.sha256(pack["prompt_fragments"]["core"].encode()).hexdigest() == LEGACY_CORE_DIGEST
    assert hashlib.sha256(pack["surface_behavior"].encode()).hexdigest() == LEGACY_SURFACE_DIGEST
    assert hashlib.sha256(pack["edge_behavior"].encode()).hexdigest() == LEGACY_EDGE_DIGEST


def test_l_transformation_newly_created_stage0_bytes():
    result = compile_result(_xf_spec("newly_created"))
    sections = result["prompt_sections"]
    assert "art_method" not in sections
    assert "material_behavior" not in sections
    assert _sha(result["prompt"]) == STAGE0_XF_NEW


def test_l_transformation_aged_stage0_bytes():
    result = compile_result(_xf_spec("aged"))
    assert _sha(result["prompt"]) == STAGE0_XF_AGED


# ---------------------------------------------------------------------------
# S — Semantic / state-aware behavior
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("state", STATES)
def test_s_state_aware_ten_states(state: str):
    pack = load_json("references/art-methods/bronze_sculpture.json")
    result = compile_result(
        _stage0_spec(state, art_method_emission_contract="state_aware_v1")
    )
    sections = result["prompt_sections"]
    assert result["art_method_emission_contract"] == "state_aware_v1"
    assert result["selected_emission_contract_count"] == 1
    assert result["compiler_version"] == "3.6.0"
    assert pack["technique"]["prompt_core"] in sections["art_method"]
    assert pack["technique"]["surface"] in sections["material_behavior"]
    assert pack["technique"]["edge"] in sections["material_behavior"]
    # XOR against legacy aging-bearing emission fields
    assert pack["prompt_fragments"]["core"] not in result["prompt"]
    assert pack["surface_behavior"] not in result["prompt"]
    # technique.edge is fabrication-only and intentionally not identical to edge_behavior
    assert pack["technique"]["edge"] in sections["material_behavior"]
    assert pack["technique"]["edge"] != pack["edge_behavior"]

    overlay = pack["condition_overlays"][state]
    if state in FRESH_STATES:
        assert overlay is None
        assert "aged patina" not in sections["material_behavior"].casefold()
        assert "localized corrosion" not in sections["material_behavior"].casefold()
        assert "active corrosion" not in sections["material_behavior"].casefold()
        # Intentional finish remains available on fresh objects.
        assert "intentionally applied" in sections["material_behavior"].casefold() or (
            "intentionally applied" in sections["art_method"].casefold()
        )
    else:
        assert isinstance(overlay, str) and overlay.strip()
        assert overlay in sections["material_behavior"]

    low = result["prompt"].casefold()
    assert "cast" in low or "copper-alloy" in low
    assert "metal" in low


def test_s_technique_forbids_deterioration_language():
    pack = load_json("references/art-methods/bronze_sculpture.json")
    tech = " ".join(pack["technique"].values()).casefold()
    for phrase in FORBIDDEN_TECHNIQUE_DETERIORATION:
        assert phrase not in tech


def test_s_unqualified_patina_absent_from_technique():
    pack = load_json("references/art-methods/bronze_sculpture.json")
    tech = " ".join(pack["technique"].values())
    # Bare token "patina" must not appear; qualified "patination"/"patinated" are allowed.
    import re

    assert re.search(r"\bpatina\b", tech.casefold()) is None
    assert "patination" in tech.casefold() or "patinated" in tech.casefold()


def test_s_determinism_dual_compile():
    spec = _stage0_spec("aged", art_method_emission_contract="state_aware_v1")
    a = compile_result(spec)["prompt"]
    b = compile_result(copy.deepcopy(spec))["prompt"]
    assert a == b


# ---------------------------------------------------------------------------
# V — Validation
# ---------------------------------------------------------------------------


def test_v_pack_schema_valid_with_capability():
    schema = load_json("data/schemas/art_method.schema.json")
    pack = load_json("references/art-methods/bronze_sculpture.json")
    Draft202012Validator(schema).validate(pack)
    assert pack["version"] == "1.2.0"
    assert "state_aware_v1" in pack["supported_art_method_emission_contracts"]


def test_v_null_selector_schema_error():
    spec = _stage0_spec("newly_created")
    spec["art"]["art_method_emission_contract"] = None
    errs = _errors(spec)
    assert errs
    assert any(e["code"] == "schema" for e in errs)


def test_v_invalid_selector_schema_error():
    errs = _errors(_stage0_spec("newly_created", art_method_emission_contract="state_aware_v2"))
    assert errs
    assert any(e["code"] == "schema" for e in errs)


def test_v_state_aware_null_state():
    errs = _errors(_stage0_spec("newly_created", artifact_state=None, art_method_emission_contract="state_aware_v1"))
    assert any(e["code"] == "state_aware_requires_artifact_state" for e in errs)


def test_v_state_aware_with_transformation():
    spec = _xf_spec("newly_created")
    spec["art"]["art_method_emission_contract"] = "state_aware_v1"
    errs = _errors(spec)
    assert any(e["code"] == "state_aware_incompatible_with_transformation" for e in errs)


def test_v_state_aware_technique_incomplete(monkeypatch):
    def mutate(pack):
        pack["technique"]["prompt_core"] = ""

    _patch_bronze_pack(monkeypatch, mutate)
    _assert_public_entry_rejects(
        _stage0_spec("newly_created", art_method_emission_contract="state_aware_v1"),
        "state_aware_technique_incomplete",
    )


def test_v_state_aware_overlays_incomplete(monkeypatch):
    def mutate(pack):
        del pack["condition_overlays"]["excavated"]

    _patch_bronze_pack(monkeypatch, mutate)
    _assert_public_entry_rejects(
        _stage0_spec("aged", art_method_emission_contract="state_aware_v1"),
        "state_aware_overlays_incomplete",
    )


def test_v_state_aware_fresh_overlay_not_null(monkeypatch):
    def mutate(pack):
        pack["condition_overlays"]["newly_created"] = "Show aged corrosion on a new cast."

    _patch_bronze_pack(monkeypatch, mutate)
    _assert_public_entry_rejects(
        _stage0_spec("newly_created", art_method_emission_contract="state_aware_v1"),
        "state_aware_fresh_overlay_not_null",
    )


def test_v_state_aware_overlay_missing_aged_null(monkeypatch):
    def mutate(pack):
        pack["condition_overlays"]["aged"] = None

    _patch_bronze_pack(monkeypatch, mutate)
    _assert_public_entry_rejects(
        _stage0_spec("aged", art_method_emission_contract="state_aware_v1"),
        "state_aware_overlay_missing",
    )


def test_v_production_technique_passes_unqualified_patina_authoring_rule():
    """Compiler gates do not tokenize 'patina'; authoring rule is enforced in tests."""
    import re

    pack = load_json("references/art-methods/bronze_sculpture.json")
    tech = " ".join(pack["technique"].values()).casefold()
    assert re.search(r"\bpatina\b", tech) is None


# ---------------------------------------------------------------------------
# C — Compatibility
# ---------------------------------------------------------------------------


def test_c_xor_no_dual_emission():
    pack = load_json("references/art-methods/bronze_sculpture.json")
    result = compile_result(
        _stage0_spec("newly_created", art_method_emission_contract="state_aware_v1")
    )
    assert pack["prompt_fragments"]["core"] not in result["prompt"]
    assert pack["surface_behavior"] not in result["prompt"]
    assert pack["technique"]["prompt_core"] in result["prompt"]
    assert pack["technique"]["edge"] != pack["edge_behavior"]


def test_c_legacy_default_compiler_version():
    result = compile_result(_stage0_spec("museum_conserved"))
    assert result["art_method_emission_contract"] == "legacy"
    assert result["compiler_version"] == "3.2.0"
    assert result["selected_emission_contract_count"] == 1


def test_c_state_aware_opt_in_compiler_version():
    result = compile_result(
        _stage0_spec("museum_conserved", art_method_emission_contract="state_aware_v1")
    )
    assert result["compiler_version"] == "3.6.0"


def test_c_schemas_unchanged_presence():
    # Smoke: shared schemas still load and accept Bronze + mural packs.
    schema = load_json("data/schemas/art_method.schema.json")
    Draft202012Validator(schema).validate(load_json("references/art-methods/bronze_sculpture.json"))
    Draft202012Validator(schema).validate(load_json("references/art-methods/mineral_pigment_mural.json"))


def test_c_no_automatic_migration_existing_cases_remain_legacy():
    case = load_json("cases/golden/03-roman-bronze-bust/case.json")
    assert "art_method_emission_contract" not in case["art"]
    result = compile_result(case)
    assert result["art_method_emission_contract"] == "legacy"
