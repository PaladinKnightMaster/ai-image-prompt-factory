from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(REPO_ROOT / ".env")


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