"""Creative recipe → generation provenance bridge (PR-CR-002).

Binds PromptRecipe compile receipts to generation metadata and optional
local image digests. Does not call image providers and does not invent
provider-confirmed identifiers.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path, PurePosixPath
import json
import os
import re
import struct
import tempfile
from typing import Any

from .model_adapter import (
    AdapterContractError,
    build_generation_metadata,
    normalize_request,
    sha256_file,
)
from .recipes import (
    RecipeError,
    RecipeValidationError,
    canonical_json_bytes,
    compile_recipe,
    load_bindings,
    load_recipe,
    sha256_bytes,
    sha256_canonical,
)

CREATIVE_PROVENANCE_SCHEMA_VERSION = "1.0.0"
BUNDLE_MANIFEST_NAME = "manifest.json"
RECEIPT_NAME = "receipt.json"
PROMPT_NAME = "prompt.txt"
GENERATION_NAME = "generation.json"
BINDINGS_NAME = "bindings.json"
DEFAULT_OUTPUT_NAME = "output.png"

# Evidence levels are descriptive only; higher levels never invent provider proof.
EVIDENCE_COMPILATION_CONSISTENT = "compilation_consistent"
EVIDENCE_LOCALLY_VERIFIED = "locally_verified_generation"
EVIDENCE_MANUAL_IMPORT = "locally_verified_manual_import"
EVIDENCE_PROVIDER_CONFIRMED = "provider_confirmed_partial"
EVIDENCE_INCOMPLETE = "incomplete_or_unverifiable"

CHATGPT_WEB_SOURCE_SCHEMA_VERSION = "1.0.0"
CHATGPT_WEB_SOURCE_NAME = "source.json"
CHATGPT_WEB_IMAGE_NAME = "original.png"
CHATGPT_WEB_CAPTURE_NAME = "submitted_prompt_capture.txt"
CHATGPT_WEB_MANIFEST_NAME = "manifest.json"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

_MANUAL_AUTHENTICITY_LIMITS = [
    "Manual ChatGPT Web download; not OpenAI Images API output.",
    "Local hash consistency and recipe linkage are not provider-origin proof.",
    "Model identity is unknown unless separately attested by a future channel.",
    "ChatGPT internal effective prompt is not known from this import.",
    "provider_confirmed_partial is unreachable on the chatgpt_web_manual channel.",
    "publication_status remains private_only until a separately authorized gallery gate.",
]

_FORBIDDEN_STAGE_PREFIXES = (
    "website/generated",
    "website\\generated",
    "/cases/",
    "\\cases\\",
)


class CreativeProvenanceError(ValueError):
    """Raised when provenance preparation or verification fails closed."""


def utf8_sha256_text(text: str) -> str:
    """SHA-256 of exact Unicode text encoded as UTF-8 (no BOM)."""
    return sha256_bytes(text.encode("utf-8"))


def adapter_effective_prompt(compiled_prompt: str) -> str:
    """Return the exact prompt bytes that ``normalize_request`` would submit.

    V3.4 ``compile_result`` terminates prompts with a single trailing newline
    after an internal strip (``compiler.py``). ``normalize_request`` strips
    again for CLI compatibility. Provenance therefore distinguishes:

    - *compiler prompt* — receipt ``compilation.prompt`` (may end with ``\\n``)
    - *adapter prompt* — ``compiled_prompt.strip()`` submitted to the API path

    Any strip that removes more than outer whitespace equivalence to that
    documented pair is rejected as an unexpected transformation.
    """
    if not isinstance(compiled_prompt, str):
        raise CreativeProvenanceError("compiled prompt must be a string")
    try:
        compiled_prompt.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise CreativeProvenanceError(
            "compiled prompt is not UTF-8 encodable"
        ) from exc
    if "\x00" in compiled_prompt:
        raise CreativeProvenanceError("compiled prompt contains NUL bytes")
    stripped = compiled_prompt.strip()
    if not stripped:
        raise CreativeProvenanceError("compiled prompt is empty after strip")
    # Accept compiler form (content + single trailing newline) or already-stripped.
    if compiled_prompt == stripped or compiled_prompt == stripped + "\n":
        return stripped
    raise CreativeProvenanceError(
        "compiled prompt has unexpected leading/trailing whitespace beyond "
        "the documented compiler trailing newline; refusing silent alteration"
    )


def assert_prompt_adapter_integrity(prompt: str) -> str:
    """Fail closed unless prompt is adapter-safe; return adapter-effective text."""
    return adapter_effective_prompt(prompt)


def build_creative_provenance(
    receipt: dict[str, Any],
    *,
    recipe_path: str | None = None,
) -> dict[str, Any]:
    """Build optional creative_provenance from a compile_recipe receipt."""
    if not isinstance(receipt, dict):
        raise CreativeProvenanceError("receipt must be an object")
    recipe_meta = receipt.get("recipe")
    if not isinstance(recipe_meta, dict):
        raise CreativeProvenanceError("receipt.recipe is required")
    required = (
        "recipe_id",
        "recipe_version",
        "recipe_schema_version",
        "recipe_sha256",
        "semantic_spec_sha256",
    )
    missing = [k for k in required if not recipe_meta.get(k)]
    if missing:
        raise CreativeProvenanceError(
            f"receipt.recipe missing fields: {', '.join(missing)}"
        )
    prompt = (receipt.get("compilation") or {}).get("prompt")
    if not isinstance(prompt, str) or not prompt:
        raise CreativeProvenanceError("receipt.compilation.prompt is required")
    adapter_prompt = adapter_effective_prompt(prompt)
    prompt_sha = receipt.get("prompt_sha256")
    if prompt_sha != utf8_sha256_text(prompt):
        raise CreativeProvenanceError(
            "receipt.prompt_sha256 does not match UTF-8 digest of compilation.prompt"
        )
    adapter_prompt_sha = utf8_sha256_text(adapter_prompt)

    block: dict[str, Any] = {
        "schema_version": CREATIVE_PROVENANCE_SCHEMA_VERSION,
        "recipe_id": recipe_meta["recipe_id"],
        "recipe_version": recipe_meta["recipe_version"],
        "recipe_schema_version": recipe_meta["recipe_schema_version"],
        "recipe_sha256": recipe_meta["recipe_sha256"],
        "semantic_spec_sha256": recipe_meta["semantic_spec_sha256"],
        "compiler_version": receipt.get("compiler_version"),
        "prompt_sha256": prompt_sha,
        "adapter_prompt_sha256": adapter_prompt_sha,
        "recipe_receipt_sha256": sha256_canonical(receipt),
    }
    if recipe_path is not None:
        block["recipe_path"] = str(recipe_path)

    var = receipt.get("variable_resolution")
    if isinstance(var, dict):
        block["submitted_bindings_sha256"] = var.get("submitted_bindings_sha256")
        block["effective_bindings_sha256"] = var.get("effective_bindings_sha256")
        block["resolved_semantic_spec_sha256"] = var.get(
            "resolved_semantic_spec_sha256"
        )
        block["effective_bindings"] = deepcopy(var.get("effective_bindings") or {})
        block["submitted_variable_names"] = list(
            var.get("submitted_variable_names") or []
        )
    return block


def attach_creative_provenance(
    metadata: dict[str, Any],
    provenance: dict[str, Any],
) -> dict[str, Any]:
    """Return a copy of generation metadata with creative_provenance attached."""
    if not isinstance(metadata, dict):
        raise CreativeProvenanceError("generation metadata must be an object")
    out = deepcopy(metadata)
    out["creative_provenance"] = deepcopy(provenance)
    meta_prompt = out.get("prompt_sha256")
    # Generation metadata uses the adapter-effective prompt digest.
    expected = provenance.get("adapter_prompt_sha256") or provenance.get("prompt_sha256")
    if meta_prompt != expected:
        raise CreativeProvenanceError(
            "generation metadata prompt_sha256 does not match "
            "creative_provenance.adapter_prompt_sha256"
        )
    return out


def validate_creative_provenance_block(block: dict[str, Any]) -> list[str]:
    """Return human-readable errors for a creative_provenance object."""
    errors: list[str] = []
    if not isinstance(block, dict):
        return ["creative_provenance must be an object"]
    for key in (
        "schema_version",
        "recipe_id",
        "recipe_version",
        "recipe_schema_version",
        "recipe_sha256",
        "semantic_spec_sha256",
        "prompt_sha256",
        "recipe_receipt_sha256",
        "compiler_version",
    ):
        if not block.get(key):
            errors.append(f"missing creative_provenance.{key}")
    for key in (
        "recipe_sha256",
        "semantic_spec_sha256",
        "prompt_sha256",
        "recipe_receipt_sha256",
    ):
        val = block.get(key)
        if val is not None and not re.fullmatch(r"[0-9a-f]{64}", str(val)):
            errors.append(f"creative_provenance.{key} must be 64 lowercase hex")
    return errors


def _resolve_stage_root(path: str | Path, *, env_name: str = "AIPF_CREATIVE_OUTPUT_PATH") -> Path:
    raw = Path(path)
    if not raw.is_absolute():
        env = os.environ.get(env_name)
        if env:
            raw = Path(env) / raw
        else:
            raise CreativeProvenanceError(
                f"staging path must be absolute, or set {env_name} for relative paths: {path}"
            )
    resolved = raw.resolve()
    posix = resolved.as_posix()
    for prefix in _FORBIDDEN_STAGE_PREFIXES:
        if prefix.replace("\\", "/") in posix:
            raise CreativeProvenanceError(
                f"refusing to stage under public gallery tree ({prefix}): {resolved}"
            )
    return resolved


def _refuse_overwrite(path: Path, *, force: bool) -> None:
    if path.exists() and not force:
        raise CreativeProvenanceError(
            f"refusing to overwrite existing evidence file without --force: {path}"
        )


def prepare_recipe_generation_bundle(
    *,
    recipe_path: str | Path,
    output_dir: str | Path,
    bindings: dict[str, Any] | None = None,
    bindings_path: str | Path | None = None,
    model: str = "gpt-image-2",
    model_snapshot: str | None = None,
    snapshot_explicit: bool = False,
    size: str = "auto",
    quality: str = "auto",
    background: str | None = None,
    prompt_profile: str = "standard",
    compiler_version: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Compile a recipe and write a private offline preparation bundle.

    Performs no network I/O. Writes dry-run generation metadata only.
    """
    recipe_path = Path(recipe_path)
    recipe = load_recipe(recipe_path)
    if bindings_path is not None:
        bindings = load_bindings(bindings_path)
    if bindings is None:
        receipt = compile_recipe(recipe)
        submitted_bindings: dict[str, Any] = {}
    else:
        if not isinstance(bindings, dict):
            raise CreativeProvenanceError("bindings must be a JSON object")
        receipt = compile_recipe(recipe, bindings)
        submitted_bindings = dict(bindings)

    compiler_prompt = receipt["compilation"]["prompt"]
    prompt = adapter_effective_prompt(compiler_prompt)
    cv = compiler_version or receipt.get("compiler_version") or "3.2.0"
    provenance = build_creative_provenance(
        receipt, recipe_path=str(recipe_path.as_posix())
    )

    try:
        req = normalize_request(
            prompt=prompt,
            model=model,
            model_snapshot=model_snapshot,
            size=size,
            quality=quality,
            background=background,
            images=None,
            execute=False,
            snapshot_explicit=snapshot_explicit,
        )
    except AdapterContractError as exc:
        raise CreativeProvenanceError(str(exc)) from exc

    if req["prompt"] != prompt:
        raise CreativeProvenanceError(
            "adapter normalization altered the adapter-effective prompt"
        )
    if req["prompt_sha256"] != provenance["adapter_prompt_sha256"]:
        raise CreativeProvenanceError(
            "adapter prompt_sha256 does not match creative_provenance.adapter_prompt_sha256"
        )
    if utf8_sha256_text(compiler_prompt) != receipt["prompt_sha256"]:
        raise CreativeProvenanceError(
            "compiler prompt digest does not match receipt.prompt_sha256"
        )

    metadata = build_generation_metadata(
        req,
        prompt_profile=prompt_profile,
        compiler_version=str(cv),
        result_meta=None,
        provider_verified_model_id=None,
    )
    metadata = attach_creative_provenance(metadata, provenance)

    stage = _resolve_stage_root(output_dir)
    stage.mkdir(parents=True, exist_ok=True)
    receipt_path = stage / RECEIPT_NAME
    prompt_path = stage / PROMPT_NAME
    generation_path = stage / GENERATION_NAME
    bindings_out = stage / BINDINGS_NAME
    manifest_path = stage / BUNDLE_MANIFEST_NAME
    compiler_prompt_path = stage / "compiler_prompt.txt"
    preview_path = stage / "adapter_request_preview.json"
    for path in (
        receipt_path,
        prompt_path,
        compiler_prompt_path,
        generation_path,
        bindings_out,
        manifest_path,
        preview_path,
    ):
        _refuse_overwrite(path, force=force)

    receipt_path.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    # Adapter-effective prompt bytes (UTF-8). Compiler form remains in receipt.json.
    prompt_path.write_bytes(prompt.encode("utf-8"))
    compiler_prompt_path.write_bytes(compiler_prompt.encode("utf-8"))
    generation_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    bindings_out.write_text(
        json.dumps(submitted_bindings, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    request_preview = {
        "dry_run": True,
        "mode": req["mode"],
        "requested_model_id": req["requested_model_id"],
        "declared_model_snapshot": req["declared_model_snapshot"],
        "size": req["size"],
        "quality": req["quality"],
        "background": req.get("background"),
        "prompt_sha256": req["prompt_sha256"],
        "effective_request": {
            k: v for k, v in req["effective_request"].items() if k != "prompt"
        },
        "note": (
            "Prompt text omitted from this preview; see prompt.txt. "
            "No provider call was made. Use scripts/generate_api.py --execute "
            "separately only when explicitly authorized."
        ),
    }
    preview_path.write_text(
        json.dumps(request_preview, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    manifest = {
        "schema_version": "1.0.0",
        "bundle_kind": "creative_recipe_generation_preparation",
        "recipe_path": str(recipe_path.as_posix()),
        "files": {
            "receipt": RECEIPT_NAME,
            "prompt": PROMPT_NAME,
            "compiler_prompt": "compiler_prompt.txt",
            "generation_metadata": GENERATION_NAME,
            "bindings": BINDINGS_NAME,
            "adapter_request_preview": "adapter_request_preview.json",
            "output_image": None,
        },
        "evidence_level": EVIDENCE_COMPILATION_CONSISTENT,
        "authenticity_limits": [
            "This bundle is offline preparation only.",
            "dry_run generation metadata is not completed generation.",
            "Hash consistency is not independent provider-origin proof.",
            "provider_verified_model_id is null unless a live provider returns one.",
        ],
        "first_visual_campaign_note": (
            "Camera variation c2 remains a legal recipe variable but is excluded "
            "from the separately authorized first visual-test campaign due to "
            "known framing ambiguity (CR-GATE-003)."
        ),
        "prompt_sha256": receipt["prompt_sha256"],
        "adapter_prompt_sha256": provenance["adapter_prompt_sha256"],
        "recipe_receipt_sha256": provenance["recipe_receipt_sha256"],
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return {
        "stage_dir": str(stage),
        "manifest": manifest,
        "receipt": receipt,
        "generation_metadata": metadata,
        "prompt_sha256": receipt["prompt_sha256"],
    }


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def classify_evidence_level(
    metadata: dict[str, Any],
    *,
    output_path: Path | None,
    output_matches: bool,
) -> str:
    """Classify evidence without inventing provider confirmation.

    Offline verification of self-authored generation metadata never returns
    ``provider_confirmed_partial``. A non-null ``provider_verified_model_id``
    in local JSON is an unverified claim and does not raise authenticity.
    ``EVIDENCE_PROVIDER_CONFIRMED`` is reserved for a future separately
    authorized attestation channel.
    """
    if metadata.get("dry_run"):
        return EVIDENCE_INCOMPLETE
    if not metadata.get("generation_completed"):
        return EVIDENCE_INCOMPLETE
    result = metadata.get("result") or {}
    if result.get("transport") == "url":
        return EVIDENCE_INCOMPLETE
    if not output_path or not output_matches:
        return EVIDENCE_INCOMPLETE
    # Claimed provider_verified_model_id values are ignored for elevation.
    return EVIDENCE_LOCALLY_VERIFIED


def verify_recipe_generation_bundle(
    stage_dir: str | Path,
    *,
    expect_recipe_id: str | None = None,
    expect_recipe_version: str | None = None,
    expect_recipe_sha256: str | None = None,
    output_name: str = DEFAULT_OUTPUT_NAME,
) -> dict[str, Any]:
    """Verify an existing private bundle. Never rewrites evidence files."""
    stage = Path(stage_dir)
    if not stage.is_dir():
        raise CreativeProvenanceError(f"bundle directory not found: {stage}")

    findings: list[dict[str, str]] = []

    def err(code: str, message: str) -> None:
        findings.append({"level": "error", "code": code, "message": message})

    def warn(code: str, message: str) -> None:
        findings.append({"level": "warning", "code": code, "message": message})

    receipt_path = stage / RECEIPT_NAME
    prompt_path = stage / PROMPT_NAME
    generation_path = stage / GENERATION_NAME
    for required in (receipt_path, prompt_path, generation_path):
        if not required.is_file():
            err("missing_file", f"required file missing: {required.name}")
    if findings:
        return {
            "ok": False,
            "evidence_level": EVIDENCE_INCOMPLETE,
            "findings": findings,
        }

    receipt = _load_json(receipt_path)
    metadata = _load_json(generation_path)
    prompt_bytes = prompt_path.read_bytes()
    try:
        prompt_text = prompt_bytes.decode("utf-8")
    except UnicodeDecodeError:
        err("prompt_encoding", "prompt.txt is not valid UTF-8")
        return {
            "ok": False,
            "evidence_level": EVIDENCE_INCOMPLETE,
            "findings": findings,
        }

    compiler_prompt = (receipt.get("compilation") or {}).get("prompt")
    try:
        expected_adapter = adapter_effective_prompt(compiler_prompt or "")
    except CreativeProvenanceError as exc:
        err("prompt_integrity", str(exc))
        expected_adapter = None

    recomputed_adapter_sha = sha256_bytes(prompt_bytes)
    if expected_adapter is not None and prompt_text != expected_adapter:
        err(
            "prompt_receipt_text_mismatch",
            "prompt.txt is not the adapter-effective form of receipt.compilation.prompt",
        )
    if metadata.get("prompt_sha256") != recomputed_adapter_sha:
        err(
            "prompt_metadata_mismatch",
            "prompt.txt digest does not match generation.prompt_sha256",
        )
    if isinstance(compiler_prompt, str):
        if receipt.get("prompt_sha256") != utf8_sha256_text(compiler_prompt):
            err(
                "prompt_receipt_mismatch",
                "receipt.prompt_sha256 does not match receipt.compilation.prompt",
            )
        compiler_file = stage / "compiler_prompt.txt"
        if compiler_file.is_file():
            if compiler_file.read_bytes() != compiler_prompt.encode("utf-8"):
                err(
                    "compiler_prompt_file_mismatch",
                    "compiler_prompt.txt does not match receipt.compilation.prompt",
                )

    try:
        expected_prov = build_creative_provenance(receipt)
    except CreativeProvenanceError as exc:
        err("receipt_invalid", str(exc))
        expected_prov = {}

    block = metadata.get("creative_provenance")
    if block is None:
        err("missing_creative_provenance", "generation metadata lacks creative_provenance")
    else:
        for message in validate_creative_provenance_block(block):
            err("provenance_schema", message)
        if expected_prov:
            for key in (
                "recipe_id",
                "recipe_version",
                "recipe_schema_version",
                "recipe_sha256",
                "semantic_spec_sha256",
                "prompt_sha256",
                "adapter_prompt_sha256",
                "compiler_version",
                "resolved_semantic_spec_sha256",
                "effective_bindings_sha256",
            ):
                if key in expected_prov and block.get(key) != expected_prov.get(key):
                    err(
                        "provenance_mismatch",
                        f"creative_provenance.{key} does not match recomputed receipt",
                    )
            if block.get("recipe_receipt_sha256") != sha256_canonical(receipt):
                err(
                    "receipt_digest_mismatch",
                    "creative_provenance.recipe_receipt_sha256 does not match receipt.json",
                )
            if block.get("effective_bindings") != expected_prov.get("effective_bindings"):
                err(
                    "bindings_mismatch",
                    "creative_provenance.effective_bindings do not match receipt",
                )

    if expect_recipe_id and (block or {}).get("recipe_id") != expect_recipe_id:
        err("recipe_id_mismatch", f"expected recipe_id {expect_recipe_id}")
    if expect_recipe_version and (block or {}).get("recipe_version") != expect_recipe_version:
        err(
            "recipe_version_mismatch",
            f"expected recipe_version {expect_recipe_version}",
        )
    if expect_recipe_sha256 and (block or {}).get("recipe_sha256") != expect_recipe_sha256:
        err("recipe_sha_mismatch", "recipe_sha256 does not match expected value")

    output_path = stage / output_name
    output_matches = False
    if output_path.is_file():
        digest = sha256_file(output_path)
        result = metadata.get("result") or {}
        declared = result.get("output_sha256")
        if not metadata.get("generation_completed"):
            err(
                "completed_flag_false",
                "output image present but generation_completed is not true",
            )
        if metadata.get("dry_run"):
            err("dry_run_with_output", "dry_run metadata cannot authenticate an output image")
        if declared != digest:
            err(
                "output_sha_mismatch",
                "output file digest does not match result.output_sha256",
            )
        else:
            output_matches = True
            if result.get("transport") != "b64_json":
                warn(
                    "transport_not_b64",
                    "local file matches digest but transport is not b64_json",
                )
    else:
        if metadata.get("generation_completed"):
            err(
                "missing_output",
                "generation_completed is true but output image file is missing",
            )
        result = metadata.get("result") or {}
        if result.get("transport") == "url":
            warn("url_only", "URL-only result remains incomplete (no local asset)")

    if metadata.get("dry_run"):
        warn("dry_run", "record is dry-run preparation only")

    claimed_provider_id = metadata.get("provider_verified_model_id")
    if claimed_provider_id is None:
        warn(
            "no_provider_verified_model",
            "provider_verified_model_id is null; no provider-confirmed model evidence",
        )
    else:
        warn(
            "claimed_provider_model_unverified",
            "provider_verified_model_id is present in local metadata but is not "
            "independently authenticated; it does not elevate evidence_level",
        )

    errors = [f for f in findings if f["level"] == "error"]
    if errors:
        evidence = EVIDENCE_INCOMPLETE
    elif metadata.get("dry_run") and not (output_path.is_file()):
        # Offline preparation bundles verify as compilation-consistent only.
        evidence = EVIDENCE_COMPILATION_CONSISTENT
    else:
        evidence = classify_evidence_level(
            metadata,
            output_path=output_path if output_path.is_file() else None,
            output_matches=output_matches,
        )
    # Hard guard: offline verify must never emit provider_confirmed_partial.
    if evidence == EVIDENCE_PROVIDER_CONFIRMED:
        evidence = EVIDENCE_LOCALLY_VERIFIED
        warn(
            "provider_confirmed_suppressed",
            "provider_confirmed_partial is reserved; offline verification cannot grant it",
        )
    return {
        "ok": not errors,
        "evidence_level": evidence,
        "findings": findings,
        "prompt_sha256": recomputed_adapter_sha,
        "output_verified": output_matches,
        "authenticity_limits": [
            "Local hash consistency is not independent third-party attestation.",
            "A non-null provider_verified_model_id in self-authored JSON is an "
            "unverified claim and does not prove a provider event.",
            "ok:true means local checks passed; it does not imply provider confirmation.",
            "provider_confirmed_partial is reserved for a future attested channel.",
            "dry_run and URL-only records are never successful generation provenance.",
        ],
    }


def simulate_completed_generation_metadata(
    preparation_metadata: dict[str, Any],
    *,
    output_path: Path,
    transport: str = "b64_json",
) -> dict[str, Any]:
    """Test helper: mark metadata completed from a local simulated asset.

    Does not call providers. Used only in tests / offline verification drills.
    """
    if transport == "url":
        result = {
            "url": "https://example.invalid/image",
            "transport": "url",
            "note": "Remote URL returned; no local image was saved.",
            "generation_completed": False,
        }
        out = deepcopy(preparation_metadata)
        out["dry_run"] = False
        out["generation_completed"] = False
        out["result"] = result
        return out

    digest = sha256_file(output_path)
    result = {
        "saved": str(output_path),
        "transport": "b64_json",
        "output_sha256": digest,
        "generation_completed": True,
    }
    out = deepcopy(preparation_metadata)
    out["dry_run"] = False
    out["generation_completed"] = True
    out["result"] = result
    # Never invent provider confirmation.
    out["provider_verified_model_id"] = None
    return out


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except Exception:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass
        raise


def _atomic_write_text(path: Path, text: str) -> None:
    _atomic_write_bytes(path, (text if text.endswith("\n") else text + "\n").encode("utf-8"))


def _parse_custody_sha256(custody_path: Path) -> str:
    text = custody_path.read_text(encoding="utf-8")
    match = re.search(r"(?im)^\s*SHA-?256\s*[:=]\s*([0-9a-f]{64})\s*$", text)
    if not match:
        raise CreativeProvenanceError(
            f"custody record missing SHA-256 declaration: {custody_path}"
        )
    return match.group(1).lower()


def inspect_png_file(path: Path) -> dict[str, Any]:
    """Validate PNG signature and read IHDR dimensions. No pixel decode."""
    if not path.is_file():
        raise CreativeProvenanceError(f"image file not found: {path}")
    data = path.read_bytes()
    if len(data) < 24 or not data.startswith(PNG_SIGNATURE):
        raise CreativeProvenanceError(
            f"unsupported image format or missing PNG signature: {path}"
        )
    # signature(8) + length(4) + type(4) + IHDR(13) ...
    length = struct.unpack(">I", data[8:12])[0]
    chunk_type = data[12:16]
    if chunk_type != b"IHDR" or length < 8:
        raise CreativeProvenanceError(f"PNG IHDR missing or invalid: {path}")
    width, height = struct.unpack(">II", data[16:24])
    if width < 1 or height < 1:
        raise CreativeProvenanceError(f"PNG dimensions invalid: {path}")
    return {
        "sha256": sha256(data).hexdigest(),
        "byte_length": len(data),
        "mime_type": "image/png",
        "format": "PNG",
        "width": width,
        "height": height,
        "bytes": data,
    }


def import_chatgpt_web_manual(
    *,
    prep_dir: str | Path,
    image_path: str | Path,
    output_dir: str | Path,
    expect_image_sha256: str,
    custody_path: str | Path | None = None,
    submitted_prompt_path: str | Path | None = None,
    operator_attests_prompt_submission: bool = False,
    attestation_note: str | None = None,
    conversation_reference: str | None = None,
    expect_recipe_id: str | None = None,
    expect_recipe_version: str | None = None,
    expect_recipe_sha256: str | None = None,
) -> dict[str, Any]:
    """Import a manually downloaded ChatGPT Images PNG into a private bundle.

    Does not call providers. Does not mutate the source image or custody file.
    Does not grant provider confirmation. No overwrite of destination assets.
    """
    if not re.fullmatch(r"[0-9a-f]{64}", expect_image_sha256 or ""):
        raise CreativeProvenanceError("expect_image_sha256 must be 64 lowercase hex")

    prep = Path(prep_dir)
    image = Path(image_path)
    stage = _resolve_stage_root(output_dir)

    prep_report = verify_recipe_generation_bundle(
        prep,
        expect_recipe_id=expect_recipe_id,
        expect_recipe_version=expect_recipe_version,
        expect_recipe_sha256=expect_recipe_sha256,
    )
    if not prep_report.get("ok"):
        raise CreativeProvenanceError(
            "preparation bundle verification failed: "
            + "; ".join(f["message"] for f in prep_report.get("findings", []) if f["level"] == "error")
        )

    receipt = _load_json(prep / RECEIPT_NAME)
    metadata = _load_json(prep / GENERATION_NAME)
    provenance = metadata.get("creative_provenance")
    if not isinstance(provenance, dict):
        raise CreativeProvenanceError("preparation generation.json lacks creative_provenance")
    for message in validate_creative_provenance_block(provenance):
        raise CreativeProvenanceError(message)

    intended_adapter_sha = sha256_file(prep / PROMPT_NAME)
    intended_compiler_sha = provenance.get("prompt_sha256")
    if intended_adapter_sha != provenance.get("adapter_prompt_sha256"):
        raise CreativeProvenanceError(
            "preparation prompt.txt does not match creative_provenance.adapter_prompt_sha256"
        )

    if submitted_prompt_path is not None and operator_attests_prompt_submission:
        raise CreativeProvenanceError(
            "provide either submitted_prompt_path or operator attestation, not both"
        )
    if submitted_prompt_path is None and not operator_attests_prompt_submission:
        raise CreativeProvenanceError(
            "prompt evidence required: pass submitted_prompt_path for an independently "
            "captured submission, or set operator_attests_prompt_submission=True"
        )

    operator_attestation = None
    capture_bytes: bytes | None = None
    if submitted_prompt_path is not None:
        capture_path = Path(submitted_prompt_path)
        if not capture_path.is_file():
            raise CreativeProvenanceError(f"submitted prompt capture not found: {capture_path}")
        capture_bytes = capture_path.read_bytes()
        if capture_bytes != (prep / PROMPT_NAME).read_bytes():
            raise CreativeProvenanceError(
                "submitted prompt capture does not exactly match preparation prompt.txt"
            )
        prompt_submission = {
            "intended_adapter_prompt_sha256": intended_adapter_sha,
            "intended_compiler_prompt_sha256": intended_compiler_sha,
            "independent_capture_status": "provided",
            "submitted_prompt_sha256": sha256(capture_bytes).hexdigest(),
            "submission_verification": "exact_match",
            "operator_attestation": None,
            "chatgpt_effective_prompt_known": False,
        }
    else:
        operator_attestation = {
            "attested": True,
            "note": attestation_note,
            "attested_at_utc": _utc_now_iso(),
        }
        prompt_submission = {
            "intended_adapter_prompt_sha256": intended_adapter_sha,
            "intended_compiler_prompt_sha256": intended_compiler_sha,
            "independent_capture_status": "unavailable",
            "submitted_prompt_sha256": None,
            "submission_verification": "operator_attested_uncaptured",
            "operator_attestation": operator_attestation,
            "chatgpt_effective_prompt_known": False,
        }

    png = inspect_png_file(image)
    if png["sha256"] != expect_image_sha256:
        raise CreativeProvenanceError(
            "image SHA-256 does not match expect_image_sha256"
        )

    custody_declared = None
    custody_record_path = None
    if custody_path is not None:
        custody_file = Path(custody_path)
        if not custody_file.is_file():
            raise CreativeProvenanceError(f"custody record not found: {custody_file}")
        custody_declared = _parse_custody_sha256(custody_file)
        if custody_declared != png["sha256"]:
            raise CreativeProvenanceError(
                "custody SHA-256 does not match image file digest"
            )
        custody_record_path = str(custody_file)

    # Refuse destination overwrite / duplicate import (no --force in MVP).
    dest_image = stage / CHATGPT_WEB_IMAGE_NAME
    dest_source = stage / CHATGPT_WEB_SOURCE_NAME
    dest_manifest = stage / CHATGPT_WEB_MANIFEST_NAME
    dest_capture = stage / CHATGPT_WEB_CAPTURE_NAME
    for path in (dest_image, dest_source, dest_manifest, dest_capture):
        if path.exists():
            raise CreativeProvenanceError(
                f"refusing duplicate import / overwrite of existing evidence file: {path}"
            )
    if stage.exists() and any(stage.iterdir()):
        raise CreativeProvenanceError(
            f"refusing import into non-empty destination directory: {stage}"
        )

    aspect = None
    bindings = provenance.get("effective_bindings") or {}
    if isinstance(bindings, dict):
        aspect = bindings.get("aspect")

    imported_at = _utc_now_iso()
    source: dict[str, Any] = {
        "schema_version": CHATGPT_WEB_SOURCE_SCHEMA_VERSION,
        "record_kind": "chatgpt_web_manual_source",
        "generation_channel": "chatgpt_web_manual",
        "recipe": {
            "recipe_id": provenance["recipe_id"],
            "recipe_version": provenance["recipe_version"],
            "recipe_schema_version": provenance["recipe_schema_version"],
            "recipe_sha256": provenance["recipe_sha256"],
            "semantic_spec_sha256": provenance["semantic_spec_sha256"],
            "resolved_semantic_spec_sha256": provenance.get(
                "resolved_semantic_spec_sha256"
            ),
            "effective_bindings_sha256": provenance.get("effective_bindings_sha256"),
            "submitted_bindings_sha256": provenance.get("submitted_bindings_sha256"),
            "recipe_receipt_sha256": provenance["recipe_receipt_sha256"],
            "compiler_version": provenance["compiler_version"],
            "compiler_prompt_sha256": provenance["prompt_sha256"],
            "adapter_prompt_sha256": provenance["adapter_prompt_sha256"],
            "effective_bindings": deepcopy(bindings),
            "prep_dir": str(prep.resolve()),
        },
        "prompt_submission": prompt_submission,
        "conversation_reference": {
            "status": "provided" if conversation_reference else "unavailable",
            "url_or_id": conversation_reference,
            "note": None,
        },
        "image": {
            "original_filename": image.name,
            "stored_filename": CHATGPT_WEB_IMAGE_NAME,
            "sha256": png["sha256"],
            "byte_length": png["byte_length"],
            "mime_type": "image/png",
            "format": "PNG",
            "width": png["width"],
            "height": png["height"],
            "requested_aspect_ratio": aspect,
            "observed_aspect_ratio": f"{png['width']}:{png['height']}",
        },
        "model_identity": {
            "status": "unknown",
            "operator_reported_label": None,
            "provider_verified_model_id": None,
        },
        "custody": {
            "source_image_path": str(image.resolve()),
            "custody_record_path": custody_record_path,
            "custody_sha256_declared": custody_declared,
            "expect_image_sha256": expect_image_sha256,
            "sha256_verified": True,
        },
        "publication_status": "private_only",
        "evidence_level": EVIDENCE_MANUAL_IMPORT,
        "imported_at_utc": imported_at,
        "verified_at_utc": None,
        "authenticity_limits": list(_MANUAL_AUTHENTICITY_LIMITS),
    }

    manifest = {
        "schema_version": "1.0.0",
        "bundle_kind": "chatgpt_web_manual_import",
        "generation_channel": "chatgpt_web_manual",
        "evidence_level": EVIDENCE_MANUAL_IMPORT,
        "prep_dir": str(prep.resolve()),
        "files": {
            "source": CHATGPT_WEB_SOURCE_NAME,
            "original_image": CHATGPT_WEB_IMAGE_NAME,
            "submitted_prompt_capture": (
                CHATGPT_WEB_CAPTURE_NAME if capture_bytes is not None else None
            ),
            "manifest": CHATGPT_WEB_MANIFEST_NAME,
        },
        "image_sha256": png["sha256"],
        "adapter_prompt_sha256": intended_adapter_sha,
        "recipe_receipt_sha256": provenance["recipe_receipt_sha256"],
        "authenticity_limits": list(_MANUAL_AUTHENTICITY_LIMITS),
        "publication_status": "private_only",
        "imported_at_utc": imported_at,
    }

    stage.mkdir(parents=True, exist_ok=True)
    _atomic_write_bytes(dest_image, png["bytes"])
    if dest_image.read_bytes() != png["bytes"]:
        raise CreativeProvenanceError("copied original.png bytes do not match source image")
    if capture_bytes is not None:
        _atomic_write_bytes(dest_capture, capture_bytes)
    _atomic_write_text(
        dest_source, json.dumps(source, ensure_ascii=False, indent=2)
    )
    _atomic_write_text(
        dest_manifest, json.dumps(manifest, ensure_ascii=False, indent=2)
    )

    return {
        "ok": True,
        "stage_dir": str(stage),
        "evidence_level": EVIDENCE_MANUAL_IMPORT,
        "image_sha256": png["sha256"],
        "source": source,
        "manifest": manifest,
        "prep_verification": prep_report,
    }


def verify_chatgpt_web_manual(stage_dir: str | Path) -> dict[str, Any]:
    """Verify a chatgpt_web_manual import bundle. Never rewrites evidence files."""
    stage = Path(stage_dir)
    findings: list[dict[str, str]] = []

    def err(code: str, message: str) -> None:
        findings.append({"level": "error", "code": code, "message": message})

    def warn(code: str, message: str) -> None:
        findings.append({"level": "warning", "code": code, "message": message})

    if not stage.is_dir():
        return {
            "ok": False,
            "evidence_level": EVIDENCE_INCOMPLETE,
            "findings": [
                {
                    "level": "error",
                    "code": "missing_bundle",
                    "message": f"import directory not found: {stage}",
                }
            ],
        }

    source_path = stage / CHATGPT_WEB_SOURCE_NAME
    image_path = stage / CHATGPT_WEB_IMAGE_NAME
    manifest_path = stage / CHATGPT_WEB_MANIFEST_NAME
    for required in (source_path, image_path, manifest_path):
        if not required.is_file():
            err("missing_file", f"required file missing: {required.name}")
    if findings:
        return {
            "ok": False,
            "evidence_level": EVIDENCE_INCOMPLETE,
            "findings": findings,
        }

    try:
        source = _load_json(source_path)
    except (OSError, json.JSONDecodeError) as exc:
        err("source_unreadable", str(exc))
        return {"ok": False, "evidence_level": EVIDENCE_INCOMPLETE, "findings": findings}

    if source.get("record_kind") != "chatgpt_web_manual_source":
        err("record_kind", "source.json record_kind must be chatgpt_web_manual_source")
    if source.get("generation_channel") != "chatgpt_web_manual":
        err("generation_channel", "generation_channel must be chatgpt_web_manual")
    if source.get("evidence_level") != EVIDENCE_MANUAL_IMPORT:
        err("evidence_level", "evidence_level must be locally_verified_manual_import")
    if source.get("publication_status") != "private_only":
        err("publication_status", "publication_status must remain private_only")

    # Reject API / provider-confirmation pollution.
    if "provider_verified_model_id" in source and source.get("provider_verified_model_id") is not None:
        err("provider_claim_forbidden", "top-level provider_verified_model_id is forbidden")
    model = source.get("model_identity") or {}
    if not isinstance(model, dict):
        err("model_identity_invalid", "model_identity must be an object")
    else:
        if model.get("status") != "unknown":
            err("model_identity_invalid", "model_identity.status must be unknown")
        if model.get("provider_verified_model_id") is not None:
            err(
                "provider_claim_forbidden",
                "provider_verified_model_id must be null on chatgpt_web_manual",
            )
    if source.get("result") or source.get("transport") or source.get("dry_run") is not None:
        err("api_fields_forbidden", "API generation metadata fields are forbidden on manual source")

    try:
        png = inspect_png_file(image_path)
    except CreativeProvenanceError as exc:
        err("image_invalid", str(exc))
        png = None

    image_meta = source.get("image") or {}
    if png is not None:
        if image_meta.get("sha256") != png["sha256"]:
            err("image_sha_mismatch", "original.png digest does not match source.image.sha256")
        if image_meta.get("width") != png["width"] or image_meta.get("height") != png["height"]:
            err("image_dimensions_mismatch", "stored PNG dimensions do not match source.image")
        if image_meta.get("byte_length") != png["byte_length"]:
            err("image_length_mismatch", "stored PNG length does not match source.image")

    custody = source.get("custody") or {}
    if custody.get("expect_image_sha256") != image_meta.get("sha256"):
        err("expect_hash_mismatch", "custody.expect_image_sha256 does not match image.sha256")
    if custody.get("sha256_verified") is not True:
        err("sha_not_verified", "custody.sha256_verified must be true")

    prompt = source.get("prompt_submission") or {}
    if prompt.get("chatgpt_effective_prompt_known") is not False:
        err("effective_prompt_claim", "chatgpt_effective_prompt_known must be false")
    capture_path = stage / CHATGPT_WEB_CAPTURE_NAME
    if prompt.get("independent_capture_status") == "provided":
        if not capture_path.is_file():
            err("missing_capture", "submitted_prompt_capture.txt missing for provided capture")
        elif sha256(capture_path.read_bytes()).hexdigest() != prompt.get(
            "submitted_prompt_sha256"
        ):
            err("capture_digest_mismatch", "capture file digest mismatch")
        if prompt.get("submission_verification") != "exact_match":
            err("capture_verification", "provided capture must use exact_match verification")
    elif prompt.get("independent_capture_status") == "unavailable":
        if capture_path.exists():
            err(
                "mislabelled_capture",
                "submitted_prompt_capture.txt must not exist when independent capture is unavailable",
            )
        if prompt.get("submission_verification") != "operator_attested_uncaptured":
            err(
                "attestation_verification",
                "uncaptured submission must be operator_attested_uncaptured",
            )
        if prompt.get("submitted_prompt_sha256") is not None:
            err("uncaptured_hash", "uncaptured submission must not claim submitted_prompt_sha256")
        attestation = prompt.get("operator_attestation") or {}
        if not attestation.get("attested"):
            err("attestation_missing", "operator attestation required when capture unavailable")
    else:
        err("capture_status", "independent_capture_status missing or invalid")

    prep_dir = (source.get("recipe") or {}).get("prep_dir")
    if prep_dir:
        prep_path = Path(prep_dir)
        if prep_path.is_dir():
            prep_report = verify_recipe_generation_bundle(prep_path)
            if not prep_report.get("ok"):
                err("prep_link_invalid", "linked preparation bundle no longer verifies")
            else:
                prep_meta = _load_json(prep_path / GENERATION_NAME)
                block = prep_meta.get("creative_provenance") or {}
                recipe = source.get("recipe") or {}
                for key in (
                    "recipe_id",
                    "recipe_version",
                    "recipe_sha256",
                    "recipe_receipt_sha256",
                    "adapter_prompt_sha256",
                ):
                    expected = block.get(key) if key != "adapter_prompt_sha256" else block.get(
                        "adapter_prompt_sha256"
                    )
                    if key == "adapter_prompt_sha256":
                        if recipe.get(key) != expected:
                            err("prep_digest_mismatch", f"recipe.{key} does not match prep bundle")
                    elif recipe.get(key) != block.get(key):
                        err("prep_digest_mismatch", f"recipe.{key} does not match prep bundle")
                if recipe.get("compiler_prompt_sha256") != block.get("prompt_sha256"):
                    err(
                        "prep_digest_mismatch",
                        "compiler_prompt_sha256 does not match prep creative_provenance.prompt_sha256",
                    )
        else:
            warn("prep_dir_missing", f"linked prep_dir not found: {prep_dir}")

    errors = [f for f in findings if f["level"] == "error"]
    evidence = EVIDENCE_MANUAL_IMPORT if not errors else EVIDENCE_INCOMPLETE
    if evidence == EVIDENCE_PROVIDER_CONFIRMED:
        evidence = EVIDENCE_MANUAL_IMPORT
        warn(
            "provider_confirmed_suppressed",
            "provider_confirmed_partial is reserved; manual import cannot grant it",
        )
    return {
        "ok": not errors,
        "evidence_level": evidence,
        "findings": findings,
        "image_sha256": (png or {}).get("sha256") if png else image_meta.get("sha256"),
        "authenticity_limits": list(
            source.get("authenticity_limits") or _MANUAL_AUTHENTICITY_LIMITS
        ),
    }
