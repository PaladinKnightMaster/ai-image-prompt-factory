"""Private creative gallery candidates (PR-CR-003A).

Connects verified PromptRecipe preparation + ChatGPT web manual import into a
private candidate record and local HTML preview. Never publishes to
``website/generated`` and never copies raster bytes into the git repository.
"""
from __future__ import annotations

from datetime import datetime, timezone
from html import escape
from pathlib import Path
import json
import re
from typing import Any

from .creative_provenance import (
    CHATGPT_WEB_IMAGE_NAME,
    CHATGPT_WEB_SOURCE_NAME,
    EVIDENCE_MANUAL_IMPORT,
    PROMPT_NAME,
    CreativeProvenanceError,
    _atomic_write_text,
    _load_json,
    _resolve_stage_root,
    inspect_png_file,
    verify_chatgpt_web_manual,
    verify_recipe_generation_bundle,
)
from .model_adapter import sha256_file

CANDIDATE_SCHEMA_VERSION = "1.0.0"
CANDIDATE_STATUS_PRIVATE = "private_candidate"
CANDIDATE_NAME = "candidate.json"
PREVIEW_NAME = "preview.html"

_CANDIDATE_AUTHENTICITY_LIMITS = [
    "Private creative gallery candidate only; not a public gallery entry.",
    "Locally verified manual-import evidence is not independent provider-origin proof.",
    "ChatGPT internal effective prompt is not known.",
    "Model identity is unknown unless separately attested.",
    "Rights review and publication approval remain pending until separately authorized.",
    "Does not participate in EXP-019, ESR, or AIPF-AIQ scientific evaluation.",
    "Cannot automatically promote into website/generated or Pages.",
]

_EXTRA_FORBIDDEN = (
    "website/generated",
    "website\\generated",
    "/cases/",
    "\\cases\\",
    "/cases\\",
    "\\cases/",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_private_candidate_root(path: str | Path) -> Path:
    resolved = _resolve_stage_root(path)
    posix = resolved.as_posix()
    for prefix in _EXTRA_FORBIDDEN:
        if prefix.replace("\\", "/") in posix:
            raise CreativeProvenanceError(
                f"refusing private candidate under forbidden path ({prefix}): {resolved}"
            )
    # Refuse paths inside the repository tree (source checkout).
    try:
        repo_root = Path(__file__).resolve().parents[2]
        resolved.relative_to(repo_root)
    except ValueError:
        return resolved
    raise CreativeProvenanceError(
        f"refusing private candidate inside repository tree: {resolved}"
    )


def _require_qualitative_review(notes: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(notes, dict):
        raise CreativeProvenanceError("qualitative_review must be an object")
    for key in ("recommendation", "strengths", "limitations"):
        if key not in notes:
            raise CreativeProvenanceError(f"qualitative_review missing {key}")
    if notes.get("scientific_claims") is not False:
        raise CreativeProvenanceError("qualitative_review.scientific_claims must be false")
    strengths = notes.get("strengths")
    limitations = notes.get("limitations")
    if not isinstance(strengths, list) or not all(isinstance(x, str) for x in strengths):
        raise CreativeProvenanceError("qualitative_review.strengths must be a string array")
    if not isinstance(limitations, list) or not all(isinstance(x, str) for x in limitations):
        raise CreativeProvenanceError("qualitative_review.limitations must be a string array")
    attach = notes.get("non_custody_assessment_attachment_sha256")
    if attach is not None and not re.fullmatch(r"[0-9a-f]{64}", str(attach)):
        raise CreativeProvenanceError(
            "non_custody_assessment_attachment_sha256 must be 64 lowercase hex or null"
        )
    return {
        "recommendation": str(notes["recommendation"]),
        "strengths": list(strengths),
        "limitations": list(limitations),
        "scientific_claims": False,
        "non_custody_assessment_attachment_sha256": attach,
    }


def _render_preview_html(candidate: dict[str, Any], *, prompt_text: str) -> str:
    image_path = Path(candidate["image"]["private_image_path"])
    try:
        image_uri = image_path.resolve().as_uri()
    except OSError:
        image_uri = ""
    recipe = candidate["recipe"]
    bindings = recipe.get("effective_bindings") or {}
    review = candidate["qualitative_review"]
    strengths = "".join(f"<li>{escape(x)}</li>" for x in review["strengths"])
    limitations = "".join(f"<li>{escape(x)}</li>" for x in review["limitations"])
    limits = "".join(f"<li>{escape(x)}</li>" for x in candidate["authenticity_limits"])
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Private candidate {escape(candidate["candidate_id"])}</title>
<style>
body{{font:16px/1.5 system-ui,sans-serif;margin:24px;color:#1f2328;background:#f6f4ef;max-width:960px}}
img{{max-width:100%;height:auto;border:1px solid #d8d2c8}}
pre{{white-space:pre-wrap;background:#fff;border:1px solid #d8d2c8;padding:12px}}
.meta{{color:#656d76}}
.warn{{border-left:4px solid #8a5a2b;padding-left:12px;margin:16px 0}}
</style>
</head>
<body>
<h1>Private gallery candidate</h1>
<p class="meta">Local preview only — not a public gallery page.</p>
<p><b>ID:</b> {escape(candidate["candidate_id"])}<br>
<b>Status:</b> {escape(candidate["candidate_status"])}<br>
<b>Recipe:</b> {escape(recipe["recipe_id"])} {escape(recipe["recipe_version"])}<br>
<b>Channel:</b> {escape(candidate["generation_channel"])}<br>
<b>Evidence:</b> {escape(candidate["evidence_level"])}</p>
<section>
<h2>Verified imported image</h2>
{"<img src=\"" + escape(image_uri, quote=True) + "\" alt=\"verified private import\">" if image_uri else "<p>Image path unavailable</p>"}
<p class="meta">SHA-256: <code>{escape(candidate["image"]["sha256"])}</code><br>
Dimensions: {candidate["image"]["width"]}×{candidate["image"]["height"]}<br>
Requested aspect: {escape(str(candidate["image"].get("requested_aspect_ratio")))}<br>
Observed aspect: {escape(candidate["image"]["observed_aspect_ratio"])}</p>
</section>
<section>
<h2>Prepared AIPF adapter-effective prompt</h2>
<pre>{escape(prompt_text)}</pre>
<p class="meta">adapter_prompt_sha256: <code>{escape(candidate["prompt"]["adapter_prompt_sha256"])}</code></p>
</section>
<section>
<h2>Configuration</h2>
<ul>
<li>Camera: {escape(str(bindings.get("camera")))}</li>
<li>Light: {escape(str(bindings.get("light")))}</li>
<li>Aspect: {escape(str(bindings.get("aspect")))}</li>
</ul>
</section>
<section>
<h2>Qualitative review</h2>
<p><b>Recommendation:</b> {escape(review["recommendation"])}</p>
<p><b>Strengths</b></p><ul>{strengths}</ul>
<p><b>Limitations</b></p><ul>{limitations}</ul>
<p class="meta">scientific_claims: false</p>
</section>
<section class="warn">
<h2>Uncertainties and gates</h2>
<ul>
<li>Model identity: {escape(candidate["model_identity"]["status"])} (provider_verified_model_id null)</li>
<li>Prompt submission: {escape(candidate["prompt_submission"]["submission_verification"])} / capture {escape(candidate["prompt_submission"]["independent_capture_status"])}</li>
<li>ChatGPT effective prompt known: false</li>
<li>Rights review: {escape(candidate["rights_review_status"])}</li>
<li>Publication approval: {escape(candidate["publication_approval_status"])}</li>
</ul>
<p><b>Authenticity limits</b></p><ul>{limits}</ul>
</section>
</body>
</html>
"""


def create_private_gallery_candidate(
    *,
    candidate_id: str,
    prep_dir: str | Path,
    import_dir: str | Path,
    output_dir: str | Path,
    expect_image_sha256: str,
    qualitative_review: dict[str, Any],
    expect_recipe_id: str | None = None,
    expect_recipe_version: str | None = None,
    expect_recipe_sha256: str | None = None,
) -> dict[str, Any]:
    """Create a private candidate + local HTML preview after provenance verification."""
    if not candidate_id or not isinstance(candidate_id, str):
        raise CreativeProvenanceError("candidate_id is required")
    if not re.fullmatch(r"[0-9a-f]{64}", expect_image_sha256 or ""):
        raise CreativeProvenanceError("expect_image_sha256 must be 64 lowercase hex")

    review = _require_qualitative_review(qualitative_review)
    prep = Path(prep_dir)
    imp = Path(import_dir)
    stage = _resolve_private_candidate_root(output_dir)

    prep_report = verify_recipe_generation_bundle(
        prep,
        expect_recipe_id=expect_recipe_id,
        expect_recipe_version=expect_recipe_version,
        expect_recipe_sha256=expect_recipe_sha256,
    )
    if not prep_report.get("ok"):
        raise CreativeProvenanceError(
            "preparation bundle verification failed: "
            + "; ".join(
                f["message"]
                for f in prep_report.get("findings", [])
                if f.get("level") == "error"
            )
        )

    import_report = verify_chatgpt_web_manual(imp)
    if not import_report.get("ok"):
        raise CreativeProvenanceError(
            "manual-import verification failed: "
            + "; ".join(
                f["message"]
                for f in import_report.get("findings", [])
                if f.get("level") == "error"
            )
        )

    source = _load_json(imp / CHATGPT_WEB_SOURCE_NAME)
    if source.get("generation_channel") != "chatgpt_web_manual":
        raise CreativeProvenanceError("import is not chatgpt_web_manual")
    if source.get("evidence_level") != EVIDENCE_MANUAL_IMPORT:
        raise CreativeProvenanceError("import evidence_level is not locally_verified_manual_import")
    if source.get("record_kind") != "chatgpt_web_manual_source":
        raise CreativeProvenanceError("import record_kind mismatch")

    image_path = imp / CHATGPT_WEB_IMAGE_NAME
    png = inspect_png_file(image_path)
    if png["sha256"] != expect_image_sha256:
        raise CreativeProvenanceError("imported image SHA-256 does not match expect_image_sha256")
    if png["sha256"] != (source.get("image") or {}).get("sha256"):
        raise CreativeProvenanceError("imported image digest does not match source.json")
    if import_report.get("image_sha256") != png["sha256"]:
        raise CreativeProvenanceError("verify report image digest mismatch")

    recipe_block = source.get("recipe") or {}
    gen = _load_json(prep / "generation.json")
    prov = gen.get("creative_provenance") or {}
    for key in (
        "recipe_id",
        "recipe_version",
        "recipe_sha256",
        "recipe_receipt_sha256",
        "adapter_prompt_sha256",
    ):
        if recipe_block.get(key) != prov.get(key):
            raise CreativeProvenanceError(f"prep/import recipe linkage mismatch on {key}")
    if recipe_block.get("compiler_prompt_sha256") != prov.get("prompt_sha256"):
        raise CreativeProvenanceError("compiler prompt digest linkage mismatch")

    if expect_recipe_id and recipe_block.get("recipe_id") != expect_recipe_id:
        raise CreativeProvenanceError("recipe_id does not match expectation")
    if expect_recipe_version and recipe_block.get("recipe_version") != expect_recipe_version:
        raise CreativeProvenanceError("recipe_version does not match expectation")
    if expect_recipe_sha256 and recipe_block.get("recipe_sha256") != expect_recipe_sha256:
        raise CreativeProvenanceError("recipe_sha256 does not match expectation")

    prompt_path = prep / PROMPT_NAME
    if sha256_file(prompt_path) != recipe_block.get("adapter_prompt_sha256"):
        raise CreativeProvenanceError("preparation prompt.txt digest mismatch")
    prompt_text = prompt_path.read_text(encoding="utf-8")

    model = source.get("model_identity") or {}
    if model.get("status") != "unknown" or model.get("provider_verified_model_id") is not None:
        raise CreativeProvenanceError("model identity must remain unknown on manual channel")

    prompt_sub = source.get("prompt_submission") or {}
    if prompt_sub.get("chatgpt_effective_prompt_known") is not False:
        raise CreativeProvenanceError("chatgpt_effective_prompt_known must be false")

    dest_cand = stage / CANDIDATE_NAME
    dest_preview = stage / PREVIEW_NAME
    if stage.exists() and any(stage.iterdir()):
        raise CreativeProvenanceError(
            f"refusing private candidate into non-empty destination: {stage}"
        )
    for path in (dest_cand, dest_preview):
        if path.exists():
            raise CreativeProvenanceError(
                f"refusing duplicate/overwrite of existing candidate file: {path}"
            )

    created = _utc_now()
    candidate: dict[str, Any] = {
        "schema_version": CANDIDATE_SCHEMA_VERSION,
        "record_kind": "creative_gallery_candidate",
        "candidate_id": candidate_id,
        "candidate_status": CANDIDATE_STATUS_PRIVATE,
        "recipe": {
            "recipe_id": recipe_block["recipe_id"],
            "recipe_version": recipe_block["recipe_version"],
            "recipe_schema_version": recipe_block.get("recipe_schema_version"),
            "recipe_sha256": recipe_block["recipe_sha256"],
            "semantic_spec_sha256": recipe_block.get("semantic_spec_sha256"),
            "recipe_receipt_sha256": recipe_block["recipe_receipt_sha256"],
            "adapter_prompt_sha256": recipe_block["adapter_prompt_sha256"],
            "compiler_prompt_sha256": recipe_block["compiler_prompt_sha256"],
            "effective_bindings": dict(recipe_block.get("effective_bindings") or {}),
            "prep_dir": str(prep.resolve()),
        },
        "import_reference": {
            "import_dir": str(imp.resolve()),
            "source_record_kind": "chatgpt_web_manual_source",
            "image_sha256": png["sha256"],
        },
        "generation_channel": "chatgpt_web_manual",
        "evidence_level": EVIDENCE_MANUAL_IMPORT,
        "prompt": {
            "adapter_prompt_sha256": recipe_block["adapter_prompt_sha256"],
            "adapter_prompt_path": str(prompt_path.resolve()),
            "compiler_prompt_sha256": recipe_block.get("compiler_prompt_sha256"),
        },
        "prompt_submission": {
            "independent_capture_status": prompt_sub.get("independent_capture_status"),
            "submission_verification": prompt_sub.get("submission_verification"),
            "submitted_prompt_sha256": prompt_sub.get("submitted_prompt_sha256"),
            "chatgpt_effective_prompt_known": False,
        },
        "image": {
            "sha256": png["sha256"],
            "byte_length": png["byte_length"],
            "width": png["width"],
            "height": png["height"],
            "mime_type": "image/png",
            "requested_aspect_ratio": (source.get("image") or {}).get("requested_aspect_ratio"),
            "observed_aspect_ratio": f"{png['width']}:{png['height']}",
            "private_image_path": str(image_path.resolve()),
        },
        "model_identity": {
            "status": "unknown",
            "provider_verified_model_id": None,
        },
        "qualitative_review": review,
        "rights_review_status": "pending",
        "publication_approval_status": "pending",
        "chatgpt_effective_prompt_known": False,
        "created_at_utc": created,
        "preview_html": PREVIEW_NAME,
        "authenticity_limits": list(_CANDIDATE_AUTHENTICITY_LIMITS),
    }

    preview = _render_preview_html(candidate, prompt_text=prompt_text)
    stage.mkdir(parents=True, exist_ok=True)
    _atomic_write_text(dest_cand, json.dumps(candidate, ensure_ascii=False, indent=2))
    _atomic_write_text(dest_preview, preview if preview.endswith("\n") else preview + "\n")

    # Ensure we did not copy raster into candidate dir.
    if any(stage.glob("*.png")):
        raise CreativeProvenanceError("private candidate directory must not contain PNG rasters")

    return {
        "ok": True,
        "candidate_dir": str(stage),
        "candidate_status": CANDIDATE_STATUS_PRIVATE,
        "candidate": candidate,
        "prep_verification": prep_report,
        "import_verification": import_report,
        "image_sha256": png["sha256"],
    }


def verify_private_gallery_candidate(candidate_dir: str | Path) -> dict[str, Any]:
    """Verify a private candidate record without rewriting files."""
    stage = Path(candidate_dir)
    findings: list[dict[str, str]] = []

    def err(code: str, message: str) -> None:
        findings.append({"level": "error", "code": code, "message": message})

    if not stage.is_dir():
        return {
            "ok": False,
            "findings": [
                {"level": "error", "code": "missing_dir", "message": f"missing: {stage}"}
            ],
        }
    cand_path = stage / CANDIDATE_NAME
    if not cand_path.is_file():
        err("missing_candidate", "candidate.json missing")
        return {"ok": False, "findings": findings}

    try:
        cand = _load_json(cand_path)
    except (OSError, json.JSONDecodeError) as exc:
        err("unreadable", str(exc))
        return {"ok": False, "findings": findings}

    if cand.get("record_kind") != "creative_gallery_candidate":
        err("record_kind", "record_kind must be creative_gallery_candidate")
    if cand.get("candidate_status") != CANDIDATE_STATUS_PRIVATE:
        err("status", "candidate_status must be private_candidate")
    if cand.get("generation_channel") != "chatgpt_web_manual":
        err("channel", "generation_channel must be chatgpt_web_manual")
    if cand.get("evidence_level") != EVIDENCE_MANUAL_IMPORT:
        err("evidence", "evidence_level must be locally_verified_manual_import")
    if cand.get("rights_review_status") != "pending":
        err("rights", "rights_review_status must remain pending in PR-CR-003A")
    if cand.get("publication_approval_status") != "pending":
        err("publication", "publication_approval_status must remain pending in PR-CR-003A")
    model = cand.get("model_identity") or {}
    if model.get("status") != "unknown" or model.get("provider_verified_model_id") is not None:
        err("model", "model identity must be unknown")
    if cand.get("chatgpt_effective_prompt_known") is not False:
        err("effective_prompt", "chatgpt_effective_prompt_known must be false")
    if any(stage.glob("*.png")):
        err("raster_present", "candidate directory must not contain PNG files")

    image_meta = cand.get("image") or {}
    private_image = Path(image_meta.get("private_image_path") or "")
    if not private_image.is_file():
        err("missing_image", "private_image_path missing")
    else:
        try:
            png = inspect_png_file(private_image)
            if png["sha256"] != image_meta.get("sha256"):
                err("image_sha_mismatch", "private image digest mismatch")
        except CreativeProvenanceError as exc:
            err("image_invalid", str(exc))

    imp_dir = Path((cand.get("import_reference") or {}).get("import_dir") or "")
    if imp_dir.is_dir():
        imp_report = verify_chatgpt_web_manual(imp_dir)
        if not imp_report.get("ok"):
            err("import_invalid", "linked import bundle no longer verifies")
    else:
        err("import_missing", "linked import_dir missing")

    prep_dir = Path((cand.get("recipe") or {}).get("prep_dir") or "")
    if prep_dir.is_dir():
        prep_report = verify_recipe_generation_bundle(prep_dir)
        if not prep_report.get("ok"):
            err("prep_invalid", "linked prep bundle no longer verifies")
    else:
        err("prep_missing", "linked prep_dir missing")

    errors = [f for f in findings if f["level"] == "error"]
    return {
        "ok": not errors,
        "candidate_status": cand.get("candidate_status"),
        "evidence_level": cand.get("evidence_level"),
        "image_sha256": image_meta.get("sha256"),
        "findings": findings,
        "authenticity_limits": list(cand.get("authenticity_limits") or _CANDIDATE_AUTHENTICITY_LIMITS),
    }
