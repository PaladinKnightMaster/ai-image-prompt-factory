"""ESR reviewer-image sanitization (metadata-safe PNG rebuild).

Separate from EXP-019 scientific review paths. Requires Pillow
(``pip install ai-image-prompt-factory[esr]``).
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path

SUPPORTED_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


class EsrImageError(ValueError):
    """Raised when an ESR input image cannot be sanitized."""


def require_pillow():
    try:
        from PIL import Image, ImageOps  # noqa: F401
    except ImportError as exc:  # pragma: no cover - exercised in packaging smoke
        raise EsrImageError(
            "Pillow is required for ESR packaging. "
            "Install with: pip install 'ai-image-prompt-factory[esr]'"
        ) from exc
    return Image, ImageOps


def sanitize_to_metadata_free_png(source: Path) -> bytes:
    """Decode *source*, apply EXIF orientation, re-encode as a plain PNG.

    Color-management / embedded ICC profiles are not preserved; the reviewer
    copy uses Pillow's default decode/encode path. Unsupported or undecodable
    inputs raise ``EsrImageError``.
    """
    Image, ImageOps = require_pillow()
    suffix = source.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise EsrImageError(
            f"unsupported image format {suffix!r}; expected PNG, JPEG, or WEBP"
        )
    try:
        with Image.open(source) as img:
            img.load()
            oriented = ImageOps.exif_transpose(img)
            if oriented is None:
                oriented = img
            # Flatten to a stable RGB/RGBA raster without ancillary metadata.
            if oriented.mode not in {"RGB", "RGBA", "L"}:
                oriented = oriented.convert("RGBA" if "A" in oriented.getbands() else "RGB")
            buffer = BytesIO()
            oriented.save(buffer, format="PNG", optimize=False)
            return buffer.getvalue()
    except EsrImageError:
        raise
    except Exception as exc:
        raise EsrImageError(f"undecodable image {source}: {exc}") from exc
