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
CR002_KNOWN_RECIPE_SHA = "2fc6fc85163206023c77c9d492e0f5437ec4f1ff00f0a2dbb04bcac84c5b59d9"
CR002_KNOWN_PROMPT_SHA = "0bf699d3c75fb89d0df8d48445fbe514f00b43d72e99a8bdb3a13cc71cb873a4"
CR003_PATH = RECIPES_ROOT / "cr-003-refraction-ledger" / "1.0.0.json"
CR003_ID = "cr-003-refraction-ledger"
CR003_VERSION = "1.0.0"
CR003_KNOWN_RECIPE_SHA = "844a63f40d8c1e2fa9339c06f7936daad2d1fb14186372e2b70727078d94f1f3"
CR003_KNOWN_PROMPT_SHA = "e0c131daf9badac5ec5cac960a33e14f928345a299846a5ad767bb50feee271f"
CR004_PATH = RECIPES_ROOT / "cr-004-marble-afterimage" / "1.0.0.json"
CR004_ID = "cr-004-marble-afterimage"
CR004_VERSION = "1.0.0"
CR004_KNOWN_RECIPE_SHA = "232f1fe8f9ab20dc33e5aa70c2469ae02b05e12214214bfedff9d18a666b67c2"
CR004_KNOWN_PROMPT_SHA = "f42f2631e644e037c70ac2bf959c2587eff26fb981ae97dd169cf057b0d3d02d"
CR004_SOURCE_IMAGE_SHA = "0dcf8af6cac15441d5e728f98ac53314442984d3a27a5dd193effa2bac46f41e"
CR005_PATH = RECIPES_ROOT / "cr-005-silk-on-plaster" / "1.0.0.json"
CR005_ID = "cr-005-silk-on-plaster"
CR005_VERSION = "1.0.0"
CR005_KNOWN_RECIPE_SHA = "cfe891967c42206606b278306d8f0e16158aece2610759e8060e3ea5cf0eaf88"
CR005_KNOWN_PROMPT_SHA = "6e3f9d6416fffc05c4e94cf81c3312a80b3564f1cd1689a54bfbe31da13984da"
CR005_SOURCE_IMAGE_SHA = "a457c47cd96633b18d69e218f3316edb9886ea58114b96f2b4c0d1dce18221e0"
CR006_PATH = RECIPES_ROOT / "cr-006-held-light" / "1.0.0.json"
CR006_ID = "cr-006-held-light"
CR006_VERSION = "1.0.0"
CR006_KNOWN_RECIPE_SHA = "2222db4d21923c9ee3e2630fd2bcd4dc14808ce702d48db7588369b9d5798f51"
CR006_KNOWN_PROMPT_SHA = "5bb47d64c127019cd89070cfcaa460401e325e46e38dbdc3d931db36e4947ec4"
CR006_REF_A_IMAGE_SHA = "0dcf8af6cac15441d5e728f98ac53314442984d3a27a5dd193effa2bac46f41e"
CR006_REF_B_IMAGE_SHA = "43a9ff6e0a0aaed177fae1145ac3e1ed88566ab507952c4e68fde97d10b3d1c4"
CR007_PATH = RECIPES_ROOT / "cr-007-porcelain-echo" / "1.0.0.json"
CR007_ID = "cr-007-porcelain-echo"
CR007_VERSION = "1.0.0"
CR007_KNOWN_RECIPE_SHA = "6af6a0756b344d45a4281e882280f593bd3ffed09b54d9be7b0f86ceb14c3b42"
CR007_KNOWN_PROMPT_SHA = "ae067b7b1d6c1b1877cdd1b4f9d39d5ab0e6bc861611178b0c47b68fca4138eb"
CR007_SOURCE_IMAGE_SHA = "a457c47cd96633b18d69e218f3316edb9886ea58114b96f2b4c0d1dce18221e0"
CR009_PATH = RECIPES_ROOT / "cr-009-golden-seam" / "1.0.0.json"
CR009_ID = "cr-009-golden-seam"
CR009_VERSION = "1.0.0"
CR009_KNOWN_RECIPE_SHA = "8bff3467bbe5a1436881098b82eafee239a4644c78b6d08af48a635e196817ed"
CR009_KNOWN_PROMPT_SHA = "7273bd83193d65a47cf97b789aff64bf69abe901a87cbcfe67a08cf900d52f5a"
CR009_SOURCE_IMAGE_SHA = "15b082d7573ee973740553d463aa2693634fcc45a6d0a4d8538dd5e0c4dcbc97"
CR001_KNOWN_RECIPE_SHA = "60c4547ed59a31dfa1fcebd0dcc959729fff7a2f61d235a1fcb6228724aebdce"
CR001_KNOWN_PROMPT_SHA = "92f4c6643c005281ee2c287d72c05321aa0dd14043513761188a0b05c8e9a7e4"
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
    # Post PR #46: Song ink fragment must not appear for null ArtMethod photography.
    sections = first["compilation"]["prompt_sections"]
    assert "era_song" in sections
    assert "era_fragment_song" not in sections
    assert "ink transformation" not in prompt.casefold()
    assert "hybrids" not in sections
    assert recipe["semantic_spec"]["historical"]["intentional_hybrids"] == []
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


def test_cr001_unchanged_alongside_later_creative_recipes():
    recipe = load_recipe(CR001_PATH)
    assert recipe["recipe_id"] == CR001_ID
    assert recipe["semantic_spec"]["historical"]["packs"] == []
    assert sha256_canonical(recipe) == CR001_KNOWN_RECIPE_SHA
    receipt = compile_recipe(recipe)
    assert receipt["recipe"]["recipe_id"] == CR001_ID
    assert receipt["prompt_sha256"] == CR001_KNOWN_PROMPT_SHA


def test_cr002_unchanged_alongside_later_creative_recipes():
    recipe = load_recipe(CR002_PATH)
    assert recipe["recipe_id"] == CR002_ID
    assert sha256_canonical(recipe) == CR002_KNOWN_RECIPE_SHA
    receipt = compile_recipe(recipe)
    assert receipt["prompt_sha256"] == CR002_KNOWN_PROMPT_SHA


def test_cr003_unchanged_alongside_cr004():
    recipe = load_recipe(CR003_PATH)
    assert recipe["recipe_id"] == CR003_ID
    assert sha256_canonical(recipe) == CR003_KNOWN_RECIPE_SHA
    receipt = compile_recipe(recipe)
    assert receipt["prompt_sha256"] == CR003_KNOWN_PROMPT_SHA


def test_cr002_all_variable_combinations_stay_photographic_song():
    recipe = load_recipe(CR002_PATH)
    cams = recipe["variables"]["camera"]["choices"]
    lights = recipe["variables"]["light"]["choices"]
    aspects = recipe["variables"]["aspect"]["choices"]
    assert len(cams) == 3 and len(lights) == 3 and len(aspects) == 2
    for camera in cams:
        for light in lights:
            for aspect in aspects:
                bound = compile_recipe(
                    recipe, bindings={"camera": camera, "light": light, "aspect": aspect}
                )
                prompt = bound["compilation"]["prompt"]
                sections = bound["compilation"]["prompt_sections"]
                assert "era_song" in sections
                assert "era_fragment_song" not in sections
                assert "ink transformation" not in prompt.casefold()
                assert "hybrids" not in sections
                assert camera in prompt
                assert light in prompt
                assert aspect in prompt
                assert "beizi" in prompt.casefold()
                assert "corridor" in prompt.casefold()


def test_cr003_file_exists_and_path_matches_identity():
    assert CR003_PATH.is_file()
    assert CR003_PATH.parent.name == CR003_ID
    assert CR003_PATH.stem == CR003_VERSION


def test_cr003_loads_and_schema_validation_passes():
    recipe = load_recipe(CR003_PATH)
    findings = validate_recipe(recipe)
    assert _errors(findings) == [], findings
    assert recipe["recipe_schema_version"] == "1.1"
    assert recipe["recipe_id"] == CR003_ID
    assert recipe["recipe_version"] == CR003_VERSION
    assert RECIPE_ID_RE.fullmatch(recipe["recipe_id"])
    assert RECIPE_VERSION_RE.fullmatch(recipe["recipe_version"])


def test_cr003_semantic_spec_is_luxury_product_still_life():
    recipe = load_recipe(CR003_PATH)
    spec = recipe["semantic_spec"]
    assert spec["route"] == "new_generation"
    assert spec["historical"]["packs"] == []
    assert spec["art"]["method"] is None
    assert spec["art"]["artifact_form"] is None
    assert spec["art"]["artifact_state"] is None
    assert spec["identity"]["mode"] == "identity_unlocked"
    assert spec["body_transformation"]["mode"] == "presentation_only"
    assert spec["output"]["aspect_ratio"] == "4:5"
    assert spec["output"].get("generation_requested") is False
    request = spec["request"].casefold()
    assert "photographic" in request
    assert "glass" in request
    assert "perfume" in request or "flacon" in request
    assert "limestone" in request or "plinth" in request
    assert "brushed" in request
    locked = json.dumps(spec.get("locks") or {}).casefold()
    assert "no_human" in locked or "product_only" in locked or "still_life" in locked
    director = json.dumps(spec["director"]).casefold()
    assert "glass" in director
    assert "metal" in director or "brushed" in director
    assert "stone" in director or "limestone" in director or "plinth" in director
    assert "TODO" not in json.dumps(spec)
    assert "placeholder" not in json.dumps(spec).casefold()
    # Product still-life must not borrow fashion/portrait framing.
    blob = json.dumps(spec).casefold()
    assert "evening gown" not in blob
    assert "chignon" not in blob
    assert "beizi" not in blob
    assert "xianxia" not in blob


def test_cr003_variables_follow_v11_allowlist_and_baselines():
    recipe = load_recipe(CR003_PATH)
    variables = recipe.get("variables") or {}
    assert set(variables) == {"camera", "light", "aspect"}
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
    assert len(variables["camera"]["choices"]) == 3
    assert len(variables["light"]["choices"]) == 3
    assert set(variables["aspect"]["choices"]) == {"4:5", "1:1"}


def test_cr003_compiles_deterministically_and_audits_prompt():
    recipe = load_recipe(CR003_PATH)
    original = deepcopy(recipe)
    first = compile_recipe(recipe)
    second = compile_recipe(recipe)
    assert recipe == original
    assert first == second
    assert sha256_canonical(recipe) == CR003_KNOWN_RECIPE_SHA
    assert first["prompt_sha256"] == CR003_KNOWN_PROMPT_SHA
    prompt = first["compilation"]["prompt"]
    sections = first["compilation"]["prompt_sections"]
    low = prompt.casefold()
    assert "4:5" in prompt
    assert "photographic" in low
    assert "glass" in low
    assert "brushed" in low
    assert "plinth" in low or "limestone" in low
    assert "Art/craft method" not in prompt
    assert "era_" not in sections  # no historical packs
    assert "hybrids" not in sections
    assert "generation" not in first
    # Avoid portrait / historical / painterly leakage.
    assert "evening gown" not in low
    assert "beizi" not in low
    assert "song dynasty" not in low
    assert "ink painting" not in low
    assert "portrait of" not in low
    # No impossible optical-simulation promises.
    assert "physically accurate ray" not in low
    assert "scientifically verified optics" not in low
    assert "guaranteed caustic accuracy" not in low


def test_cr003_optional_binding_changes_only_allowlisted_targets():
    recipe = load_recipe(CR003_PATH)
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


def test_cr003_all_variable_combinations_keep_product_identity():
    recipe = load_recipe(CR003_PATH)
    cams = recipe["variables"]["camera"]["choices"]
    lights = recipe["variables"]["light"]["choices"]
    aspects = recipe["variables"]["aspect"]["choices"]
    assert len(cams) == 3 and len(lights) == 3 and len(aspects) == 2
    # Lighting choices must not internally contradict bright-field vs dark-field.
    for light in lights:
        low = light.casefold()
        claims_bright = "bright-field" in low or "bright field" in low
        claims_dark = "dark-field" in low or "dark field" in low
        assert not (claims_bright and claims_dark), light
    for camera in cams:
        for light in lights:
            for aspect in aspects:
                bound = compile_recipe(
                    recipe, bindings={"camera": camera, "light": light, "aspect": aspect}
                )
                prompt = bound["compilation"]["prompt"]
                low = prompt.casefold()
                assert camera in prompt
                assert light in prompt
                assert aspect in prompt
                assert "glass" in low
                assert "brushed" in low
                assert "plinth" in low or "limestone" in low
                assert "transparent" in low or "clear glass" in low or "faceted" in low
                assert "evening gown" not in low
                assert "beizi" not in low
                assert "song dynasty" not in low
                assert "Art/craft method" not in prompt


def test_cr004_file_exists_and_path_matches_identity():
    assert CR004_PATH.is_file()
    assert CR004_PATH.parent.name == CR004_ID
    assert CR004_PATH.stem == CR004_VERSION


def test_cr004_loads_and_schema_validation_passes():
    recipe = load_recipe(CR004_PATH)
    findings = validate_recipe(recipe)
    assert _errors(findings) == [], findings
    assert recipe["recipe_schema_version"] == "1.1"
    assert recipe["recipe_id"] == CR004_ID
    assert recipe["recipe_version"] == CR004_VERSION
    assert RECIPE_ID_RE.fullmatch(recipe["recipe_id"])
    assert RECIPE_VERSION_RE.fullmatch(recipe["recipe_version"])


def test_cr004_semantic_spec_is_source_backed_marble_transformation():
    recipe = load_recipe(CR004_PATH)
    spec = recipe["semantic_spec"]
    assert spec["route"] == "artifact_transform"
    assert spec["route"] != "new_generation"
    assert spec["transformation"]["pack_id"] == "portrait_to_volumetric_sculpture"
    assert spec["transformation"]["source_representation"] == "portrait"
    assert spec["art"]["method"] == "marble_sculpture"
    assert spec["art"]["artifact_form"] == "free_standing_statue"
    assert spec["art"]["artifact_state"] == "newly_created"
    assert spec["historical"]["packs"] == []
    assert spec["identity"]["mode"] == "recognizable_identity"
    assert spec["body_transformation"]["mode"] == "artistic_stylization"
    assert spec["output"]["aspect_ratio"] == "4:5"
    assert spec["output"].get("generation_requested") is False
    refs = spec["references"]
    assert len(refs) == 1
    assert set(refs[0]["roles"]) >= {"identity", "pose", "outfit"}
    notes = (refs[0].get("notes") or "").casefold()
    assert CR004_SOURCE_IMAGE_SHA in notes
    request = spec["request"].casefold()
    assert "marble" in request
    assert "sculpture" in request or "statue" in request
    assert "photograph" in request or "source" in request
    assert "not a classical greek reconstruction" in request
    assert "not an ancient excavated antiquity" in request
    blob = json.dumps(spec).casefold()
    assert "TODO" not in json.dumps(spec)
    assert "placeholder" not in blob
    assert "xianxia" not in blob


def test_cr004_variables_follow_v11_allowlist_and_baselines():
    recipe = load_recipe(CR004_PATH)
    variables = recipe.get("variables") or {}
    assert 1 <= len(variables) <= 3
    assert "camera" in variables
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
    assert len(variables["camera"]["choices"]) >= 2


def test_cr004_compiles_as_transformation_not_unreferenced_new_generation():
    recipe = load_recipe(CR004_PATH)
    original = deepcopy(recipe)
    first = compile_recipe(recipe)
    second = compile_recipe(recipe)
    assert recipe == original
    assert first == second
    assert sha256_canonical(recipe) == CR004_KNOWN_RECIPE_SHA
    assert first["prompt_sha256"] == CR004_KNOWN_PROMPT_SHA
    prompt = first["compilation"]["prompt"]
    sections = first["compilation"]["prompt_sections"]
    low = prompt.casefold()
    assert "4:5" in prompt
    assert "references" in sections
    assert "transformation" in sections
    assert "artifact_form" in sections
    assert "portrait" in low
    assert "volumetric_sculpture" in prompt
    assert "marble" in low
    assert "free standing" in low or "free-standing" in low
    assert "carved" in low
    assert "living skin" in low
    assert "classical greek reconstruction" in low  # explicit negation in request
    assert "song dynasty" not in low
    assert "beizi" not in low
    assert "perfume flacon" not in low
    assert "generation" not in first
    # Negative: dropping transformation silently changes the contract away from source-backed transform.
    mutated = deepcopy(recipe)
    mutated["semantic_spec"]["route"] = "new_generation"
    del mutated["semantic_spec"]["transformation"]
    mutated_receipt = compile_recipe(mutated)
    mutated_sections = mutated_receipt["compilation"]["prompt_sections"]
    assert "transformation" not in mutated_sections
    assert mutated_receipt["prompt_sha256"] != first["prompt_sha256"]


def test_cr004_camera_bindings_preserve_transformation_contract():
    recipe = load_recipe(CR004_PATH)
    cams = recipe["variables"]["camera"]["choices"]
    assert len(cams) >= 2
    for camera in cams:
        bound = compile_recipe(recipe, bindings={"camera": camera})
        prompt = bound["compilation"]["prompt"]
        sections = bound["compilation"]["prompt_sections"]
        assert camera in prompt
        assert "transformation" in sections
        assert "references" in sections
        assert recipe["semantic_spec"]["route"] == "artifact_transform"
        assert "marble" in prompt.casefold()
        assert "perfume flacon" not in prompt.casefold()


def test_cr005_file_exists_and_path_matches_identity():
    assert CR005_PATH.is_file()
    assert CR005_PATH.parent.name == CR005_ID
    assert CR005_PATH.stem == CR005_VERSION


def test_cr005_loads_and_schema_validation_passes():
    recipe = load_recipe(CR005_PATH)
    findings = validate_recipe(recipe)
    assert _errors(findings) == [], findings
    assert recipe["recipe_schema_version"] == "1.1"
    assert recipe["recipe_id"] == CR005_ID
    assert recipe["recipe_version"] == CR005_VERSION
    assert RECIPE_ID_RE.fullmatch(recipe["recipe_id"])
    assert RECIPE_VERSION_RE.fullmatch(recipe["recipe_version"])


def test_cr005_semantic_spec_is_source_backed_mural_transformation():
    recipe = load_recipe(CR005_PATH)
    spec = recipe["semantic_spec"]
    assert spec["route"] == "artifact_transform"
    assert spec["route"] != "new_generation"
    assert spec["transformation"]["pack_id"] == "portrait_to_architectural_mural"
    assert spec["transformation"]["source_representation"] == "portrait"
    assert spec["art"]["method"] == "mineral_pigment_mural"
    assert spec["art"]["artifact_form"] == "wall_surface"
    assert spec["art"]["artifact_state"] == "newly_created"
    assert spec["historical"]["packs"] == []
    assert spec["identity"]["mode"] == "recognizable_identity"
    assert spec["body_transformation"]["mode"] == "artistic_stylization"
    assert spec["output"]["aspect_ratio"] == "4:5"
    assert spec["output"].get("generation_requested") is False
    refs = spec["references"]
    assert len(refs) == 1
    assert refs[0]["id"] == "cr002-c0-l0-4x5-source"
    assert set(refs[0]["roles"]) == {"identity", "pose", "outfit", "hairstyle"}
    assert "environment" not in refs[0]["roles"]
    notes = refs[0].get("notes") or ""
    assert CR005_SOURCE_IMAGE_SHA in notes
    assert "D:\\" not in notes
    assert "/Users/" not in notes
    request = spec["request"].casefold()
    assert "mural" in request
    assert "plaster" in request
    assert "mineral" in request
    assert "photograph" in request or "source" in request
    assert "not an excavated song-dynasty or dunhuang cave reconstruction" in request
    blob = json.dumps(spec).casefold()
    assert "TODO" not in json.dumps(spec)
    assert "placeholder" not in blob
    assert "perfume flacon" not in blob
    assert "evening gown" not in blob
    assert "marble sculpture" not in blob
    assert "xianxia" not in blob
    # Tracked recipe must not embed host-absolute private paths.
    raw = CR005_PATH.read_text(encoding="utf-8")
    assert "AIPF_Creative_Private" not in raw
    assert "D:\\\\1_PROJECT" not in raw


def test_cr005_variables_follow_v11_allowlist_and_baselines():
    recipe = load_recipe(CR005_PATH)
    variables = recipe.get("variables") or {}
    assert 1 <= len(variables) <= 3
    assert set(variables) == {"camera"}
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
    assert len(variables["camera"]["choices"]) == 3


def test_cr005_compiles_as_architectural_mural_transformation_not_new_generation():
    recipe = load_recipe(CR005_PATH)
    original = deepcopy(recipe)
    first = compile_recipe(recipe)
    second = compile_recipe(recipe)
    assert recipe == original
    assert first == second
    assert sha256_canonical(recipe) == CR005_KNOWN_RECIPE_SHA
    assert first["prompt_sha256"] == CR005_KNOWN_PROMPT_SHA
    prompt = first["compilation"]["prompt"]
    sections = first["compilation"]["prompt_sections"]
    low = prompt.casefold()
    assert "4:5" in prompt
    assert "references" in sections
    assert "transformation" in sections
    assert "artifact_form" in sections
    assert "artifact_state" in sections
    assert "architectural_mural" in prompt
    assert "mineral" in low
    assert "plaster" in low
    assert "wall" in low
    assert "cr002-c0-l0-4x5-source" in prompt
    assert "excavated song-dynasty or dunhuang cave reconstruction" in low
    assert "evening gown" not in low
    assert "perfume flacon" not in low
    assert "marble" not in low
    assert "generation" not in first
    # Negative: dropping transformation silently changes the contract away from mural transform.
    mutated = deepcopy(recipe)
    mutated["semantic_spec"]["route"] = "new_generation"
    del mutated["semantic_spec"]["transformation"]
    mutated_receipt = compile_recipe(mutated)
    mutated_sections = mutated_receipt["compilation"]["prompt_sections"]
    assert "transformation" not in mutated_sections
    assert mutated_receipt["prompt_sha256"] != first["prompt_sha256"]
    assert "architectural_mural" not in mutated_receipt["compilation"]["prompt"]


def test_cr005_camera_bindings_preserve_transformation_contract():
    recipe = load_recipe(CR005_PATH)
    cams = recipe["variables"]["camera"]["choices"]
    assert len(cams) == 3
    for camera in cams:
        bound = compile_recipe(recipe, bindings={"camera": camera})
        prompt = bound["compilation"]["prompt"]
        sections = bound["compilation"]["prompt_sections"]
        assert camera in prompt
        assert "transformation" in sections
        assert "references" in sections
        assert recipe["semantic_spec"]["route"] == "artifact_transform"
        assert "architectural_mural" in prompt
        assert "perfume flacon" not in prompt.casefold()
        assert "evening gown" not in prompt.casefold()


def test_cr006_file_exists_and_path_matches_identity():
    assert CR006_PATH.is_file()
    assert CR006_PATH.parent.name == CR006_ID
    assert CR006_PATH.stem == CR006_VERSION


def test_cr006_loads_and_schema_validation_passes():
    recipe = load_recipe(CR006_PATH)
    findings = validate_recipe(recipe)
    assert _errors(findings) == [], findings
    assert recipe["recipe_schema_version"] == "1.1"
    assert recipe["recipe_id"] == CR006_ID
    assert recipe["recipe_version"] == CR006_VERSION
    assert RECIPE_ID_RE.fullmatch(recipe["recipe_id"])
    assert RECIPE_VERSION_RE.fullmatch(recipe["recipe_version"])


def test_cr006_semantic_spec_is_two_reference_fragrance_campaign():
    recipe = load_recipe(CR006_PATH)
    spec = recipe["semantic_spec"]
    assert spec["route"] == "new_generation"
    assert spec["route"] != "artifact_transform"
    assert "transformation" not in spec
    assert spec["art"]["method"] is None
    assert spec["historical"]["packs"] == []
    assert spec["identity"]["mode"] == "recognizable_identity"
    assert spec["body_transformation"]["mode"] == "presentation_only"
    assert spec["output"]["aspect_ratio"] == "4:5"
    assert spec["output"].get("generation_requested") is False
    refs = spec["references"]
    assert len(refs) == 2
    assert refs[0]["id"] == "cr001-c0-l0-4x5-source"
    assert refs[1]["id"] == "cr003-c0-l0-4x5-source"
    assert set(refs[0]["roles"]) == {"identity", "outfit", "hairstyle"}
    assert "pose" not in refs[0]["roles"]
    assert "environment" not in refs[0]["roles"]
    assert set(refs[1]["roles"]) == {"artifact"}
    assert "environment" not in refs[1]["roles"]
    assert set(refs[0]["roles"]).isdisjoint(set(refs[1]["roles"]))
    notes_a = refs[0].get("notes") or ""
    notes_b = refs[1].get("notes") or ""
    assert CR006_REF_A_IMAGE_SHA in notes_a
    assert CR006_REF_B_IMAGE_SHA in notes_b
    assert "D:\\" not in notes_a and "D:\\" not in notes_b
    assert "/Users/" not in notes_a and "/Users/" not in notes_b
    request = spec["request"].casefold()
    assert "fragrance" in request or "perfume" in request
    assert "two references" in request or "fashion-subject reference" in request
    assert "hand-held" in request or "holding" in request
    blob = json.dumps(spec).casefold()
    assert "TODO" not in json.dumps(spec)
    assert "placeholder" not in blob
    assert "marble sculpture" not in blob
    assert "mineral-pigment mural" not in blob
    assert "song-dynasty" not in blob
    assert "dunhuang" not in blob
    assert "xianxia" not in blob
    raw = CR006_PATH.read_text(encoding="utf-8")
    assert "AIPF_Creative_Private" not in raw
    assert "D:\\\\1_PROJECT" not in raw


def test_cr006_variables_follow_v11_allowlist_and_baselines():
    recipe = load_recipe(CR006_PATH)
    variables = recipe.get("variables") or {}
    assert 1 <= len(variables) <= 3
    assert set(variables) == {"camera"}
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
    assert len(variables["camera"]["choices"]) == 3


def test_cr006_compiles_with_independent_reference_roles_and_ordering():
    recipe = load_recipe(CR006_PATH)
    original = deepcopy(recipe)
    first = compile_recipe(recipe)
    second = compile_recipe(recipe)
    assert recipe == original
    assert first == second
    assert sha256_canonical(recipe) == CR006_KNOWN_RECIPE_SHA
    assert first["prompt_sha256"] == CR006_KNOWN_PROMPT_SHA
    prompt = first["compilation"]["prompt"]
    sections = first["compilation"]["prompt_sections"]
    low = prompt.casefold()
    assert "4:5" in prompt
    assert "references" in sections
    assert "transformation" not in sections
    ref_clause = sections["references"]
    assert "cr001-c0-l0-4x5-source supplies identity, outfit, hairstyle only" in ref_clause
    assert "cr003-c0-l0-4x5-source supplies artifact only" in ref_clause
    assert ref_clause.index("cr001-c0-l0-4x5-source") < ref_clause.index("cr003-c0-l0-4x5-source")
    assert "do not import unassigned" in ref_clause.casefold()
    assert "champagne satin" in low or "satin" in low
    assert "perfume" in low or "flacon" in low
    assert "brushed-metal" in low or "brushed metal" in low
    assert "limestone plinth" in low
    assert "without importing its limestone plinth" in low
    assert "marble" not in low
    assert "mineral-pigment" not in low
    assert "architectural mural" not in low
    assert "generation" not in first


def test_cr006_negative_reference_removal_changes_compiled_semantics():
    recipe = load_recipe(CR006_PATH)
    baseline = compile_recipe(recipe)
    baseline_refs = baseline["compilation"]["prompt_sections"]["references"]

    drop_a = deepcopy(recipe)
    drop_a["semantic_spec"]["references"] = [
        r for r in drop_a["semantic_spec"]["references"] if r["id"] != "cr001-c0-l0-4x5-source"
    ]
    receipt_a = compile_recipe(drop_a)
    refs_a = receipt_a["compilation"]["prompt_sections"]["references"]
    assert receipt_a["prompt_sha256"] != baseline["prompt_sha256"]
    assert "cr001-c0-l0-4x5-source" not in refs_a
    assert "cr003-c0-l0-4x5-source supplies artifact only" in refs_a
    assert refs_a != baseline_refs

    drop_b = deepcopy(recipe)
    drop_b["semantic_spec"]["references"] = [
        r for r in drop_b["semantic_spec"]["references"] if r["id"] != "cr003-c0-l0-4x5-source"
    ]
    receipt_b = compile_recipe(drop_b)
    refs_b = receipt_b["compilation"]["prompt_sections"]["references"]
    assert receipt_b["prompt_sha256"] != baseline["prompt_sha256"]
    assert receipt_b["prompt_sha256"] != receipt_a["prompt_sha256"]
    assert "cr003-c0-l0-4x5-source" not in refs_b
    assert "cr001-c0-l0-4x5-source supplies identity, outfit, hairstyle only" in refs_b

    drop_both = deepcopy(recipe)
    drop_both["semantic_spec"]["references"] = []
    receipt_both = compile_recipe(drop_both)
    assert "references" not in receipt_both["compilation"]["prompt_sections"]
    assert receipt_both["prompt_sha256"] != baseline["prompt_sha256"]


def test_cr006_camera_bindings_preserve_two_reference_contract():
    recipe = load_recipe(CR006_PATH)
    cams = recipe["variables"]["camera"]["choices"]
    assert len(cams) == 3
    for camera in cams:
        bound = compile_recipe(recipe, bindings={"camera": camera})
        prompt = bound["compilation"]["prompt"]
        sections = bound["compilation"]["prompt_sections"]
        assert camera in prompt
        assert "references" in sections
        assert "transformation" not in sections
        assert recipe["semantic_spec"]["route"] == "new_generation"
        assert "cr001-c0-l0-4x5-source" in sections["references"]
        assert "cr003-c0-l0-4x5-source" in sections["references"]
        assert "architectural mural" not in prompt.casefold()
        assert "marble sculpture" not in prompt.casefold()


def test_cr007_file_exists_and_path_matches_identity():
    assert CR007_PATH.is_file()
    assert CR007_PATH.parent.name == CR007_ID
    assert CR007_PATH.stem == CR007_VERSION


def test_cr007_loads_and_schema_validation_passes():
    recipe = load_recipe(CR007_PATH)
    findings = validate_recipe(recipe)
    assert _errors(findings) == [], findings
    assert recipe["recipe_schema_version"] == "1.1"
    assert recipe["recipe_id"] == CR007_ID
    assert recipe["recipe_version"] == CR007_VERSION
    assert RECIPE_ID_RE.fullmatch(recipe["recipe_id"])
    assert RECIPE_VERSION_RE.fullmatch(recipe["recipe_version"])


def test_cr007_semantic_spec_is_source_backed_decorated_artifact_transformation():
    recipe = load_recipe(CR007_PATH)
    spec = recipe["semantic_spec"]
    assert spec["route"] == "artifact_transform"
    assert spec["route"] != "new_generation"
    assert spec["transformation"]["pack_id"] == "portrait_to_decorated_artifact"
    assert spec["transformation"]["source_representation"] == "portrait"
    assert "ceramic.porcelain_body" in spec["transformation"]["selected_concepts"]
    assert spec["art"]["method"] == "blue_white_ceramic"
    assert spec["art"]["artifact_form"] == "vase"
    assert spec["art"]["artifact_state"] == "newly_created"
    assert spec["historical"]["packs"] == []
    assert spec["identity"]["mode"] == "recognizable_identity"
    assert spec["body_transformation"]["mode"] == "artistic_stylization"
    assert spec["output"]["aspect_ratio"] == "4:5"
    assert spec["output"].get("generation_requested") is False
    refs = spec["references"]
    assert len(refs) == 1
    assert refs[0]["id"] == "cr002-c0-l0-4x5-source"
    assert set(refs[0]["roles"]) == {"identity", "pose", "outfit", "hairstyle"}
    assert "environment" not in refs[0]["roles"]
    notes = refs[0].get("notes") or ""
    assert CR007_SOURCE_IMAGE_SHA in notes
    assert "D:\\" not in notes
    assert "/Users/" not in notes
    request = spec["request"].casefold()
    assert "porcelain" in request or "ceramic" in request
    assert "vase" in request
    assert "underglaze" in request or "cobalt" in request
    assert "photograph" in request or "source" in request
    assert "not present the object as an authenticated song-dynasty artifact" in request
    blob = json.dumps(spec).casefold()
    assert "TODO" not in json.dumps(spec)
    assert "placeholder" not in blob
    assert "perfume flacon" not in blob
    assert "evening gown" not in blob
    assert "marble sculpture" not in blob
    assert "mineral-pigment mural" not in blob
    assert "fragrance" not in blob
    assert "xianxia" not in blob
    raw = CR007_PATH.read_text(encoding="utf-8")
    assert "AIPF_Creative_Private" not in raw
    assert "D:\\\\1_PROJECT" not in raw


def test_cr007_variables_follow_v11_allowlist_and_baselines():
    recipe = load_recipe(CR007_PATH)
    variables = recipe.get("variables") or {}
    assert 1 <= len(variables) <= 3
    assert set(variables) == {"camera"}
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
    assert len(variables["camera"]["choices"]) == 2


def test_cr007_compiles_as_decorated_artifact_transformation_not_new_generation():
    recipe = load_recipe(CR007_PATH)
    original = deepcopy(recipe)
    first = compile_recipe(recipe)
    second = compile_recipe(recipe)
    assert recipe == original
    assert first == second
    assert sha256_canonical(recipe) == CR007_KNOWN_RECIPE_SHA
    assert first["prompt_sha256"] == CR007_KNOWN_PROMPT_SHA
    prompt = first["compilation"]["prompt"]
    sections = first["compilation"]["prompt_sections"]
    low = prompt.casefold()
    assert "4:5" in prompt
    assert "references" in sections
    assert "transformation" in sections
    assert "artifact_form" in sections
    assert "artifact_state" in sections
    assert "decorated_artifact" in prompt
    assert "blue" in low or "cobalt" in low
    assert "porcelain" in low or "ceramic" in low
    assert "vase" in low
    assert "underglaze" in low or "glaze" in low
    assert "cr002-c0-l0-4x5-source" in prompt
    assert "authenticated song-dynasty artifact" in low
    assert "evening gown" not in low
    assert "perfume flacon" not in low
    assert "marble" not in low
    assert "mural" not in low
    assert "fragrance" not in low
    assert "generation" not in first
    # Negative: dropping transformation silently changes the contract away from decorated-artifact transform.
    mutated = deepcopy(recipe)
    mutated["semantic_spec"]["route"] = "new_generation"
    del mutated["semantic_spec"]["transformation"]
    mutated_receipt = compile_recipe(mutated)
    mutated_sections = mutated_receipt["compilation"]["prompt_sections"]
    assert "transformation" not in mutated_sections
    assert mutated_receipt["prompt_sha256"] != first["prompt_sha256"]
    assert "decorated_artifact" not in mutated_receipt["compilation"]["prompt"]


def test_cr007_camera_bindings_preserve_transformation_contract():
    recipe = load_recipe(CR007_PATH)
    cams = recipe["variables"]["camera"]["choices"]
    assert len(cams) == 2
    for camera in cams:
        bound = compile_recipe(recipe, bindings={"camera": camera})
        prompt = bound["compilation"]["prompt"]
        sections = bound["compilation"]["prompt_sections"]
        assert camera in prompt
        assert "transformation" in sections
        assert "references" in sections
        assert recipe["semantic_spec"]["route"] == "artifact_transform"
        assert "decorated_artifact" in prompt
        assert "perfume flacon" not in prompt.casefold()
        assert "evening gown" not in prompt.casefold()
        assert "marble" not in prompt.casefold()
        assert "mural" not in prompt.casefold()


def test_cr001_through_cr006_locked_digests_remain_unchanged():
    assert sha256_canonical(load_recipe(CR001_PATH)) == CR001_KNOWN_RECIPE_SHA
    assert compile_recipe(load_recipe(CR001_PATH))["prompt_sha256"] == CR001_KNOWN_PROMPT_SHA
    assert sha256_canonical(load_recipe(CR002_PATH)) == CR002_KNOWN_RECIPE_SHA
    assert compile_recipe(load_recipe(CR002_PATH))["prompt_sha256"] == CR002_KNOWN_PROMPT_SHA
    assert sha256_canonical(load_recipe(CR003_PATH)) == CR003_KNOWN_RECIPE_SHA
    assert compile_recipe(load_recipe(CR003_PATH))["prompt_sha256"] == CR003_KNOWN_PROMPT_SHA
    assert sha256_canonical(load_recipe(CR004_PATH)) == CR004_KNOWN_RECIPE_SHA
    assert compile_recipe(load_recipe(CR004_PATH))["prompt_sha256"] == CR004_KNOWN_PROMPT_SHA
    assert sha256_canonical(load_recipe(CR005_PATH)) == CR005_KNOWN_RECIPE_SHA
    assert compile_recipe(load_recipe(CR005_PATH))["prompt_sha256"] == CR005_KNOWN_PROMPT_SHA
    assert sha256_canonical(load_recipe(CR006_PATH)) == CR006_KNOWN_RECIPE_SHA
    assert compile_recipe(load_recipe(CR006_PATH))["prompt_sha256"] == CR006_KNOWN_PROMPT_SHA


def test_cr001_through_cr007_locked_digests_remain_unchanged():
    test_cr001_through_cr006_locked_digests_remain_unchanged()
    assert sha256_canonical(load_recipe(CR007_PATH)) == CR007_KNOWN_RECIPE_SHA
    assert compile_recipe(load_recipe(CR007_PATH))["prompt_sha256"] == CR007_KNOWN_PROMPT_SHA


def test_cr008_remains_research_only_without_recipe():
    assert not (RECIPES_ROOT / "cr-008-golden-fault").exists()
    doc = (ROOT / "docs" / "CR_008_GOLDEN_FAULT.md").read_text(encoding="utf-8")
    assert "BLOCKED — LOCAL EDIT CAPABILITY GAP" in doc
    lib = (ROOT / "docs" / "CREATIVE_RECIPE_LIBRARY.md").read_text(encoding="utf-8")
    assert "CR-008 status (blocked)" in lib
    assert "implementation blocked" in lib.casefold() or "IMPLEMENTATION BLOCKED" in lib or "blocked" in lib.casefold()


def test_cr009_file_exists_and_path_matches_identity():
    assert CR009_PATH.is_file()
    assert CR009_PATH.parent.name == CR009_ID
    assert CR009_PATH.stem == CR009_VERSION


def test_cr009_loads_and_schema_validation_passes():
    recipe = load_recipe(CR009_PATH)
    findings = validate_recipe(recipe)
    assert _errors(findings) == [], findings
    assert recipe["recipe_schema_version"] == "1.1"
    assert recipe["recipe_id"] == CR009_ID
    assert recipe["recipe_version"] == CR009_VERSION


def test_cr009_semantic_spec_is_source_conditioned_whole_image_revision():
    recipe = load_recipe(CR009_PATH)
    spec = recipe["semantic_spec"]
    assert spec["route"] == "reference_transform"
    assert spec["route"] != "artifact_transform"
    assert spec["route"] != "new_generation"
    assert "transformation" not in spec or spec.get("transformation") in (None, {})
    assert spec.get("transformation") is None
    assert spec["art"]["method"] is None
    assert spec["art"]["artifact_form"] is None
    assert spec["art"]["artifact_state"] is None
    assert spec["historical"]["packs"] == []
    assert spec["identity"]["mode"] == "recognizable_identity"
    assert spec["body_transformation"]["mode"] == "preserve"
    assert spec["output"]["aspect_ratio"] == "4:5"
    assert spec["output"].get("generation_requested") is False
    refs = spec["references"]
    assert len(refs) == 1
    assert refs[0]["id"] == "cr007-c0-4x5-source"
    assert set(refs[0]["roles"]) == {
        "identity",
        "artifact",
        "environment",
        "layout",
        "palette",
    }
    notes = refs[0].get("notes") or ""
    assert CR009_SOURCE_IMAGE_SHA in notes
    assert "D:\\" not in notes
    assert "/Users/" not in notes
    assert "mask" in notes.casefold()
    request = spec["request"].casefold()
    assert "edit the attached" in request or "edit the attached existing" in request
    assert "gold-lacquer" in request or "gold lacquer" in request
    assert "upper-right shoulder" in request
    assert "whole-image" in request
    assert "pixel-exact" in request or "masked local edit" in request
    assert "not a pixel-exact or masked local edit" in request
    blob = json.dumps(spec).casefold()
    assert "TODO" not in json.dumps(spec)
    assert "placeholder" not in blob
    assert "perfume flacon" not in blob
    assert "marble sculpture" not in blob
    assert "mineral-pigment mural" not in blob
    assert "fragrance" not in blob
    assert "edit_region" not in blob
    assert '"mask"' not in blob
    raw = CR009_PATH.read_text(encoding="utf-8")
    assert "AIPF_Creative_Private" not in raw
    assert "D:\\\\1_PROJECT" not in raw
    assert recipe.get("variables") == {}


def test_cr009_compiles_as_reference_transform_edit_not_medium_translation():
    recipe = load_recipe(CR009_PATH)
    original = deepcopy(recipe)
    first = compile_recipe(recipe)
    second = compile_recipe(recipe)
    assert recipe == original
    assert first == second
    assert sha256_canonical(recipe) == CR009_KNOWN_RECIPE_SHA
    assert first["prompt_sha256"] == CR009_KNOWN_PROMPT_SHA
    prompt = first["compilation"]["prompt"]
    sections = first["compilation"]["prompt_sections"]
    low = prompt.casefold()
    assert "4:5" in prompt
    assert "references" in sections
    assert "transformation" not in sections
    assert "artifact_form" not in sections
    assert "cr007-c0-4x5-source" in prompt
    assert "gold-lacquer" in low or "gold lacquer" in low
    assert "upper-right shoulder" in low
    assert "edit the attached" in low
    assert "whole-image" in low
    assert "pixel-exact" in low or "masked local edit" in low
    assert "decorated_artifact" not in low
    assert "perfume flacon" not in low
    assert "marble sculpture" not in low
    assert "mineral-pigment mural" not in low
    assert "fragrance" not in low
    assert "generation" not in first
    assert "D:\\" not in prompt
    assert "AIPF_Creative_Private" not in prompt


def test_cr009_negative_removing_seam_instruction_changes_prompt_sha():
    recipe = load_recipe(CR009_PATH)
    baseline = compile_recipe(recipe)
    mutated = deepcopy(recipe)
    mutated["semantic_spec"]["request"] = (
        "Edit the attached existing photograph of one free-standing blue-and-white "
        "porcelain vase—do not invent an unrelated new vase or a different composition. "
        "Keep a recognizable whole-image revision of the attached source with semantic "
        "preservation guidance only; this is not a pixel-exact or masked local edit."
    )
    # Clear director lines that restate the seam so the negative isolates seam semantics.
    for key in ("moment", "action", "midground", "material_response", "micro_story", "light_source"):
        text = mutated["semantic_spec"]["director"][key]
        mutated["semantic_spec"]["director"][key] = (
            text.replace("gold-lacquer repair seam", "unchanged glaze surface")
            .replace("gold-lacquer seam", "unchanged glaze surface")
            .replace("lacquer join finished with restrained powdered gold on the upper-right shoulder", "unchanged glaze continuity")
            .replace("one restrained gold-lacquer seam", "no material addition")
            .replace("fictional gold-lacquer seam", "source continuity")
        )
    mutated["semantic_spec"]["requested_elements"] = [
        e
        for e in mutated["semantic_spec"]["requested_elements"]
        if "gold" not in e.casefold() and "seam" not in e.casefold() and "branch" not in e.casefold()
    ]
    receipt = compile_recipe(mutated)
    assert receipt["prompt_sha256"] != baseline["prompt_sha256"]
    low = receipt["compilation"]["prompt"].casefold()
    assert "adding one narrow, irregular gold-lacquer" not in low
    assert "gold-lacquer repair seam" not in low


def test_cr009_negative_removing_source_reference_changes_editing_semantics():
    recipe = load_recipe(CR009_PATH)
    baseline = compile_recipe(recipe)
    mutated = deepcopy(recipe)
    mutated["semantic_spec"]["references"] = []
    receipt = compile_recipe(mutated)
    assert receipt["prompt_sha256"] != baseline["prompt_sha256"]
    assert "references" not in receipt["compilation"]["prompt_sections"]
    assert "cr007-c0-4x5-source" not in receipt["compilation"]["prompt"]


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
