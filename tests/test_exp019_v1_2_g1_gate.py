"""Guards for the EXP-019 v1.2 gate-G1 engineering-contract record (PR-5).

PR-5 formalizes the engineering contract and the G1 gate documentation
only. These tests assert that the record states the owner approvals and
their limited scope, that the contract is digest-pinned and covers the
runtime-reserved obligations, and that v1.2 remains scientifically
inactive: unregistered, with no allocation, run root, or checkpoint
created. They authorize and create nothing.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs/EXP-019-v1.2.0.ENGINEERING-CONTRACT.md"
GATE_RECORD = ROOT / "docs/EXP-019-v1.2.0.GATE-G1-RECORD.md"
DEFINITION_DRAFT = ROOT / "experiments/drafts/EXP-019-v1.2.0.DEFINITION-DRAFT.json"


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
    assert not list(package.glob("exp019_v1_2*.py"))


def test_gate_record_creates_no_activation_artifacts() -> None:
    text = _norm(GATE_RECORD)
    assert "No allocation exists" in text
    assert "No run root or experimental checkpoint exists" in text
