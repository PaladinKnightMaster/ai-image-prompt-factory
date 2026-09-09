from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
import zipfile
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]


def run(
    args: list[str],
    *,
    cwd: Path = ROOT,
    capture: bool = False,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        check=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=capture,
        env=env,
    )


def project_version() -> str:
    with (ROOT / "pyproject.toml").open("rb") as f:
        data = tomllib.load(f)

    return data["project"]["version"]


def artifact_suffix(version: str) -> str:
    major, minor, patch = version.split(".")

    if patch == "0":
        return f"V{major}_{minor}"

    return f"V{major}_{minor}_{patch}"


def ensure_clean_worktree() -> None:
    result = run(
        ["git", "status", "--porcelain"],
        capture=True,
    )

    dirty = result.stdout.strip()

    if dirty:
        raise RuntimeError(
            "Working tree is not clean. Commit or stash changes before "
            "building a release.\n\n"
            + dirty
        )


def validate_tag(ref: str, version: str) -> None:
    if not ref.startswith("v"):
        return

    expected = f"v{version}"

    if ref != expected:
        raise RuntimeError(
            f"Tag/version mismatch: ref={ref}, expected={expected}"
        )


def run_source_tests() -> None:
    print("\n==> Running source tests")
    run([sys.executable, "-m", "pytest", "-q"])

    print("\n==> Running source validation")
    run([sys.executable, "scripts/validate_repo.py"])


def create_git_archive(
    ref: str,
    output: Path,
) -> None:
    print(f"\n==> Creating tracked-source archive from {ref}")

    output.parent.mkdir(parents=True, exist_ok=True)

    if output.exists():
        output.unlink()

    run(
        [
            "git",
            "archive",
            "--format=zip",
            "--prefix=ai-image-prompt-factory/",
            f"--output={output}",
            ref,
        ]
    )


def forbidden_member(name: str) -> str | None:
    path = PurePosixPath(name)
    parts = set(path.parts)

    forbidden_dirs = {
        ".git",
        ".venv",
        ".pytest_cache",
        ".pytest_tmp",
        "__pycache__",
        "aipf-private",
        "internal-corpus",
    }

    found = parts.intersection(forbidden_dirs)

    if found:
        return f"forbidden directory: {sorted(found)[0]}"

    if any(part.endswith(".egg-info") for part in path.parts):
        return "generated *.egg-info metadata"

    if path.name == ".env":
        return "private .env file"

    lowered = name.lower()

    if "image library.zip" in lowered:
        return "private Image Library archive"

    return None


def inspect_archive(zip_path: Path) -> None:
    print("\n==> Inspecting release archive")

    violations: list[str] = []

    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()

        if not names:
            raise RuntimeError("Release ZIP is empty.")

        for name in names:
            reason = forbidden_member(name)

            if reason:
                violations.append(f"{name}: {reason}")

    if violations:
        raise RuntimeError(
            "Release archive contains forbidden content:\n"
            + "\n".join(violations)
        )

    print("Archive hygiene: OK")


def validate_packaged_copy(
    zip_path: Path,
) -> dict:
    print("\n==> Testing extracted release package")

    temp_dir = Path(tempfile.mkdtemp(prefix="aipf-release-"))

    try:
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(temp_dir)

        package_root = temp_dir / "ai-image-prompt-factory"

        if not package_root.exists():
            raise RuntimeError(
                "Expected ai-image-prompt-factory/ root missing from ZIP."
            )

        env = os.environ.copy()

        src_path = str(package_root / "src")
        existing_pythonpath = env.get("PYTHONPATH")

        env["PYTHONPATH"] = (
            src_path
            if not existing_pythonpath
            else src_path + os.pathsep + existing_pythonpath
        )

        run(
            [sys.executable, "-m", "pytest", "-q"],
            cwd=package_root,
            env=env,
        )

        validation = run(
            [sys.executable, "scripts/validate_repo.py"],
            cwd=package_root,
            capture=True,
            env=env,
        )

        report = json.loads(validation.stdout)

        if not report.get("ok"):
            raise RuntimeError(
                "Packaged repository validation failed:\n"
                + validation.stdout
            )

        if report.get("errors"):
            raise RuntimeError(
                "Packaged repository contains validation errors:\n"
                + json.dumps(report["errors"], indent=2)
            )

        print("Packaged-copy validation: OK")

        return report

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def write_validation_report(
    report: dict,
    output: Path,
    version: str,
) -> None:
    text = (
        f"# AI Image Prompt Factory v{version} Validation Report\n\n"
        "Generated from the clean extracted release artifact.\n\n"
        "```json\n"
        + json.dumps(report, indent=2, ensure_ascii=False)
        + "\n```\n"
    )

    output.write_text(text, encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def write_checksum(
    zip_path: Path,
    output: Path,
) -> str:
    digest = sha256_file(zip_path)

    output.write_text(
        f"{digest}  {zip_path.name}\n",
        encoding="ascii",
    )

    return digest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build and verify AI Image Prompt Factory release artifacts."
    )

    parser.add_argument(
        "--ref",
        default="HEAD",
        help="Git ref to package. Default: HEAD",
    )

    parser.add_argument(
        "--dist",
        default="dist/release",
        help="Output directory. Default: dist/release",
    )

    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Allow a dirty local working tree.",
    )

    args = parser.parse_args()

    version = project_version()
    suffix = artifact_suffix(version)

    if not args.allow_dirty:
        ensure_clean_worktree()

    validate_tag(args.ref, version)

    dist = (ROOT / args.dist).resolve()
    dist.mkdir(parents=True, exist_ok=True)

    zip_path = dist / f"AI_Image_Prompt_Factory_{suffix}.zip"
    checksum_path = dist / f"{zip_path.name}.sha256"
    report_path = (
        dist
        / f"AI_Image_Prompt_Factory_{suffix}_VALIDATION_REPORT.md"
    )

    run_source_tests()

    create_git_archive(
        args.ref,
        zip_path,
    )

    inspect_archive(zip_path)

    validation_report = validate_packaged_copy(zip_path)

    write_validation_report(
        validation_report,
        report_path,
        version,
    )

    digest = write_checksum(
        zip_path,
        checksum_path,
    )

    print("\n========================================")
    print(f"AI Image Prompt Factory v{version}")
    print("Release build completed successfully.")
    print("========================================")
    print(f"ZIP:        {zip_path}")
    print(f"SHA-256:    {digest}")
    print(f"Checksum:   {checksum_path}")
    print(f"Validation: {report_path}")


if __name__ == "__main__":
    main()