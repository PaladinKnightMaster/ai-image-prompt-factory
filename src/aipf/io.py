from __future__ import annotations
from pathlib import Path
import json


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_json(path: str | Path):
    p = Path(path)
    if not p.is_absolute():
        p = repo_root() / p
    return json.loads(p.read_text(encoding="utf-8"))


def write_json(path: str | Path, data) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = repo_root() / p
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return p
