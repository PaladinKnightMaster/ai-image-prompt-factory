"""Medium-safe EraPack fragment selection (AIPF-ERA-FRAGMENT-FIX-001)."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json

from aipf.compiler import _era_fragment, compile_result
from aipf.io import load_json
from aipf.recipes import compile_recipe, load_recipe, sha256_canonical

ROOT = Path(__file__).resolve().parents[1]
CR001 = ROOT / "recipes" / "cr-001-material-driven-fashion-editorial" / "1.0.0.json"
CR001_KNOWN_RECIPE_SHA = "60c4547ed59a31dfa1fcebd0dcc959729fff7a2f61d235a1fcb6228724aebdce"
# Adapter/compiler prompt digests for CR-001 remain the provenance contract used elsewhere.
CR001_KNOWN_PROMPT_SHA = "92f4c6643c005281ee2c287d72c05321aa0dd14043513761188a0b05c8e9a7e4"


def _song_pack():
    return load_json("references/eras/song.json")


def _tang_pack():
    return load_json("references/eras/tang.json")


def test_song_photographic_new_generation_omits_ink_fragment():
    pack = _song_pack()
    art = {"method": None}
    assert (
        _era_fragment(pack, art, "new_generation", "garden viewing or travel") is None
    )
    assert _era_fragment(pack, art, "historical_portrait", "garden viewing or travel") is None


def test_song_chinese_ink_painting_keeps_ink_fragment():
    pack = _song_pack()
    art = {"method": "chinese_ink_painting"}
    frag = _era_fragment(pack, art, "art_style_transform", "quiet landscape encounter")
    assert frag is not None
    assert "ink transformation" in frag
    assert "do not simulate a photograph" in frag


def test_tang_lantern_occasion_keeps_lantern_fragment():
    pack = _tang_pack()
    art = {"method": None}
    frag = _era_fragment(
        pack, art, "historical_portrait", "Shangyuan lantern-festival evening"
    )
    assert frag is not None
    assert "lantern festival" in frag.casefold()


def test_tang_historical_portrait_prefers_portrait_not_fallthrough_only():
    pack = _tang_pack()
    frag = _era_fragment(pack, {"method": None}, "historical_portrait", None)
    assert frag is not None
    assert "living person" in frag.casefold() or "court subject" in frag.casefold()


def test_missing_fragment_match_returns_none_without_inventing_text():
    pack = {
        "prompt_fragments": {
            "ink": "For a Song-oriented ink transformation, leave photography."
        }
    }
    assert _era_fragment(pack, {"method": None}, "new_generation", None) is None
    assert _era_fragment(pack, {"method": "marble_sculpture"}, "new_generation", None) is None


def test_compile_song_living_photo_keeps_anchors_without_ink_fragment():
    spec = {
        "version": "3.2",
        "id": "probe-song-photo",
        "request": "Create a photographic Song-informed corridor editorial of an adult woman.",
        "route": "new_generation",
        "locks": {"adult_subject": True},
        "references": [],
        "identity": {"mode": "identity_unlocked", "locked_features": []},
        "body_transformation": {"mode": "presentation_only"},
        "historical": {
            "strictness": "historically_informed",
            "packs": ["song"],
            "subperiod": "Southern Song-inspired",
            "region": "China",
            "role": "court woman",
            "occasion": "garden viewing or travel",
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
            "moment": "pause",
            "action": "standing",
            "gaze": "toward courtyard",
            "body_weight": "grounded",
            "hand_logic": "relaxed",
            "foreground": "floor",
            "midground": "figure",
            "background": "corridor",
            "camera": "eye-level three-quarter full-length editorial frame",
            "light_source": "soft daylight from corridor openings",
            "material_response": "silk",
            "micro_story": "quiet walk",
        },
        "output": {
            "profile": "standard",
            "aspect_ratio": "4:5",
            "text_in_image": [],
            "generation_requested": False,
        },
        "visual_patterns": {"enable_validated": False, "include": [], "exclude": []},
    }
    result = compile_result(spec)
    sections = result["prompt_sections"]
    assert "era_song" in sections
    assert "Song dynasty" in sections["historical"]
    assert "era_fragment_song" not in sections
    assert "ink transformation" not in result["prompt"].casefold()
    assert "do not simulate a photograph with an ink filter" not in result["prompt"].casefold()


def test_compile_song_ink_art_method_keeps_fragment():
    case = json.loads(
        (ROOT / "cases" / "golden" / "09-song-ink-transform" / "case.json").read_text(
            encoding="utf-8"
        )
    )
    spec = {
        k: v
        for k, v in case.items()
        if k not in {"title", "status", "case_record", "notes"}
    }
    result = compile_result(spec)
    assert "era_fragment_song" in result["prompt_sections"]
    assert "ink transformation" in result["prompt_sections"]["era_fragment_song"]


def test_dunhuang_mural_no_longer_imports_tang_living_portrait_fragment():
    case = json.loads(
        (ROOT / "cases" / "golden" / "05-tang-dunhuang-mural" / "case.json").read_text(
            encoding="utf-8"
        )
    )
    spec = {
        k: v
        for k, v in case.items()
        if k not in {"title", "status", "case_record", "notes"}
    }
    result = compile_result(spec)
    sections = result["prompt_sections"]
    assert "era_fragment_dunhuang" in sections
    assert "era_fragment_tang" not in sections
    assert "living person" not in sections.get("era_fragment_dunhuang", "").casefold()
    # Tang historical anchors may still appear via structured fields.
    assert "era_tang" in sections or "Tang" in sections["historical"]


def test_cr001_digests_unchanged():
    recipe = load_recipe(CR001)
    assert sha256_canonical(recipe) == CR001_KNOWN_RECIPE_SHA
    # CR-001 empty packs: fragment selection path is unused; prompt digest stable.
    receipt = compile_recipe(recipe)
    assert receipt["prompt_sha256"] == CR001_KNOWN_PROMPT_SHA
    assert (
        sha256(receipt["compilation"]["prompt"].encode("utf-8")).hexdigest()
        == CR001_KNOWN_PROMPT_SHA
    )
