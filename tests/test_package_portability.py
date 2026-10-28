"""Installed-wheel portability and source/sdist resource integrity tests."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import tarfile
import venv
import zipfile

import pytest

from contextlib import contextmanager

from aipf.compiler import compile_result
from aipf.io import load_json, write_json
from aipf.resources import (
    PackagedResourceWriteError,
    ResourceError,
    iter_resource_dir,
    read_bytes,
    source_checkout_root,
)
import aipf.resources as resources_mod
from aipf_packaging.stage_knowledge import (
    ResourceContentError,
    canonical_resource_bytes,
    filter_sdist_knowledge_files,
    load_inventory,
    verify_canonical,
    write_canonical_resource,
)

ROOT = Path(__file__).resolve().parents[1]

PARITY_CASES = [
    ("legacy", "cases/golden/01-classical-greek-heroic-living/case.json"),
    ("greek_marble", "cases/candidates/v34-greek-marble-bust/case.json"),
    ("dunhuang", "cases/candidates/v34-dunhuang-mural/case.json"),
    ("edo_woodblock", "cases/candidates/v34-edo-woodblock/case.json"),
    ("blue_white", "cases/candidates/v34-blue-white-vase/case.json"),
    ("evidence_compat", "cases/regression/reg-hellenistic-copy-survival-bias/case.json"),
    ("visual_pattern", "cases/golden/07-edo-ukiyoe-transform/case.json"),
]


def _sha(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _semantic_fingerprint(result: dict) -> dict:
    return {
        "prompt_sha256": _sha(result["prompt"]),
        "evidence_snapshot_sha256": result["evidence_snapshot"]["snapshot_sha256"],
        "compatibility": result["compatibility_audit"],
        "lint_findings": result["lint_findings"],
        "transformation_resolution": result.get("transformation_resolution"),
        "resolved_concepts": result.get("resolved_concepts"),
        "lexical_trace": result.get("lexical_trace"),
        "pattern_trace": result.get("pattern_trace"),
    }


def _run(cmd: list[str], *, cwd: Path, env: dict | None = None) -> subprocess.CompletedProcess:
    raw = subprocess.run(
        cmd,
        cwd=str(cwd),
        env=env,
        capture_output=True,
        check=False,
    )
    # Decode explicitly as UTF-8 so Windows cp1252 consoles cannot corrupt prompts.
    return subprocess.CompletedProcess(
        raw.args,
        raw.returncode,
        raw.stdout.decode("utf-8", errors="replace"),
        raw.stderr.decode("utf-8", errors="replace"),
    )


def _venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _venv_aipf(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "aipf.exe"
    return venv_dir / "bin" / "aipf"


@pytest.fixture(scope="module")
def source_baselines() -> dict[str, dict]:
    out = {}
    for name, rel in PARITY_CASES:
        spec = json.loads((ROOT / rel).read_text(encoding="utf-8"))
        result = compile_result(spec)
        out[name] = {
            "spec": spec,
            "result": result,
            "fingerprint": _semantic_fingerprint(result),
            "prompt_bytes": result["prompt"].encode("utf-8"),
        }
    return out


@pytest.fixture(scope="module")
def built_artifacts(tmp_path_factory) -> dict[str, Path]:
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "build"],
        cwd=str(ROOT),
        check=True,
    )
    dist = tmp_path_factory.mktemp("dist")
    built = _run(
        [sys.executable, "-m", "build", "--outdir", str(dist)],
        cwd=ROOT,
    )
    assert built.returncode == 0, built.stderr + built.stdout
    wheel = next(dist.glob("*.whl"))
    sdist = next(dist.glob("*.tar.gz"))
    return {"wheel": wheel, "sdist": sdist, "dist": dist}


def _install_wheel_env(tmp_path: Path, wheel: Path) -> tuple[Path, Path, dict]:
    venv_dir = tmp_path / "venv"
    venv.create(venv_dir, with_pip=True, clear=True)
    py = _venv_python(venv_dir)
    work = tmp_path / "work"
    work.mkdir()
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env["PYTHONNOUSERSITE"] = "1"
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    install = _run(
        [str(py), "-m", "pip", "install", str(wheel)],
        cwd=work,
        env=env,
    )
    assert install.returncode == 0, install.stdout + install.stderr
    return venv_dir, work, env


def _compile_installed(py: Path, spec_path: Path, work: Path, env: dict) -> dict:
    """Compile via installed Python; write JSON to a file to avoid console encoding issues."""
    out_json = work / "_parity_result.json"
    script = (
        "import json,sys; from aipf.compiler import compile_result; "
        "spec=json.loads(open(sys.argv[1],encoding='utf-8').read()); "
        "path=sys.argv[2]; "
        "path_write=open(path,'w',encoding='utf-8'); "
        "json.dump(compile_result(spec), path_write, ensure_ascii=False); "
        "path_write.write('\\n'); path_write.close()"
    )
    ran = _run([str(py), "-c", script, str(spec_path), str(out_json)], cwd=work, env=env)
    assert ran.returncode == 0, ran.stderr
    return json.loads(out_json.read_text(encoding="utf-8"))


def test_inventory_matches_canonical_bytes():
    errors = verify_canonical()
    assert errors == []
    inv = load_inventory()
    assert inv["file_count"] == len(inv["files"]) == 99
    assert inv["total_bytes"] == 414049


def test_canonical_lf_and_crlf_resource_inputs(tmp_path: Path):
    lf = b'{"id": "sample", "ok": true}\n'
    crlf = b'{"id": "sample", "ok": true}\r\n'
    digest = sha256(lf).hexdigest()
    assert canonical_resource_bytes(lf) == lf
    assert canonical_resource_bytes(crlf) == lf
    assert sha256(canonical_resource_bytes(crlf)).hexdigest() == digest

    root = tmp_path / "tree"
    rel = "references/eras/sample.json"
    path = root / rel
    inv = {"files": [{"path": rel, "sha256": digest, "size": len(lf)}]}

    path.parent.mkdir(parents=True)
    path.write_bytes(lf)
    assert verify_canonical(inv, root=root) == []
    staged = tmp_path / "staged" / rel
    write_canonical_resource(staged, lf, expected_sha256=digest)
    assert staged.read_bytes() == lf

    path.write_bytes(crlf)
    assert verify_canonical(inv, root=root) == []
    staged_crlf = tmp_path / "staged_crlf" / rel
    write_canonical_resource(staged_crlf, crlf, expected_sha256=digest)
    assert staged_crlf.read_bytes() == lf
    assert b"\r" not in staged_crlf.read_bytes()


def test_canonical_rejects_content_and_forbidden_representations(tmp_path: Path):
    lf = b'{"id": "sample", "ok": true}\n'
    digest = sha256(lf).hexdigest()
    root = tmp_path / "tree"
    rel = "references/eras/sample.json"
    path = root / rel
    path.parent.mkdir(parents=True)
    inv = {"files": [{"path": rel, "sha256": digest, "size": len(lf)}]}

    path.write_bytes(b'{"id": "sample", "ok": false}\n')
    errs = verify_canonical(inv, root=root)
    assert errs and "hash mismatch" in errs[0]

    with pytest.raises(ResourceContentError, match="bare carriage-return"):
        canonical_resource_bytes(b'{"id": "sample"}\r')

    path.write_bytes(b'{"id": "sample", "ok": true}\r')
    errs = verify_canonical(inv, root=root)
    assert errs and "resource content error" in errs[0]

    # Unexpected UTF-16 bytes are not a permitted conversion; hash must fail.
    path.write_bytes(b"\xff\xfe{\x00}")
    errs = verify_canonical(inv, root=root)
    assert errs and "hash mismatch" in errs[0]


def test_source_checkout_resource_reads_and_enumeration():
    assert source_checkout_root() == ROOT
    registry = load_json("evidence/registry.json")
    assert "claim_sets" in registry
    claims = iter_resource_dir("evidence/claims", "*.json")
    assert any(path.endswith("classical_greek.json") for path in claims)
    assert read_bytes("references/lexicon/registry.json")[:1] == b"{"


def test_invalid_resource_path_rejected():
    with pytest.raises(ResourceError):
        read_bytes("../secrets.json")
    with pytest.raises(ResourceError):
        read_bytes("references/no-such-pack.json")


def test_relative_write_stays_in_checkout(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    target = write_json("tmp_portability_write.json", {"ok": True})
    assert target == ROOT / "tmp_portability_write.json"
    assert target.is_file()
    target.unlink()


def _install_fake_packaged_knowledge(monkeypatch, knowledge: Path) -> None:
    """Point installed-mode resource writes at an isolated synthetic _knowledge tree."""
    monkeypatch.setattr(resources_mod, "source_checkout_root", lambda: None)

    @contextmanager
    def _as_file(_traversable):
        yield knowledge

    monkeypatch.setattr(resources_mod, "_packaged_root", lambda: knowledge)
    monkeypatch.setattr(resources_mod.resources, "as_file", _as_file)


def test_write_json_permits_normal_output(tmp_path: Path, monkeypatch):
    knowledge = tmp_path / "_knowledge"
    knowledge.mkdir()
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    _install_fake_packaged_knowledge(monkeypatch, knowledge)
    monkeypatch.chdir(out_dir)
    target = write_json("allowed_output.json", {"ok": True})
    assert target == out_dir / "allowed_output.json"
    assert json.loads(target.read_text(encoding="utf-8")) == {"ok": True}


def test_write_json_rejects_packaged_knowledge_root(tmp_path: Path, monkeypatch):
    knowledge = tmp_path / "_knowledge"
    knowledge.mkdir()
    marker = knowledge / "resource_inventory.json"
    original = b'{"file_count": 0}\n'
    marker.write_bytes(original)
    _install_fake_packaged_knowledge(monkeypatch, knowledge)
    with pytest.raises(PackagedResourceWriteError, match="refusing to write"):
        write_json(marker, {"tampered": True})
    assert marker.read_bytes() == original


def test_write_json_rejects_nested_packaged_knowledge(tmp_path: Path, monkeypatch):
    knowledge = tmp_path / "_knowledge"
    nested = knowledge / "references" / "lexicon"
    nested.mkdir(parents=True)
    target = nested / "registry.json"
    original = b'{"concepts": []}\n'
    target.write_bytes(original)
    _install_fake_packaged_knowledge(monkeypatch, knowledge)
    with pytest.raises(PackagedResourceWriteError, match="refusing to write"):
        write_json(target, {"concepts": [{"id": "tampered"}]})
    assert target.read_bytes() == original


def test_installed_relative_output_uses_cwd(tmp_path: Path, monkeypatch):
    knowledge = tmp_path / "_knowledge"
    knowledge.mkdir()
    work = tmp_path / "work"
    work.mkdir()
    _install_fake_packaged_knowledge(monkeypatch, knowledge)
    monkeypatch.chdir(work)
    target = write_json("cwd_relative.json", {"cwd": True})
    assert target == work / "cwd_relative.json"
    assert not (knowledge / "cwd_relative.json").exists()


def test_regression_fail_closed_missing_or_empty(tmp_path: Path):
    from aipf.regression import run_regression

    missing = tmp_path / "missing-cases"
    with pytest.raises(FileNotFoundError, match="not found"):
        run_regression(missing)
    empty = tmp_path / "empty-cases"
    empty.mkdir()
    with pytest.raises(FileNotFoundError, match="No regression cases"):
        run_regression(empty)


def _knowledge_json_members(archive_names: list[str], *, strip_prefix: str | None = None) -> set[str]:
    knowledge_prefixes = (
        "references/",
        "evidence/",
        "compatibility/",
        "visual-patterns/",
        "evaluation/",
        "data/schemas/",
    )
    out: set[str] = set()
    for name in archive_names:
        rel = name
        if strip_prefix and rel.startswith(strip_prefix):
            rel = rel[len(strip_prefix) :]
        rel = rel.replace("\\", "/")
        if any(rel == p.rstrip("/") or rel.startswith(p) for p in knowledge_prefixes) and rel.endswith(".json"):
            out.add(rel)
    return out


def _assert_no_private_archive_members(names: list[str]) -> None:
    assert not any("EXP-019" in n for n in names)
    assert not any(n.endswith(".env") for n in names)
    assert not any("/private/" in n or n.startswith("private/") for n in names)
    assert not any("experiments/" in n for n in names)
    assert not any("gallery/" in n for n in names)
    assert not any("corpus/" in n and "schema" not in n for n in names)
    assert not any(n.endswith(ext) for n in names for ext in (".png", ".jpg", ".jpeg", ".webp"))


def test_sdist_filter_drops_uninventoried_knowledge_paths():
    inv = load_inventory()
    allowed = {row["path"] for row in inv["files"]}
    sample = next(iter(allowed))
    files = [
        "setup.py",
        "src/aipf/resources.py",
        sample,
        "references/eras/uninventoried_packaging_canary.json",
        "evaluation/example_evaluation.json",
    ]
    kept = filter_sdist_knowledge_files(files, inv)
    assert "setup.py" in kept
    assert "src/aipf/resources.py" in kept
    assert sample in kept
    assert "references/eras/uninventoried_packaging_canary.json" not in kept
    assert "evaluation/example_evaluation.json" not in kept


def test_wheel_archive_inventory_and_forbidden_paths(built_artifacts):
    wheel = built_artifacts["wheel"]
    inv = load_inventory()
    with zipfile.ZipFile(wheel) as zf:
        names = zf.namelist()
        assert any(n.startswith("aipf/_knowledge/") for n in names)
        for row in inv["files"]:
            member = f"aipf/_knowledge/{row['path']}"
            assert member in names, member
            digest = sha256(zf.read(member)).hexdigest()
            assert digest == row["sha256"], row["path"]
        _assert_no_private_archive_members(names)


def test_sdist_archive_matches_inventory_exactly(built_artifacts):
    sdist = built_artifacts["sdist"]
    inv = load_inventory()
    allowed = {row["path"].replace("\\", "/") for row in inv["files"]}

    with tarfile.open(sdist, "r:gz") as tf:
        names = tf.getnames()
        prefix = names[0].split("/", 1)[0] + "/"
        knowledge = _knowledge_json_members(names, strip_prefix=prefix)
        assert knowledge == allowed
        for row in inv["files"]:
            member = prefix + row["path"]
            extracted = tf.extractfile(member)
            assert extracted is not None, member
            digest = sha256(extracted.read()).hexdigest()
            assert digest == row["sha256"], row["path"]
        _assert_no_private_archive_members([n[len(prefix) :] for n in names if n.startswith(prefix)])


def test_sdist_excludes_uninventoried_canary(tmp_path: Path):
    """Isolated tree + synthetic canary must not enter sdist or wheel-from-sdist."""
    export = tmp_path / "export"
    export.mkdir()
    listed = _run(
        ["git", "-C", str(ROOT), "ls-files", "-z"],
        cwd=ROOT,
    )
    assert listed.returncode == 0, listed.stderr
    for rel in listed.stdout.split("\0"):
        if not rel:
            continue
        src = ROOT / rel
        if not src.is_file():
            continue
        dest = export / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)

    canary_rel = "references/eras/uninventoried_packaging_canary.json"
    canary = export / canary_rel
    canary.write_text('{"id": "canary", "do_not_ship": true}\n', encoding="utf-8")
    assert canary.is_file()
    assert canary_rel not in {row["path"] for row in load_inventory()["files"]}

    dist = tmp_path / "dist"
    dist.mkdir()
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    ensure_build = _run(
        [sys.executable, "-m", "pip", "install", "-q", "build"],
        cwd=export,
        env=env,
    )
    assert ensure_build.returncode == 0, ensure_build.stderr
    built = _run(
        [sys.executable, "-m", "build", "--sdist", "--outdir", str(dist)],
        cwd=export,
        env=env,
    )
    assert built.returncode == 0, built.stderr + built.stdout
    sdist = next(dist.glob("*.tar.gz"))

    with tarfile.open(sdist, "r:gz") as tf:
        members = [n.replace("\\", "/") for n in tf.getnames()]
    assert not any(n.endswith(canary_rel) for n in members), members

    extract = tmp_path / "sdist_extract"
    extract.mkdir()
    try:
        shutil.unpack_archive(sdist, extract, filter="data")
    except TypeError:
        shutil.unpack_archive(sdist, extract)
    src_root = next(p for p in extract.iterdir() if p.is_dir())
    assert not (src_root / canary_rel).exists()

    wheel_out = tmp_path / "wheel_from_canary_sdist"
    wheel_out.mkdir()
    rebuilt = _run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(wheel_out)],
        cwd=src_root,
        env=env,
    )
    assert rebuilt.returncode == 0, rebuilt.stderr + rebuilt.stdout
    wheel = next(wheel_out.glob("*.whl"))
    with zipfile.ZipFile(wheel) as zf:
        wheel_names = zf.namelist()
    assert not any(canary_rel in n for n in wheel_names)


def test_clean_wheel_install_compile_parity(tmp_path, built_artifacts, source_baselines):
    venv_dir, work, env = _install_wheel_env(tmp_path, built_artifacts["wheel"])
    py = _venv_python(venv_dir)
    aipf_bin = _venv_aipf(venv_dir)

    loc = _run(
        [str(py), "-c", "import aipf, pathlib; print(pathlib.Path(aipf.__file__).resolve())"],
        cwd=work,
        env=env,
    )
    assert loc.returncode == 0, loc.stderr
    installed_path = Path(loc.stdout.strip())
    assert venv_dir.resolve() in installed_path.parents
    assert (ROOT.resolve() / "src") not in installed_path.parents
    assert "site-packages" in str(installed_path)

    regress = _run([str(aipf_bin), "regress"], cwd=work, env=env)
    assert regress.returncode != 0
    combined = (regress.stderr + regress.stdout).casefold()
    assert "not found" in combined or "unavailable" in combined or "repository root" in combined

    for name, payload in source_baselines.items():
        spec_path = work / f"{name}.json"
        out_path = work / f"{name}.out.json"
        spec_path.write_text(
            json.dumps(payload["spec"], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        result = _compile_installed(py, spec_path, work, env)
        assert result["prompt"].encode("utf-8") == payload["prompt_bytes"]
        assert _semantic_fingerprint(result) == payload["fingerprint"]
        out_path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")

        # CLI smoke from outside the repository (UTF-8 forced in env).
        for cmd in (
            [str(aipf_bin), "compile", str(spec_path)],
            [str(aipf_bin), "lint", str(spec_path)],
            [str(aipf_bin), "audit", str(spec_path)],
            [str(aipf_bin), "evidence", str(spec_path)],
            [str(aipf_bin), "classify", payload["spec"].get("request", "portrait")],
        ):
            ran = _run(cmd, cwd=work, env=env)
            assert ran.returncode == 0, ran.stderr

    assert out_path.is_file()
    assert not list(installed_path.parent.rglob("*.out.json"))


def test_wheel_from_sdist_parity(tmp_path, built_artifacts, source_baselines):
    extract = tmp_path / "sdist"
    extract.mkdir()
    try:
        shutil.unpack_archive(built_artifacts["sdist"], extract, filter="data")
    except TypeError:
        shutil.unpack_archive(built_artifacts["sdist"], extract)
    src_root = next(p for p in extract.iterdir() if p.is_dir())
    assert (src_root / "aipf_packaging" / "resource_inventory.json").is_file()
    assert (src_root / "references" / "lexicon" / "registry.json").is_file()

    wheel_out = tmp_path / "wheel-from-sdist"
    wheel_out.mkdir()
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    rebuilt = _run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(wheel_out)],
        cwd=src_root,
        env=env,
    )
    assert rebuilt.returncode == 0, rebuilt.stderr + rebuilt.stdout
    wheel = next(wheel_out.glob("*.whl"))

    inv = load_inventory()
    with zipfile.ZipFile(wheel) as zf:
        for row in inv["files"]:
            member = f"aipf/_knowledge/{row['path']}"
            assert member in zf.namelist(), member
            assert sha256(zf.read(member)).hexdigest() == row["sha256"]

    venv_dir, work, env = _install_wheel_env(tmp_path / "sdist-venv", wheel)
    py = _venv_python(venv_dir)
    sample = source_baselines["greek_marble"]
    spec_path = work / "case.json"
    spec_path.write_text(json.dumps(sample["spec"], ensure_ascii=False), encoding="utf-8")
    result = _compile_installed(py, spec_path, work, env)
    assert result["prompt"].encode("utf-8") == sample["prompt_bytes"]
    assert _semantic_fingerprint(result) == sample["fingerprint"]


def test_missing_packaged_resource_fails(monkeypatch):
    import aipf.resources as resources

    monkeypatch.setattr(resources, "source_checkout_root", lambda: None)

    class FakeTraversable:
        def joinpath(self, *parts):
            return self

        def read_bytes(self):
            raise FileNotFoundError("missing")

        def is_file(self):
            return False

        def is_dir(self):
            return False

        def iterdir(self):
            return iter(())

    monkeypatch.setattr(resources, "_packaged_root", lambda: FakeTraversable())
    with pytest.raises(ResourceError, match="missing packaged knowledge resource"):
        resources.read_bytes("references/lexicon/registry.json")
    with pytest.raises(ResourceError, match="missing packaged knowledge resource directory"):
        resources.iter_resource_dir("evidence/claims", "*.json")
