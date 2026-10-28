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
# MANIFEST.in may discover candidates under those trees; only inventory paths ship.
KNOWLEDGE_PREFIXES = (
    "references/",
    "evidence/",
    "compatibility/",
    "visual-patterns/",
    "evaluation/",
    "data/schemas/",
)


class ResourceContentError(ValueError):
    """Raised when resource bytes cannot be mapped to the approved canonical form."""


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


def canonical_resource_bytes(raw: bytes) -> bytes:
    """Map working-tree bytes to canonical LF resource bytes.

    The only permitted transformation is CRLF (``\\r\\n``) → LF (``\\n``).
    Bare CR, unexpected encodings, or other alterations are rejected upstream
    by comparing the result to the inventory SHA-256.
    """
    if b"\r" in raw.replace(b"\r\n", b""):
        raise ResourceContentError(
            "unsupported bare carriage-return bytes in knowledge resource"
        )
    return raw.replace(b"\r\n", b"\n")


def read_canonical_resource(path: Path) -> bytes:
    return canonical_resource_bytes(path.read_bytes())


def verify_canonical(inventory: dict | None = None, *, root: Path | None = None) -> list[str]:
    """Return actionable errors if inventory files are missing or modified."""
    inventory = inventory or load_inventory()
    root = ROOT if root is None else root
    errors: list[str] = []
    for row in inventory["files"]:
        path = root / row["path"]
        if not path.is_file():
            errors.append(f"missing required resource: {row['path']}")
            continue
        try:
            digest = sha256(read_canonical_resource(path)).hexdigest()
        except ResourceContentError as exc:
            errors.append(f"resource content error for {row['path']}: {exc}")
            continue
        if digest != row["sha256"]:
            errors.append(
                f"resource hash mismatch for {row['path']}: "
                f"expected {row['sha256']}, got {digest}"
            )
    return errors


def write_canonical_resource(dest: Path, data: bytes, *, expected_sha256: str) -> None:
    canonical = canonical_resource_bytes(data)
    digest = sha256(canonical).hexdigest()
    if digest != expected_sha256:
        raise SystemExit(
            f"canonical hash mismatch for {dest}: expected {expected_sha256}, got {digest}"
        )
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(canonical)
    staged = sha256(dest.read_bytes()).hexdigest()
    if staged != expected_sha256:
        raise SystemExit(f"staged hash mismatch for {dest}: expected {expected_sha256}, got {staged}")


def stage_knowledge(*, clean: bool = True, root: Path | None = None) -> Path:
    inventory = load_inventory()
    root = ROOT if root is None else root
    stage_root = (root / "src" / "aipf" / "_knowledge") if root != ROOT else STAGE_ROOT
    errors = verify_canonical(inventory, root=root)
    if errors:
        raise SystemExit("Knowledge staging failed:\n- " + "\n- ".join(errors))
    if clean and stage_root.exists():
        shutil.rmtree(stage_root)
    stage_root.mkdir(parents=True, exist_ok=True)
    (stage_root / "README").write_text(
        "Derived read-only copy of allowlisted public knowledge resources.\n"
        "Canonical source remains the repository trees listed in "
        "aipf_packaging/resource_inventory.json.\n"
        "Packaged bytes use LF newlines (CRLF working trees are normalized at build).\n",
        encoding="utf-8",
    )
    for row in inventory["files"]:
        src = root / row["path"]
        dest = stage_root / row["path"]
        write_canonical_resource(dest, src.read_bytes(), expected_sha256=row["sha256"])
    inventory_src = root / "aipf_packaging" / "resource_inventory.json"
    shutil.copy2(inventory_src, stage_root / "resource_inventory.json")
    return stage_root


def rewrite_tree_knowledge_to_canonical(tree_root: Path, inventory: dict | None = None) -> None:
    """Rewrite allowlisted knowledge members under ``tree_root`` to canonical LF bytes."""
    inventory = inventory or load_inventory()
    for row in inventory["files"]:
        path = tree_root / row["path"]
        if not path.is_file():
            raise SystemExit(f"missing sdist knowledge member: {row['path']}")
        write_canonical_resource(path, path.read_bytes(), expected_sha256=row["sha256"])


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
