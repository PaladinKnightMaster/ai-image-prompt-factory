"""Guards for the EXP-019 v1.2 gate-G1 engineering-contract record (PR-5).

PR-5 formalizes the engineering contract and the G1 gate documentation
only. These tests assert that the record states the owner approvals and
their limited scope, that the contract is digest-pinned and covers the
runtime-reserved obligations, and that v1.2 remains scientifically
inactive: unregistered, with no allocation, run root, or checkpoint
created. They authorize and create nothing.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs/EXP-019-v1.2.0.ENGINEERING-CONTRACT.md"
GATE_RECORD = ROOT / "docs/EXP-019-v1.2.0.GATE-G1-RECORD.md"
DEFINITION_DRAFT = ROOT / "experiments/drafts/EXP-019-v1.2.0.DEFINITION-DRAFT.json"

# Authorized, non-executing v1.2 modules. Authorization is by explicit
# name and by capability scan below, never by avoiding a filename: any
# other v1.2-scoped module, under any filename, is held to the same
# prohibition scan.
AUTHORIZED_V12_MODULES = {"exp019_v1_2_evidence.py"}

_V12_SCOPE = re.compile(r"1\.2\.0|v1_2|EXP-019 v1\.2")
_PROHIBITED_DEF = re.compile(
    r"allocat|generat|checkpoint|reveal|run_root|create_run|make_run|"
    r"activate|register_protocol|host_request|execute_attempt",
    re.IGNORECASE)


def _is_v12_scoped(path: Path) -> bool:
    if "v1_2" in path.name:
        return True
    try:
        return bool(_V12_SCOPE.search(path.read_text(encoding="utf-8")))
    except (OSError, UnicodeDecodeError):
        return False


def prohibited_v12_capabilities(path: Path) -> list:
    """Prohibited activation capabilities in a v1.2-scoped module.

    Detects, by AST rather than filename: executable protocol
    registration for v1.2, run-root/allocation/generation/checkpoint/
    reveal functionality, and any call registering or activating v1.2.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            if _PROHIBITED_DEF.search(node.name):
                found.append(f"definition:{node.name}")
        if isinstance(node, ast.Call):
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else \
                getattr(func, "id", "")
            if name in {"frozen_protocol", "register_frozen_protocol"} and \
                    any(isinstance(a, ast.Constant) and a.value == "1.2.0"
                        for a in node.args):
                found.append("call:register-v1.2")
    return found


def _norm(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def test_both_g1_documents_are_non_executable() -> None:
    for path in (CONTRACT, GATE_RECORD):
        assert "NON-EXECUTABLE" in _norm(path), path.name


def test_gate_record_states_owner_approvals_and_scope() -> None:
    text = _norm(GATE_RECORD)
    assert text.count("APPROVED") >= 3
    assert "2026-10-22" in text
    assert "protocol drafting and engineering preparation" in text
    assert "do **not** authorize scientific activation" in text or (
        "not** authorize scientific activation" in text)
    for decision in ("H1", "H2", "H3"):
        assert decision in text


def test_engineering_contract_is_digest_pinned_and_current() -> None:
    """Every artifact digest in the contract must recompute canonically."""
    text = CONTRACT.read_text(encoding="utf-8")
    checked = 0
    for line in text.splitlines():
        if "` | `" not in line:
            continue
        artifact, digest = (part.strip(" `") for part in line.split("|")[1:3])
        canonical = (ROOT / artifact).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(canonical).hexdigest() == digest, artifact
        checked += 1
    assert checked == 13


def test_engineering_contract_covers_runtime_reserved_obligations() -> None:
    text = _norm(CONTRACT)
    for obligation in (
        "digest recomputation",
        "class-C authentication",
        "Q1–Q5",
        "PENDING_UNKNOWN",
        "terminal attempt receipt",
        "run_disposition",
        "Activation lockout",
        "allocation custodian",
    ):
        assert obligation in text, obligation


def test_v1_2_remains_scientifically_inactive() -> None:
    definition = json.loads(DEFINITION_DRAFT.read_text(encoding="utf-8"))
    assert definition["status"] == "draft"
    assert definition["executable"] is False
    assert definition["allocation"]["randomization_committed"] is False
    assert definition["run"]["run_root_created"] is False
    assert definition["run"]["checkpoints_created"] is False

    from aipf.exp019_protocol import frozen_protocol

    with pytest.raises(ValueError, match="unknown EXP-019 frozen protocol version"):
        frozen_protocol("1.2.0")
    package = ROOT / "src" / "aipf"
    assert not (package / "exp019_v12").exists()
    # Authorized non-executing evidence validation is explicitly
    # permitted under clear v1.2 naming; activation capability is not.
    assert (package / "exp019_v1_2_evidence.py").exists()
    for module in sorted(package.glob("*.py")):
        if _is_v12_scoped(module):
            assert prohibited_v12_capabilities(module) == [], module.name


def test_activation_guard_detects_prohibited_code_under_any_filename(
        tmp_path) -> None:
    """The capability scan fails on activation code, whatever its name."""
    innocent_name = tmp_path / "totally_innocent_name.py"
    innocent_name.write_text(
        '"""EXP-019 v1.2 helper."""\n\n'
        "def generate_image():\n    return None\n", encoding="utf-8")
    assert prohibited_v12_capabilities(innocent_name) == [
        "definition:generate_image"]

    registrar = tmp_path / "another_innocent_name.py"
    registrar.write_text(
        '"""v1_2 helper."""\n'
        "from aipf.exp019_protocol import frozen_protocol\n"
        'frozen_protocol("1.2.0")\n', encoding="utf-8")
    assert prohibited_v12_capabilities(registrar) == ["call:register-v1.2"]

    validator_like = tmp_path / "evidence_check.py"
    validator_like.write_text(
        '"""EXP-019 v1.2 evidence validation."""\n\n'
        "def validate_evidence_bundle(bundle):\n    return bundle\n",
        encoding="utf-8")
    assert prohibited_v12_capabilities(validator_like) == []


def test_authorized_v12_validator_exposes_validation_only() -> None:
    import aipf.exp019_v1_2_evidence as validator

    public = {name for name in vars(validator) if not name.startswith("_")}
    assert "validate_evidence_bundle" in public
    assert not {name for name in public if _PROHIBITED_DEF.search(name)}


def test_contract_clarifies_indeterminate_authorization_and_dual_role() -> None:
    text = _norm(CONTRACT)
    assert "only through the indeterminate-disposition procedure" in text
    assert "authorized by H3" in text
    assert "recorded-unanchored" in text
    assert "never represented as personal blindness" in text
    assert "require distinct" in text and "persons for an independence claim" in text
    for field in ("schema_version", "run_id", "sequence", "event_type",
                  "evidence_sha256", "previous_anchor_commit"):
        assert f"`{field}`" in text


def test_gate_record_creates_no_activation_artifacts() -> None:
    text = _norm(GATE_RECORD)
    assert "No allocation exists" in text
    assert "No run root or experimental checkpoint exists" in text
