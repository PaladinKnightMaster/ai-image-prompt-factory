"""PR-CR-003A: private creative gallery candidate (synthetic fixtures only)."""
from __future__ import annotations

from pathlib import Path
import html
import json
import os
import struct
import zlib

import pytest
from jsonschema import Draft202012Validator

from aipf.creative_provenance import (
    EVIDENCE_MANUAL_IMPORT,
    CreativeProvenanceError,
    import_chatgpt_web_manual,
    prepare_recipe_generation_bundle,
)
from aipf.model_adapter import sha256_file
from aipf.private_gallery_candidate import (
    CANDIDATE_STATUS_PRIVATE,
    create_private_gallery_candidate,
    verify_private_gallery_candidate,
)
from aipf.recipes import load_recipe, sha256_canonical

ROOT = Path(__file__).resolve().parents[1]
CR001 = ROOT / "recipes" / "cr-001-material-driven-fashion-editorial" / "1.0.0.json"
KNOWN_RECIPE_SHA = "60c4547ed59a31dfa1fcebd0dcc959729fff7a2f61d235a1fcb6228724aebdce"
KNOWN_PROMPT_SHA = "92f4c6643c005281ee2c287d72c05321aa0dd14043513761188a0b05c8e9a7e4"
SCHEMA = ROOT / "data" / "schemas" / "creative_gallery_candidate.schema.json"


def _png_bytes(*, width: int = 8, height: int = 10, rgb=(10, 20, 30)) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    raw = b"".join(b"\x00" + bytes(rgb) * width for _ in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def _chain(tmp_path: Path):
    prep = tmp_path / "01_prep"
    prepare_recipe_generation_bundle(
        recipe_path=CR001,
        output_dir=prep,
        bindings={"aspect": "4:5"},
    )
    raw = tmp_path / "04_raw"
    raw.mkdir()
    img = raw / "synthetic.png"
    payload = _png_bytes(rgb=(3, 4, 5))
    img.write_bytes(payload)
    digest = sha256_file(img)
    custody = raw / "custody.txt"
    custody.write_text(f"SHA256: {digest}\n", encoding="utf-8", newline="\n")
    imp = tmp_path / "05_import"
    import_chatgpt_web_manual(
        prep_dir=prep,
        image_path=img,
        output_dir=imp,
        expect_image_sha256=digest,
        custody_path=custody,
        operator_attests_prompt_submission=True,
        attestation_note="synthetic test attestation",
    )
    return prep, img, digest, imp, payload


def _notes() -> dict:
    return {
        "recommendation": "KEEP",
        "strengths": ["garment architecture", "satin drape"],
        "limitations": ["one image only", "model unknown"],
        "scientific_claims": False,
        "non_custody_assessment_attachment_sha256": None,
    }


def test_cr001_unchanged():
    recipe = load_recipe(CR001)
    assert sha256_canonical(recipe) == KNOWN_RECIPE_SHA
    from aipf.recipes import compile_recipe

    assert compile_recipe(recipe)["prompt_sha256"] == KNOWN_PROMPT_SHA


def test_valid_private_candidate_creation_and_schema(tmp_path):
    prep, img, digest, imp, payload = _chain(tmp_path)
    out = tmp_path / "06_private_gallery_candidates" / "cand-synth-001"
    result = create_private_gallery_candidate(
        candidate_id="cand-synth-001",
        prep_dir=prep,
        import_dir=imp,
        output_dir=out,
        expect_image_sha256=digest,
        qualitative_review=_notes(),
    )
    assert result["ok"] is True
    assert result["candidate_status"] == CANDIDATE_STATUS_PRIVATE
    cand_path = out / "candidate.json"
    assert cand_path.is_file()
    cand = json.loads(cand_path.read_text(encoding="utf-8"))
    Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8"))).validate(cand)
    assert cand["candidate_id"] == "cand-synth-001"
    assert cand["candidate_status"] == "private_candidate"
    assert cand["generation_channel"] == "chatgpt_web_manual"
    assert cand["evidence_level"] == EVIDENCE_MANUAL_IMPORT
    assert cand["image"]["sha256"] == digest
    assert cand["model_identity"]["status"] == "unknown"
    assert cand["prompt_submission"]["submission_verification"] == "operator_attested_uncaptured"
    assert cand["rights_review_status"] == "pending"
    assert cand["publication_approval_status"] == "pending"
    assert cand["chatgpt_effective_prompt_known"] is False
    assert not list(out.glob("*.png"))
    assert img.read_bytes() == payload
    assert (imp / "original.png").read_bytes() == payload
    preview = out / "preview.html"
    assert preview.is_file()
    html_text = preview.read_text(encoding="utf-8")
    assert digest in html_text
    assert "private_candidate" in html_text
    assert "locally_verified_manual_import" in html_text
    report = verify_private_gallery_candidate(out)
    assert report["ok"] is True


def test_tampered_import_image_rejected(tmp_path):
    prep, img, digest, imp, _ = _chain(tmp_path)
    (imp / "original.png").write_bytes(_png_bytes(rgb=(9, 9, 9)))
    with pytest.raises(CreativeProvenanceError):
        create_private_gallery_candidate(
            candidate_id="bad",
            prep_dir=prep,
            import_dir=imp,
            output_dir=tmp_path / "06" / "bad",
            expect_image_sha256=digest,
            qualitative_review=_notes(),
        )


def test_missing_import_rejected(tmp_path):
    prep, _, digest, _, _ = _chain(tmp_path)
    with pytest.raises(CreativeProvenanceError):
        create_private_gallery_candidate(
            candidate_id="missing",
            prep_dir=prep,
            import_dir=tmp_path / "no-import",
            output_dir=tmp_path / "06" / "missing",
            expect_image_sha256=digest,
            qualitative_review=_notes(),
        )


def test_wrong_expect_hash_rejected(tmp_path):
    prep, _, _, imp, _ = _chain(tmp_path)
    with pytest.raises(CreativeProvenanceError, match="sha|hash|image"):
        create_private_gallery_candidate(
            candidate_id="hash",
            prep_dir=prep,
            import_dir=imp,
            output_dir=tmp_path / "06" / "hash",
            expect_image_sha256="0" * 64,
            qualitative_review=_notes(),
        )


def test_wrong_recipe_expectation_rejected(tmp_path):
    prep, _, digest, imp, _ = _chain(tmp_path)
    with pytest.raises(CreativeProvenanceError):
        create_private_gallery_candidate(
            candidate_id="recipe",
            prep_dir=prep,
            import_dir=imp,
            output_dir=tmp_path / "06" / "recipe",
            expect_image_sha256=digest,
            qualitative_review=_notes(),
            expect_recipe_id="not-cr-001",
        )


def test_api_claim_fields_rejected_on_verify(tmp_path):
    prep, _, digest, imp, _ = _chain(tmp_path)
    out = tmp_path / "06" / "api"
    create_private_gallery_candidate(
        candidate_id="api",
        prep_dir=prep,
        import_dir=imp,
        output_dir=out,
        expect_image_sha256=digest,
        qualitative_review=_notes(),
    )
    cand = json.loads((out / "candidate.json").read_text(encoding="utf-8"))
    cand["generation_channel"] = "openai_images_api"
    cand["model_identity"]["provider_verified_model_id"] = "gpt-image-2"
    (out / "candidate.json").write_text(json.dumps(cand, indent=2) + "\n", encoding="utf-8")
    report = verify_private_gallery_candidate(out)
    assert report["ok"] is False


def test_unknown_model_and_pending_gates(tmp_path):
    prep, _, digest, imp, _ = _chain(tmp_path)
    out = tmp_path / "06" / "gates"
    create_private_gallery_candidate(
        candidate_id="gates",
        prep_dir=prep,
        import_dir=imp,
        output_dir=out,
        expect_image_sha256=digest,
        qualitative_review=_notes(),
    )
    cand = json.loads((out / "candidate.json").read_text(encoding="utf-8"))
    assert cand["model_identity"]["status"] == "unknown"
    assert cand["model_identity"]["provider_verified_model_id"] is None
    assert cand["rights_review_status"] == "pending"
    assert cand["publication_approval_status"] == "pending"
    assert cand["prompt_submission"]["independent_capture_status"] == "unavailable"


def test_duplicate_refused(tmp_path):
    prep, _, digest, imp, _ = _chain(tmp_path)
    out = tmp_path / "06" / "dup"
    create_private_gallery_candidate(
        candidate_id="dup",
        prep_dir=prep,
        import_dir=imp,
        output_dir=out,
        expect_image_sha256=digest,
        qualitative_review=_notes(),
    )
    with pytest.raises(CreativeProvenanceError, match="overwrite|exist|duplicate|non-empty"):
        create_private_gallery_candidate(
            candidate_id="dup",
            prep_dir=prep,
            import_dir=imp,
            output_dir=out,
            expect_image_sha256=digest,
            qualitative_review=_notes(),
        )


def test_forbidden_public_and_cases_paths(tmp_path):
    prep, _, digest, imp, _ = _chain(tmp_path)
    for bad in (
        tmp_path / "website" / "generated" / "cand",
        tmp_path / "cases" / "experimental" / "cand",
        tmp_path / "cases" / "public" / "cand",
    ):
        bad.mkdir(parents=True)
        with pytest.raises(CreativeProvenanceError, match="gallery|cases|public|website|forbidden"):
            create_private_gallery_candidate(
                candidate_id="badpath",
                prep_dir=prep,
                import_dir=imp,
                output_dir=bad,
                expect_image_sha256=digest,
                qualitative_review=_notes(),
            )


def test_symlink_to_website_generated_rejected(tmp_path):
    prep, _, digest, imp, _ = _chain(tmp_path)
    target = tmp_path / "website" / "generated" / "linked"
    target.mkdir(parents=True)
    link = tmp_path / "link_out"
    try:
        os.symlink(target, link, target_is_directory=True)
    except OSError:
        pytest.skip("symlink not permitted")
    with pytest.raises(CreativeProvenanceError, match="gallery|website|forbidden"):
        create_private_gallery_candidate(
            candidate_id="sym",
            prep_dir=prep,
            import_dir=imp,
            output_dir=link,
            expect_image_sha256=digest,
            qualitative_review=_notes(),
        )


def test_html_escapes_unsafe_content(tmp_path):
    prep, _, digest, imp, _ = _chain(tmp_path)
    notes = _notes()
    notes["strengths"] = ['<script>alert("x")</script>', "ok"]
    notes["limitations"] = ["a & b < c"]
    out = tmp_path / "06" / "esc"
    create_private_gallery_candidate(
        candidate_id="esc",
        prep_dir=prep,
        import_dir=imp,
        output_dir=out,
        expect_image_sha256=digest,
        qualitative_review=notes,
    )
    text = (out / "preview.html").read_text(encoding="utf-8")
    assert "<script>alert" not in text
    assert html.escape('<script>alert("x")</script>') in text or "&lt;script&gt;" in text
    assert "&amp;" in text or "a &amp; b" in text


def test_public_gallery_unchanged_publishable_count():
    import importlib.util

    path = ROOT / "website" / "generate_gallery.py"
    spec = importlib.util.spec_from_file_location("aipf_generate_gallery", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    data = mod.records()
    assert sum(1 for x in data if x.get("output_image")) == 0
