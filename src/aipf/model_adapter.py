"""Minimal GPT Image 2 request normalization for scripts/generate_api.py.

Not a multi-provider framework. The sole adapter record remains
references/core/gpt_image_2_adapter.json.
"""
from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SUPPORTED_MODEL_IDS = frozenset({
    "gpt-image-2",
    "gpt-image-2-2026-04-21",
})
ALIAS_MODEL_ID = "gpt-image-2"
DATED_SNAPSHOT_MODEL_ID = "gpt-image-2-2026-04-21"
SUPPORTED_QUALITIES = frozenset({"low", "medium", "high", "auto"})
SUPPORTED_BACKGROUNDS = frozenset({"transparent", "opaque", "auto"})
ADAPTER_RELATIVE_PATH = Path("references/core/gpt_image_2_adapter.json")

# Backward-compatible aliases used by the executor script.
VERIFIED_MODEL_IDS = SUPPORTED_MODEL_IDS
AdapterValidationError = None  # set below after class definition
GenerationIncompleteError = None


class AdapterContractError(ValueError):
    """Request or result violates the GPT Image 2 executor contract."""


AdapterValidationError = AdapterContractError
GenerationIncompleteError = AdapterContractError


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_gpt_image_2_adapter(root: Path | None = None) -> dict[str, Any]:
    base = Path(root) if root is not None else _repo_root()
    path = base / ADAPTER_RELATIVE_PATH
    data = json.loads(path.read_text(encoding="utf-8"))
    contract = data.get("request_contract") or {}
    verified = set(contract.get("verified_model_ids") or data.get("verified_execution_model_ids") or [])
    if verified != set(SUPPORTED_MODEL_IDS):
        raise AdapterContractError(
            f"Adapter verified model ids mismatch: {sorted(verified)}"
        )
    return data


def _validate_size(size: str) -> None:
    if size == "auto" or size in {"1024x1024", "1536x1024", "1024x1536"}:
        return
    if "x" not in size:
        raise AdapterContractError(f"unsupported size: {size!r}")
    left, _, right = size.partition("x")
    if not (left.isdigit() and right.isdigit()):
        raise AdapterContractError(f"unsupported size: {size!r}")
    width, height = int(left), int(right)
    if width <= 0 or height <= 0 or width % 16 or height % 16:
        raise AdapterContractError(f"unsupported size: {size!r}")
    ratio = width / height
    if ratio < 1 / 3 or ratio > 3 or width > 3840 or height > 2160:
        raise AdapterContractError(f"unsupported size: {size!r}")


def _resolve_readable_images(images: list[str] | None) -> list[str]:
    resolved: list[str] = []
    for raw in images or []:
        path = Path(raw)
        if not path.is_file():
            raise AdapterContractError(
                f"reference image missing or unreadable: {raw}"
            )
        try:
            with path.open("rb") as fh:
                fh.read(1)
        except OSError as exc:
            raise AdapterContractError(
                f"reference image missing or unreadable: {raw}: {exc}"
            ) from exc
        resolved.append(str(path.resolve()))
    return resolved


def _declared_snapshot(
    *,
    model: str,
    model_snapshot: str | None,
    snapshot_explicit: bool,
) -> str | None:
    if model == DATED_SNAPSHOT_MODEL_ID:
        return DATED_SNAPSHOT_MODEL_ID
    if not snapshot_explicit:
        return None
    if model_snapshot is None:
        return None
    if model_snapshot == DATED_SNAPSHOT_MODEL_ID:
        return DATED_SNAPSHOT_MODEL_ID
    if model_snapshot == ALIAS_MODEL_ID:
        return None
    raise AdapterContractError(
        f"unsupported declared model snapshot: {model_snapshot!r}"
    )


def normalize_request(
    *,
    prompt: str,
    model: str,
    model_snapshot: str | None,
    size: str = "auto",
    quality: str = "auto",
    background: str | None = None,
    images: list[str] | None = None,
    execute: bool = False,
    snapshot_explicit: bool = False,
) -> dict[str, Any]:
    # Preserve legacy CLI .strip() whitespace semantics inside normalization.
    prompt = prompt.strip()
    if model not in SUPPORTED_MODEL_IDS:
        raise AdapterContractError(
            f"unsupported model identifier: {model!r}. "
            f"Allowed: {', '.join(sorted(SUPPORTED_MODEL_IDS))}"
        )
    if quality not in SUPPORTED_QUALITIES:
        raise AdapterContractError(f"unsupported quality: {quality!r}")
    if background is not None and background not in SUPPORTED_BACKGROUNDS:
        raise AdapterContractError(f"unsupported background: {background!r}")
    _validate_size(size)

    image_paths = _resolve_readable_images(images)
    mode = "edit" if image_paths else "generate"
    declared = _declared_snapshot(
        model=model,
        model_snapshot=model_snapshot,
        snapshot_explicit=snapshot_explicit,
    )

    effective: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
    }
    if size != "auto":
        effective["size"] = size
    if quality != "auto":
        effective["quality"] = quality
    if background is not None and background != "auto":
        effective["background"] = background
    if image_paths:
        effective["image"] = image_paths if len(image_paths) > 1 else image_paths[0]

    return {
        "dry_run": not execute,
        "mode": mode,
        "prompt": prompt,
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "requested_model_id": model,
        "execution_model_id": model,
        "declared_model_snapshot": declared,
        "size": size,
        "quality": quality,
        "background": background,
        "image_paths": image_paths,
        "effective_request": effective,
        "sdk_params": {k: v for k, v in effective.items()},
    }


def build_sdk_kwargs(req: dict[str, Any]) -> dict[str, Any]:
    """Serializable SDK kwargs derived from the normalized effective request.

    Image values remain filesystem paths here; open file handles are a
    transport concern for the executor only.
    """
    return dict(req["effective_request"])


def materialize_sdk_kwargs(req: dict[str, Any]) -> tuple[dict[str, Any], list[Any]]:
    """Open reference-image handles for live SDK calls."""
    kwargs = build_sdk_kwargs(req)
    handles: list[Any] = []
    if req["mode"] == "edit":
        paths = req["image_paths"]
        handles = [open(p, "rb") for p in paths]
        kwargs["image"] = handles if len(handles) > 1 else handles[0]
    return kwargs, handles


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def persist_api_result(result: Any, output: Path) -> dict[str, Any]:
    data = getattr(result, "data", None)
    if not data:
        raise AdapterContractError("API returned empty data; no image to save.")
    datum = data[0]
    b64 = getattr(datum, "b64_json", None)
    if b64:
        try:
            raw = base64.b64decode(b64, validate=True)
        except Exception as exc:
            raise AdapterContractError(
                f"Invalid base64 image payload from API: {exc}"
            ) from exc
        if not raw:
            raise AdapterContractError("Decoded API image payload was empty.")
        try:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(raw)
        except OSError as exc:
            raise AdapterContractError(
                f"Failed to write output image: {exc}"
            ) from exc
        return {
            "saved": str(output),
            "transport": "b64_json",
            "output_sha256": sha256_file(output),
            "generation_completed": True,
        }
    url = getattr(datum, "url", None)
    if url:
        return {
            "url": url,
            "transport": "url",
            "note": "Remote URL returned; no local image was saved.",
            "generation_completed": False,
        }
    raise AdapterContractError(
        "API returned no recognized b64_json/url field; generation incomplete."
    )


def build_generation_metadata(
    req: dict[str, Any],
    *,
    prompt_profile: str,
    compiler_version: str,
    result_meta: dict[str, Any] | None = None,
    provider_verified_model_id: str | None = None,
    skill_version: str = "3.2.0",
) -> dict[str, Any]:
    refs = []
    for path_str in req.get("image_paths") or []:
        path = Path(path_str)
        refs.append({
            "path": str(path),
            "sha256": sha256_file(path) if path.is_file() else None,
        })
    result = result_meta or {}
    generation_completed = bool(result.get("generation_completed")) if result else False
    if req.get("dry_run"):
        generation_completed = False
    declared = req.get("declared_model_snapshot")
    return {
        "schema_version": "3.1",
        "provider": "openai",
        "model": req["requested_model_id"],
        "model_snapshot": declared,
        "requested_model_id": req["requested_model_id"],
        "declared_model_snapshot": declared,
        "provider_verified_model_id": provider_verified_model_id,
        "generation_date_utc": datetime.now(timezone.utc).isoformat(),
        "mode": req["mode"],
        "prompt_profile": prompt_profile,
        "prompt_sha256": req["prompt_sha256"],
        "input_references": refs,
        "size": req["size"],
        "quality": req["quality"],
        "background": req.get("background"),
        "compiler_version": compiler_version,
        "skill_version": skill_version,
        "seed": None,
        "dry_run": bool(req.get("dry_run")),
        "generation_completed": generation_completed,
        "result": result,
    }
