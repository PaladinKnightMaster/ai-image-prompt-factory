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


def _display_recipe_title(recipe_id: str) -> str:
    """Humanize a recipe_id slug for editorial display without inventing marketing copy."""
    text = (recipe_id or "").strip()
    if text.lower().startswith("cr-") and len(text) > 3:
        # Keep CR-00N prefix readable: cr-001-foo -> CR-001 · Foo...
        parts = text.split("-")
        if len(parts) >= 3 and parts[1].isdigit():
            rest = " ".join(parts[2:]).replace("_", " ").strip()
            titled = rest[:1].upper() + rest[1:] if rest else text
            return f"CR-{parts[1]} · {titled}"
    return text.replace("-", " ").replace("_", " ")


def _render_preview_html(candidate: dict[str, Any], *, prompt_text: str) -> str:
    """Render an offline, image-first private editorial preview (no external assets)."""
    image_meta = candidate.get("image") or {}
    image_path = Path(image_meta.get("private_image_path") or "")
    image_uri = ""
    if image_path:
        try:
            if image_path.is_file():
                image_uri = image_path.resolve().as_uri()
        except OSError:
            image_uri = ""

    recipe = candidate.get("recipe") or {}
    bindings = recipe.get("effective_bindings") or {}
    review = candidate.get("qualitative_review") or {}
    prompt_sub = candidate.get("prompt_submission") or {}
    model = candidate.get("model_identity") or {}
    recipe_id = str(recipe.get("recipe_id") or "")
    recipe_version = str(recipe.get("recipe_version") or "")
    display_title = _display_recipe_title(recipe_id)
    width = image_meta.get("width")
    height = image_meta.get("height")
    dim_label = (
        f"{width}×{height}"
        if isinstance(width, int) and isinstance(height, int)
        else "dimensions unavailable"
    )

    strengths = "".join(f"<li>{escape(x)}</li>" for x in (review.get("strengths") or []))
    limitations = "".join(f"<li>{escape(x)}</li>" for x in (review.get("limitations") or []))
    limits = "".join(
        f"<li>{escape(x)}</li>" for x in (candidate.get("authenticity_limits") or [])
    )
    attach = review.get("non_custody_assessment_attachment_sha256")
    attach_html = (
        f"<p class=\"note\">Qualitative observations are attributed to a separate "
        f"non-custody assessment attachment "
        f"<code class=\"hash\">{escape(str(attach))}</code>, not a byte-identical "
        f"re-inspection of the custody original.</p>"
        if attach
        else ""
    )

    if image_uri:
        figure_html = (
            f'<figure class="hero">'
            f'<img src="{escape(image_uri, quote=True)}" '
            f'alt="Verified private import for {escape(candidate.get("candidate_id") or "")}" '
            f'width="{escape(str(width or ""))}" height="{escape(str(height or ""))}">'
            f"<figcaption>{escape(dim_label)} · requested "
            f"{escape(str(image_meta.get('requested_aspect_ratio') or 'n/a'))} · "
            f"observed {escape(str(image_meta.get('observed_aspect_ratio') or 'n/a'))}"
            f"</figcaption></figure>"
        )
    else:
        figure_html = (
            '<figure class="hero hero-missing" role="img" '
            'aria-label="Private import image unavailable">'
            "<p>Verified import image path is unavailable on this machine. "
            "Provenance records remain unchanged; open this preview where the "
            "linked private import PNG exists.</p></figure>"
        )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>{escape(display_title)} · private candidate</title>
<style>
:root {{
  --paper: #f5f6f8;
  --panel: #ffffff;
  --ink: #14171c;
  --muted: #5a6472;
  --line: #d5dae2;
  --accent: #1b5f5a;
  --warn-bg: #f3eee6;
  --display: Georgia, "Iowan Old Style", "Palatino Linotype", "Book Antiqua", serif;
  --sans: "Segoe UI", "Avenir Next", "Helvetica Neue", sans-serif;
  --mono: ui-monospace, "Cascadia Code", Consolas, monospace;
  --measure: 42rem;
  --shell: min(72rem, calc(100vw - 2.5rem));
}}
* {{ box-sizing: border-box; }}
html {{ scroll-behavior: smooth; }}
body {{
  margin: 0;
  color: var(--ink);
  background: var(--paper);
  font: 1rem/1.55 var(--sans);
  -webkit-font-smoothing: antialiased;
}}
a {{ color: var(--accent); }}
.site {{
  width: var(--shell);
  margin: 0 auto;
  padding: 1.25rem 0 3.5rem;
}}
.masthead {{
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 0.5rem 1.5rem;
  align-items: baseline;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--line);
  margin-bottom: 1.5rem;
}}
.masthead .brand {{
  font: 0.78rem/1.3 var(--sans);
  letter-spacing: 0.04em;
  color: var(--muted);
}}
.masthead .brand strong {{
  color: var(--ink);
  font-weight: 600;
  letter-spacing: 0;
}}
.privacy {{
  font-size: 0.8rem;
  color: var(--accent);
  font-weight: 600;
}}
.hero {{
  margin: 0 0 1.75rem;
  background: #0e1014;
  border-radius: 2px;
  overflow: hidden;
}}
.hero img {{
  display: block;
  width: 100%;
  height: auto;
  max-height: min(88vh, 960px);
  object-fit: contain;
  object-position: center center;
  background: #0e1014;
}}
.hero figcaption {{
  margin: 0;
  padding: 0.65rem 1rem;
  font-size: 0.78rem;
  color: #c5ccd6;
  background: #0e1014;
}}
.hero-missing {{
  padding: 3rem 1.25rem;
  color: #c5ccd6;
  text-align: center;
}}
.editorial {{
  max-width: var(--measure);
}}
.editorial h1 {{
  margin: 0 0 0.4rem;
  font: 700 2rem/1.15 var(--display);
  letter-spacing: -0.01em;
}}
.lede {{
  margin: 0 0 1.25rem;
  color: var(--muted);
  font-size: 1.05rem;
}}
.meta-row {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr));
  gap: 0.75rem 1.25rem;
  margin: 0 0 1.75rem;
  padding: 1rem 0;
  border-top: 1px solid var(--line);
  border-bottom: 1px solid var(--line);
}}
.meta-row dt {{
  margin: 0;
  font-size: 0.72rem;
  color: var(--muted);
}}
.meta-row dd {{
  margin: 0.15rem 0 0;
  font-size: 0.95rem;
  overflow-wrap: anywhere;
}}
section {{
  margin: 0 0 2rem;
  max-width: var(--measure);
}}
section h2 {{
  margin: 0 0 0.75rem;
  font: 600 1.15rem/1.25 var(--display);
}}
.prompt-panel {{
  max-width: none;
}}
.prompt-frame {{
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 2px;
  max-height: min(28rem, 70vh);
  overflow: auto;
}}
.prompt-frame pre {{
  margin: 0;
  padding: 1rem 1.1rem;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  font: 0.86rem/1.5 var(--mono);
  color: var(--ink);
}}
.note, .hash-line {{
  margin: 0.65rem 0 0;
  color: var(--muted);
  font-size: 0.82rem;
}}
.hash, code {{
  font-family: var(--mono);
  font-size: 0.8em;
  overflow-wrap: anywhere;
  word-break: break-all;
}}
.review-grid {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.25rem;
}}
.review-grid h3 {{
  margin: 0 0 0.5rem;
  font: 600 0.95rem/1.3 var(--sans);
}}
.review-grid ul {{
  margin: 0;
  padding-left: 1.1rem;
}}
.review-grid li {{
  margin: 0 0 0.35rem;
}}
.decision {{
  margin: 0 0 1rem;
  font-size: 1.05rem;
}}
.decision strong {{
  color: var(--accent);
}}
details.provenance {{
  max-width: none;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 2px;
  padding: 0.35rem 1rem 1rem;
}}
details.provenance > summary {{
  cursor: pointer;
  list-style: none;
  padding: 0.85rem 0;
  font: 600 1rem/1.3 var(--sans);
}}
details.provenance > summary::-webkit-details-marker {{ display: none; }}
details.provenance > summary::before {{
  content: "▸ ";
  color: var(--accent);
}}
details.provenance[open] > summary::before {{ content: "▾ "; }}
.provenance dl {{
  display: grid;
  grid-template-columns: minmax(8rem, 14rem) 1fr;
  gap: 0.45rem 1rem;
  margin: 0.5rem 0 1rem;
}}
.provenance dt {{ color: var(--muted); font-size: 0.82rem; }}
.provenance dd {{ margin: 0; overflow-wrap: anywhere; font-size: 0.9rem; }}
.gate-box {{
  margin-top: 1rem;
  padding: 0.9rem 1rem;
  background: var(--warn-bg);
  border-left: 3px solid var(--accent);
}}
.gate-box ul {{ margin: 0.4rem 0 0; padding-left: 1.1rem; }}
@media (max-width: 720px) {{
  .site {{ width: calc(100vw - 1.5rem); padding-top: 1rem; }}
  .editorial h1 {{ font-size: 1.55rem; }}
  .review-grid {{ grid-template-columns: 1fr; }}
  .provenance dl {{ grid-template-columns: 1fr; }}
  .hero img {{ max-height: none; }}
}}
@media (prefers-reduced-motion: reduce) {{
  html {{ scroll-behavior: auto; }}
}}
</style>
</head>
<body>
<div class="site">
<header class="masthead">
  <p class="brand"><strong>AIPF</strong> Creative Archive</p>
  <p class="privacy">Private candidate · not published</p>
</header>

{figure_html}

<article class="editorial">
  <h1>{escape(display_title)}</h1>
  <p class="lede">Version {escape(recipe_version)} · qualitative decision
  <strong>{escape(str(review.get("recommendation") or "n/a"))}</strong>.
  Local file preview only — rights review and publication approval remain pending.</p>

  <dl class="meta-row">
    <div><dt>Recipe</dt><dd>{escape(recipe_id)} <span class="note">v{escape(recipe_version)}</span></dd></div>
    <div><dt>Candidate</dt><dd>{escape(str(candidate.get("candidate_id") or ""))}</dd></div>
    <div><dt>Camera</dt><dd>{escape(str(bindings.get("camera") or "n/a"))}</dd></div>
    <div><dt>Lighting</dt><dd>{escape(str(bindings.get("light") or "n/a"))}</dd></div>
    <div><dt>Aspect</dt><dd>{escape(str(bindings.get("aspect") or image_meta.get("requested_aspect_ratio") or "n/a"))}</dd></div>
    <div><dt>Channel</dt><dd>{escape(str(candidate.get("generation_channel") or ""))}</dd></div>
  </dl>
</article>

<section class="prompt-panel" aria-labelledby="prompt-heading">
  <h2 id="prompt-heading">Compiled adapter-effective prompt</h2>
  <div class="prompt-frame"><pre>{escape(prompt_text)}</pre></div>
  <p class="hash-line">adapter_prompt_sha256 · <code class="hash">{escape(str((candidate.get("prompt") or {}).get("adapter_prompt_sha256") or ""))}</code></p>
</section>

<section aria-labelledby="review-heading">
  <h2 id="review-heading">Creative assessment</h2>
  <p class="decision">Decision: <strong>{escape(str(review.get("recommendation") or "n/a"))}</strong>
  · scientific claims: false</p>
  {attach_html}
  <div class="review-grid">
    <div>
      <h3>Observed strengths</h3>
      <ul>{strengths or "<li>None recorded</li>"}</ul>
    </div>
    <div>
      <h3>Limitations</h3>
      <ul>{limitations or "<li>None recorded</li>"}</ul>
    </div>
  </div>
</section>

<details class="provenance">
  <summary>Provenance and technical evidence</summary>
  <dl>
    <dt>Status</dt><dd>{escape(str(candidate.get("candidate_status") or ""))}</dd>
    <dt>Evidence</dt><dd>{escape(str(candidate.get("evidence_level") or ""))}</dd>
    <dt>Model identity</dt><dd>{escape(str(model.get("status") or "unknown"))} · provider_verified_model_id null</dd>
    <dt>Prompt submission</dt><dd>{escape(str(prompt_sub.get("submission_verification") or "unavailable"))} · capture {escape(str(prompt_sub.get("independent_capture_status") or "unavailable"))}</dd>
    <dt>ChatGPT effective prompt</dt><dd>unknown / not captured</dd>
    <dt>Image SHA-256</dt><dd><code class="hash">{escape(str(image_meta.get("sha256") or ""))}</code></dd>
    <dt>Recipe SHA-256</dt><dd><code class="hash">{escape(str(recipe.get("recipe_sha256") or ""))}</code></dd>
    <dt>Compiler prompt SHA-256</dt><dd><code class="hash">{escape(str((candidate.get("prompt") or {}).get("compiler_prompt_sha256") or recipe.get("compiler_prompt_sha256") or ""))}</code></dd>
    <dt>Rights review</dt><dd>{escape(str(candidate.get("rights_review_status") or "pending"))}</dd>
    <dt>Publication approval</dt><dd>{escape(str(candidate.get("publication_approval_status") or "pending"))}</dd>
  </dl>
  <div class="gate-box">
    <strong>Authenticity limits</strong>
    <ul>{limits}</ul>
  </div>
</details>
</div>
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


def refresh_private_gallery_preview(candidate_dir: str | Path) -> dict[str, Any]:
    """Regenerate only ``preview.html`` for an existing verified private candidate.

    Preserves ``candidate.json`` and all linked prep/import/image evidence.
    Refuses repository / public gallery destinations. Does not create a new
    candidate record or copy rasters.
    """
    stage = _resolve_private_candidate_root(candidate_dir)
    cand_path = stage / CANDIDATE_NAME
    preview_path = stage / PREVIEW_NAME
    if not cand_path.is_file():
        raise CreativeProvenanceError(f"candidate.json missing: {cand_path}")

    before = cand_path.read_bytes()
    report = verify_private_gallery_candidate(stage)
    if not report.get("ok"):
        raise CreativeProvenanceError(
            "refusing preview refresh until candidate verifies: "
            + "; ".join(
                f["message"]
                for f in report.get("findings", [])
                if f.get("level") == "error"
            )
        )

    cand = _load_json(cand_path)
    prompt_path = Path((cand.get("prompt") or {}).get("adapter_prompt_path") or "")
    if not prompt_path.is_file():
        raise CreativeProvenanceError("adapter prompt path missing; cannot refresh preview")
    expected = (cand.get("prompt") or {}).get("adapter_prompt_sha256")
    digest = sha256_file(prompt_path)
    if expected and digest != expected:
        raise CreativeProvenanceError("adapter prompt digest mismatch; refusing preview refresh")
    prompt_text = prompt_path.read_text(encoding="utf-8")

    preview = _render_preview_html(cand, prompt_text=prompt_text)
    _atomic_write_text(preview_path, preview if preview.endswith("\n") else preview + "\n")

    after = cand_path.read_bytes()
    if after != before:
        raise CreativeProvenanceError(
            "candidate.json changed during preview refresh; aborting integrity check failed"
        )
    if any(stage.glob("*.png")):
        raise CreativeProvenanceError("private candidate directory must not contain PNG rasters")

    return {
        "ok": True,
        "candidate_dir": str(stage),
        "preview_html": str(preview_path),
        "candidate_status": cand.get("candidate_status"),
        "image_sha256": (cand.get("image") or {}).get("sha256"),
        "candidate_json_unchanged": True,
        "verification": report,
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
