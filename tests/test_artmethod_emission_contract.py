# -*- coding: utf-8 -*-
"""L/S/V/C regression for CR-017 art_method_emission_contract."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from aipf import gates as gates_mod
from aipf.compiler import compile_result
from aipf.io import load_json
from aipf.linting import lint_spec
from aipf.recipes import compile_recipe, load_recipe, sha256_canonical

ROOT = Path(__file__).resolve().parents[1]
STAGE0 = Path(
    r"D:\1_PROJECT\AI_Kits\AI Image Prompt Factory\IDEA_POOL\AIPF_Creative_Private"
    r"\CR-017-ARTMETHOD-STAGE0-BASELINE-CAPTURE-01\binaries"
)

FORBIDDEN_LEGACY_AGING = (
    "localized loss and aging",
    "cracks, abrasions and losses",
    "cracks and loss",
)

STATES = [
    "newly_created",
    "in_period",
    "aged",
    "damaged",
    "excavated",
    "partially_restored",
    "museum_conserved",
    "modern_reconstruction",
    "replica",
    "fantasy_artifact",
]
FRESH_STATES = {"newly_created", "modern_reconstruction", "replica", "fantasy_artifact"}


def _sha(prompt: str) -> tuple[str, int]:
    raw = prompt.encode("utf-8")
    return hashlib.sha256(raw).hexdigest(), len(raw)


def _base_spec(**art_overrides) -> dict:
    art = {
        "method": "mineral_pigment_mural",
        "artifact_form": "wall_surface",
        "artifact_state": "newly_created",
        "variant": None,
    }
    art.update(art_overrides)
    return {
        "version": "3.1",
        "id": "cr017-emission-contract-fixture",
        "request": "Render a mineral-pigment mural on a prepared wall.",
        "route": "art_style_transform",
        "locks": {"adult_subject": True},
        "references": [],
        "identity": {
            "mode": "recognizable_identity",
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
            "packs": ["dunhuang", "tang"],
            "subperiod": "Tang-period Mogao-inspired cave mural context",
            "region": "Mogao/Dunhuang",
            "role": None,
            "occasion": None,
            "intentional_hybrids": [],
        },
        "art": art,
        "requested_elements": [],
        "director": {},
        "output": {
            "profile": "standard",
            "aspect_ratio": "4:5",
            "text_in_image": [],
            "generation_requested": False,
        },
    }


def _errors(spec: dict) -> list[dict]:
    return [f for f in lint_spec(spec) if f["level"] == "error"]


def _isv_spec():
    path = ROOT / "tests/test_installed_surface_verification.py"
    uspec = importlib.util.spec_from_file_location("isv_mod", path)
    mod = importlib.util.module_from_spec(uspec)
    uspec.loader.exec_module(mod)
    return mod._spec_for_method("mineral_pigment_mural")


# ---------------------------------------------------------------------------
# L — Legacy parity
# ---------------------------------------------------------------------------


def test_l_absent_selector_matches_stage0_cr017_bytes():
    receipt = compile_recipe(load_recipe(ROOT / "recipes/cr-017-pigment-beneath-plaster/1.0.0.json"))
    prompt = receipt["compilation"]["prompt"]
    digest, nbytes = _sha(prompt)
    expected = (STAGE0 / "B0_01_cr017_legacy.prompt.txt").read_bytes()
    assert prompt.encode("utf-8") == expected
    assert digest == "5bd1c2bfd865fb3040f07ce6e4e92d722e123759ada6a7f7ea82e419dd8bd85d"
    assert nbytes == 7049
    assert receipt["compilation"]["art_method_emission_contract"] == "legacy"
    assert receipt["compilation"]["selected_emission_contract_count"] == 1


def test_l_explicit_legacy_equals_absent_prompt_bytes():
    absent = compile_result(_base_spec())
    explicit = compile_result(_base_spec(art_method_emission_contract="legacy"))
    assert absent["prompt"] == explicit["prompt"]
    assert _sha(absent["prompt"]) == _sha(explicit["prompt"])
    # Canonical identity differs when key present vs absent, prompts equal.
    a_spec = _base_spec()
    e_spec = _base_spec(art_method_emission_contract="legacy")
    assert sha256_canonical(a_spec["art"]) != sha256_canonical(e_spec["art"])


def test_l_cr005_transform_stage0_bytes_and_skip():
    receipt = compile_recipe(load_recipe(ROOT / "recipes/cr-005-silk-on-plaster/1.0.0.json"))
    prompt = receipt["compilation"]["prompt"]
    expected = (STAGE0 / "B0_02_cr005_transform.prompt.txt").read_bytes()
    assert prompt.encode("utf-8") == expected
    sections = receipt["compilation"]["prompt_sections"]
    assert "art_method" not in sections
    assert "material_behavior" not in sections
    assert _sha(prompt) == (
        "6e3f9d6416fffc05c4e94cf81c3312a80b3564f1cd1689a54bfbe31da13984da",
        5369,
    )


def test_l_tang_golden_prompt_body_stage0_bytes():
    case = load_json("cases/golden/05-tang-dunhuang-mural/case.json")
    prompt = compile_result(case)["prompt"]
    expected = (STAGE0 / "B0_03_tang_golden_prompt_body.prompt.txt").read_bytes()
    assert prompt.encode("utf-8") == expected
    assert _sha(prompt) == (
        "cd1a694eba866ed525d2d18904e57c7aa14720e1472c9897221195e598daf755",
        5328,
    )


def test_l_isv_aged_stage0_bytes():
    prompt = compile_result(_isv_spec())["prompt"]
    expected = (STAGE0 / "B0_04_isv_mineral_aged.prompt.txt").read_bytes()
    assert prompt.encode("utf-8") == expected
    assert _sha(prompt) == (
        "eef91b4d413021c9a1f3d9e30a9f1e2a54ff0a849b776a9f0bbfa0f229d33b4f",
        4473,
    )


def test_l_legacy_pack_field_digests_unchanged():
    pack = load_json("references/art-methods/mineral_pigment_mural.json")
    assert (
        hashlib.sha256(pack["prompt_fragments"]["core"].encode()).hexdigest()
        == "64fc9e323d5c486ba0bc80cf7114c2634f02231d44d7395b9e48ecb8b5f3b84f"
    )
    assert (
        hashlib.sha256(pack["surface_behavior"].encode()).hexdigest()
        == "2637e26804d5458e69c655893efdb05167e0220e6b03eccd653d124d94e9d1fd"
    )
    assert (
        hashlib.sha256(pack["edge_behavior"].encode()).hexdigest()
        == "7f48c5d94e8e54e086af834c2a2790cd1757fad010ad1319ed2366284afb7a6f"
    )


# ---------------------------------------------------------------------------
# S — State-aware
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("state", STATES)
def test_s_state_aware_ten_states(state: str):
    result = compile_result(
        _base_spec(artifact_state=state, art_method_emission_contract="state_aware_v1")
    )
    pack = load_json("references/art-methods/mineral_pigment_mural.json")
    sections = result["prompt_sections"]
    assert result["art_method_emission_contract"] == "state_aware_v1"
    assert result["selected_emission_contract_count"] == 1
    assert pack["technique"]["prompt_core"] in sections["art_method"]
    assert pack["technique"]["surface"] in sections["material_behavior"]
    assert pack["technique"]["edge"] in sections["material_behavior"]
    # XOR: no legacy aging imperatives from legacy fields
    for phrase in FORBIDDEN_LEGACY_AGING:
        assert phrase not in result["prompt"]
    overlay = pack["condition_overlays"][state]
    if state in FRESH_STATES:
        assert overlay is None
        for phrase in FORBIDDEN_LEGACY_AGING:
            assert phrase not in sections["material_behavior"]
    else:
        assert isinstance(overlay, str) and overlay
        assert overlay in sections["material_behavior"]
    # technique retention tokens
    low = result["prompt"].casefold()
    assert "mineral" in low or "pigment" in low
    assert "wall" in low or "plaster" in low


def test_s_determinism_dual_compile():
    spec = _base_spec(artifact_state="aged", art_method_emission_contract="state_aware_v1")
    a = compile_result(spec)["prompt"]
    b = compile_result(copy.deepcopy(spec))["prompt"]
    assert a == b


# ---------------------------------------------------------------------------
# V — Validation
# ---------------------------------------------------------------------------


def test_v_null_selector_schema_error():
    spec = _base_spec()
    spec["art"]["art_method_emission_contract"] = None
    errs = _errors(spec)
    assert errs
    assert any(e["code"] == "schema" for e in errs)


def test_v_invalid_selector_schema_error():
    spec = _base_spec(art_method_emission_contract="state_aware_v2")
    errs = _errors(spec)
    assert errs
    assert any(e["code"] == "schema" for e in errs)


def test_v_state_aware_null_state():
    spec = _base_spec(artifact_state=None, art_method_emission_contract="state_aware_v1")
    errs = _errors(spec)
    assert any(e["code"] == "state_aware_requires_artifact_state" for e in errs)


def test_v_state_aware_unknown_state():
    spec = _base_spec(artifact_state="not_a_state", art_method_emission_contract="state_aware_v1")
    errs = _errors(spec)
    assert any(e["code"] == "unknown_artifact_state" for e in errs)


def test_v_state_aware_with_transformation():
    recipe = load_recipe(ROOT / "recipes/cr-005-silk-on-plaster/1.0.0.json")
    spec = copy.deepcopy(recipe["semantic_spec"])
    spec["art"]["art_method_emission_contract"] = "state_aware_v1"
    errs = _errors(spec)
    assert any(e["code"] == "state_aware_incompatible_with_transformation" for e in errs)


def test_v_state_aware_missing_capability_on_other_method():
    spec = _base_spec(
        method="watercolor",
        artifact_form="album_leaf",
        artifact_state="newly_created",
        art_method_emission_contract="state_aware_v1",
    )
    errs = _errors(spec)
    assert any(e["code"] == "state_aware_pack_capability_missing" for e in errs)


def test_v_pack_schema_requires_structures_when_capability_declared():
    schema = load_json("data/schemas/art_method.schema.json")
    pack = load_json("references/art-methods/mineral_pigment_mural.json")
    Draft202012Validator(schema).validate(pack)
    broken = copy.deepcopy(pack)
    del broken["technique"]
    errs = list(Draft202012Validator(schema).iter_errors(broken))
    assert errs


def _mineral_pack_path(path: str | Path) -> bool:
    return Path(str(path)).as_posix().endswith("references/art-methods/mineral_pigment_mural.json")


def _patch_mineral_pack(monkeypatch, mutator):
    """Serve a mutated mineral pack through gates.load_json (public lint/compile path)."""
    real = gates_mod.load_json

    def fake_load_json(path):
        data = real(path)
        if _mineral_pack_path(path):
            data = copy.deepcopy(data)
            mutator(data)
        return data

    monkeypatch.setattr(gates_mod, "load_json", fake_load_json)


def _assert_public_entry_rejects(spec: dict, code: str) -> None:
    """Require structured lint code and failed compile_result (no successful prompt)."""
    findings = lint_spec(spec)
    err_codes = [f["code"] for f in findings if f.get("level") == "error"]
    assert code in err_codes, f"expected {code} in {err_codes}"
    with pytest.raises(ValueError) as raised:
        compile_result(spec)
    # Must not fall back to a successful legacy/state-aware compilation.
    assert "Cannot compile invalid spec" in str(raised.value)
    assert raised.value.args  # non-empty failure


def test_v_state_aware_technique_incomplete_empty_prompt_core(monkeypatch):
    def mutate(pack):
        pack["technique"]["prompt_core"] = ""

    _patch_mineral_pack(monkeypatch, mutate)
    spec = _base_spec(artifact_state="newly_created", art_method_emission_contract="state_aware_v1")
    _assert_public_entry_rejects(spec, "state_aware_technique_incomplete")


def test_v_state_aware_technique_incomplete_missing_surface(monkeypatch):
    def mutate(pack):
        del pack["technique"]["surface"]

    _patch_mineral_pack(monkeypatch, mutate)
    spec = _base_spec(artifact_state="aged", art_method_emission_contract="state_aware_v1")
    _assert_public_entry_rejects(spec, "state_aware_technique_incomplete")


def test_v_state_aware_overlays_malformed_not_object(monkeypatch):
    def mutate(pack):
        pack["condition_overlays"] = ["aged"]

    _patch_mineral_pack(monkeypatch, mutate)
    spec = _base_spec(artifact_state="aged", art_method_emission_contract="state_aware_v1")
    _assert_public_entry_rejects(spec, "state_aware_overlays_malformed")


def test_v_state_aware_overlays_incomplete_missing_key(monkeypatch):
    def mutate(pack):
        del pack["condition_overlays"]["excavated"]

    _patch_mineral_pack(monkeypatch, mutate)
    spec = _base_spec(artifact_state="aged", art_method_emission_contract="state_aware_v1")
    _assert_public_entry_rejects(spec, "state_aware_overlays_incomplete")


def test_v_state_aware_overlay_missing_aged_null_schema_permitted(monkeypatch):
    """Schema allows aged:null; compiler gate must still reject via public entry."""

    def mutate(pack):
        pack["condition_overlays"]["aged"] = None

    _patch_mineral_pack(monkeypatch, mutate)
    # Confirm schema still accepts this pack shape (asymmetry under test).
    schema = load_json("data/schemas/art_method.schema.json")
    broken = copy.deepcopy(load_json("references/art-methods/mineral_pigment_mural.json"))
    broken["condition_overlays"]["aged"] = None
    Draft202012Validator(schema).validate(broken)

    spec = _base_spec(artifact_state="aged", art_method_emission_contract="state_aware_v1")
    _assert_public_entry_rejects(spec, "state_aware_overlay_missing")


def test_v_state_aware_overlay_missing_empty_string(monkeypatch):
    def mutate(pack):
        pack["condition_overlays"]["damaged"] = "   "

    _patch_mineral_pack(monkeypatch, mutate)
    spec = _base_spec(artifact_state="damaged", art_method_emission_contract="state_aware_v1")
    _assert_public_entry_rejects(spec, "state_aware_overlay_missing")


def test_v_state_aware_fresh_overlay_not_null(monkeypatch):
    def mutate(pack):
        pack["condition_overlays"]["newly_created"] = "Show aging cracks on a fresh mural."

    _patch_mineral_pack(monkeypatch, mutate)
    spec = _base_spec(artifact_state="newly_created", art_method_emission_contract="state_aware_v1")
    _assert_public_entry_rejects(spec, "state_aware_fresh_overlay_not_null")


def test_v_artifact_state_null_distinct_from_overlay_null():
    """Null artifact_state is a different gate than a null condition overlay."""
    spec = _base_spec(artifact_state=None, art_method_emission_contract="state_aware_v1")
    errs = _errors(spec)
    assert any(e["code"] == "state_aware_requires_artifact_state" for e in errs)
    assert all(e["code"] != "state_aware_overlay_missing" for e in errs)
    with pytest.raises(ValueError, match="Cannot compile invalid spec"):
        compile_result(spec)


def test_v_state_aware_neighbor_valid_still_compiles_after_negative_paths():
    """Valid neighboring state-aware config remains compilable (no production pack mutation)."""
    result = compile_result(
        _base_spec(artifact_state="newly_created", art_method_emission_contract="state_aware_v1")
    )
    assert result["art_method_emission_contract"] == "state_aware_v1"
    assert result["selected_emission_contract_count"] == 1
    assert "prompt" in result and result["prompt"]


# ---------------------------------------------------------------------------
# C — Contract integrity
# ---------------------------------------------------------------------------


def test_c_xor_no_dual_emission_provenance():
    pack = load_json("references/art-methods/mineral_pigment_mural.json")
    result = compile_result(
        _base_spec(artifact_state="newly_created", art_method_emission_contract="state_aware_v1")
    )
    assert pack["prompt_fragments"]["core"] not in result["prompt"]
    assert pack["surface_behavior"] not in result["prompt"]
    assert pack["edge_behavior"] not in result["prompt"]
    assert pack["technique"]["prompt_core"] in result["prompt"]


def test_c_no_automatic_migration_existing_recipes_remain_legacy():
    for path in [
        ROOT / "recipes/cr-017-pigment-beneath-plaster/1.0.0.json",
        ROOT / "recipes/cr-005-silk-on-plaster/1.0.0.json",
    ]:
        recipe = load_recipe(path)
        assert "art_method_emission_contract" not in recipe["semantic_spec"]["art"]
        receipt = compile_recipe(recipe)
        assert receipt["compilation"]["art_method_emission_contract"] == "legacy"
