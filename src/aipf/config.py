from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from .resources import source_checkout_root


_CHECKOUT = source_checkout_root()
# Preserve source-checkout .env loading. Installed wheels must not treat an
# unrelated virtualenv parent directory as a project repository.
if _CHECKOUT is not None:
    REPO_ROOT = _CHECKOUT
    load_dotenv(_CHECKOUT / ".env")
else:
    REPO_ROOT = Path.cwd()


def corpus_path() -> Path | None:
    value = os.getenv("AIPF_CORPUS_PATH")
    return Path(value).expanduser().resolve() if value else None


def internal_gallery_path() -> Path | None:
    value = os.getenv("AIPF_INTERNAL_GALLERY_PATH")
    return Path(value).expanduser().resolve() if value else None


def experiment_output_path() -> Path | None:
    value = os.getenv("AIPF_EXPERIMENT_OUTPUT_PATH")
    return Path(value).expanduser().resolve() if value else None


def research_path() -> Path | None:
    value = os.getenv("AIPF_RESEARCH_PATH")
    return Path(value).expanduser().resolve() if value else None
