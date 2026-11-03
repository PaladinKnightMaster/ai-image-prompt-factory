"""PR-CR-002A: ChatGPT web manual image import (offline, synthetic fixtures only)."""
from __future__ import annotations

from pathlib import Path
import json
import struct
import zlib

import pytest
from jsonschema import Draft202012Validator

from aipf.creative_provenance import (
    EVIDENCE_LOCALLY_VERIFIED,
    EVIDENCE_MANUAL_IMPORT,
    EVIDENCE_PROVIDER_CONFIRMED,
    CreativeProvenanceError,
    import_chatgpt_web_manual,
    prepare_recipe_generation_bundle,
    verify_chatgpt_web_manual,
    verify_recipe_generation_bundle,
)
from aipf.model_adapter import sha256_file
from aipf.recipes import load_recipe, sha256_canonical

ROOT = Path(__file__).resolve().parents[1]
CR001 = ROOT / "recipes" / "cr-001-material-driven-fashion-editorial" / "1.0.0.json"
KNOWN_RECIPE_SHA = "60c4547ed59a31dfa1fcebd0dcc959729fff7a2f61d235a1fcb6228724aebdce"
KNOWN_PROMPT_SHA = "92f4c6643c005281ee2c287d72c05321aa0dd14043513761188a0b05c8e9a7e4"
SCHEMA = ROOT / "data" / "schemas" / "chatgpt_web_manual_source.schema.json"


def _png_bytes(*, width: int = 8, height: int = 10, rgb: tuple[int, int, int] = (10, 20, 30)) -> bytes:
    """Minimal valid RGB PNG with distinct digest per color/size."""

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    raw = b"".join(
        b"\x00" + bytes(rgb) * width for _ in range(height)
    )
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def _write_png(path: Path, **kwargs) -> Path:
    path.write_bytes(_png_bytes(**kwargs))
    return path


def _write_custody(path: Path, digest: str) -> Path:
    path.write_text(
        "AIPF synthetic custody\n"
        f"SHA256: {digest}\n"
        "Source channel: chatgpt_web_manual\n"
        "Publication status: private_only\n",
        encoding="utf-8",
        newline="\n",
    )
    return path


def _prep(tmp_path: Path) -> Path:
    stage = tmp_path / "prep"
    prepare_recipe_generation_bundle(
        recipe_path=CR001,
        output_dir=stage,
        bindings={"aspect": "4:5"},
    )
    return stage


def _import_ok(tmp_path: Path, *, attestation: bool = True, capture: bool = False, **kwargs):
    prep = _prep(tmp_path)
    raw_root = tmp_path / "raw_immutable"
    raw_root.mkdir()
    image = _write_png(raw_root / "synthetic.png", rgb=(11, 22, 33))
    digest = sha256_file(image)
    custody = _write_custody(raw_root / "download_custody.txt", digest)
    out = tmp_path / "import_out"
    call = {
        "prep_dir": prep,
        "image_path": image,
        "output_dir": out,
        "expect_image_sha256": digest,
        "custody_path": custody,
    }
    if capture:
        submitted = tmp_path / "captured_submission.txt"
        submitted.write_bytes((prep / "prompt.txt").read_bytes())
        call["submitted_prompt_path"] = submitted
    elif attestation:
        call["operator_attests_prompt_submission"] = True
        call["attestation_note"] = "Operator attests exact ChatGPT paste of prep prompt."
    call.update(kwargs)
    result = import_chatgpt_web_manual(**call)
    return prep, image, custody, out, result, digest


def test_cr001_digests_unchanged():
    recipe = load_recipe(CR001)
    assert sha256_canonical(recipe) == KNOWN_RECIPE_SHA
    from aipf.recipes import compile_recipe

    assert compile_recipe(recipe)["prompt_sha256"] == KNOWN_PROMPT_SHA


def test_successful_synthetic_manual_import_and_schema(tmp_path):
    prep, image, custody, out, result, digest = _import_ok(tmp_path)
    assert result["ok"] is True
    assert result["evidence_level"] == EVIDENCE_MANUAL_IMPORT
    assert result["evidence_level"] != EVIDENCE_PROVIDER_CONFIRMED
    assert result["evidence_level"] != EVIDENCE_LOCALLY_VERIFIED
    source_path = out / "source.json"
    assert source_path.is_file()
    source = json.loads(source_path.read_text(encoding="utf-8"))
    Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8"))).validate(source)
    assert source["record_kind"] == "chatgpt_web_manual_source"
    assert source["generation_channel"] == "chatgpt_web_manual"
    assert source["image"]["sha256"] == digest
    assert source["image"]["width"] == 8
    assert source["image"]["height"] == 10
    assert source["image"]["mime_type"] == "image/png"
    assert source["model_identity"]["status"] == "unknown"
    assert source["model_identity"]["provider_verified_model_id"] is None
    assert source["publication_status"] == "private_only"
    assert source["prompt_submission"]["chatgpt_effective_prompt_known"] is False
    assert (out / "original.png").read_bytes() == image.read_bytes()
    assert not (out / "submitted_prompt_capture.txt").exists()
    report = verify_chatgpt_web_manual(out)
    assert report["ok"] is True
    assert report["evidence_level"] == EVIDENCE_MANUAL_IMPORT


def test_evidence_classification_manual_not_api(tmp_path):
    _, _, _, out, result, _ = _import_ok(tmp_path)
    assert result["evidence_level"] == EVIDENCE_MANUAL_IMPORT
    source = json.loads((out / "source.json").read_text(encoding="utf-8"))
    assert "transport" not in source
    assert "result" not in source or "transport" not in (source.get("result") or {})
    assert source.get("provider_verified_model_id") in (None, ...)
    assert "provider_verified_model_id" not in source or source["model_identity"][
        "provider_verified_model_id"
    ] is None


def test_expect_image_sha_comparison(tmp_path):
    prep = _prep(tmp_path)
    image = _write_png(tmp_path / "img.png")
    digest = sha256_file(image)
    custody = _write_custody(tmp_path / "custody.txt", digest)
    with pytest.raises(CreativeProvenanceError, match="image_sha|expect"):
        import_chatgpt_web_manual(
            prep_dir=prep,
            image_path=image,
            output_dir=tmp_path / "out",
            expect_image_sha256="0" * 64,
            custody_path=custody,
            operator_attests_prompt_submission=True,
        )


def test_missing_and_corrupted_png_rejected(tmp_path):
    prep = _prep(tmp_path)
    missing = tmp_path / "missing.png"
    with pytest.raises(CreativeProvenanceError, match="missing|not found|image"):
        import_chatgpt_web_manual(
            prep_dir=prep,
            image_path=missing,
            output_dir=tmp_path / "out1",
            expect_image_sha256="a" * 64,
            operator_attests_prompt_submission=True,
        )
    bad = tmp_path / "bad.png"
    bad.write_bytes(b"not-a-png")
    digest = sha256_file(bad)
    custody = _write_custody(tmp_path / "c.txt", digest)
    with pytest.raises(CreativeProvenanceError, match="PNG|format|signature"):
        import_chatgpt_web_manual(
            prep_dir=prep,
            image_path=bad,
            output_dir=tmp_path / "out2",
            expect_image_sha256=digest,
            custody_path=custody,
            operator_attests_prompt_submission=True,
        )


def test_custody_hash_mismatch_rejected(tmp_path):
    prep = _prep(tmp_path)
    image = _write_png(tmp_path / "img.png")
    digest = sha256_file(image)
    custody = _write_custody(tmp_path / "custody.txt", "b" * 64)
    with pytest.raises(CreativeProvenanceError, match="custody"):
        import_chatgpt_web_manual(
            prep_dir=prep,
            image_path=image,
            output_dir=tmp_path / "out",
            expect_image_sha256=digest,
            custody_path=custody,
            operator_attests_prompt_submission=True,
        )


def test_wrong_recipe_expectation_rejected(tmp_path):
    prep = _prep(tmp_path)
    image = _write_png(tmp_path / "img.png")
    digest = sha256_file(image)
    custody = _write_custody(tmp_path / "custody.txt", digest)
    with pytest.raises(CreativeProvenanceError, match="recipe"):
        import_chatgpt_web_manual(
            prep_dir=prep,
            image_path=image,
            output_dir=tmp_path / "out",
            expect_image_sha256=digest,
            custody_path=custody,
            operator_attests_prompt_submission=True,
            expect_recipe_id="not-this-recipe",
        )


def test_captured_prompt_mismatch_rejected(tmp_path):
    prep = _prep(tmp_path)
    image = _write_png(tmp_path / "img.png")
    digest = sha256_file(image)
    custody = _write_custody(tmp_path / "custody.txt", digest)
    submitted = tmp_path / "wrong.txt"
    submitted.write_text("not the prep prompt\n", encoding="utf-8")
    with pytest.raises(CreativeProvenanceError, match="prompt"):
        import_chatgpt_web_manual(
            prep_dir=prep,
            image_path=image,
            output_dir=tmp_path / "out",
            expect_image_sha256=digest,
            custody_path=custody,
            submitted_prompt_path=submitted,
        )


def test_operator_attested_uncaptured_prompt_handling(tmp_path):
    prep, image, _, out, result, _ = _import_ok(tmp_path, attestation=True, capture=False)
    source = json.loads((out / "source.json").read_text(encoding="utf-8"))
    ps = source["prompt_submission"]
    assert ps["independent_capture_status"] == "unavailable"
    assert ps["submission_verification"] == "operator_attested_uncaptured"
    assert ps["submitted_prompt_sha256"] is None
    assert ps["intended_adapter_prompt_sha256"] == sha256_file(prep / "prompt.txt")
    assert ps["operator_attestation"]["attested"] is True
    # Must not mislabel a prep copy as independent ChatGPT capture.
    assert not (out / "submitted_prompt_capture.txt").exists()
    assert result["ok"] is True


def test_exact_captured_prompt_accepted(tmp_path):
    prep, _, _, out, result, _ = _import_ok(tmp_path, attestation=False, capture=True)
    source = json.loads((out / "source.json").read_text(encoding="utf-8"))
    ps = source["prompt_submission"]
    assert ps["independent_capture_status"] == "provided"
    assert ps["submission_verification"] == "exact_match"
    assert ps["submitted_prompt_sha256"] == sha256_file(prep / "prompt.txt")
    capture = out / "submitted_prompt_capture.txt"
    assert capture.is_file()
    assert capture.read_bytes() == (prep / "prompt.txt").read_bytes()
    assert result["ok"] is True


def test_duplicate_import_same_destination_refused(tmp_path):
    prep = _prep(tmp_path)
    image = _write_png(tmp_path / "img.png", rgb=(1, 2, 3))
    digest = sha256_file(image)
    custody = _write_custody(tmp_path / "custody.txt", digest)
    out = tmp_path / "import_out"
    import_chatgpt_web_manual(
        prep_dir=prep,
        image_path=image,
        output_dir=out,
        expect_image_sha256=digest,
        custody_path=custody,
        operator_attests_prompt_submission=True,
    )
    with pytest.raises(CreativeProvenanceError, match="overwrite|exist|duplicate"):
        import_chatgpt_web_manual(
            prep_dir=prep,
            image_path=image,
            output_dir=out,
            expect_image_sha256=digest,
            custody_path=custody,
            operator_attests_prompt_submission=True,
        )


def test_forbidden_public_paths_rejected(tmp_path):
    prep = _prep(tmp_path)
    image = _write_png(tmp_path / "img.png")
    digest = sha256_file(image)
    custody = _write_custody(tmp_path / "custody.txt", digest)
    bad = tmp_path / "website" / "generated" / "import"
    bad.mkdir(parents=True)
    with pytest.raises(CreativeProvenanceError, match="gallery|public|website"):
        import_chatgpt_web_manual(
            prep_dir=prep,
            image_path=image,
            output_dir=bad,
            expect_image_sha256=digest,
            custody_path=custody,
            operator_attests_prompt_submission=True,
        )


def test_unknown_model_identity(tmp_path):
    _, _, _, out, _, _ = _import_ok(tmp_path)
    source = json.loads((out / "source.json").read_text(encoding="utf-8"))
    assert source["model_identity"]["status"] == "unknown"
    assert source["model_identity"]["provider_verified_model_id"] is None


def test_reject_api_provider_confirmation_claims_on_verify(tmp_path):
    _, _, _, out, _, _ = _import_ok(tmp_path)
    source = json.loads((out / "source.json").read_text(encoding="utf-8"))
    source["model_identity"]["provider_verified_model_id"] = "gpt-image-2-FORGED"
    source["model_identity"]["status"] = "provider_confirmed"
    (out / "source.json").write_text(
        json.dumps(source, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    report = verify_chatgpt_web_manual(out)
    assert report["ok"] is False
    codes = {f["code"] for f in report["findings"]}
    assert "provider_claim_forbidden" in codes or "model_identity_invalid" in codes
    assert report["evidence_level"] != EVIDENCE_PROVIDER_CONFIRMED


def test_original_source_bytes_unchanged(tmp_path):
    prep = _prep(tmp_path)
    raw = tmp_path / "raw"
    raw.mkdir()
    image = _write_png(raw / "original.png", rgb=(9, 8, 7))
    before = image.read_bytes()
    digest = sha256_file(image)
    custody = _write_custody(raw / "custody.txt", digest)
    out = tmp_path / "import_out"
    import_chatgpt_web_manual(
        prep_dir=prep,
        image_path=image,
        output_dir=out,
        expect_image_sha256=digest,
        custody_path=custody,
        operator_attests_prompt_submission=True,
    )
    assert image.read_bytes() == before
    assert custody.read_text(encoding="utf-8").startswith("AIPF synthetic custody")
    assert (out / "original.png").read_bytes() == before


def test_api_provenance_still_works(tmp_path):
    prep = _prep(tmp_path)
    report = verify_recipe_generation_bundle(
        prep,
        expect_recipe_id="cr-001-material-driven-fashion-editorial",
        expect_recipe_version="1.0.0",
        expect_recipe_sha256=KNOWN_RECIPE_SHA,
    )
    assert report["ok"] is True


def test_require_prompt_evidence_mode(tmp_path):
    prep = _prep(tmp_path)
    image = _write_png(tmp_path / "img.png")
    digest = sha256_file(image)
    custody = _write_custody(tmp_path / "custody.txt", digest)
    with pytest.raises(CreativeProvenanceError, match="prompt|attest"):
        import_chatgpt_web_manual(
            prep_dir=prep,
            image_path=image,
            output_dir=tmp_path / "out",
            expect_image_sha256=digest,
            custody_path=custody,
        )
