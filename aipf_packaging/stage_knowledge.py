"""Build-time staging of allowlisted knowledge into the installable package."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = ROOT / "aipf_packaging" / "resource_inventory.json"
STAGE_ROOT = ROOT / "src" / "aipf" / "_knowledge"

# Repository-relative prefixes that host allowlisted knowledge JSON.
# MANIFEST.in may discover candidates under these trees; only inventory paths ship.
KNOWLEDGE_PREFIXES = (
    "references/",
    "evidence/",
    "compatibility/",
    "visual-patterns/",
    "evaluation/",
    "data/schemas/",
)


def load_inventory() -> dict:
    return json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))


def _normalize_repo_path(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def filter_sdist_knowledge_files(files: list[str], inventory: dict | None = None) -> list[str]:
    """Keep non-knowledge files plus only inventory-authorized knowledge JSON."""
    inventory = inventory or load_inventory()
    allowed = {_normalize_repo_path(row["path"]) for row in inventory["files"]}
    kept: list[str] = []
    for path in files:
        norm = _normalize_repo_path(path)
        if any(norm == prefix.rstrip("/") or norm.startswith(prefix) for prefix in KNOWLEDGE_PREFIXES):
            if norm not in allowed:
                continue
        kept.append(path)
    return kept



def verify_canonical(inventory: dict | None = None) -> list[str]:
    """Return actionable errors if inventory files are missing or modified."""
    inventory = inventory or load_inventory()
    errors: list[str] = []
    for row in inventory["files"]:
        path = ROOT / row["path"]
        if not path.is_file():
            errors.append(f"missing required resource: {row['path']}")
            continue
        digest = sha256(path.read_bytes()).hexdigest()
        if digest != row["sha256"]:
            errors.append(
                f"resource hash mismatch for {row['path']}: "
                f"expected {row['sha256']}, got {digest}"
            )
    return errors


def stage_knowledge(*, clean: bool = True) -> Path:
    inventory = load_inventory()
    errors = verify_canonical(inventory)
    if errors:
        raise SystemExit("Knowledge staging failed:\n- " + "\n- ".join(errors))
    if clean and STAGE_ROOT.exists():
        shutil.rmtree(STAGE_ROOT)
    STAGE_ROOT.mkdir(parents=True, exist_ok=True)
    (STAGE_ROOT / "README").write_text(
        "Derived read-only copy of allowlisted public knowledge resources.\n"
        "Canonical source remains the repository trees listed in "
        "aipf_packaging/resource_inventory.json.\n",
        encoding="utf-8",
    )
    for row in inventory["files"]:
        src = ROOT / row["path"]
        dest = STAGE_ROOT / row["path"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        staged = sha256(dest.read_bytes()).hexdigest()
        if staged != row["sha256"]:
            raise SystemExit(f"staged hash mismatch for {row['path']}")
    shutil.copy2(INVENTORY_PATH, STAGE_ROOT / "resource_inventory.json")
    return STAGE_ROOT


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "verify":
        errors = verify_canonical()
        if errors:
            print("FAIL")
            for err in errors:
                print("-", err)
            return 1
        inv = load_inventory()
        print(f"OK {inv['file_count']} files / {inv['total_bytes']} bytes")
        return 0
    stage_knowledge()
    inv = load_inventory()
    print(f"staged {inv['file_count']} files into {STAGE_ROOT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
