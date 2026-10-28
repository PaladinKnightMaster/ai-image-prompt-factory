"""Read-only resolution for allowlisted knowledge resources.

Source checkouts continue to read canonical repository trees. Installed
wheels read the derived copy staged under ``aipf/_knowledge``. Absolute
external paths are never rewritten. Missing packaged resources fail clearly
without searching parent directories or the current working directory.
"""
from __future__ import annotations

from importlib import resources
from pathlib import Path, PurePosixPath
import json


class ResourceError(FileNotFoundError):
    """Raised when a required knowledge resource cannot be resolved."""


class PackagedResourceWriteError(OSError):
    """Raised when a write would target installed packaged knowledge."""


_SOURCE_MARKERS = ("pyproject.toml", "src/aipf", "references", "aipf_packaging/resource_inventory.json")


def source_checkout_root() -> Path | None:
    """Return the repository root when running from a source/src layout."""
    module_path = Path(__file__).resolve()
    # src/aipf/resources.py -> parents[2] == repository root
    candidate = module_path.parents[2]
    if not (candidate / "pyproject.toml").is_file():
        return None
    if not (candidate / "src" / "aipf").is_dir():
        return None
    if not (candidate / "references").is_dir():
        return None
    if not (candidate / "aipf_packaging" / "resource_inventory.json").is_file():
        return None
    return candidate


def repo_root() -> Path:
    """Repository root for worktree-only workflows.

    Installed wheels do not expose a project repository. Callers that require
    cases, experiments, or other worktree assets must supply explicit paths.
    """
    root = source_checkout_root()
    if root is not None:
        return root
    raise ResourceError(
        "Repository root is unavailable in installed-package mode. "
        "Pass an explicit absolute path for worktree-only assets "
        "(cases, experiments, baselines), or run from a source checkout."
    )


def _normalize_rel(path: str | Path) -> str:
    text = PurePosixPath(str(path).replace("\\", "/")).as_posix().lstrip("/")
    if not text or text.startswith("..") or "/../" in f"/{text}/":
        raise ResourceError(f"invalid resource reference path: {path!r}")
    return text


def _packaged_root():
    return resources.files("aipf") / "_knowledge"


def packaged_knowledge_available() -> bool:
    root = _packaged_root()
    try:
        return root.joinpath("resource_inventory.json").is_file()
    except Exception:
        return False


def resolve_resource(path: str | Path) -> Path | None:
    """Resolve a relative knowledge path to a real filesystem Path if possible.

    Returns ``None`` when the resource is only available as a packaged
    traversable (for example inside a zipimport). Prefer ``read_text`` /
    ``load_json`` / ``iter_resource_dir`` for portable reads.
    """
    rel = _normalize_rel(path)
    absolute = Path(path)
    if absolute.is_absolute():
        return absolute

    checkout = source_checkout_root()
    if checkout is not None:
        candidate = checkout / rel
        if candidate.is_file() or candidate.is_dir():
            return candidate
        raise ResourceError(f"missing knowledge resource: {rel}")

    packaged = _packaged_root().joinpath(*PurePosixPath(rel).parts)
    try:
        with resources.as_file(packaged) as concrete:
            if concrete.exists():
                return Path(concrete)
    except (FileNotFoundError, NotADirectoryError, OSError):
        pass
    raise ResourceError(
        f"missing packaged knowledge resource: {rel}. "
        "The installed wheel's allowlisted resource inventory does not include "
        "this path, or the package was built without staged knowledge."
    )


def read_bytes(path: str | Path) -> bytes:
    absolute = Path(path)
    if absolute.is_absolute():
        if not absolute.is_file():
            raise ResourceError(f"missing resource file: {absolute}")
        return absolute.read_bytes()

    rel = _normalize_rel(path)
    checkout = source_checkout_root()
    if checkout is not None:
        candidate = checkout / rel
        if not candidate.is_file():
            raise ResourceError(f"missing knowledge resource: {rel}")
        return candidate.read_bytes()

    packaged = _packaged_root().joinpath(*PurePosixPath(rel).parts)
    try:
        return packaged.read_bytes()
    except (FileNotFoundError, IsADirectoryError, OSError, AttributeError) as exc:
        raise ResourceError(
            f"missing packaged knowledge resource: {rel}. "
            "The installed wheel's allowlisted resource inventory does not include "
            "this path, or the package was built without staged knowledge."
        ) from exc


def read_text(path: str | Path, *, encoding: str = "utf-8") -> str:
    return read_bytes(path).decode(encoding)


def load_resource_json(path: str | Path):
    return json.loads(read_text(path))


def iter_resource_dir(path: str | Path, pattern: str = "*") -> list[str]:
    """Return sorted relative resource paths under ``path`` matching ``pattern``."""
    from fnmatch import fnmatch

    rel = _normalize_rel(path)
    checkout = source_checkout_root()
    if checkout is not None:
        directory = checkout / rel
        if not directory.is_dir():
            raise ResourceError(f"missing knowledge resource directory: {rel}")
        return sorted(
            f"{rel}/{child.name}".replace("\\", "/")
            for child in directory.iterdir()
            if child.is_file() and fnmatch(child.name, pattern)
        )

    packaged = _packaged_root().joinpath(*PurePosixPath(rel).parts)
    try:
        if not packaged.is_dir():
            raise ResourceError(f"missing packaged knowledge resource directory: {rel}")
        names = [
            f"{rel}/{child.name}"
            for child in packaged.iterdir()
            if child.is_file() and fnmatch(child.name, pattern)
        ]
        return sorted(names)
    except ResourceError:
        raise
    except Exception as exc:
        raise ResourceError(f"missing packaged knowledge resource directory: {rel}") from exc


def output_root() -> Path:
    """Writable root for relative output paths."""
    checkout = source_checkout_root()
    if checkout is not None:
        return checkout
    return Path.cwd()


def assert_not_packaged_write_target(path: Path) -> None:
    """Reject writes that would target the installed knowledge tree."""
    try:
        packaged = _packaged_root()
        with resources.as_file(packaged) as concrete:
            root = Path(concrete).resolve()
            try:
                path.resolve().relative_to(root)
            except ValueError:
                return
            raise PackagedResourceWriteError(
                f"refusing to write into installed read-only knowledge resources: {path}"
            )
    except PackagedResourceWriteError:
        raise
    except (FileNotFoundError, NotADirectoryError, OSError, AttributeError):
        return
