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


def _channel_badge_label(channel: str) -> str:
    labels = {
        "chatgpt_web_manual": "ChatGPT Web",
    }
    text = (channel or "").strip()
    if not text:
        return "channel n/a"
    return labels.get(text, text.replace("_", " "))


def _short_config_chips(candidate_id: str) -> list[str]:
    """Extract compact cN/lN chips from candidate_id when present (e.g. cr001-c0-l0-4x5)."""
    chips: list[str] = []
    cid = candidate_id or ""
    cam = re.search(r"(?i)(?:^|-)(c\d+)(?:-|$)", cid)
    if cam:
        chips.append(cam.group(1).lower())
    light = re.search(r"(?i)(?:^|-)(l\d+)(?:-|$)", cid)
    if light:
        chips.append(light.group(1).lower())
    return chips


def _badge_html(label: str, *, kind: str = "") -> str:
    cls = "badge" if not kind else f"badge badge-{kind}"
    return f'<li class="{cls}">{escape(label)}</li>'


def _json_for_inline_script(value: str) -> str:
    """Serialize text for embedding inside an inline ``<script>`` string literal.

    Uses JSON then neutralizes HTML/script breakouts (``</script>``, ``<!--``)
    and JS line separators so the verified prompt bytes round-trip exactly when
    parsed by ``JSON.parse`` / assignment, without injection into HTML.
    """
    encoded = json.dumps(value, ensure_ascii=False)
    return (
        encoded.replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def _copy_prompt_inline_script(prompt_text: str) -> str:
    """Narrow offline copy handler: Clipboard API with local selectable fallback."""
    prompt_js = _json_for_inline_script(prompt_text)
    # Literal braces must not be interpreted by the caller f-string; return plain text.
    return f"""<script id="aipf-copy-prompt">
(function () {{
  var PROMPT = {prompt_js};
  var btn = document.getElementById("copy-prompt-btn");
  var label = document.getElementById("copy-prompt-label");
  var live = document.getElementById("copy-prompt-status");
  var pre = document.getElementById("adapter-prompt-text");
  if (!btn || !label || !live || !pre) return;

  var iconCopy = btn.querySelector("[data-icon=copy]");
  var iconOk = btn.querySelector("[data-icon=ok]");
  var resetTimer = null;

  function setState(kind, message) {{
    label.textContent = message;
    btn.setAttribute("data-state", kind);
    live.textContent = message;
    if (iconCopy) iconCopy.hidden = kind === "ok";
    if (iconOk) iconOk.hidden = kind !== "ok";
    if (resetTimer) window.clearTimeout(resetTimer);
    if (kind === "ok") {{
      resetTimer = window.setTimeout(function () {{
        setState("idle", "Copy prompt");
      }}, 2000);
    }}
  }}

  function selectPromptForManualCopy() {{
    var range = document.createRange();
    range.selectNodeContents(pre);
    var sel = window.getSelection();
    if (sel) {{
      sel.removeAllRanges();
      sel.addRange(range);
    }}
    try {{ pre.focus(); }} catch (err) {{}}
    setState("fail", "Select prompt");
  }}

  function legacyCopy() {{
    var ta = document.createElement("textarea");
    ta.value = PROMPT;
    ta.setAttribute("readonly", "");
    ta.style.position = "fixed";
    ta.style.top = "0";
    ta.style.left = "0";
    ta.style.width = "1px";
    ta.style.height = "1px";
    ta.style.padding = "0";
    ta.style.border = "none";
    ta.style.outline = "none";
    ta.style.boxShadow = "none";
    ta.style.background = "transparent";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    ta.setSelectionRange(0, ta.value.length);
    var ok = false;
    try {{
      ok = document.execCommand("copy");
    }} catch (err) {{
      ok = false;
    }}
    document.body.removeChild(ta);
    return ok;
  }}

  function onCopied() {{
    setState("ok", "Copied!");
  }}

  function onFailed() {{
    selectPromptForManualCopy();
  }}

  btn.addEventListener("click", function () {{
    if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {{
      navigator.clipboard.writeText(PROMPT).then(onCopied).catch(function () {{
        if (legacyCopy()) onCopied();
        else onFailed();
      }});
      return;
    }}
    if (legacyCopy()) onCopied();
    else onFailed();
  }});
}})();
</script>"""


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
    candidate_id = str(candidate.get("candidate_id") or "")
    channel = str(candidate.get("generation_channel") or "")
    recommendation = str(review.get("recommendation") or "n/a")
    aspect = str(
        bindings.get("aspect")
        or image_meta.get("requested_aspect_ratio")
        or "n/a"
    )
    camera_full = str(bindings.get("camera") or "n/a")
    light_full = str(bindings.get("light") or "n/a")
    width = image_meta.get("width")
    height = image_meta.get("height")
    dim_label = (
        f"{width}×{height}"
        if isinstance(width, int) and isinstance(height, int)
        else "dimensions unavailable"
    )

    badge_items = [
        _badge_html(f"v{recipe_version}" if recipe_version else "version n/a"),
        _badge_html(recommendation, kind="decision"),
        _badge_html(aspect, kind="aspect"),
    ]
    for chip in _short_config_chips(candidate_id):
        badge_items.append(_badge_html(chip, kind="config"))
    badge_items.append(_badge_html(_channel_badge_label(channel), kind="channel"))
    badge_items.append(_badge_html("private", kind="status"))
    badges_html = f'<ul class="badge-row" aria-label="Core specs">{"".join(badge_items)}</ul>'

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
  margin: 0 0 0.85rem;
  color: var(--muted);
  font-size: 1.02rem;
}}
.badge-row {{
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  list-style: none;
  margin: 0 0 0.85rem;
  padding: 0;
}}
.badge {{
  display: inline-block;
  margin: 0;
  padding: 0.22rem 0.55rem;
  border: 1px solid var(--line);
  border-radius: 2px;
  background: var(--panel);
  color: var(--ink);
  font: 600 0.75rem/1.3 var(--sans);
  letter-spacing: 0.01em;
}}
.badge-decision {{
  border-color: #b7d0cd;
  color: var(--accent);
}}
.badge-status {{
  border-color: #c5ccd6;
  color: var(--muted);
}}
details.advanced {{
  margin: 0 0 1.75rem;
  padding: 0;
  border: none;
  background: transparent;
}}
details.advanced > summary {{
  cursor: pointer;
  list-style: none;
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.2rem 0;
  color: var(--accent);
  font: 600 0.88rem/1.4 var(--sans);
}}
details.advanced > summary::-webkit-details-marker {{ display: none; }}
details.advanced > summary::before {{
  content: "▸";
  color: var(--accent);
}}
details.advanced[open] > summary::before {{ content: "▾"; }}
.advanced-body {{
  margin-top: 0.75rem;
  padding: 0.9rem 1rem;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 2px;
}}
.advanced-body dl {{
  display: grid;
  grid-template-columns: minmax(7rem, 9rem) 1fr;
  gap: 0.55rem 1rem;
  margin: 0;
}}
.advanced-body dt {{
  margin: 0;
  color: var(--muted);
  font-size: 0.78rem;
}}
.advanced-body dd {{
  margin: 0;
  font-size: 0.9rem;
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
.prompt-header {{
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem 1rem;
  margin: 0 0 0.75rem;
}}
.prompt-header h2 {{
  margin: 0;
}}
.copy-prompt {{
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  margin: 0;
  padding: 0.28rem 0.55rem;
  border: 1px solid var(--line);
  border-radius: 2px;
  background: var(--panel);
  color: var(--ink);
  font: 600 0.78rem/1.2 var(--sans);
  cursor: pointer;
}}
.copy-prompt:hover {{
  border-color: #b7d0cd;
  color: var(--accent);
}}
.copy-prompt:focus {{
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}}
.copy-prompt:focus:not(:focus-visible) {{
  outline: none;
}}
.copy-prompt:focus-visible {{
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}}
.copy-prompt[data-state="ok"] {{
  border-color: #b7d0cd;
  color: var(--accent);
}}
.copy-prompt[data-state="fail"] {{
  border-color: #c5ccd6;
  color: var(--muted);
}}
.copy-prompt svg {{
  width: 0.95rem;
  height: 0.95rem;
  flex: 0 0 auto;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.6;
  stroke-linecap: round;
  stroke-linejoin: round;
}}
.copy-prompt-status {{
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
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
  .provenance dl, .advanced-body dl {{ grid-template-columns: 1fr; }}
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
  <p class="lede">Local file preview only — rights review and publication approval remain pending.</p>
  {badges_html}
  <details class="advanced">
    <summary>Advanced details</summary>
    <div class="advanced-body">
      <dl>
        <dt>Recipe</dt><dd>{escape(recipe_id)} <span class="note">v{escape(recipe_version)}</span></dd>
        <dt>Candidate</dt><dd>{escape(candidate_id)}</dd>
        <dt>Camera</dt><dd>{escape(camera_full)}</dd>
        <dt>Lighting</dt><dd>{escape(light_full)}</dd>
        <dt>Aspect</dt><dd>{escape(aspect)}</dd>
        <dt>Channel</dt><dd>{escape(channel)}</dd>
      </dl>
    </div>
  </details>
</article>

<section class="prompt-panel" aria-labelledby="prompt-heading">
  <div class="prompt-header">
    <h2 id="prompt-heading">Compiled adapter-effective prompt</h2>
    <button type="button" class="copy-prompt" id="copy-prompt-btn" data-state="idle"
      aria-describedby="copy-prompt-status"
      aria-label="Copy the entire adapter-effective generation prompt">
      <svg data-icon="copy" viewBox="0 0 16 16" aria-hidden="true" focusable="false">
        <rect x="5.2" y="5.2" width="8.2" height="8.2" rx="1.1"></rect>
        <rect x="2.6" y="2.6" width="8.2" height="8.2" rx="1.1"></rect>
      </svg>
      <svg data-icon="ok" viewBox="0 0 16 16" aria-hidden="true" focusable="false" hidden>
        <path d="M3.2 8.2 6.4 11.2 12.8 4.6"></path>
      </svg>
      <span id="copy-prompt-label">Copy prompt</span>
    </button>
    <span id="copy-prompt-status" class="copy-prompt-status" role="status" aria-live="polite"></span>
  </div>
  <div class="prompt-frame"><pre id="adapter-prompt-text" tabindex="0">{escape(prompt_text)}</pre></div>
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
{_copy_prompt_inline_script(prompt_text)}
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
