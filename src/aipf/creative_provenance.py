"""Creative recipe → generation provenance bridge (PR-CR-002).

Binds PromptRecipe compile receipts to generation metadata and optional
local image digests. Does not call image providers and does not invent
provider-confirmed identifiers.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path, PurePosixPath
import json
import os
import re
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
EVIDENCE_PROVIDER_CONFIRMED = "provider_confirmed_partial"
EVIDENCE_INCOMPLETE = "incomplete_or_unverifiable"

_FORBIDDEN_STAGE_PREFIXES = (
    "website/generated",
    "website\\generated",
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
    """Classify evidence without inventing provider confirmation."""
    if metadata.get("dry_run"):
        return EVIDENCE_INCOMPLETE
    if not metadata.get("generation_completed"):
        return EVIDENCE_INCOMPLETE
    result = metadata.get("result") or {}
    if result.get("transport") == "url":
        return EVIDENCE_INCOMPLETE
    if not output_path or not output_matches:
        return EVIDENCE_INCOMPLETE
    if metadata.get("provider_verified_model_id"):
        return EVIDENCE_PROVIDER_CONFIRMED
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

    if metadata.get("provider_verified_model_id") is None:
        warn(
            "no_provider_verified_model",
            "provider_verified_model_id is null; no provider-confirmed model evidence",
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
    return {
        "ok": not errors,
        "evidence_level": evidence,
        "findings": findings,
        "prompt_sha256": recomputed_adapter_sha,
        "output_verified": output_matches,
        "authenticity_limits": [
            "Local hash consistency is not independent third-party attestation.",
            "Operator assertions without provider identifiers are not provider-origin proof.",
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
