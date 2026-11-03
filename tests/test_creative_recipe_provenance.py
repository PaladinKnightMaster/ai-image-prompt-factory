"""PR-CR-002: creative recipe → generation provenance (offline only)."""
from __future__ import annotations

from pathlib import Path
import json
import os

import pytest
from jsonschema import Draft202012Validator

from aipf.creative_provenance import (
    EVIDENCE_COMPILATION_CONSISTENT,
    EVIDENCE_INCOMPLETE,
    EVIDENCE_LOCALLY_VERIFIED,
    EVIDENCE_PROVIDER_CONFIRMED,
    CreativeProvenanceError,
    assert_prompt_adapter_integrity,
    attach_creative_provenance,
    build_creative_provenance,
    classify_evidence_level,
    prepare_recipe_generation_bundle,
    simulate_completed_generation_metadata,
    utf8_sha256_text,
    verify_recipe_generation_bundle,
)
from aipf.model_adapter import build_generation_metadata, normalize_request, sha256_file
from aipf.recipes import compile_recipe, load_recipe, sha256_canonical

ROOT = Path(__file__).resolve().parents[1]
CR001 = ROOT / "recipes" / "cr-001-material-driven-fashion-editorial" / "1.0.0.json"
KNOWN_RECIPE_SHA = "60c4547ed59a31dfa1fcebd0dcc959729fff7a2f61d235a1fcb6228724aebdce"
KNOWN_PROMPT_SHA = "92f4c6643c005281ee2c287d72c05321aa0dd14043513761188a0b05c8e9a7e4"
SCHEMA = ROOT / "data" / "schemas" / "generation_metadata.schema.json"


def _load_schema() -> dict:
    return json.loads(SCHEMA.read_text(encoding="utf-8"))


def test_cr001_content_and_known_hashes_unchanged():
    recipe = load_recipe(CR001)
    assert recipe["recipe_id"] == "cr-001-material-driven-fashion-editorial"
    assert recipe["recipe_version"] == "1.0.0"
    assert sha256_canonical(recipe) == KNOWN_RECIPE_SHA
    receipt = compile_recipe(recipe)
    assert receipt["prompt_sha256"] == KNOWN_PROMPT_SHA
    assert receipt["recipe"]["recipe_sha256"] == KNOWN_RECIPE_SHA


def test_recipe_to_compilation_hash_chain_and_provenance_block():
    recipe = load_recipe(CR001)
    bindings = {
        "camera": recipe["variables"]["camera"]["choices"][1],
        "light": recipe["variables"]["light"]["choices"][0],
        "aspect": "1:1",
    }
    receipt = compile_recipe(recipe, bindings)
    prov = build_creative_provenance(receipt)
    assert prov["recipe_id"] == recipe["recipe_id"]
    assert prov["recipe_version"] == "1.0.0"
    assert prov["recipe_sha256"] == KNOWN_RECIPE_SHA
    assert prov["prompt_sha256"] == receipt["prompt_sha256"]
    assert prov["effective_bindings"]["aspect"] == "1:1"
    assert prov["resolved_semantic_spec_sha256"] == receipt["variable_resolution"][
        "resolved_semantic_spec_sha256"
    ]
    assert prov["recipe_receipt_sha256"] == sha256_canonical(receipt)
    assert utf8_sha256_text(receipt["compilation"]["prompt"]) == receipt["prompt_sha256"]


def test_prompt_integrity_rejects_unexpected_padding():
    with pytest.raises(CreativeProvenanceError, match="whitespace"):
        assert_prompt_adapter_integrity("  padded  ")


def test_prompt_integrity_accepts_compiler_trailing_newline():
    assert assert_prompt_adapter_integrity("body\n") == "body"


def test_adapter_prompt_matches_receipt_without_silent_alteration():
    recipe = load_recipe(CR001)
    receipt = compile_recipe(recipe)
    compiler_prompt = receipt["compilation"]["prompt"]
    prompt = assert_prompt_adapter_integrity(compiler_prompt)
    assert prompt + "\n" == compiler_prompt
    req = normalize_request(
        prompt=prompt,
        model="gpt-image-2",
        model_snapshot=None,
        execute=False,
        snapshot_explicit=False,
    )
    assert req["prompt"] == prompt
    assert req["prompt_sha256"] == utf8_sha256_text(prompt)
    assert req["prompt_sha256"] != receipt["prompt_sha256"]
    assert receipt["prompt_sha256"] == KNOWN_PROMPT_SHA


def test_prepare_bundle_offline_and_verify_compilation_consistent(tmp_path, monkeypatch):
    stage = tmp_path / "stage"
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = prepare_recipe_generation_bundle(
        recipe_path=CR001,
        output_dir=stage,
        bindings={"aspect": "4:5"},
    )
    assert result["manifest"]["evidence_level"] == EVIDENCE_COMPILATION_CONSISTENT
    assert (stage / "receipt.json").is_file()
    assert (stage / "prompt.txt").is_file()
    assert (stage / "generation.json").is_file()
    meta = json.loads((stage / "generation.json").read_text(encoding="utf-8"))
    assert meta["dry_run"] is True
    assert meta["generation_completed"] is False
    assert "creative_provenance" in meta
    Draft202012Validator(_load_schema()).validate(meta)

    report = verify_recipe_generation_bundle(
        stage,
        expect_recipe_id="cr-001-material-driven-fashion-editorial",
        expect_recipe_version="1.0.0",
        expect_recipe_sha256=KNOWN_RECIPE_SHA,
    )
    assert report["ok"] is True
    assert report["evidence_level"] == EVIDENCE_COMPILATION_CONSISTENT


def test_prepare_refuses_overwrite_without_force(tmp_path):
    stage = tmp_path / "stage"
    prepare_recipe_generation_bundle(recipe_path=CR001, output_dir=stage)
    with pytest.raises(CreativeProvenanceError, match="overwrite"):
        prepare_recipe_generation_bundle(recipe_path=CR001, output_dir=stage)


def test_prepare_refuses_website_generated_path(tmp_path):
    bad = tmp_path / "website" / "generated" / "bundle"
    bad.mkdir(parents=True)
    with pytest.raises(CreativeProvenanceError, match="gallery"):
        prepare_recipe_generation_bundle(recipe_path=CR001, output_dir=bad)


def test_dry_run_never_qualifies_as_completed(tmp_path):
    stage = tmp_path / "stage"
    prepare_recipe_generation_bundle(recipe_path=CR001, output_dir=stage)
    meta = json.loads((stage / "generation.json").read_text(encoding="utf-8"))
    assert meta["dry_run"] is True
    assert meta.get("generation_completed") is False
    report = verify_recipe_generation_bundle(stage)
    assert report["ok"] is True
    assert report["evidence_level"] == EVIDENCE_COMPILATION_CONSISTENT


def test_url_only_remains_incomplete(tmp_path):
    stage = tmp_path / "stage"
    prepare_recipe_generation_bundle(recipe_path=CR001, output_dir=stage)
    meta = json.loads((stage / "generation.json").read_text(encoding="utf-8"))
    completed = simulate_completed_generation_metadata(
        meta, output_path=stage / "unused.png", transport="url"
    )
    (stage / "generation.json").write_text(
        json.dumps(completed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    report = verify_recipe_generation_bundle(stage)
    assert report["ok"] is True or any(f["code"] == "url_only" for f in report["findings"])
    assert report["evidence_level"] == EVIDENCE_INCOMPLETE
    assert report["output_verified"] is False


def test_simulated_b64_output_verification(tmp_path):
    stage = tmp_path / "stage"
    prepare_recipe_generation_bundle(recipe_path=CR001, output_dir=stage)
    meta = json.loads((stage / "generation.json").read_text(encoding="utf-8"))
    output = stage / "output.png"
    output.write_bytes(b"fake-png-bytes-for-digest-only")
    completed = simulate_completed_generation_metadata(meta, output_path=output)
    assert completed["generation_completed"] is True
    assert completed["provider_verified_model_id"] is None
    (stage / "generation.json").write_text(
        json.dumps(completed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    report = verify_recipe_generation_bundle(stage)
    assert report["ok"] is True
    assert report["output_verified"] is True
    assert report["evidence_level"] == EVIDENCE_LOCALLY_VERIFIED
    assert report["evidence_level"] != EVIDENCE_PROVIDER_CONFIRMED
    assert sha256_file(output) == completed["result"]["output_sha256"]


def _write_completed_bundle(tmp_path, *, provider_verified_model_id=None, payload=b"local-asset"):
    stage = tmp_path / "stage"
    prepare_recipe_generation_bundle(recipe_path=CR001, output_dir=stage)
    meta = json.loads((stage / "generation.json").read_text(encoding="utf-8"))
    output = stage / "output.png"
    output.write_bytes(payload)
    completed = simulate_completed_generation_metadata(meta, output_path=output)
    completed["provider_verified_model_id"] = provider_verified_model_id
    (stage / "generation.json").write_text(
        json.dumps(completed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return stage, completed, output


def test_forged_provider_id_does_not_elevate_evidence(tmp_path):
    stage, completed, output = _write_completed_bundle(
        tmp_path, provider_verified_model_id="gpt-image-2-FORGED"
    )
    report = verify_recipe_generation_bundle(stage)
    assert report["ok"] is True
    assert report["output_verified"] is True
    assert report["evidence_level"] == EVIDENCE_LOCALLY_VERIFIED
    assert report["evidence_level"] != EVIDENCE_PROVIDER_CONFIRMED
    assert any(
        f["code"] == "claimed_provider_model_unverified" for f in report["findings"]
    )
    direct = classify_evidence_level(
        completed, output_path=output, output_matches=True
    )
    assert direct == EVIDENCE_LOCALLY_VERIFIED
    assert direct != EVIDENCE_PROVIDER_CONFIRMED


def test_legitimate_looking_provider_id_does_not_elevate_evidence(tmp_path):
    stage, completed, output = _write_completed_bundle(
        tmp_path, provider_verified_model_id="gpt-image-2"
    )
    report = verify_recipe_generation_bundle(stage)
    assert report["ok"] is True
    assert report["evidence_level"] == EVIDENCE_LOCALLY_VERIFIED
    assert report["evidence_level"] != EVIDENCE_PROVIDER_CONFIRMED
    assert classify_evidence_level(
        completed, output_path=output, output_matches=True
    ) == EVIDENCE_LOCALLY_VERIFIED


def test_null_provider_id_preserves_local_verification(tmp_path):
    stage, completed, output = _write_completed_bundle(
        tmp_path, provider_verified_model_id=None
    )
    report = verify_recipe_generation_bundle(stage)
    assert report["ok"] is True
    assert report["evidence_level"] == EVIDENCE_LOCALLY_VERIFIED
    assert any(f["code"] == "no_provider_verified_model" for f in report["findings"])
    assert classify_evidence_level(
        completed, output_path=output, output_matches=True
    ) == EVIDENCE_LOCALLY_VERIFIED


def test_mismatched_output_digest_rejected(tmp_path):
    stage = tmp_path / "stage"
    prepare_recipe_generation_bundle(recipe_path=CR001, output_dir=stage)
    meta = json.loads((stage / "generation.json").read_text(encoding="utf-8"))
    output = stage / "output.png"
    output.write_bytes(b"bytes-a")
    completed = simulate_completed_generation_metadata(meta, output_path=output)
    completed["result"]["output_sha256"] = "0" * 64
    (stage / "generation.json").write_text(
        json.dumps(completed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    report = verify_recipe_generation_bundle(stage)
    assert report["ok"] is False
    assert any(f["code"] == "output_sha_mismatch" for f in report["findings"])


def test_missing_output_with_completed_flag_rejected(tmp_path):
    stage = tmp_path / "stage"
    prepare_recipe_generation_bundle(recipe_path=CR001, output_dir=stage)
    meta = json.loads((stage / "generation.json").read_text(encoding="utf-8"))
    meta["dry_run"] = False
    meta["generation_completed"] = True
    meta["result"] = {
        "transport": "b64_json",
        "output_sha256": "a" * 64,
        "generation_completed": True,
    }
    (stage / "generation.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    report = verify_recipe_generation_bundle(stage)
    assert report["ok"] is False
    assert any(f["code"] == "missing_output" for f in report["findings"])


def test_incorrect_recipe_identity_rejected(tmp_path):
    stage = tmp_path / "stage"
    prepare_recipe_generation_bundle(recipe_path=CR001, output_dir=stage)
    report = verify_recipe_generation_bundle(
        stage, expect_recipe_id="not-the-recipe", expect_recipe_version="9.9.9"
    )
    assert report["ok"] is False
    codes = {f["code"] for f in report["findings"]}
    assert "recipe_id_mismatch" in codes
    assert "recipe_version_mismatch" in codes


def test_corrupted_receipt_linkage_rejected(tmp_path):
    stage = tmp_path / "stage"
    prepare_recipe_generation_bundle(recipe_path=CR001, output_dir=stage)
    meta = json.loads((stage / "generation.json").read_text(encoding="utf-8"))
    meta["creative_provenance"]["recipe_receipt_sha256"] = "b" * 64
    (stage / "generation.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    report = verify_recipe_generation_bundle(stage)
    assert report["ok"] is False
    assert any(f["code"] == "receipt_digest_mismatch" for f in report["findings"])


def test_prompt_tamper_rejected(tmp_path):
    stage = tmp_path / "stage"
    prepare_recipe_generation_bundle(recipe_path=CR001, output_dir=stage)
    prompt_path = stage / "prompt.txt"
    prompt_path.write_bytes(prompt_path.read_bytes() + b"\nTAMPER")
    report = verify_recipe_generation_bundle(stage)
    assert report["ok"] is False
    assert any(
        f["code"] in {"prompt_receipt_mismatch", "prompt_metadata_mismatch", "prompt_receipt_text_mismatch"}
        for f in report["findings"]
    )


def test_legacy_generation_metadata_without_provenance_still_schema_valid():
    req = normalize_request(
        prompt="hello world",
        model="gpt-image-2",
        model_snapshot=None,
        execute=False,
        snapshot_explicit=False,
    )
    meta = build_generation_metadata(
        req, prompt_profile="standard", compiler_version="3.2.0"
    )
    assert "creative_provenance" not in meta
    Draft202012Validator(_load_schema()).validate(meta)


def test_attach_provenance_requires_matching_prompt_hash():
    recipe = load_recipe(CR001)
    receipt = compile_recipe(recipe)
    prov = build_creative_provenance(receipt)
    req = normalize_request(
        prompt=receipt["compilation"]["prompt"],
        model="gpt-image-2",
        model_snapshot=None,
        execute=False,
        snapshot_explicit=False,
    )
    meta = build_generation_metadata(
        req, prompt_profile="standard", compiler_version=receipt["compiler_version"]
    )
    attached = attach_creative_provenance(meta, prov)
    assert attached["creative_provenance"]["recipe_id"] == recipe["recipe_id"]
    bad = dict(meta)
    bad["prompt_sha256"] = "0" * 64
    with pytest.raises(CreativeProvenanceError):
        attach_creative_provenance(bad, prov)


def test_relative_stage_requires_env(tmp_path, monkeypatch):
    monkeypatch.delenv("AIPF_CREATIVE_OUTPUT_PATH", raising=False)
    with pytest.raises(CreativeProvenanceError, match="absolute"):
        prepare_recipe_generation_bundle(
            recipe_path=CR001, output_dir="relative-stage"
        )
    monkeypatch.setenv("AIPF_CREATIVE_OUTPUT_PATH", str(tmp_path))
    result = prepare_recipe_generation_bundle(
        recipe_path=CR001, output_dir="relative-stage"
    )
    assert Path(result["stage_dir"]) == (tmp_path / "relative-stage").resolve()


def test_no_network_imports_during_prepare(tmp_path, monkeypatch):
    """Guard: prepare path must not import openai."""
    import sys

    monkeypatch.setitem(sys.modules, "openai", None)
    # If prepare tried to import openai, it would get None and fail oddly;
    # instead it should succeed without touching openai.
    prepare_recipe_generation_bundle(recipe_path=CR001, output_dir=tmp_path / "n")
