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
    spec = _load_case(PARITY_CASES[1][1])
    assert "→" in compile_result(spec)["prompt"]
    spec_path = tmp_path / "spec.json"
    recipe_path = tmp_path / "recipe.json"
    spec_path.write_text(json.dumps(spec, ensure_ascii=False) + "\n", encoding="utf-8")
    _write_recipe(recipe_path, _wrap_recipe(spec, recipe_id="greek-marble-bust"))
    legacy = _run(_aipf_cmd("compile", str(spec_path)))
    recipe = _run(_aipf_cmd("recipe", "compile", str(recipe_path)))
    assert legacy.returncode == 0, legacy.stderr
    assert recipe.returncode == 0, recipe.stderr
    assert recipe.stdout.encode("utf-8") == legacy.stdout.encode("utf-8")


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
