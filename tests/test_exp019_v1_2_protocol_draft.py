"""Guards for the EXP-019 v1.2 protocol DRAFT artifacts (PR-4).

These drafts are non-executable by construction. These tests assert that
they stay that way: every draft is marked draft and non-executable, v1.2 is
still unregistered, and no randomization, identifier allocation, run root,
prompt text, or treatment text has been committed into the draft artifacts.
They authorize no experiment and create nothing.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

DRAFT_DOCS = (
    ROOT / "experiments/drafts/EXP-019-v1.2.0.PREREGISTRATION-DRAFT.md",
    ROOT / "docs/drafts/EXP-019-v1.2.0.EVIDENCE-CONTRACT-DRAFT.md",
    ROOT / "docs/drafts/EXP-019-v1.2.0.ADMISSION-FAILURE-POLICY-DRAFT.md",
    ROOT / "docs/drafts/EXP-019-v1.2.0.ROLES-BLINDING-DRAFT.md",
    ROOT / "docs/drafts/EXP-019-v1.2.0.PILOT-READINESS-DRAFT.md",
    ROOT / "docs/drafts/EXP-019-v1.2.0.PROPOSED-DECISIONS-H1-H3.md",
)
DEFINITION_DRAFT = ROOT / "experiments/drafts/EXP-019-v1.2.0.DEFINITION-DRAFT.json"


@pytest.mark.parametrize("path", DRAFT_DOCS, ids=lambda p: p.name)
def test_every_draft_doc_is_marked_draft_and_non_executable(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    assert "DRAFT" in text
    assert "NON-EXECUTABLE" in text


def test_definition_draft_is_marked_and_commits_no_allocation() -> None:
    definition = json.loads(DEFINITION_DRAFT.read_text(encoding="utf-8"))
    assert definition["status"] == "draft"
    assert definition["executable"] is False
    allocation = definition["allocation"]
    assert allocation["randomization_committed"] is False
    assert allocation["invocation_order_committed"] is False
    assert allocation["opaque_identifiers_committed"] is False
    run = definition["run"]
    assert run["run_root_created"] is False
    assert run["run_id_issued"] is False
    assert run["checkpoints_created"] is False


def test_definition_draft_preserves_science_by_reference_only() -> None:
    definition = json.loads(DEFINITION_DRAFT.read_text(encoding="utf-8"))
    source = definition["scientific_source"]
    assert source["preserved_by_reference"] is True
    assert source["treatment_text_copied"] is False
    assert source["prompt_text_copied"] is False
    assert definition["design"] == {
        "conditions": 3,
        "replicates_per_condition": 4,
        "planned_generations": 12,
        "outputs_per_invocation": 1,
        "first_technically_evaluable_image_retained": True,
        "quality_based_rerolls_allowed": False,
    }


def test_decisions_h1_h3_remain_unapproved() -> None:
    text = (ROOT / "docs/drafts/EXP-019-v1.2.0.PROPOSED-DECISIONS-H1-H3.md"
            ).read_text(encoding="utf-8")
    assert "NOT APPROVED" in text
    assert text.count("*(pending)*") == 3
    assert "operator_evidenced_host_provenance" in text


def test_v1_2_is_still_not_registered() -> None:
    from aipf.exp019_protocol import frozen_protocol

    with pytest.raises(ValueError, match="unknown EXP-019 frozen protocol version"):
        frozen_protocol("1.2.0")


def test_no_v1_2_runtime_module_exists() -> None:
    package = ROOT / "src" / "aipf"
    assert not (package / "exp019_v12").exists()
    assert not list(package.glob("exp019_v1_2*.py"))
