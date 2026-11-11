"""ISV-01 — Installed Surface Verification (ArtMethods, Eras, overlays, emission).

Offline deterministic coverage only. Does not generate images, edit packs,
or change compiler behavior. See docs/ISV_01_INSTALLED_SURFACE_VERIFICATION.md.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from aipf.compiler import compile_result
from aipf.linting import lint_spec

ROOT = Path(__file__).resolve().parents[1]

# Fields the non-transformation compiler path is known to emit into prompt prose.
EMITTED_BY_STANDARD_COMPILER = {
    "name",
    "prompt_fragments",  # core fragment
    "surface_behavior",
    "edge_behavior",
    "typical_generation_failures",  # first three
}

# Pack fields reserved for schema/metadata/evaluation/loader; not standard prompt prose.
INTENTIONAL_NON_EMISSION_OR_CONDITIONAL = {
    "id",
    "version",
    "family",
    "material",
    "fabrication_process",
    "visible_production_marks",
    "mark_making",
    "color_behavior",
    "composition_behavior",
    "structural_limitations",
    "aging_weathering",
    "artifact_compatibility",
    "evaluation_criteria",  # extended profile only
    "sources",
    "scope_note",
    "concept_refs",  # transformation/lexical path only
}


def _load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _method_registry() -> list[dict]:
    return _load("references/art-methods/registry.json")["methods"]


def _era_registry() -> list[dict]:
    return _load("references/eras/registry.json")["packs"]


def _method_doc(method_id: str) -> dict:
    path = next(r["path"] for r in _method_registry() if r["id"] == method_id)
    return _load(path)


def _era_doc(era_id: str) -> dict:
    path = next(r["path"] for r in _era_registry() if r["id"] == era_id)
    return _load(path)


def _minimal_spec(**overrides) -> dict:
    spec = {
        "version": "3.1",
        "id": "isv01-case",
        "title": "ISV-01 installed surface case",
        "status": "spec_only",
        "request": "Offline verification of an installed creative surface.",
        "route": "art_style_transform",
        "locks": {
            "adult_subject": True,
            "primary_subject": "same adult subject across transformations",
            "do_not_silently_add_rank_or_sacred_status": True,
        },
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
            "packs": [],
            "subperiod": None,
            "region": None,
            "role": None,
            "occasion": None,
            "intentional_hybrids": [],
        },
        "art": {
            "method": None,
            "artifact_form": None,
            "artifact_state": None,
            "variant": None,
        },
        "requested_elements": [],
        "director": {
            "moment": "quiet controlled presentation",
            "action": "stable primary subject pose",
            "gaze": "calm forward focus",
            "body_weight": "balanced stance",
            "hand_logic": "hands contained and readable",
            "foreground": "near surface detail",
            "midground": "primary subject",
            "background": "restrained supporting environment",
            "camera": "clear three-quarter view",
            "light_source": "soft directional light",
            "material_response": "material and fabrication cues remain legible",
            "micro_story": "offline verification of installed surface emission",
        },
        "output": {
            "profile": "standard",
            "aspect_ratio": "4:5",
            "text_in_image": [],
            "generation_requested": False,
        },
    }
    for key, value in overrides.items():
        if key in {"historical", "art", "director", "output", "identity", "body_transformation"} and isinstance(
            value, dict
        ):
            spec[key] = {**spec[key], **value}
        else:
            spec[key] = value
    return spec


# Route/form/context chosen from installed compatibility — not invented architecture.
METHOD_CASES = {
    "marble_sculpture": {
        "route": "artifact_transform",
        "packs": ["classical_greek"],
        "form": "free_standing_statue",
        "state": "museum_conserved",
        "request": "Render the subject as a Classical Greek marble statue.",
        "must_substrings": ["marble sculpture", "carved stone", "stone"],
        "material_tokens": ["crystalline stone", "polish"],
        "must_not_substrings": ["transparent layered washes", "cast copper-alloy"],
        "failure_tokens": ["living skin patches", "plastic/resin gloss"],
    },
    "bronze_sculpture": {
        "route": "artifact_transform",
        "packs": ["roman_imperial"],
        "form": "bust",
        "state": "museum_conserved",
        "request": "Render the subject as a Roman Imperial bronze bust.",
        "must_substrings": ["bronze sculpture", "cast", "metal"],
        "material_tokens": ["patina", "metal reflects"],
        "must_not_substrings": ["carved stone masses", "transparent layered washes"],
        "failure_tokens": ["orange plastic surface", "stone-like diffuse shading"],
    },
    "carved_stone_relief": {
        "route": "artifact_transform",
        "packs": ["classical_greek"],
        "form": "relief",
        "state": "museum_conserved",
        "request": "Render the subject as a carved stone relief.",
        "must_substrings": ["carved stone relief", "backing plane", "relief"],
        "material_tokens": ["backing plane", "carved"],
        "must_not_substrings": ["cast copper-alloy", "transparent layered washes"],
        "failure_tokens": ["grayscale photograph embossed", "figures detach from slab"],
    },
    "chinese_ink_painting": {
        "route": "art_style_transform",
        "packs": ["song"],
        "form": "scroll",
        "state": "newly_created",
        "request": "Render as a Song-informed Chinese ink painting.",
        "must_substrings": ["chinese ink painting", "brush", "ink"],
        "material_tokens": ["absorbent", "calligraphic"],
        "must_not_substrings": ["cast copper-alloy", "transparent layered washes"],
        "failure_tokens": ["photograph with black watercolor overlay", "uniform gray wash"],
    },
    "gongbi_painting": {
        "route": "art_style_transform",
        "packs": ["ming"],
        "form": "scroll",
        "state": "newly_created",
        "request": "Render as a Gongbi fine-line painting.",
        "must_substrings": ["gongbi", "fine contour", "layered color"],
        "material_tokens": ["controlled", "outline"],
        "must_not_substrings": ["cast copper-alloy", "transparent layered washes"],
        "failure_tokens": ["anime cel", "hyperreal skin pores"],
    },
    "mineral_pigment_mural": {
        "route": "art_style_transform",
        "packs": ["dunhuang", "tang"],
        "form": "wall_surface",
        "state": "aged",
        "subperiod": "Tang-period Mogao-inspired cave mural context",
        "region": "Mogao/Dunhuang",
        "request": "Render as a Dunhuang mineral-pigment mural on a wall surface.",
        "must_substrings": ["mineral-pigment mural", "wall", "pigment"],
        "material_tokens": ["mineral wall", "plaster"],
        "must_not_substrings": ["buon fresco"],
        "failure_tokens": ["digital fresco filter", "uniform cracked overlay", "neon pigments"],
    },
    "watercolor": {
        "route": "art_style_transform",
        "packs": [],
        "form": "album_leaf",
        "state": "newly_created",
        "request": "Render a contemporary portrait as transparent watercolor on paper.",
        "must_substrings": [
            "watercolor",
            "transparent layered washes",
            "reserve light",
            "granulate",
        ],
        "material_tokens": ["paper tooth", "capillary", "water load"],
        "must_not_substrings": ["cast copper-alloy", "carved stone masses"],
        "failure_tokens": ["soft pastel digital painting", "opaque airbrush"],
    },
    "japanese_woodblock_print": {
        "route": "art_style_transform",
        "packs": ["edo"],
        "form": "print_sheet",
        "state": "newly_created",
        "request": "Render as an Edo-period Japanese woodblock print.",
        "must_substrings": ["woodblock", "registration", "carved-and-printed", "bokashi"],
        "material_tokens": ["keyline", "registration", "mulberry"],
        "must_not_substrings": ["cast copper-alloy", "transparent layered washes"],
        "failure_tokens": ["anime screenshot", "3D photoreal shading"],
    },
    "blue_white_ceramic": {
        "route": "artifact_transform",
        "packs": ["edo"],
        "form": "vase",
        "state": "museum_conserved",
        "request": "Render as blue-and-white ceramic decoration on a vase.",
        "must_substrings": ["blue-and-white ceramic", "glaze", "cobalt"],
        "material_tokens": ["glaze", "ceramic", "underglaze"],
        "must_not_substrings": ["marble sculpture", "transparent layered washes"],
        "failure_tokens": ["photo printed as blue decal", "blue paint floats above glaze"],
    },
    "manuscript_miniature": {
        "route": "art_style_transform",
        "packs": [],
        "form": "book_page",
        "state": "newly_created",
        "request": "Render as a manuscript miniature on a book page.",
        "must_substrings": ["manuscript miniature", "parchment", "tempera", "miniature"],
        "material_tokens": ["parchment", "gold"],
        "must_not_substrings": ["standalone tempera pack", "cast copper-alloy"],
        "failure_tokens": ["fantasy digital painting pasted on parchment", "gold rendered as flat yellow"],
    },
    "paper_cut_layered": {
        "route": "art_style_transform",
        "packs": [],
        "form": "popup_diorama",
        "state": "newly_created",
        "request": "Render as layered paper-cut construction with physical depth.",
        "must_substrings": ["paper-cut", "layered", "cut", "shadow"],
        "material_tokens": ["paper", "shadow", "thickness"],
        "must_not_substrings": ["cast copper-alloy", "marble sculpture"],
        "failure_tokens": ["3D plastic toy look", "floating unsupported paper islands"],
    },
    "embroidery_textile": {
        "route": "art_style_transform",
        "packs": [],
        "form": "folding_screen",
        "state": "newly_created",
        "request": "Render as embroidery textile with stitch-based construction.",
        "must_substrings": ["embroidery", "stitch", "thread"],
        "material_tokens": ["stitch", "textile", "thread"],
        "must_not_substrings": ["cast copper-alloy", "marble sculpture"],
        "failure_tokens": ["printed fabric texture", "photographic skin with embroidery overlay"],
    },
}


ERA_CASES = {
    "han": {
        "type": "historical_era",
        "route": "historical_portrait",
        "packs": ["han"],
        "request": "Han dynasty living portrait.",
        "expect_name": "Han dynasty",
        "anchor_tokens": ["han"],
    },
    "tang": {
        "type": "historical_era",
        "route": "historical_portrait",
        "packs": ["tang"],
        "occasion": "Shangyuan lantern-festival evening",
        "request": "Tang court living portrait at a lantern festival.",
        "expect_name": "Tang dynasty",
        "anchor_tokens": ["tang"],
        "fragment_tokens": ["lantern"],
    },
    "song": {
        "type": "historical_era",
        "route": "art_style_transform",
        "packs": ["song"],
        "method": "chinese_ink_painting",
        "form": "scroll",
        "state": "newly_created",
        "request": "Song dynasty Chinese ink painting.",
        "expect_name": "Song dynasty",
        "anchor_tokens": ["song"],
        "fragment_tokens": ["ink"],
    },
    "ming": {
        "type": "historical_era",
        "route": "historical_portrait",
        "packs": ["ming"],
        "request": "Ming dynasty living portrait.",
        "expect_name": "Ming dynasty",
        "anchor_tokens": ["ming"],
    },
    "qing": {
        "type": "historical_era",
        "route": "historical_portrait",
        "packs": ["qing"],
        "request": "Qing court living portrait.",
        "expect_name": "Qing dynasty",
        "anchor_tokens": ["qing"],
    },
    "heian": {
        "type": "historical_era",
        "route": "historical_portrait",
        "packs": ["heian"],
        "request": "Heian court living portrait.",
        "expect_name": "Heian period",
        "anchor_tokens": ["heian"],
    },
    "edo": {
        "type": "historical_era",
        "route": "art_style_transform",
        "packs": ["edo"],
        "method": "japanese_woodblock_print",
        "form": "print_sheet",
        "state": "newly_created",
        "request": "Edo period Japanese woodblock print.",
        "expect_name": "Edo period",
        "anchor_tokens": ["edo"],
        "fragment_tokens": ["print", "registration"],
    },
    "classical_greek": {
        "type": "historical_era",
        "route": "historical_portrait",
        "packs": ["classical_greek"],
        "request": "Classical Greek living portrait.",
        "expect_name": "Classical Greek",
        "anchor_tokens": ["classical greek"],
        "fragment_tokens": ["living", "marble statue"],
    },
    "hellenistic_greek": {
        "type": "historical_era",
        "route": "artifact_transform",
        "packs": ["hellenistic_greek"],
        "method": "marble_sculpture",
        "form": "free_standing_statue",
        "state": "museum_conserved",
        "request": "Hellenistic Greek marble sculpture.",
        "expect_name": "Hellenistic Greek",
        "anchor_tokens": ["hellenistic"],
        "fragment_tokens": ["torque", "movement"],
    },
    "roman_imperial": {
        "type": "historical_era",
        "route": "artifact_transform",
        "packs": ["roman_imperial"],
        "method": "bronze_sculpture",
        "form": "bust",
        "state": "museum_conserved",
        "request": "Roman Imperial bronze bust.",
        "expect_name": "Roman Imperial",
        "anchor_tokens": ["roman"],
        "fragment_tokens": ["bust"],
    },
    "dunhuang": {
        "type": "site_tradition",
        "route": "art_style_transform",
        "packs": ["dunhuang", "tang"],
        "method": "mineral_pigment_mural",
        "form": "wall_surface",
        "state": "aged",
        "subperiod": "Tang-period Mogao-inspired cave mural context",
        "region": "Mogao/Dunhuang",
        "request": "Dunhuang mineral-pigment mural with Tang context.",
        "expect_name": "Dunhuang",
        "anchor_tokens": ["dunhuang"],
        "fragment_tokens": ["mural", "wall"],
    },
    "wuxia": {
        "type": "genre_overlay",
        "route": "historical_portrait",
        "packs": ["ming", "wuxia"],
        "strictness": "period_drama",
        "request": "Ming historical context with Wuxia overlay.",
        "expect_name": "Wuxia",
        "overlay_tokens": ["genre/fantasy overlay", "martial"],
        "anchor_tokens": ["ming"],
    },
    "xianxia": {
        "type": "fantasy_overlay",
        "route": "historical_portrait",
        "packs": ["tang", "xianxia"],
        "strictness": "fantasy_hybrid",
        "hybrids": ["cultivation fantasy layered on Tang visual anchors"],
        "request": "Fantasy-hybrid Xianxia with Tang base era.",
        "expect_name": "Xianxia",
        "overlay_tokens": ["genre/fantasy overlay", "supernatural"],
        "anchor_tokens": ["tang"],
    },
}


def _spec_for_method(method_id: str) -> dict:
    cfg = METHOD_CASES[method_id]
    return _minimal_spec(
        id=f"isv01-method-{method_id}",
        route=cfg["route"],
        request=cfg["request"],
        historical={
            "packs": list(cfg.get("packs", [])),
            "subperiod": cfg.get("subperiod"),
            "region": cfg.get("region"),
            "strictness": cfg.get("strictness", "historically_informed"),
        },
        art={
            "method": method_id,
            "artifact_form": cfg["form"],
            "artifact_state": cfg["state"],
        },
    )


def _spec_for_era(era_id: str) -> dict:
    cfg = ERA_CASES[era_id]
    art = {
        "method": cfg.get("method"),
        "artifact_form": cfg.get("form"),
        "artifact_state": cfg.get("state"),
    }
    return _minimal_spec(
        id=f"isv01-era-{era_id}",
        route=cfg["route"],
        request=cfg["request"],
        historical={
            "packs": list(cfg["packs"]),
            "strictness": cfg.get("strictness", "historically_informed"),
            "subperiod": cfg.get("subperiod"),
            "region": cfg.get("region"),
            "occasion": cfg.get("occasion"),
            "intentional_hybrids": list(cfg.get("hybrids", [])),
        },
        art=art,
    )


def _assert_no_lint_errors(spec: dict) -> None:
    errors = [f for f in lint_spec(spec) if f["level"] == "error"]
    assert not errors, errors


def _core_emitted(sections: dict, method_doc: dict) -> None:
    art_method = sections.get("art_method", "")
    assert art_method, "art_method section missing"
    assert method_doc["name"] in art_method
    core = method_doc["prompt_fragments"]["core"]
    # Distinctive core instruction must survive compilation (not merely the method name).
    assert core[:80] in art_method
    material = sections.get("material_behavior", "")
    assert method_doc["surface_behavior"] in material
    assert method_doc["edge_behavior"] in material
    failures = sections.get("material_failure_checks", "")
    for item in method_doc.get("typical_generation_failures", [])[:3]:
        assert item in failures


# ---------------------------------------------------------------------------
# Registry / schema
# ---------------------------------------------------------------------------


def test_isv01_art_method_registry_matches_twelve_expected_ids():
    rows = _method_registry()
    ids = [r["id"] for r in rows]
    assert ids == list(METHOD_CASES.keys())
    assert len(ids) == 12


def test_isv01_era_registry_matches_thirteen_expected_ids():
    rows = _era_registry()
    ids = [r["id"] for r in rows]
    expected = [
        "han",
        "tang",
        "song",
        "ming",
        "qing",
        "dunhuang",
        "wuxia",
        "xianxia",
        "heian",
        "edo",
        "classical_greek",
        "hellenistic_greek",
        "roman_imperial",
    ]
    assert ids == expected
    assert len(ids) == 13


@pytest.mark.parametrize("method_id", list(METHOD_CASES.keys()))
def test_isv01_art_method_schema_and_loader(method_id: str):
    schema = _load("data/schemas/art_method.schema.json")
    doc = _method_doc(method_id)
    Draft202012Validator(schema).validate(doc)
    assert doc["id"] == method_id
    assert doc.get("version")
    assert doc["artifact_compatibility"]
    assert "core" in doc["prompt_fragments"]
    cfg = METHOD_CASES[method_id]
    assert cfg["form"] in doc["artifact_compatibility"]


@pytest.mark.parametrize("era_id", list(ERA_CASES.keys()))
def test_isv01_era_pack_schema_loader_and_type(era_id: str):
    schema = _load("data/schemas/era_pack.schema.json")
    doc = _era_doc(era_id)
    Draft202012Validator(schema).validate(doc)
    assert doc["id"] == era_id
    assert doc.get("version")
    assert doc["pack_type"] == ERA_CASES[era_id]["type"]


# ---------------------------------------------------------------------------
# ArtMethod valid-path emission
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("method_id", list(METHOD_CASES.keys()))
def test_isv01_art_method_valid_path_emits_distinctive_instructions(method_id: str):
    cfg = METHOD_CASES[method_id]
    doc = _method_doc(method_id)
    spec = _spec_for_method(method_id)
    _assert_no_lint_errors(spec)
    result = compile_result(spec)
    sections = result["prompt_sections"]
    prompt = result["prompt"]
    low = prompt.casefold()

    assert "transformation_resolution" not in result
    assert "lexical_realization" not in sections
    _core_emitted(sections, doc)
    assert f"Artifact form — {cfg['form'].replace('_', ' ')}" in sections["artifact_form"]
    assert f"Artifact state — {cfg['state'].replace('_', ' ')}" in sections["artifact_state"]

    for token in cfg["must_substrings"]:
        assert token.casefold() in low, (method_id, token)
    for token in cfg["material_tokens"]:
        assert token.casefold() in low, (method_id, token)
    for token in cfg.get("must_not_substrings", []):
        assert token.casefold() not in low, (method_id, token)
    for token in cfg.get("failure_tokens", []):
        if token:
            assert token.casefold() in low, (method_id, token)

    forms = _load("references/artifacts/forms.json")["forms"]
    assert forms[cfg["form"]]["geometry"] in sections["artifact_form"]


def test_isv01_marble_and_bronze_do_not_collapse():
    marble = compile_result(_spec_for_method("marble_sculpture"))["prompt"].casefold()
    bronze = compile_result(_spec_for_method("bronze_sculpture"))["prompt"].casefold()
    assert "carved stone masses" in marble
    assert "cast copper-alloy" in bronze
    assert "cast copper-alloy" not in marble
    assert "carved stone masses" not in bronze


def test_isv01_watercolor_requires_more_than_method_name():
    result = compile_result(_spec_for_method("watercolor"))
    art_method = result["prompt_sections"]["art_method"].casefold()
    material = result["prompt_sections"]["material_behavior"].casefold()
    # Name alone is insufficient; wash/paper/edge semantics must appear.
    assert "transparent layered washes" in art_method
    assert "reserve light" in art_method
    assert "granulate" in art_method
    assert "paper tooth" in material or "capillary" in material
    assert "edges should vary with water" in material


def test_isv01_mineral_mural_not_silently_relabeled_buon_fresco():
    prompt = compile_result(_spec_for_method("mineral_pigment_mural"))["prompt"].casefold()
    assert "mineral-pigment mural" in prompt
    assert "prepared wall" in prompt or "wall ground" in prompt or "mineral wall" in prompt
    assert "buon fresco" not in prompt


def test_isv01_manuscript_not_relabeled_as_standalone_tempera_pack():
    sections = compile_result(_spec_for_method("manuscript_miniature"))["prompt_sections"]
    assert "Manuscript miniature" in sections["art_method"]
    assert "tempera pack" not in sections["art_method"].casefold()
    assert "book page" in sections["artifact_form"].casefold()


def test_isv01_extended_profile_emits_evaluation_criteria_conditionally():
    spec = _spec_for_method("watercolor")
    spec["output"]["profile"] = "extended"
    sections = compile_result(spec)["prompt_sections"]
    assert "audit_notes" in sections
    for criterion in _method_doc("watercolor")["evaluation_criteria"][:3]:
        assert criterion in sections["audit_notes"]


def test_isv01_field_emission_contract_documents_intentional_omissions():
    """Non-emission of metadata/eval fields is not automatically a defect."""
    doc = _method_doc("watercolor")
    sections = compile_result(_spec_for_method("watercolor"))["prompt_sections"]
    prompt = "\n".join(sections.values())
    for field in EMITTED_BY_STANDARD_COMPILER:
        assert field in doc
    # Standard path does not dump fabrication_process list verbatim.
    assert doc["fabrication_process"][0] not in prompt
    assert "sources" in INTENTIONAL_NON_EMISSION_OR_CONDITIONAL
    assert "evaluation_criteria" in INTENTIONAL_NON_EMISSION_OR_CONDITIONAL


# ---------------------------------------------------------------------------
# Era / overlay valid-path emission
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("era_id", list(ERA_CASES.keys()))
def test_isv01_era_valid_context_emits_or_overlays(era_id: str):
    cfg = ERA_CASES[era_id]
    spec = _spec_for_era(era_id)
    _assert_no_lint_errors(spec)
    result = compile_result(spec)
    sections = result["prompt_sections"]
    prompt = result["prompt"].casefold()
    assert cfg["expect_name"].casefold() in sections["historical"].casefold()
    for token in cfg.get("anchor_tokens", []):
        assert token.casefold() in prompt
    if cfg["type"] in {"genre_overlay", "fantasy_overlay"}:
        overlay_key = f"overlay_{era_id}"
        assert overlay_key in sections
        for token in cfg.get("overlay_tokens", []):
            assert token.casefold() in sections[overlay_key].casefold() or token.casefold() in prompt
    else:
        # Base historical/site packs emit selective anchors when no transformation.
        era_key = f"era_{era_id if era_id != 'dunhuang' else 'dunhuang'}"
        # dunhuang may share section with tang; at least one era_* section expected
        era_sections = [k for k in sections if k.startswith("era_") and not k.startswith("era_fragment")]
        assert era_sections, (era_id, sorted(sections))
        for token in cfg.get("fragment_tokens", []):
            assert token.casefold() in prompt


def test_isv01_overlays_are_not_classified_as_historical_periods():
    assert _era_doc("wuxia")["pack_type"] == "genre_overlay"
    assert _era_doc("xianxia")["pack_type"] == "fantasy_overlay"
    assert "Not an era" in _era_doc("wuxia")["period"] or "overlay" in _era_doc("wuxia")["summary"].casefold()
    assert _era_doc("dunhuang")["pack_type"] == "site_tradition"


# ---------------------------------------------------------------------------
# Combinations + compatibility gates
# ---------------------------------------------------------------------------


def test_isv01_combo_classical_living_versus_marble():
    living = _minimal_spec(
        id="isv01-combo-classical-living",
        route="historical_portrait",
        request="Classical Greek living portrait.",
        historical={"packs": ["classical_greek"]},
        art={"method": None, "artifact_form": None, "artifact_state": None},
        body_transformation={"mode": "presentation_only"},
    )
    marble = _spec_for_method("marble_sculpture")
    _assert_no_lint_errors(living)
    _assert_no_lint_errors(marble)
    living_sections = compile_result(living)["prompt_sections"]
    marble_sections = compile_result(marble)["prompt_sections"]
    assert "art_method" not in living_sections
    assert "living adult figure" in living_sections.get("era_fragment_classical_greek", "").casefold()
    assert "marble sculpture" in marble_sections["art_method"].casefold()
    assert "not a marble statue" in living_sections.get("era_fragment_classical_greek", "").casefold()


def test_isv01_combo_hellenistic_marble():
    result = compile_result(_spec_for_era("hellenistic_greek"))
    sections = result["prompt_sections"]
    assert "Hellenistic Greek" in sections["historical"]
    assert "Marble sculpture" in sections["art_method"]


def test_isv01_combo_roman_bronze():
    result = compile_result(_spec_for_era("roman_imperial"))
    sections = result["prompt_sections"]
    assert "Roman Imperial" in sections["historical"]
    assert "Bronze sculpture" in sections["art_method"]
    assert "cast" in sections["art_method"].casefold()


def test_isv01_combo_ming_wuxia():
    result = compile_result(_spec_for_era("wuxia"))
    sections = result["prompt_sections"]
    assert "Ming dynasty + Wuxia" in sections["historical"]
    assert "overlay_wuxia" in sections
    assert "martial" in sections["overlay_wuxia"].casefold()


def test_isv01_combo_xianxia_fantasy_hybrid():
    result = compile_result(_spec_for_era("xianxia"))
    sections = result["prompt_sections"]
    assert "fantasy_hybrid" in sections["historical"]
    assert "Xianxia" in sections["historical"]
    assert "overlay_xianxia" in sections
    assert "hybrids" in sections


def test_isv01_combo_edo_woodblock():
    result = compile_result(_spec_for_era("edo"))
    assert "Japanese woodblock print" in result["prompt_sections"]["art_method"]
    assert "registration" in result["prompt"].casefold()


def test_isv01_combo_song_ink():
    result = compile_result(_spec_for_era("song"))
    assert "Chinese ink painting" in result["prompt_sections"]["art_method"]
    assert "Song dynasty" in result["prompt_sections"]["historical"]


def test_isv01_combo_dunhuang_mural():
    result = compile_result(_spec_for_era("dunhuang"))
    sections = result["prompt_sections"]
    assert "Dunhuang" in sections["historical"]
    assert "mineral-pigment mural" in sections["art_method"].casefold()
    assert "wall surface" in sections["artifact_form"].casefold()


def test_isv01_combo_contemporary_watercolor_album_leaf():
    """Watercolor has no living-portrait form; album_leaf is the valid installed path."""
    result = compile_result(_spec_for_method("watercolor"))
    assert "album leaf" in result["prompt_sections"]["artifact_form"].casefold()
    assert "transparent layered washes" in result["prompt_sections"]["art_method"].casefold()


def test_isv01_combo_contemporary_paper_cut():
    result = compile_result(_spec_for_method("paper_cut_layered"))
    assert "popup diorama" in result["prompt_sections"]["artifact_form"].casefold()
    assert "layered" in result["prompt_sections"]["art_method"].casefold()


def test_isv01_combo_manuscript_and_embroidery_surfaces():
    manuscript = compile_result(_spec_for_method("manuscript_miniature"))
    embroidery = compile_result(_spec_for_method("embroidery_textile"))
    assert "Manuscript miniature" in manuscript["prompt_sections"]["art_method"]
    assert "book page" in manuscript["prompt_sections"]["artifact_form"].casefold()
    assert "Embroidery" in embroidery["prompt_sections"]["art_method"]
    assert "stitch" in embroidery["prompt"].casefold()


def test_isv01_reject_wuxia_as_sole_era():
    spec = _minimal_spec(
        id="isv01-reject-wuxia-only",
        route="historical_portrait",
        request="Wuxia alone as historical era.",
        historical={"packs": ["wuxia"]},
        art={"method": None},
        body_transformation={"mode": "presentation_only"},
    )
    findings = lint_spec(spec)
    assert any(f["code"] == "genre_as_era" and f["level"] == "error" for f in findings)
    with pytest.raises(ValueError, match="Cannot compile invalid spec"):
        compile_result(spec)


def test_isv01_reject_dunhuang_strict_without_subperiod():
    spec = _spec_for_era("dunhuang")
    spec["historical"]["strictness"] = "strict_reconstruction"
    spec["historical"]["subperiod"] = None
    findings = lint_spec(spec)
    assert any(f["code"] == "dunhuang_strict_narrowing" and f["level"] == "error" for f in findings)


def test_isv01_reject_incompatible_art_form():
    spec = _spec_for_method("watercolor")
    spec["art"]["artifact_form"] = "free_standing_statue"
    findings = lint_spec(spec)
    assert any(f["code"] == "art_form_incompatible" and f["level"] == "error" for f in findings)


def test_isv01_reject_xianxia_without_base():
    spec = _minimal_spec(
        id="isv01-reject-xianxia-only",
        route="historical_portrait",
        request="Xianxia alone as historical era.",
        historical={"packs": ["xianxia"], "strictness": "fantasy_hybrid"},
        art={"method": None},
        body_transformation={"mode": "presentation_only"},
    )
    findings = lint_spec(spec)
    assert any(f["code"] == "genre_as_era" and f["level"] == "error" for f in findings)
