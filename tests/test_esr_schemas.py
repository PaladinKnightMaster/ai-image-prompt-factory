"""Mandatory schema tests for ESR-v0.1 review contract (PR1 foundation).

These tests assert only Draft 2020-12 validation of
``data/schemas/esr_review.schema.json``. They do not implement package,
freeze, reveal, generation, gallery publish, or EXP-019 workflows.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "data" / "schemas" / "esr_review.schema.json"
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "esr"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def schema() -> dict:
    return _load(SCHEMA_PATH)


@pytest.fixture(scope="module")
def validator(schema: dict) -> Draft202012Validator:
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


@pytest.fixture
def valid_no_transform() -> dict:
    return _load(FIXTURE_DIR / "valid_no_transform.json")


@pytest.fixture
def valid_with_transform() -> dict:
    return _load(FIXTURE_DIR / "valid_with_transform.json")


def _errors(validator: Draft202012Validator, instance: dict) -> list:
    return list(validator.iter_errors(instance))


def _score(value, na_reason=None) -> dict:
    return {"value": value, "na_reason": na_reason}


# ---------------------------------------------------------------------------
# Valid fixtures (T1, T2)
# ---------------------------------------------------------------------------


def test_schema_is_draft_2020_12(schema: dict) -> None:
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"


def test_t1_valid_no_transform(
    validator: Draft202012Validator, valid_no_transform: dict
) -> None:
    assert _errors(validator, valid_no_transform) == []


def test_t2_valid_with_transform(
    validator: Draft202012Validator, valid_with_transform: dict
) -> None:
    assert _errors(validator, valid_with_transform) == []


# ---------------------------------------------------------------------------
# T3–T14 and extended invalid cases
# ---------------------------------------------------------------------------


def test_t3_score_out_of_range(
    validator: Draft202012Validator, valid_no_transform: dict
) -> None:
    for bad in (0, 6):
        doc = copy.deepcopy(valid_no_transform)
        doc["items"][0]["scores"]["task_brief_adherence"] = _score(bad)
        assert _errors(validator, doc), f"expected failure for value={bad}"


def test_t4_boolean_score(
    validator: Draft202012Validator, valid_no_transform: dict
) -> None:
    doc = copy.deepcopy(valid_no_transform)
    doc["items"][0]["scores"]["visual_coherence"] = _score(True)
    assert _errors(validator, doc)


def test_t5_d1_d4_null_forbidden(
    validator: Draft202012Validator, valid_no_transform: dict
) -> None:
    for dim in (
        "task_brief_adherence",
        "visual_coherence",
        "target_style_fidelity",
        "technical_cleanliness",
    ):
        doc = copy.deepcopy(valid_no_transform)
        doc["items"][0]["scores"][dim] = _score(None, "not_applicable_to_task")
        assert _errors(validator, doc), f"expected failure for null {dim}"


def test_t6_null_without_na_reason(
    validator: Draft202012Validator, valid_no_transform: dict
) -> None:
    doc = copy.deepcopy(valid_no_transform)
    doc["items"][0]["scores"]["prompt_repeatability"] = {
        "value": None,
        "na_reason": None,
    }
    assert _errors(validator, doc)


def test_t7_d5_wrong_na_reason(
    validator: Draft202012Validator, valid_no_transform: dict
) -> None:
    doc = copy.deepcopy(valid_no_transform)
    doc["items"][0]["scores"]["prompt_repeatability"] = _score(
        None, "not_applicable_to_task"
    )
    assert _errors(validator, doc)


def test_t8_d5_integer_forbidden(
    validator: Draft202012Validator, valid_no_transform: dict
) -> None:
    doc = copy.deepcopy(valid_no_transform)
    doc["items"][0]["scores"]["prompt_repeatability"] = _score(3)
    assert _errors(validator, doc)


def test_t9_d6_deferred_reason_forbidden(
    validator: Draft202012Validator, valid_no_transform: dict
) -> None:
    doc = copy.deepcopy(valid_no_transform)
    doc["items"][0]["scores"]["transformation_fidelity"] = _score(
        None, "deferred_protocol_v0_1"
    )
    assert _errors(validator, doc)


def test_t10_na_reason_with_integer_value(
    validator: Draft202012Validator, valid_no_transform: dict
) -> None:
    doc = copy.deepcopy(valid_no_transform)
    doc["items"][0]["scores"]["task_brief_adherence"] = _score(
        3, "not_applicable_to_task"
    )
    assert _errors(validator, doc)


def test_t11_invalid_evaluator_identity(
    validator: Draft202012Validator, valid_no_transform: dict
) -> None:
    doc = copy.deepcopy(valid_no_transform)
    doc["evaluator_identity_class"] = "independent_human"
    assert _errors(validator, doc)


def test_t12_independent_reviewer_true(
    validator: Draft202012Validator, valid_no_transform: dict
) -> None:
    doc = copy.deepcopy(valid_no_transform)
    doc["independent_reviewer"] = True
    assert _errors(validator, doc)


def test_t13_invalid_scientific_status(
    validator: Draft202012Validator, valid_no_transform: dict
) -> None:
    doc = copy.deepcopy(valid_no_transform)
    doc["scientific_status"] = "confirmatory"
    assert _errors(validator, doc)


def test_t14_invalid_blindness_claim(
    validator: Draft202012Validator, valid_no_transform: dict
) -> None:
    doc = copy.deepcopy(valid_no_transform)
    doc["blindness_claim"] = "fully_blind"
    assert _errors(validator, doc)


def test_transform_disabled_but_d6_scored(
    validator: Draft202012Validator, valid_no_transform: dict
) -> None:
    doc = copy.deepcopy(valid_no_transform)
    doc["items"][0]["scores"]["transformation_fidelity"] = _score(4)
    assert _errors(validator, doc)


def test_transform_enabled_but_d6_na(
    validator: Draft202012Validator, valid_with_transform: dict
) -> None:
    doc = copy.deepcopy(valid_with_transform)
    doc["items"][0]["scores"]["transformation_fidelity"] = _score(
        None, "not_applicable_to_task"
    )
    assert _errors(validator, doc)


def test_transform_enabled_missing_transformation_target(
    validator: Draft202012Validator, valid_with_transform: dict
) -> None:
    doc = copy.deepcopy(valid_with_transform)
    del doc["task_brief"]["transformation_target"]
    assert _errors(validator, doc)


def test_missing_mandatory_dimension(
    validator: Draft202012Validator, valid_no_transform: dict
) -> None:
    doc = copy.deepcopy(valid_no_transform)
    del doc["items"][0]["scores"]["visual_coherence"]
    assert _errors(validator, doc)


def test_unexpected_dimension(
    validator: Draft202012Validator, valid_no_transform: dict
) -> None:
    doc = copy.deepcopy(valid_no_transform)
    doc["items"][0]["scores"]["aesthetic_quality"] = _score(4)
    assert _errors(validator, doc)


def test_missing_shared_style_target(
    validator: Draft202012Validator, valid_no_transform: dict
) -> None:
    doc = copy.deepcopy(valid_no_transform)
    del doc["task_brief"]["style_target"]
    assert _errors(validator, doc)


def test_malformed_task_brief_digest(
    validator: Draft202012Validator, valid_no_transform: dict
) -> None:
    doc = copy.deepcopy(valid_no_transform)
    doc["task_brief"]["task_brief_sha256"] = "not-a-digest"
    assert _errors(validator, doc)


def test_duplicate_presentation_order_ids(
    validator: Draft202012Validator, valid_with_transform: dict
) -> None:
    doc = copy.deepcopy(valid_with_transform)
    doc["presentation_order"] = ["RBBBBBB3", "RBBBBBB3"]
    assert _errors(validator, doc)


def test_unrestricted_not_scored_forbidden(
    validator: Draft202012Validator, valid_no_transform: dict
) -> None:
    doc = copy.deepcopy(valid_no_transform)
    doc["items"][0]["scores"]["prompt_repeatability"] = _score(None, "not_scored")
    assert _errors(validator, doc)
