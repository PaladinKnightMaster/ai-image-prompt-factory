from __future__ import annotations

from pathlib import Path
import json

from .resources import (
    ResourceError,
    assert_not_packaged_write_target,
    load_resource_json,
    output_root,
    repo_root,
    source_checkout_root,
)

__all__ = [
    "ResourceError",
    "load_json",
    "repo_root",
    "source_checkout_root",
    "write_json",
]


def load_json(path: str | Path):
    p = Path(path)
    if p.is_absolute():
        return json.loads(p.read_text(encoding="utf-8"))
    return load_resource_json(path)


def write_json(path: str | Path, data) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = output_root() / p
    assert_not_packaged_write_target(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return p
