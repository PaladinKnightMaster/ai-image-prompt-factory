"""PromptRecipe v1: static envelope, hashing, CLI, and compiler parity."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

from aipf.compiler import compile_result
from aipf.recipes import (
    RecipeError,
    RecipeValidationError,
    canonical_json_bytes,
    compile_recipe,
    load_bindings,
    load_recipe,
    resolve_recipe,
    sha256_bytes,
    sha256_canonical,
    validate_recipe,
)

ROOT = Path(__file__).resolve().parents[1]

PARITY_CASES = [
    ("legacy", "cases/golden/01-classical-greek-heroic-living/case.json"),
    ("greek_marble", "cases/candidates/v34-greek-marble-bust/case.json"),
    ("dunhuang", "cases/candidates/v34-dunhuang-mural/case.json"),
    ("edo_woodblock", "cases/candidates/v34-edo-woodblock/case.json"),
    ("blue_white", "cases/candidates/v34-blue-white-vase/case.json"),
    ("evidence_compat", "cases/regression/reg-hellenistic-copy-survival-bias/case.json"),
    ("visual_pattern", "cases/golden/07-edo-ukiyoe-transform/case.json"),
]


def _load_case(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _wrap_recipe(spec: dict, *, recipe_id: str = "example-recipe", **extra) -> dict:
    recipe = {
        "recipe_schema_version": "1.0",
        "recipe_id": recipe_id,
        "recipe_version": "1.0.0",
        "title": "Example Recipe",
        "semantic_spec": deepcopy(spec),
    }
    recipe.update(extra)
    return recipe


def _write_recipe(path: Path, recipe: dict) -> Path:
    path.write_text(json.dumps(recipe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _aipf_cmd(*args: str) -> list[str]:
    exe = shutil.which("aipf")
    if exe:
        return [exe, *args]
    # Editable/source fallback when the console script is not on PATH.
    return [
        sys.executable,
        "-c",
        "import sys; from aipf.cli import main; sys.argv = ['aipf'] + sys.argv[1:]; main()",
        *args,
    ]


def _run(cmd: list[str], *, cwd: Path | None = None, env: dict | None = None) -> subprocess.CompletedProcess:
    raw = subprocess.run(cmd, cwd=str(cwd or ROOT), env=env, capture_output=True, check=False)
    return subprocess.CompletedProcess(
        raw.args,
        raw.returncode,
        raw.stdout.decode("utf-8", errors="replace"),
        raw.stderr.decode("utf-8", errors="replace"),
    )


def _cp1252_env() -> dict[str, str]:
    """Force recipe CLI subprocess stdout through a Windows-like charmap codec."""
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "cp1252"
    # Avoid UTF-8 mode overriding PYTHONIOENCODING on modern Windows/Python.
    env["PYTHONUTF8"] = "0"
    env["PYTHONLEGACYWINDOWSSTDIO"] = "1"
    return env


def _run_raw(
    cmd: list[str], *, cwd: Path | None = None, env: dict | None = None
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(cmd, cwd=str(cwd or ROOT), env=env, capture_output=True, check=False)


def _errors(findings: list[dict]) -> list[dict]:
    return [f for f in findings if f["level"] == "error"]


# --- validation -----------------------------------------------------------------


def test_valid_static_recipe(tmp_path: Path):
    recipe = _wrap_recipe(_load_case(PARITY_CASES[0][1]), description="legacy static")
    path = _write_recipe(tmp_path / "ok.json", recipe)
    loaded = load_recipe(path)
    findings = validate_recipe(loaded)
    assert _errors(findings) == []
    assert resolve_recipe(loaded) == recipe["semantic_spec"]


def test_valid_transformation_recipe():
    recipe = _wrap_recipe(_load_case(PARITY_CASES[1][1]), recipe_id="greek-marble-bust")
    assert _errors(validate_recipe(recipe)) == []


def test_missing_required_recipe_fields():
    recipe = _wrap_recipe(_load_case(PARITY_CASES[0][1]))
    del recipe["title"]
    errs = _errors(validate_recipe(recipe))
    assert errs
    assert any("title" in f["message"].casefold() or f["code"] == "recipe_schema" for f in errs)


def test_unknown_envelope_fields_rejected():
    recipe = _wrap_recipe(_load_case(PARITY_CASES[0][1]), variables={"x": "y"})
    errs = _errors(validate_recipe(recipe))
    assert errs
    assert any("variables" in f["message"] or f["code"] == "recipe_schema" for f in errs)


def test_unsupported_schema_version():
    recipe = _wrap_recipe(_load_case(PARITY_CASES[0][1]))
    recipe["recipe_schema_version"] = "2.0"
    errs = _errors(validate_recipe(recipe))
    assert errs


def test_invalid_recipe_id():
    recipe = _wrap_recipe(_load_case(PARITY_CASES[0][1]), recipe_id="Not A Slug")
    assert _errors(validate_recipe(recipe))


def test_invalid_recipe_version():
    recipe = _wrap_recipe(_load_case(PARITY_CASES[0][1]))
    recipe["recipe_version"] = "1.0"
    assert _errors(validate_recipe(recipe))


def test_invalid_embedded_semantic_specification():
    recipe = _wrap_recipe({"version": "3.2", "request": "incomplete"})
    errs = _errors(validate_recipe(recipe))
    assert errs
    assert any(f["code"] == "schema" or "semantic" in f["code"] for f in errs)


def test_semantic_gate_failures():
    spec = _load_case(PARITY_CASES[0][1])
    spec["historical"]["packs"] = ["wuxia"]
    recipe = _wrap_recipe(spec, recipe_id="wuxia-gate")
    errs = _errors(validate_recipe(recipe))
    assert any(f["code"] == "genre_as_era" for f in errs)


def test_rejects_pr4_variable_declarations():
    recipe = _wrap_recipe(_load_case(PARITY_CASES[0][1]))
    recipe["variables"] = {"subject": {"type": "string"}}
    assert _errors(validate_recipe(recipe))


def test_invalid_json_and_malformed_file(tmp_path: Path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(RecipeError):
        load_recipe(bad)
    empty = tmp_path / "empty.json"
    empty.write_text("null\n", encoding="utf-8")
    with pytest.raises(RecipeError):
        load_recipe(empty)


def test_lint_warnings_distinct_from_errors():
    spec = _load_case(PARITY_CASES[0][1])
    spec["request"] = spec["request"] + " with flawless skin"
    recipe = _wrap_recipe(spec, recipe_id="warn-skin")
    findings = validate_recipe(recipe)
    assert _errors(findings) == []
    assert any(f["level"] == "warning" and f["code"] == "flawless_skin" for f in findings)


# --- hashing / provenance -------------------------------------------------------


def test_key_order_does_not_alter_hashes():
    spec = _load_case(PARITY_CASES[0][1])
    a = _wrap_recipe(spec)
    b = {
        "title": a["title"],
        "semantic_spec": a["semantic_spec"],
        "recipe_version": a["recipe_version"],
        "recipe_id": a["recipe_id"],
        "recipe_schema_version": a["recipe_schema_version"],
    }
    assert sha256_canonical(a) == sha256_canonical(b)
    assert sha256_canonical(a["semantic_spec"]) == sha256_canonical(b["semantic_spec"])


def test_formatting_and_newlines_do_not_alter_content_hashes(tmp_path: Path):
    recipe = _wrap_recipe(_load_case(PARITY_CASES[0][1]))
    compact = tmp_path / "compact.json"
    pretty = tmp_path / "pretty.json"
    compact.write_bytes(json.dumps(recipe, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    pretty.write_text(json.dumps(recipe, indent=4, ensure_ascii=False) + "\r\n", encoding="utf-8")
    a = load_recipe(compact)
    b = load_recipe(pretty)
    assert sha256_canonical(a) == sha256_canonical(b)


def test_metadata_change_alters_recipe_hash_only():
    recipe = _wrap_recipe(_load_case(PARITY_CASES[0][1]))
    other = deepcopy(recipe)
    other["title"] = "Changed Title"
    assert sha256_canonical(recipe["semantic_spec"]) == sha256_canonical(other["semantic_spec"])
    assert sha256_canonical(recipe) != sha256_canonical(other)


def test_semantic_change_alters_semantic_hash():
    recipe = _wrap_recipe(_load_case(PARITY_CASES[0][1]))
    other = deepcopy(recipe)
    other["semantic_spec"]["request"] = other["semantic_spec"]["request"] + " slightly"
    assert sha256_canonical(recipe["semantic_spec"]) != sha256_canonical(other["semantic_spec"])
    assert sha256_canonical(recipe) != sha256_canonical(other)


def test_repeated_compilation_deterministic_and_no_mutation():
    recipe = _wrap_recipe(_load_case(PARITY_CASES[1][1]), recipe_id="greek-marble-bust")
    original = deepcopy(recipe)
    a = compile_recipe(recipe)
    b = compile_recipe(recipe)
    assert a == b
    assert recipe == original
    assert "created_at" not in json.dumps(a)
    assert "uuid" not in json.dumps(a).casefold()
    assert not re.search(r"[A-Za-z]:\\\\|/[Uu]sers/", json.dumps(a))


def test_prompt_hash_and_compiler_version_match_result():
    recipe = _wrap_recipe(_load_case(PARITY_CASES[0][1]))
    envelope = compile_recipe(recipe)
    prompt = envelope["compilation"]["prompt"]
    assert envelope["prompt_sha256"] == sha256(prompt.encode("utf-8")).hexdigest()
    assert envelope["compiler_version"] == envelope["compilation"]["compiler_version"]
    assert envelope["evidence_snapshot_sha256"] == envelope["compilation"]["evidence_snapshot"]["snapshot_sha256"]


# --- compilation parity ---------------------------------------------------------


@pytest.mark.parametrize("name,rel", PARITY_CASES, ids=[n for n, _ in PARITY_CASES])
def test_seven_case_source_recipe_parity(name: str, rel: str):
    spec = _load_case(rel)
    direct = compile_result(spec)
    recipe = _wrap_recipe(spec, recipe_id=f"parity-{name.replace('_', '-')}")
    envelope = compile_recipe(recipe)
    compiled = envelope["compilation"]
    assert compiled["prompt"].encode("utf-8") == direct["prompt"].encode("utf-8")
    assert envelope["prompt_sha256"] == sha256(direct["prompt"].encode("utf-8")).hexdigest()
    assert compiled == direct
    assert compiled["evidence_snapshot"] == direct["evidence_snapshot"]
    assert compiled["compatibility_audit"] == direct["compatibility_audit"]
    assert compiled.get("transformation_resolution") == direct.get("transformation_resolution")
    assert compiled.get("lexical_trace") == direct.get("lexical_trace")
    assert compiled.get("pattern_trace") == direct.get("pattern_trace")


def test_resolve_is_value_identical_not_injected():
    recipe = _wrap_recipe(_load_case(PARITY_CASES[0][1]), description="meta")
    resolved = resolve_recipe(recipe)
    assert resolved == recipe["semantic_spec"]
    assert resolved is not recipe["semantic_spec"]
    assert "recipe_id" not in resolved
    assert "description" not in resolved or resolved.get("description") == recipe["semantic_spec"].get("description")


def test_compile_rejects_invalid_without_calling_success_path():
    recipe = _wrap_recipe({"version": "3.2"})
    with pytest.raises(RecipeValidationError) as exc:
        compile_recipe(recipe)
    assert exc.value.findings
    assert _errors(exc.value.findings)


# --- CLI ------------------------------------------------------------------------


def test_cli_validate_valid_and_invalid(tmp_path: Path):
    ok = _write_recipe(tmp_path / "ok.json", _wrap_recipe(_load_case(PARITY_CASES[0][1])))
    bad = _write_recipe(tmp_path / "bad.json", _wrap_recipe(_load_case(PARITY_CASES[0][1]), recipe_id="BAD ID"))
    good = _run(_aipf_cmd("recipe", "validate", str(ok)))
    assert good.returncode == 0, good.stderr + good.stdout
    failed = _run(_aipf_cmd("recipe", "validate", str(bad)))
    assert failed.returncode != 0
    assert "Traceback" not in failed.stderr
    assert failed.stdout or failed.stderr


def test_cli_compile_plaintext_matches_legacy(tmp_path: Path):
    spec = _load_case(PARITY_CASES[0][1])
    spec_path = tmp_path / "spec.json"
    recipe_path = tmp_path / "recipe.json"
    spec_path.write_text(json.dumps(spec, ensure_ascii=False) + "\n", encoding="utf-8")
    _write_recipe(recipe_path, _wrap_recipe(spec))
    legacy = _run(_aipf_cmd("compile", str(spec_path)))
    recipe = _run(_aipf_cmd("recipe", "compile", str(recipe_path)))
    assert legacy.returncode == 0, legacy.stderr
    assert recipe.returncode == 0, recipe.stderr
    # Console text mode may translate newlines on Windows; recipe must still
    # match legacy compile byte-for-byte, and LF-normalize to the compiler.
    assert recipe.stdout.encode("utf-8") == legacy.stdout.encode("utf-8")
    assert recipe.stdout.replace("\r\n", "\n") == compile_result(spec)["prompt"]


def test_cli_compile_json_deterministic(tmp_path: Path):
    path = _write_recipe(tmp_path / "r.json", _wrap_recipe(_load_case(PARITY_CASES[1][1]), recipe_id="greek-marble-bust"))
    a = _run(_aipf_cmd("recipe", "compile", str(path), "--json"))
    b = _run(_aipf_cmd("recipe", "compile", str(path), "--json"))
    assert a.returncode == 0, a.stderr
    assert a.stdout == b.stdout
    envelope = json.loads(a.stdout)
    assert "recipe" in envelope and "compilation" in envelope
    assert envelope["recipe"]["recipe_sha256"]
    assert envelope["compilation"]["prompt"]


def test_cli_validate_diagnostics_do_not_contaminate_prompt_stdout(tmp_path: Path):
    path = _write_recipe(tmp_path / "r.json", _wrap_recipe(_load_case(PARITY_CASES[0][1])))
    _run(_aipf_cmd("recipe", "validate", str(path)))
    compiled = _run(_aipf_cmd("recipe", "compile", str(path)))
    assert compiled.returncode == 0
    assert compiled.stdout.replace("\r\n", "\n") == compile_result(_load_case(PARITY_CASES[0][1]))["prompt"]


def test_legacy_cli_commands_unchanged(tmp_path: Path):
    spec = _load_case(PARITY_CASES[0][1])
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(spec, ensure_ascii=False) + "\n", encoding="utf-8")
    compile_out = _run(_aipf_cmd("compile", str(path)))
    lint_out = _run(_aipf_cmd("lint", str(path)))
    assert compile_out.returncode == 0
    assert lint_out.returncode == 0
    assert compile_out.stdout.replace("\r\n", "\n") == compile_result(spec)["prompt"]
    findings = json.loads(lint_out.stdout.replace("\r\n", "\n"))
    assert isinstance(findings, list)


def test_canonical_json_bytes_contract():
    obj = {"b": 1, "a": 2}
    assert canonical_json_bytes(obj) == b'{"a":2,"b":1}'
    assert sha256_bytes(b"x") == sha256(b"x").hexdigest()


# --- Windows cp1252 JSON transport ----------------------------------------------


def test_cli_compile_json_ascii_safe_under_cp1252(tmp_path: Path):
    """Recipe --json must print on cp1252 stdout without losing Unicode values."""
    recipe = _wrap_recipe(_load_case(PARITY_CASES[1][1]), recipe_id="greek-marble-bust")
    path = _write_recipe(tmp_path / "r.json", recipe)
    expected = compile_recipe(recipe)
    assert "→" in expected["compilation"]["prompt"]

    raw = _run_raw(
        _aipf_cmd("recipe", "compile", str(path), "--json"),
        env=_cp1252_env(),
    )
    assert raw.returncode == 0, raw.stderr.decode("utf-8", errors="replace")
    assert b"UnicodeEncodeError" not in raw.stderr
    # Transport JSON is ASCII-only; values round-trip when parsed.
    ascii_text = raw.stdout.decode("ascii")
    envelope = json.loads(ascii_text)
    assert "→" in envelope["compilation"]["prompt"]
    assert envelope["compilation"] == expected["compilation"]
    assert envelope["recipe"]["recipe_sha256"] == expected["recipe"]["recipe_sha256"]
    assert envelope["recipe"]["semantic_spec_sha256"] == expected["recipe"]["semantic_spec_sha256"]
    assert envelope["prompt_sha256"] == expected["prompt_sha256"]
    assert envelope["evidence_snapshot_sha256"] == expected["evidence_snapshot_sha256"]
    assert envelope["compiler_version"] == expected["compiler_version"]


def test_cli_compile_json_deterministic_under_cp1252(tmp_path: Path):
    path = _write_recipe(
        tmp_path / "r.json",
        _wrap_recipe(_load_case(PARITY_CASES[1][1]), recipe_id="greek-marble-bust"),
    )
    env = _cp1252_env()
    a = _run_raw(_aipf_cmd("recipe", "compile", str(path), "--json"), env=env)
    b = _run_raw(_aipf_cmd("recipe", "compile", str(path), "--json"), env=env)
    assert a.returncode == 0, a.stderr.decode("utf-8", errors="replace")
    assert a.stdout == b.stdout
    a.stdout.decode("ascii")


def test_cli_validate_unicode_diagnostics_under_cp1252(tmp_path: Path):
    # Invalid slug so jsonschema echoes the Unicode recipe_id in the finding.
    recipe = _wrap_recipe(
        _load_case(PARITY_CASES[0][1]),
        recipe_id="bad→id",
        title="Marble → Greek",
    )
    path = _write_recipe(tmp_path / "bad.json", recipe)
    raw = _run_raw(_aipf_cmd("recipe", "validate", str(path)), env=_cp1252_env())
    assert raw.returncode != 0
    assert b"UnicodeEncodeError" not in raw.stderr
    findings = json.loads(raw.stdout.decode("ascii"))
    assert isinstance(findings, list)
    assert any("→" in f.get("message", "") for f in findings)


def test_cli_compile_invalid_json_diagnostics_under_cp1252(tmp_path: Path):
    path = _write_recipe(
        tmp_path / "bad.json",
        _wrap_recipe(
            {"version": "3.2", "request": "incomplete →"},
            recipe_id="bad→id",
            title="Broken → Recipe",
        ),
    )
    raw = _run_raw(
        _aipf_cmd("recipe", "compile", str(path), "--json"),
        env=_cp1252_env(),
    )
    assert raw.returncode != 0
    assert b"UnicodeEncodeError" not in raw.stderr
    findings = json.loads(raw.stdout.decode("ascii"))
    assert isinstance(findings, list)
    assert _errors(findings)
    assert any("→" in f.get("message", "") for f in findings)


def test_cli_plaintext_parity_unchanged_by_json_transport(tmp_path: Path):
    """Legacy and recipe plain-text CLIs must match under an explicit UTF-8 env.

    This proves parity under the same configured UTF-8 subprocess environment.
    It does not claim the legacy CLI can emit arbitrary Unicode under cp1252.
    """
    spec = _load_case(PARITY_CASES[1][1])
    expected_prompt = compile_result(spec)["prompt"]
    assert "→" in expected_prompt
    spec_path = tmp_path / "spec.json"
    recipe_path = tmp_path / "recipe.json"
    spec_path.write_text(json.dumps(spec, ensure_ascii=False) + "\n", encoding="utf-8")
    _write_recipe(recipe_path, _wrap_recipe(spec, recipe_id="greek-marble-bust"))

    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    legacy = _run_raw(_aipf_cmd("compile", str(spec_path)), env=env)
    recipe = _run_raw(_aipf_cmd("recipe", "compile", str(recipe_path)), env=env)
    assert legacy.returncode == 0, legacy.stderr.decode("utf-8", errors="replace")
    assert recipe.returncode == 0, recipe.stderr.decode("utf-8", errors="replace")
    # Raw stdout bytes must match exactly; do not normalize before this check.
    assert recipe.stdout == legacy.stdout
    arrow = "→".encode("utf-8")
    assert arrow in legacy.stdout
    assert arrow in recipe.stdout
    # Console text mode may translate newlines on Windows; account only for CRLF.
    assert recipe.stdout.replace(b"\r\n", b"\n") == expected_prompt.encode("utf-8")


def test_json_transport_does_not_alter_canonical_hashes(tmp_path: Path):
    recipe = _wrap_recipe(_load_case(PARITY_CASES[1][1]), recipe_id="greek-marble-bust")
    path = _write_recipe(tmp_path / "r.json", recipe)
    direct = compile_recipe(recipe)
    raw = _run_raw(
        _aipf_cmd("recipe", "compile", str(path), "--json"),
        env=_cp1252_env(),
    )
    assert raw.returncode == 0, raw.stderr.decode("utf-8", errors="replace")
    envelope = json.loads(raw.stdout.decode("ascii"))
    assert sha256_canonical(recipe) == direct["recipe"]["recipe_sha256"]
    assert sha256_canonical(recipe["semantic_spec"]) == direct["recipe"]["semantic_spec_sha256"]
    assert envelope["recipe"]["recipe_sha256"] == direct["recipe"]["recipe_sha256"]
    assert envelope["recipe"]["semantic_spec_sha256"] == direct["recipe"]["semantic_spec_sha256"]
    assert envelope["prompt_sha256"] == direct["prompt_sha256"]
    assert envelope["compilation"] == direct["compilation"]
    # Canonical serializer remains UTF-8 / ensure_ascii=False (not transport JSON).
    assert b"\\u" not in canonical_json_bytes({"arrow": "→"})
    assert "→".encode("utf-8") in canonical_json_bytes({"arrow": "→"})


# --- PR4 constrained variables (v1.1) -------------------------------------------


def _wrap_recipe_v11(spec: dict, *, recipe_id: str = "example-recipe", variables: dict | None = None, **extra) -> dict:
    recipe = {
        "recipe_schema_version": "1.1",
        "recipe_id": recipe_id,
        "recipe_version": "1.1.0",
        "title": "Example Recipe v1.1",
        "semantic_spec": deepcopy(spec),
    }
    if variables is not None:
        recipe["variables"] = variables
    recipe.update(extra)
    return recipe


def _three_target_variables(spec: dict) -> dict:
    return {
        "camera": {
            "type": "enum",
            "target": "director.camera",
            "choices": [
                spec["director"]["camera"],
                "tight frontal bust framing",
            ],
        },
        "light": {
            "type": "enum",
            "target": "director.light_source",
            "choices": [
                spec["director"]["light_source"],
                "soft overhead museum skylight",
            ],
        },
        "ratio": {
            "type": "enum",
            "target": "output.aspect_ratio",
            "choices": ["1:1", "4:5"],
            "required": False,
        },
    }


def test_v10_still_rejects_variables_and_bindings():
    recipe = _wrap_recipe(_load_case(PARITY_CASES[0][1]))
    assert _errors(validate_recipe(recipe)) == []
    assert any(f["code"] == "recipe_bindings_unsupported" for f in _errors(validate_recipe(recipe, bindings={})))
    with pytest.raises(RecipeValidationError):
        resolve_recipe(recipe, bindings={"x": "y"})
    with pytest.raises(RecipeValidationError):
        compile_recipe(recipe, bindings={})


def test_v11_validate_without_bindings_allows_optional_variables():
    spec = _load_case(PARITY_CASES[1][1])
    recipe = _wrap_recipe_v11(spec, recipe_id="greek-marble-bust", variables=_three_target_variables(spec))
    assert _errors(validate_recipe(recipe)) == []


def test_v11_empty_bindings_reports_missing_required():
    spec = _load_case(PARITY_CASES[1][1])
    variables = _three_target_variables(spec)
    variables["camera"]["required"] = True
    recipe = _wrap_recipe_v11(spec, recipe_id="greek-marble-bust", variables=variables)
    findings = validate_recipe(recipe, bindings={})
    errs = _errors(findings)
    assert any(f["code"] == "recipe_binding_required" for f in errs)


def test_v11_resolve_and_compile_all_three_destinations():
    spec = _load_case(PARITY_CASES[1][1])
    recipe = _wrap_recipe_v11(spec, recipe_id="greek-marble-bust", variables=_three_target_variables(spec))
    bindings = {
        "camera": "tight frontal bust framing",
        "light": "soft overhead museum skylight",
        "ratio": "1:1",
    }
    original_recipe = deepcopy(recipe)
    original_bindings = deepcopy(bindings)
    resolved = resolve_recipe(recipe, bindings)
    assert resolved["director"]["camera"] == "tight frontal bust framing"
    assert resolved["director"]["light_source"] == "soft overhead museum skylight"
    assert resolved["output"]["aspect_ratio"] == "1:1"
    assert recipe == original_recipe
    assert bindings == original_bindings
    envelope = compile_recipe(recipe, bindings)
    assert envelope["compilation"]["prompt"]
    assert "variable_resolution" in envelope
    assert envelope["recipe"]["semantic_spec_sha256"] == sha256_canonical(recipe["semantic_spec"])
    assert envelope["recipe"]["recipe_sha256"] == sha256_canonical(recipe)
    assert envelope["variable_resolution"]["resolved_semantic_spec_sha256"] == sha256_canonical(resolved)
    assert envelope["variable_resolution"]["effective_bindings"] == {
        "camera": "tight frontal bust framing",
        "light": "soft overhead museum skylight",
        "ratio": "1:1",
    }
    assert envelope["variable_resolution"]["submitted_variable_names"] == ["camera", "light", "ratio"]
    assert envelope["compiler_version"] == envelope["compilation"]["compiler_version"]


def test_v11_omitted_optional_equals_explicit_baseline_effective_hashes():
    spec = _load_case(PARITY_CASES[1][1])
    recipe = _wrap_recipe_v11(spec, recipe_id="greek-marble-bust", variables=_three_target_variables(spec))
    omitted = compile_recipe(recipe)  # omitted bindings → empty invocation
    explicit = compile_recipe(
        recipe,
        bindings={
            "camera": spec["director"]["camera"],
            "light": spec["director"]["light_source"],
            "ratio": spec["output"]["aspect_ratio"],
        },
    )
    vr_o = omitted["variable_resolution"]
    vr_e = explicit["variable_resolution"]
    assert vr_o["effective_bindings_sha256"] == vr_e["effective_bindings_sha256"]
    assert vr_o["resolved_semantic_spec_sha256"] == vr_e["resolved_semantic_spec_sha256"]
    assert vr_o["submitted_bindings_sha256"] != vr_e["submitted_bindings_sha256"]
    assert vr_o["submitted_variable_names"] == []
    assert vr_e["submitted_variable_names"] == ["camera", "light", "ratio"]


def test_v11_different_choice_changes_resolved_fingerprint():
    spec = _load_case(PARITY_CASES[1][1])
    recipe = _wrap_recipe_v11(spec, recipe_id="greek-marble-bust", variables=_three_target_variables(spec))
    a = compile_recipe(recipe, bindings={"ratio": "4:5"})
    b = compile_recipe(recipe, bindings={"ratio": "1:1"})
    assert a["variable_resolution"]["resolved_semantic_spec_sha256"] != b["variable_resolution"][
        "resolved_semantic_spec_sha256"
    ]
    assert a["prompt_sha256"] != b["prompt_sha256"]


def test_v11_repeated_compilation_deterministic():
    spec = _load_case(PARITY_CASES[1][1])
    recipe = _wrap_recipe_v11(spec, recipe_id="greek-marble-bust", variables=_three_target_variables(spec))
    bindings = {"camera": "tight frontal bust framing"}
    a = compile_recipe(recipe, bindings)
    b = compile_recipe(recipe, bindings)
    assert a == b
    dump = json.dumps(a)
    assert "created_at" not in dump
    assert "uuid" not in dump.casefold()
    assert not re.search(r"[A-Za-z]:\\\\|/[Uu]sers/", dump)


def test_v11_key_order_does_not_affect_hashes():
    spec = _load_case(PARITY_CASES[1][1])
    variables = _three_target_variables(spec)
    recipe_a = _wrap_recipe_v11(spec, recipe_id="greek-marble-bust", variables=variables)
    recipe_b = {
        "title": recipe_a["title"],
        "variables": {
            "ratio": variables["ratio"],
            "camera": variables["camera"],
            "light": variables["light"],
        },
        "semantic_spec": recipe_a["semantic_spec"],
        "recipe_version": recipe_a["recipe_version"],
        "recipe_id": recipe_a["recipe_id"],
        "recipe_schema_version": "1.1",
    }
    assert sha256_canonical(recipe_a) == sha256_canonical(recipe_b)
    bind_a = {"light": "soft overhead museum skylight", "camera": "tight frontal bust framing"}
    bind_b = {"camera": "tight frontal bust framing", "light": "soft overhead museum skylight"}
    assert compile_recipe(recipe_a, bind_a)["variable_resolution"] == compile_recipe(recipe_b, bind_b)[
        "variable_resolution"
    ]


def test_v11_rejects_unapproved_value_and_wrong_type():
    spec = _load_case(PARITY_CASES[1][1])
    recipe = _wrap_recipe_v11(spec, recipe_id="greek-marble-bust", variables=_three_target_variables(spec))
    bad_value = _errors(validate_recipe(recipe, bindings={"ratio": "16:9"}))
    assert any(f["code"] == "recipe_binding_choice" for f in bad_value)
    bad_type = _errors(validate_recipe(recipe, bindings={"ratio": 1}))
    assert any(f["code"] == "recipe_binding_type" for f in bad_type)


def test_v11_rejects_protected_field_targets():
    spec = _load_case(PARITY_CASES[1][1])
    recipe = _wrap_recipe_v11(
        spec,
        recipe_id="greek-marble-bust",
        variables={
            "route": {
                "type": "enum",
                "target": "route",
                "choices": ["artifact_transform", "historical_portrait"],
            }
        },
    )
    assert _errors(validate_recipe(recipe))


def test_v11_rejects_duplicate_target_ownership():
    spec = _load_case(PARITY_CASES[1][1])
    cam = spec["director"]["camera"]
    recipe = _wrap_recipe_v11(
        spec,
        recipe_id="greek-marble-bust",
        variables={
            "a": {"type": "enum", "target": "director.camera", "choices": [cam, "alt a"]},
            "b": {"type": "enum", "target": "director.camera", "choices": [cam, "alt b"]},
        },
    )
    errs = _errors(validate_recipe(recipe))
    assert any(f["code"] == "recipe_variable_target" for f in errs)


def test_v11_rejects_unknown_variable_and_missing_baseline_choice():
    spec = _load_case(PARITY_CASES[1][1])
    recipe = _wrap_recipe_v11(spec, recipe_id="greek-marble-bust", variables=_three_target_variables(spec))
    unknown = _errors(validate_recipe(recipe, bindings={"nope": "x"}))
    assert any(f["code"] == "recipe_binding_unknown" for f in unknown)
    broken = deepcopy(recipe)
    broken["variables"]["camera"]["choices"] = ["tight frontal bust framing", "other framing"]
    missing_baseline = _errors(validate_recipe(broken))
    assert any(f["code"] == "recipe_variable_baseline" for f in missing_baseline)


def test_v11_rejects_non_nfc_and_control_director_values():
    spec = _load_case(PARITY_CASES[1][1])
    # U+0065 + U+0301 is non-NFC (should be U+00E9)
    import unicodedata

    non_nfc = "cafe\u0301 framing"
    assert unicodedata.normalize("NFC", non_nfc) != non_nfc
    variables = {
        "camera": {
            "type": "enum",
            "target": "director.camera",
            "choices": [spec["director"]["camera"], non_nfc],
        }
    }
    recipe = _wrap_recipe_v11(spec, recipe_id="greek-marble-bust", variables=variables)
    assert any(f["code"] == "recipe_variable_unicode" for f in _errors(validate_recipe(recipe)))

    variables2 = {
        "camera": {
            "type": "enum",
            "target": "director.camera",
            "choices": [spec["director"]["camera"], "line\nbreak framing"],
        }
    }
    recipe2 = _wrap_recipe_v11(spec, recipe_id="greek-marble-bust", variables=variables2)
    assert any(f["code"] == "recipe_variable_unicode" for f in _errors(validate_recipe(recipe2)))


def test_v11_duplicate_json_keys_rejected(tmp_path: Path):
    path = tmp_path / "dup.json"
    path.write_text('{"a": 1, "a": 2}\n', encoding="utf-8")
    with pytest.raises(RecipeError, match="duplicate"):
        load_recipe(path)
    with pytest.raises(RecipeError, match="duplicate"):
        load_bindings(path)


def test_v11_load_bindings_and_cli(tmp_path: Path):
    spec = _load_case(PARITY_CASES[1][1])
    recipe = _wrap_recipe_v11(spec, recipe_id="greek-marble-bust", variables=_three_target_variables(spec))
    recipe_path = _write_recipe(tmp_path / "recipe.json", recipe)
    bindings = {"ratio": "1:1"}
    bind_path = tmp_path / "bindings.json"
    bind_path.write_text(json.dumps(bindings) + "\n", encoding="utf-8")
    assert load_bindings(bind_path) == bindings

    validated = _run(_aipf_cmd("recipe", "validate", str(recipe_path), "--bindings", str(bind_path)))
    assert validated.returncode == 0, validated.stderr + validated.stdout

    plain = _run(_aipf_cmd("recipe", "compile", str(recipe_path), "--bindings", str(bind_path)))
    assert plain.returncode == 0, plain.stderr
    assert plain.stdout.replace("\r\n", "\n") == compile_recipe(recipe, bindings)["compilation"]["prompt"]

    as_json = _run(_aipf_cmd("recipe", "compile", str(recipe_path), "--bindings", str(bind_path), "--json"))
    assert as_json.returncode == 0, as_json.stderr
    envelope = json.loads(as_json.stdout)
    assert envelope["variable_resolution"]["effective_bindings"]["ratio"] == "1:1"
    assert "→" in envelope["compilation"]["prompt"]


def test_v11_cli_invalid_bindings_no_prompt(tmp_path: Path):
    spec = _load_case(PARITY_CASES[1][1])
    recipe = _wrap_recipe_v11(spec, recipe_id="greek-marble-bust", variables=_three_target_variables(spec))
    recipe_path = _write_recipe(tmp_path / "recipe.json", recipe)
    bind_path = tmp_path / "bindings.json"
    bind_path.write_text(json.dumps({"ratio": "16:9"}) + "\n", encoding="utf-8")
    failed = _run(_aipf_cmd("recipe", "compile", str(recipe_path), "--bindings", str(bind_path)))
    assert failed.returncode == 1
    assert "Create a coherent" not in failed.stdout
    findings = json.loads(failed.stdout)
    assert _errors(findings)


def test_v11_cli_json_ascii_safe_under_cp1252(tmp_path: Path):
    spec = _load_case(PARITY_CASES[1][1])
    recipe = _wrap_recipe_v11(spec, recipe_id="greek-marble-bust", variables=_three_target_variables(spec))
    path = _write_recipe(tmp_path / "r.json", recipe)
    bind_path = tmp_path / "b.json"
    bind_path.write_text(json.dumps({"ratio": "1:1"}, ensure_ascii=False) + "\n", encoding="utf-8")
    raw = _run_raw(
        _aipf_cmd("recipe", "compile", str(path), "--bindings", str(bind_path), "--json"),
        env=_cp1252_env(),
    )
    assert raw.returncode == 0, raw.stderr.decode("utf-8", errors="replace")
    assert b"UnicodeEncodeError" not in raw.stderr
    envelope = json.loads(raw.stdout.decode("ascii"))
    assert envelope["variable_resolution"]["effective_bindings"]["ratio"] == "1:1"


def test_v11_semantic_gate_failure_blocks_compile():
    spec = _load_case(PARITY_CASES[0][1])
    spec["historical"]["packs"] = ["wuxia"]
    variables = {
        "ratio": {
            "type": "enum",
            "target": "output.aspect_ratio",
            "choices": ["1:1", "4:5"],
        }
    }
    # Ensure baseline aspect is in choices
    if spec["output"]["aspect_ratio"] not in ("1:1", "4:5"):
        spec["output"]["aspect_ratio"] = "4:5"
    recipe = _wrap_recipe_v11(spec, recipe_id="wuxia-gate", variables=variables)
    with pytest.raises(RecipeValidationError) as exc:
        compile_recipe(recipe, bindings={"ratio": "1:1"})
    assert any(f["code"] == "genre_as_era" for f in _errors(exc.value.findings))


def test_v11_missing_schema_resource_fails_closed(monkeypatch):
    from aipf import recipes as recipes_mod

    def boom(path):
        raise recipes_mod.RecipeError(f"missing packaged schema: {path}")

    monkeypatch.setattr(recipes_mod, "_load_recipe_schema", boom)
    spec = _load_case(PARITY_CASES[1][1])
    recipe = _wrap_recipe_v11(spec, recipe_id="greek-marble-bust", variables=_three_target_variables(spec))
    with pytest.raises(RecipeError, match="missing packaged schema"):
        validate_recipe(recipe)


def test_v11_v10_receipt_has_no_variable_resolution():
    recipe = _wrap_recipe(_load_case(PARITY_CASES[0][1]))
    envelope = compile_recipe(recipe)
    assert "variable_resolution" not in envelope


# --- PR4 independent-review corrections -----------------------------------------


def test_malformed_schema_version_types_do_not_raise_typeerror():
    recipe = _wrap_recipe(_load_case(PARITY_CASES[0][1]))
    for bad in (["1.1"], {"v": "1.1"}, 1.1):
        broken = deepcopy(recipe)
        broken["recipe_schema_version"] = bad
        findings = validate_recipe(broken)
        assert _errors(findings)
        assert all(isinstance(f, dict) for f in findings)


def test_non_string_variable_target_rejected_without_typeerror():
    spec = _load_case(PARITY_CASES[1][1])
    recipe = _wrap_recipe_v11(
        spec,
        recipe_id="greek-marble-bust",
        variables={
            "camera": {
                "type": "enum",
                "target": ["director.camera"],
                "choices": [spec["director"]["camera"], "tight frontal bust framing"],
            }
        },
    )
    errs = _errors(validate_recipe(recipe))
    assert any(f["code"] == "recipe_variable_target" for f in errs)


def test_resolve_and_compile_reject_non_dict_recipe_controlled():
    for bad in (None, [], "recipe", 12):
        findings = validate_recipe(bad)  # type: ignore[arg-type]
        assert any(f["code"] == "recipe_type" for f in _errors(findings))
        with pytest.raises(RecipeValidationError) as resolve_exc:
            resolve_recipe(bad)  # type: ignore[arg-type]
        assert any(f["code"] == "recipe_type" for f in _errors(resolve_exc.value.findings))
        with pytest.raises(RecipeValidationError) as compile_exc:
            compile_recipe(bad)  # type: ignore[arg-type]
        assert any(f["code"] == "recipe_type" for f in _errors(compile_exc.value.findings))


def test_director_unpaired_surrogate_is_finding_not_encode_error():
    spec = _load_case(PARITY_CASES[1][1])
    surrogate = "framing \ud800 detail"
    variables = {
        "camera": {
            "type": "enum",
            "target": "director.camera",
            "choices": [spec["director"]["camera"], surrogate],
        }
    }
    recipe = _wrap_recipe_v11(spec, recipe_id="greek-marble-bust", variables=variables)
    findings = validate_recipe(recipe)
    assert not any(isinstance(f, BaseException) for f in findings)
    assert any(f["code"] == "recipe_variable_unicode" for f in _errors(findings))
    with pytest.raises(RecipeValidationError):
        compile_recipe(recipe, bindings={"camera": surrogate})


def test_canonical_hash_rejects_non_utf8_without_uncontrolled_error():
    with pytest.raises(RecipeError, match="UTF-8"):
        sha256_canonical({"x": "bad\ud800"})


def test_evidence_retrieval_failure_promoted_for_any_message(monkeypatch):
    from aipf import recipes as recipes_mod

    messages = [
        "Evidence retrieval unavailable: dependency missing",
        "upstream evidence index refused the query",
    ]
    for message in messages:
        def fake_lint(_spec, _message=message):
            return [{"level": "warning", "code": "evidence_retrieval_failure", "message": _message}]

        monkeypatch.setattr(recipes_mod, "lint_spec", fake_lint)
        spec = _load_case(PARITY_CASES[1][1])
        recipe = _wrap_recipe_v11(spec, recipe_id="greek-marble-bust", variables=_three_target_variables(spec))
        errs = _errors(validate_recipe(recipe))
        assert any(
            f["code"] == "evidence_retrieval_failure" and f["level"] == "error" and f["message"] == message
            for f in errs
        ), message


def test_cli_validate_handles_missing_and_malformed_schema(tmp_path: Path, monkeypatch):
    from aipf import recipes as recipes_mod
    from aipf import cli as cli_mod

    spec = _load_case(PARITY_CASES[1][1])
    path = _write_recipe(
        tmp_path / "r.json",
        _wrap_recipe_v11(spec, recipe_id="greek-marble-bust", variables=_three_target_variables(spec)),
    )

    def missing(_version):
        raise RecipeError("missing packaged schema: data/schemas/prompt_recipe_v1_1.schema.json")

    monkeypatch.setattr(recipes_mod, "_load_recipe_schema", missing)
    monkeypatch.setattr(sys, "argv", ["aipf", "recipe", "validate", str(path)])
    with pytest.raises(SystemExit) as missing_exc:
        cli_mod.main()
    assert missing_exc.value.code == 1

    def malformed(_version):
        raise RecipeError("malformed packaged schema: data/schemas/prompt_recipe_v1_1.schema.json: not an object")

    monkeypatch.setattr(recipes_mod, "_load_recipe_schema", malformed)
    monkeypatch.setattr(sys, "argv", ["aipf", "recipe", "validate", str(path)])
    with pytest.raises(SystemExit) as malformed_exc:
        cli_mod.main()
    assert malformed_exc.value.code == 1


def test_oversized_director_binding_diagnostic_is_bounded():
    spec = _load_case(PARITY_CASES[1][1])
    huge = "x" * 50000
    recipe = _wrap_recipe_v11(spec, recipe_id="greek-marble-bust", variables=_three_target_variables(spec))
    findings = validate_recipe(recipe, bindings={"camera": huge})
    errs = _errors(findings)
    assert errs
    joined = " ".join(f["message"] for f in errs)
    assert huge not in joined
    assert len(joined) < 2000
    assert any(f["code"] == "recipe_variable_unicode" for f in errs)


def test_effective_bindings_key_order_stable_across_variable_reorder():
    spec = _load_case(PARITY_CASES[1][1])
    variables = _three_target_variables(spec)
    recipe_a = _wrap_recipe_v11(spec, recipe_id="greek-marble-bust", variables=variables)
    recipe_b = _wrap_recipe_v11(
        spec,
        recipe_id="greek-marble-bust",
        variables={
            "ratio": variables["ratio"],
            "camera": variables["camera"],
            "light": variables["light"],
        },
    )
    bind = {"light": "soft overhead museum skylight", "camera": "tight frontal bust framing"}
    ea = compile_recipe(recipe_a, bind)["variable_resolution"]["effective_bindings"]
    eb = compile_recipe(recipe_b, bind)["variable_resolution"]["effective_bindings"]
    assert list(ea.keys()) == sorted(ea.keys())
    assert list(ea.keys()) == list(eb.keys())
    assert list(ea.items()) == list(eb.items())


def test_resolved_lint_failure_blocks_compiler(monkeypatch):
    from aipf import recipes as recipes_mod

    calls: list[dict] = []
    compile_calls: list[dict] = []

    def fake_lint(spec):
        calls.append(deepcopy(spec))
        if len(calls) == 1:
            return []
        return [{"level": "error", "code": "resolved_only_gate", "message": "resolved specification rejected"}]

    def fake_compile(spec):
        compile_calls.append(deepcopy(spec))
        return {
            "prompt": "should-not-run",
            "compiler_version": "test",
            "evidence_snapshot": {"snapshot_sha256": "0" * 64},
            "lint_findings": [],
            "compatibility_audit": {},
        }

    monkeypatch.setattr(recipes_mod, "lint_spec", fake_lint)
    monkeypatch.setattr(recipes_mod, "compile_result", fake_compile)
    spec = _load_case(PARITY_CASES[1][1])
    recipe = _wrap_recipe_v11(spec, recipe_id="greek-marble-bust", variables=_three_target_variables(spec))
    with pytest.raises(RecipeValidationError) as exc:
        compile_recipe(recipe, bindings={"ratio": "1:1"})
    assert any(f["code"] == "resolved_only_gate" for f in _errors(exc.value.findings))
    assert compile_calls == []
    assert len(calls) >= 2


# --- PR4 final hardening (V3) ---------------------------------------------------


def test_non_string_recipe_and_variable_keys_are_findings():
    spec = _load_case(PARITY_CASES[1][1])
    recipe = _wrap_recipe_v11(spec, recipe_id="greek-marble-bust", variables=_three_target_variables(spec))
    recipe[1] = "bad-root-key"
    findings = validate_recipe(recipe)
    assert any(f["code"] == "recipe_key_type" for f in _errors(findings))
    with pytest.raises(RecipeValidationError) as resolve_exc:
        resolve_recipe(recipe)
    assert any(f["code"] == "recipe_key_type" for f in _errors(resolve_exc.value.findings))
    with pytest.raises(RecipeValidationError) as compile_exc:
        compile_recipe(recipe)
    assert any(f["code"] == "recipe_key_type" for f in _errors(compile_exc.value.findings))

    recipe2 = _wrap_recipe_v11(spec, recipe_id="greek-marble-bust", variables={})
    recipe2["variables"] = {2: {"type": "enum", "target": "output.aspect_ratio", "choices": ["1:1", "4:5"]}}
    errs = _errors(validate_recipe(recipe2))
    assert any(f["code"] == "recipe_key_type" and "variables" in f["message"] for f in errs)
    with pytest.raises(RecipeValidationError):
        compile_recipe(recipe2, bindings={})


def test_non_string_binding_keys_are_findings():
    spec = _load_case(PARITY_CASES[1][1])
    recipe = _wrap_recipe_v11(spec, recipe_id="greek-marble-bust", variables=_three_target_variables(spec))
    findings = validate_recipe(recipe, bindings={1: "1:1"})  # type: ignore[dict-item]
    assert any(f["code"] == "recipe_key_type" for f in _errors(findings))


def test_invalid_utf8_recipe_and_bindings_files(tmp_path: Path):
    bad_recipe = tmp_path / "bad_recipe.json"
    bad_bindings = tmp_path / "bad_bindings.json"
    bad_recipe.write_bytes(b'{"recipe_id": "x\xff"}')
    bad_bindings.write_bytes(b'{"ratio": "1:\xff"}')
    with pytest.raises(RecipeError, match="invalid UTF-8"):
        load_recipe(bad_recipe)
    with pytest.raises(RecipeError, match="invalid UTF-8"):
        load_bindings(bad_bindings)

    failed_validate = _run(_aipf_cmd("recipe", "validate", str(bad_recipe)))
    assert failed_validate.returncode == 1
    assert "Traceback" not in failed_validate.stderr
    assert "Traceback" not in failed_validate.stdout

    # Valid recipe + invalid bindings for compile: no prompt, exit 1, no traceback.
    good = _write_recipe(
        tmp_path / "good.json",
        _wrap_recipe_v11(
            _load_case(PARITY_CASES[1][1]),
            recipe_id="greek-marble-bust",
            variables=_three_target_variables(_load_case(PARITY_CASES[1][1])),
        ),
    )
    failed_compile = _run(
        _aipf_cmd("recipe", "compile", str(good), "--bindings", str(bad_bindings))
    )
    assert failed_compile.returncode == 1
    assert "Traceback" not in failed_compile.stderr
    assert "Create a coherent" not in failed_compile.stdout


def test_invalid_packaged_schema_definition_fails_closed(monkeypatch):
    from aipf import recipes as recipes_mod

    def fake_load_json(path):
        # Loads as a dict but fails Draft 2020-12 schema validity (invalid type).
        if str(path).endswith("prompt_recipe_v1_1.schema.json") or str(path).endswith(
            "prompt_recipe.schema.json"
        ):
            return {"type": 123}
        raise AssertionError(f"unexpected resource load: {path}")

    monkeypatch.setattr(recipes_mod, "load_json", fake_load_json)
    with pytest.raises(RecipeError, match="invalid packaged schema definition"):
        recipes_mod._load_recipe_schema("1.1")

    spec = _load_case(PARITY_CASES[1][1])
    recipe = _wrap_recipe_v11(spec, recipe_id="greek-marble-bust", variables=_three_target_variables(spec))
    with pytest.raises(RecipeError, match="invalid packaged schema definition"):
        validate_recipe(recipe)
