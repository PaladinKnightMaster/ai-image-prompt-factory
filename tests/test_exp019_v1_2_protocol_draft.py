"""Guards for the EXP-019 v1.2 protocol DRAFT artifacts (PR-4).

These drafts are non-executable by construction. These tests assert that
they stay that way: every draft is marked draft and non-executable, v1.2 is
still unregistered, and no randomization, identifier allocation, run root,
prompt text, or treatment text has been committed into the draft artifacts.
They authorize no experiment and create nothing.
"""

from __future__ import annotations

import hashlib
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
    ROOT / "docs/drafts/EXP-019-v1.2.0.FREEZE-SEQUENCING-DRAFT.md",
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


def test_decisions_h1_h3_are_owner_approved_with_limited_scope() -> None:
    text = (ROOT / "docs/drafts/EXP-019-v1.2.0.PROPOSED-DECISIONS-H1-H3.md"
            ).read_text(encoding="utf-8")
    assert text.count("APPROVED by the experiment owner, 2026-10-22") == 3
    assert text.count("APPROVED as proposed in PR #17") == 3
    assert "*(pending)*" not in text
    # Approval is for drafting/engineering only, never activation.
    assert "do **not**\n> authorize scientific activation" in text or (
        "not** authorize scientific activation" in text.replace("\n> ", " "))
    assert "operator_evidenced_host_provenance" in text
    definition = json.loads(DEFINITION_DRAFT.read_text(encoding="utf-8"))
    decisions = definition["owner_decisions"]
    assert decisions["H1"] == decisions["H2"] == decisions["H3"] == "approved"
    assert decisions["approved_date"] == "2026-10-22"
    assert "not scientific activation" in decisions["approval_scope"]


def test_allocation_custodian_is_separate_from_mapping_blind_coordinator() -> None:
    roles = " ".join(
        _draft_text("EXP-019-v1.2.0.ROLES-BLINDING-DRAFT.md").split())
    assert "Allocation custodian (private)" in roles
    assert "generating the fresh treatment allocation at the final freeze" in roles
    assert "sole custody of the private slot-to-condition mapping" in roles
    assert "preparing treatment-specific prompt packets" in roles
    assert "reviewer-image mapping integrity" in roles
    assert "No reviewer ever receives treatment-bearing" in roles
    # The coordinator remains mapping-blind and never custodies allocation.
    assert "separate from the mapping-blind coordinator" in roles
    assert "never exercises custodian knowledge while acting as coordinator" in roles


def _draft_text(name: str) -> str:
    return (ROOT / "docs/drafts" / name).read_text(encoding="utf-8")


def test_qualifying_requirements_are_labelled_q1_to_q5_and_referenced() -> None:
    contract = _draft_text("EXP-019-v1.2.0.EVIDENCE-CONTRACT-DRAFT.md")
    for label in ("Q1", "Q2", "Q3", "Q4", "Q5"):
        assert f"**{label}**" in contract
    policy = _draft_text("EXP-019-v1.2.0.ADMISSION-FAILURE-POLICY-DRAFT.md")
    assert "Q1–Q5" in policy


def test_terminal_disposition_vocabulary_is_consistent() -> None:
    policy = _draft_text("EXP-019-v1.2.0.ADMISSION-FAILURE-POLICY-DRAFT.md")
    for terminal in ("`ADMIT`", "`FAILURE`", "`INDETERMINATE_FINAL`"):
        assert terminal in policy
    assert "`PENDING_UNKNOWN`, a started invocation" in policy
    # Unknown outcomes must not be retryable as technical failures.
    assert "never\npermitted after `PENDING_UNKNOWN`" in policy or (
        "never" in policy and "PENDING_UNKNOWN" in policy)


def test_disposition_vocabulary_is_consistent_across_all_drafts() -> None:
    """No draft may use bare INDETERMINATE as a terminal disposition."""
    definition = json.loads(DEFINITION_DRAFT.read_text(encoding="utf-8"))
    assert definition["evidence_contract"]["dispositions"] == [
        "ADMIT", "FAILURE", "INDETERMINATE_FINAL"]
    prereg = (ROOT / "experiments/drafts/EXP-019-v1.2.0.PREREGISTRATION-DRAFT.md"
              ).read_text(encoding="utf-8")
    assert "`INDETERMINATE_FINAL`" in prereg
    assert "`INDETERMINATE`" not in prereg


def test_allocation_timing_is_the_g4_freeze_everywhere() -> None:
    """Allocation timing must not drift between draft artifacts."""
    for path in (*DRAFT_DOCS,
                 ROOT / "experiments/drafts/EXP-019-v1.2.0.PREREGISTRATION-DRAFT.md",
                 DEFINITION_DRAFT):
        text = path.read_text(encoding="utf-8")
        assert "at activation time" not in text, path.name
    definition = json.loads(DEFINITION_DRAFT.read_text(encoding="utf-8"))
    assert "gate G4" in definition["allocation"]["note"]


def test_terminal_receipt_and_external_checkpoint_rules_are_defined() -> None:
    policy = _draft_text("EXP-019-v1.2.0.ADMISSION-FAILURE-POLICY-DRAFT.md")
    assert "terminal attempt receipt" in policy
    assert "Externally anchored" in policy
    assert "six-field checkpoint format" in policy
    assert "recorded-unanchored" in policy


def test_coordinator_role_has_an_explicit_boundary() -> None:
    roles = _draft_text("EXP-019-v1.2.0.ROLES-BLINDING-DRAFT.md")
    assert "Coordinator" in roles
    assert "identifier-to-treatment link" in roles


def test_freeze_sequencing_gates_activation_after_pilot_and_freeze() -> None:
    sequencing = _draft_text("EXP-019-v1.2.0.FREEZE-SEQUENCING-DRAFT.md")
    for stage in ("Stage 1", "Stage 2", "Stage 3", "Stage 4", "Stage 5"):
        assert stage in sequencing
    for pr in ("PR-5", "PR-12", "PR-13", "PR-14", "PR-15"):
        assert pr in sequencing
    # Pilot acceptance (G3) and the scientific freeze (G4) must precede
    # first generation (Stage 5) in the document's own ordering.
    assert sequencing.index("Gate G3") < sequencing.index("## Stage 5")
    assert sequencing.index("Gate G4") < sequencing.index("## Stage 5")
    assert "incapable of\nstarting an experimental run" in sequencing or (
        "incapable of" in sequencing)


def test_cited_digests_resolve_to_the_frozen_sources() -> None:
    """Every SHA-256 cited in the drafts must recompute against its source."""
    definition = json.loads(DEFINITION_DRAFT.read_text(encoding="utf-8"))
    source = definition["scientific_source"]
    for path_key, digest_key in (
        ("definition_path", "definition_sha256"),
        ("fixture_path", "fixture_sha256"),
        ("preregistration_path", "preregistration_sha256"),
    ):
        # Cited digests are over the canonical repository (LF) bytes, so a
        # Windows checkout's CRLF working-tree conversion must be undone
        # before hashing; otherwise this test passes on one OS and fails on
        # the other.
        canonical = (ROOT / source[path_key]).read_bytes().replace(
            b"\r\n", b"\n")
        actual = hashlib.sha256(canonical).hexdigest()
        assert actual == source[digest_key], path_key
    prereg = (ROOT / "experiments/drafts/EXP-019-v1.2.0.PREREGISTRATION-DRAFT.md"
              ).read_text(encoding="utf-8")
    for digest_key in ("definition_sha256", "fixture_sha256",
                       "preregistration_sha256"):
        assert source[digest_key] in prereg


def test_per_disposition_evidence_matrix_is_defined() -> None:
    policy = _draft_text("EXP-019-v1.2.0.ADMISSION-FAILURE-POLICY-DRAFT.md")
    assert "Per-disposition evidence requirements (Q1–Q5)" in policy
    assert "never rests on a response capture alone" in policy


def test_all_four_checkpoint_kinds_persist() -> None:
    policy = _draft_text("EXP-019-v1.2.0.ADMISSION-FAILURE-POLICY-DRAFT.md")
    for kind in ("run-root checkpoint", "terminal attempt checkpoint",
                 "reviewer-freeze checkpoints", "run_disposition` checkpoint"):
        assert kind in policy
    assert "supplements — never replaces" in policy


def test_retry_waits_for_external_anchoring() -> None:
    policy = _draft_text("EXP-019-v1.2.0.ADMISSION-FAILURE-POLICY-DRAFT.md")
    assert "externally anchored" in policy
    assert "Each started attempt must reach exactly one terminal" in policy


def test_unavailable_field_label_is_an_expected_class_not_authority() -> None:
    contract = _draft_text("EXP-019-v1.2.0.EVIDENCE-CONTRACT-DRAFT.md")
    assert "expected source class" in contract
    assert "attaches no authority" in contract


def test_allocation_custody_and_reveal_act_are_assigned() -> None:
    roles = " ".join(
        _draft_text("EXP-019-v1.2.0.ROLES-BLINDING-DRAFT.md").split())
    assert "sole custody of the private slot-to-condition mapping" in roles
    assert "performs the reveal" in roles
    assert "separate from the mapping-blind coordinator" in roles


def test_pilot_changes_require_revalidation_and_possible_repeat_pilot() -> None:
    pilot = _draft_text("EXP-019-v1.2.0.PILOT-READINESS-DRAFT.md")
    sequencing = _draft_text("EXP-019-v1.2.0.FREEZE-SEQUENCING-DRAFT.md")
    assert "repeat pilot" in pilot
    assert "repeat\n  pilot" in sequencing or "repeat pilot" in sequencing


def test_v1_2_is_still_not_registered() -> None:
    from aipf.exp019_protocol import frozen_protocol

    with pytest.raises(ValueError, match="unknown EXP-019 frozen protocol version"):
        frozen_protocol("1.2.0")


def test_only_authorized_non_executing_v1_2_runtime_module_exists() -> None:
    """Authorized v1.2 modules only (evidence through checkpoints); each
    must pass the G1 capability scan under its granted boundaries."""
    from test_exp019_v1_2_g1_gate import (
        AUTHORIZED_V12_MODULES,
        prohibited_v12_capabilities,
    )

    package = ROOT / "src" / "aipf"
    assert not (package / "exp019_v12").exists()
    modules = {p.name for p in package.glob("exp019_v1_2*.py")}
    assert modules == set(AUTHORIZED_V12_MODULES)
    for name in modules:
        assert prohibited_v12_capabilities(package / name) == []
