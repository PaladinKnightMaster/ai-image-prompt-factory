"""Creative PromptRecipe library (PR-CR-001): worktree recipes under recipes/."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json
import re

from aipf.recipes import (
    compile_recipe,
    load_recipe,
    resolve_recipe,
    sha256_canonical,
    validate_recipe,
)

ROOT = Path(__file__).resolve().parents[1]
RECIPES_ROOT = ROOT / "recipes"
CR001_PATH = RECIPES_ROOT / "cr-001-material-driven-fashion-editorial" / "1.0.0.json"
CR001_ID = "cr-001-material-driven-fashion-editorial"
CR001_VERSION = "1.0.0"
CR002_PATH = RECIPES_ROOT / "cr-002-song-corridor-editorial" / "1.0.0.json"
CR002_ID = "cr-002-song-corridor-editorial"
CR002_VERSION = "1.0.0"
CR002_KNOWN_RECIPE_SHA = "072b0c6397dc99a907c5a6b02b3f1dc6b335480720b5b08ca7281127fd113c46"
CR002_KNOWN_PROMPT_SHA = "99b9e5d3c0f79a5e812d14b3a3b09662783690c2839cfdcc7e4e347945899a51"
ALLOWED_VARIABLE_TARGETS = frozenset(
    {"director.camera", "director.light_source", "output.aspect_ratio"}
)
ASPECT_VOCAB = frozenset({"1:1", "4:5"})
RECIPE_ID_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
RECIPE_VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


def _errors(findings: list[dict]) -> list[dict]:
    return [f for f in findings if f["level"] == "error"]


def _iter_library_recipes() -> list[Path]:
    if not RECIPES_ROOT.is_dir():
        return []
    return sorted(
        p
        for p in RECIPES_ROOT.rglob("*.json")
        if p.is_file() and not any(part.startswith(".") for part in p.parts)
    )


def _nested_get(obj: dict, dotted: str):
    cur = obj
    for part in dotted.split("."):
        cur = cur[part]
    return cur


def test_cr001_file_exists_and_path_matches_identity():
    assert CR001_PATH.is_file()
    assert CR001_PATH.parent.name == CR001_ID
    assert CR001_PATH.stem == CR001_VERSION


def test_cr001_loads_and_schema_validation_passes():
    recipe = load_recipe(CR001_PATH)
    findings = validate_recipe(recipe)
    assert _errors(findings) == [], findings
    assert recipe["recipe_schema_version"] == "1.1"
    assert recipe["recipe_id"] == CR001_ID
    assert recipe["recipe_version"] == CR001_VERSION
    assert RECIPE_ID_RE.fullmatch(recipe["recipe_id"])
    assert RECIPE_VERSION_RE.fullmatch(recipe["recipe_version"])


def test_cr001_semantic_spec_is_complete_living_editorial():
    recipe = load_recipe(CR001_PATH)
    spec = recipe["semantic_spec"]
    assert spec["route"] == "new_generation"
    assert spec["historical"]["packs"] == []
    assert spec["art"]["method"] is None
    assert spec["art"]["artifact_form"] is None
    assert spec["art"]["artifact_state"] is None
    assert spec["identity"]["mode"] == "identity_unlocked"
    assert spec["body_transformation"]["mode"] == "presentation_only"
    assert spec["body_transformation"].get("garment_shaping")
    assert spec["director"].get("fabric_response")
    assert spec["director"].get("material_response")
    assert spec["director"].get("camera")
    assert spec["director"].get("light_source")
    assert spec["output"]["aspect_ratio"] == "4:5"
    assert spec["output"].get("generation_requested") is False
    assert "TODO" not in json.dumps(spec)
    assert "<" not in spec["request"]
    assert "placeholder" not in json.dumps(spec).casefold()


def test_cr001_variables_follow_v11_allowlist_and_baselines():
    recipe = load_recipe(CR001_PATH)
    variables = recipe.get("variables") or {}
    assert 1 <= len(variables) <= 3
    targets = []
    for name, definition in variables.items():
        assert re.fullmatch(r"^[a-z][a-z0-9_]*$", name)
        assert definition["type"] == "enum"
        assert definition["target"] in ALLOWED_VARIABLE_TARGETS
        choices = definition["choices"]
        assert 2 <= len(choices) <= 8
        assert len(choices) == len(set(choices))
        baseline = _nested_get(recipe["semantic_spec"], definition["target"])
        assert baseline in choices
        if definition["target"] == "output.aspect_ratio":
            assert set(choices) <= ASPECT_VOCAB
        targets.append(definition["target"])
    assert len(targets) == len(set(targets))


def test_cr001_compiles_locally_without_generation_and_hashes_stable():
    recipe = load_recipe(CR001_PATH)
    original = deepcopy(recipe)
    first = compile_recipe(recipe)
    second = compile_recipe(recipe)
    assert recipe == original
    assert first == second
    assert first["recipe"]["recipe_id"] == CR001_ID
    assert first["recipe"]["recipe_version"] == CR001_VERSION
    assert first["recipe"]["recipe_sha256"] == sha256_canonical(recipe)
    assert first["recipe"]["semantic_spec_sha256"] == sha256_canonical(recipe["semantic_spec"])
    prompt = first["compilation"]["prompt"]
    assert prompt.strip()
    assert first["prompt_sha256"] == sha256(prompt.encode("utf-8")).hexdigest()
    assert first["evidence_snapshot_sha256"] == first["compilation"]["evidence_snapshot"]["snapshot_sha256"]
    assert "generation" not in first
    assert resolve_recipe(recipe) == recipe["semantic_spec"]


def test_cr001_optional_binding_changes_only_allowlisted_targets():
    recipe = load_recipe(CR001_PATH)
    baseline = compile_recipe(recipe)
    alt_camera = recipe["variables"]["camera"]["choices"][1]
    alt_light = recipe["variables"]["light"]["choices"][1]
    bound = compile_recipe(
        recipe,
        bindings={"camera": alt_camera, "light": alt_light, "aspect": "1:1"},
    )
    resolved = bound["compilation"]
    # Compare via resolve path embedded in variable_resolution hashes / effective bindings.
    assert bound["variable_resolution"]["effective_bindings"]["camera"] == alt_camera
    assert bound["variable_resolution"]["effective_bindings"]["light"] == alt_light
    assert bound["variable_resolution"]["effective_bindings"]["aspect"] == "1:1"
    assert bound["prompt_sha256"] != baseline["prompt_sha256"]
    assert "1:1" in resolved["prompt"] or resolved["prompt_sections"]["task"].find("1:1") >= 0


def test_cr002_file_exists_and_path_matches_identity():
    assert CR002_PATH.is_file()
    assert CR002_PATH.parent.name == CR002_ID
    assert CR002_PATH.stem == CR002_VERSION


def test_cr002_loads_and_schema_validation_passes():
    recipe = load_recipe(CR002_PATH)
    findings = validate_recipe(recipe)
    assert _errors(findings) == [], findings
    assert recipe["recipe_schema_version"] == "1.1"
    assert recipe["recipe_id"] == CR002_ID
    assert recipe["recipe_version"] == CR002_VERSION
    assert RECIPE_ID_RE.fullmatch(recipe["recipe_id"])
    assert RECIPE_VERSION_RE.fullmatch(recipe["recipe_version"])


def test_cr002_semantic_spec_is_song_informed_photographic_editorial():
    recipe = load_recipe(CR002_PATH)
    spec = recipe["semantic_spec"]
    assert spec["route"] == "new_generation"
    assert spec["historical"]["strictness"] == "historically_informed"
    assert spec["historical"]["packs"] == ["song"]
    assert spec["art"]["method"] is None
    assert spec["art"]["artifact_form"] is None
    assert spec["art"]["artifact_state"] is None
    assert spec["identity"]["mode"] == "identity_unlocked"
    assert spec["body_transformation"]["mode"] == "presentation_only"
    assert spec["output"]["aspect_ratio"] == "4:5"
    assert spec["output"].get("generation_requested") is False
    request = spec["request"].casefold()
    assert "photographic" in request
    assert "beizi" in request
    assert "corridor" in request
    assert "xianxia" in request or "fantasy" in request
    assert "ink painting" in request
    director = json.dumps(spec["director"]).casefold()
    assert "daylight" in director
    assert "silk" in director
    assert "TODO" not in json.dumps(spec)
    assert "placeholder" not in json.dumps(spec).casefold()


def test_cr002_variables_follow_v11_allowlist_and_baselines():
    recipe = load_recipe(CR002_PATH)
    variables = recipe.get("variables") or {}
    assert 1 <= len(variables) <= 3
    targets = []
    for name, definition in variables.items():
        assert re.fullmatch(r"^[a-z][a-z0-9_]*$", name)
        assert definition["type"] == "enum"
        assert definition["target"] in ALLOWED_VARIABLE_TARGETS
        choices = definition["choices"]
        assert 2 <= len(choices) <= 8
        assert len(choices) == len(set(choices))
        baseline = _nested_get(recipe["semantic_spec"], definition["target"])
        assert baseline in choices
        if definition["target"] == "output.aspect_ratio":
            assert set(choices) <= ASPECT_VOCAB
        targets.append(definition["target"])
    assert len(targets) == len(set(targets))


def test_cr002_compiles_deterministically_and_audits_prompt():
    recipe = load_recipe(CR002_PATH)
    original = deepcopy(recipe)
    first = compile_recipe(recipe)
    second = compile_recipe(recipe)
    assert recipe == original
    assert first == second
    assert sha256_canonical(recipe) == CR002_KNOWN_RECIPE_SHA
    assert first["prompt_sha256"] == CR002_KNOWN_PROMPT_SHA
    prompt = first["compilation"]["prompt"]
    assert "Song dynasty" in prompt
    assert "4:5" in prompt
    assert "beizi" in prompt.casefold() or "Beizi" in prompt
    assert "photographic" in prompt.casefold()
    # Documented EraPack limitation: song ink fragment may appear; photographic locks must remain.
    assert "living photographic" in prompt.casefold() or "photographic fashion editorial" in prompt.casefold()
    assert "qing banner" in prompt.casefold() or "Qing banner" in prompt
    assert "god-rays" in prompt or "god-rays" in prompt.casefold()
    # No ArtMethodPack section for null method.
    assert "Art/craft method" not in prompt
    avoid = prompt.casefold()
    assert "tang high-waisted" in avoid
    assert "qing banner" in avoid or "qing" in avoid
    assert "generation" not in first


def test_cr002_optional_binding_changes_only_allowlisted_targets():
    recipe = load_recipe(CR002_PATH)
    baseline = compile_recipe(recipe)
    alt_camera = recipe["variables"]["camera"]["choices"][1]
    alt_light = recipe["variables"]["light"]["choices"][1]
    bound = compile_recipe(
        recipe,
        bindings={"camera": alt_camera, "light": alt_light, "aspect": "1:1"},
    )
    assert bound["variable_resolution"]["effective_bindings"]["camera"] == alt_camera
    assert bound["variable_resolution"]["effective_bindings"]["light"] == alt_light
    assert bound["variable_resolution"]["effective_bindings"]["aspect"] == "1:1"
    assert bound["prompt_sha256"] != baseline["prompt_sha256"]
    assert "1:1" in bound["compilation"]["prompt"]


def test_cr001_unchanged_alongside_cr002():
    recipe = load_recipe(CR001_PATH)
    assert recipe["recipe_id"] == CR001_ID
    assert recipe["semantic_spec"]["historical"]["packs"] == []
    assert compile_recipe(recipe)["recipe"]["recipe_id"] == CR001_ID


def test_library_recipe_id_version_pairs_are_unique_and_path_aligned():
    paths = _iter_library_recipes()
    assert paths, "expected at least one recipe JSON under recipes/"
    pairs: list[tuple[str, str]] = []
    for path in paths:
        recipe = load_recipe(path)
        findings = validate_recipe(recipe)
        assert _errors(findings) == [], (path, findings)
        rid = recipe["recipe_id"]
        ver = recipe["recipe_version"]
        assert path.parent.name == rid, f"folder must equal recipe_id for {path}"
        assert path.stem == ver, f"filename stem must equal recipe_version for {path}"
        pairs.append((rid, ver))
    counts = Counter(pairs)
    duplicates = [pair for pair, n in counts.items() if n > 1]
    assert duplicates == [], f"duplicate recipe_id/version pairs: {duplicates}"


def test_library_rejects_concept_of_silent_inplace_revision_via_hash_contract():
    """Documented immutability: editing released JSON changes recipe_sha256."""
    recipe = load_recipe(CR001_PATH)
    receipt = compile_recipe(recipe)
    mutated = deepcopy(recipe)
    mutated["description"] = (mutated.get("description") or "") + " [edited]"
    assert sha256_canonical(mutated) != receipt["recipe"]["recipe_sha256"]
