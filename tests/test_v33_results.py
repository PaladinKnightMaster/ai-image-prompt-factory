import json
from pathlib import Path

from jsonschema import Draft202012Validator

from aipf.io import repo_root
from aipf.patterns import get_pattern


RESULT_REL = Path(
    "experiments/results/EXP-001/"
    "EXP-001-1.0.1-20260910T132045Z-DEQ4.result.json"
)


def _result():
    return json.loads((repo_root() / RESULT_REL).read_text(encoding="utf-8"))


def test_exp001_result_schema_validates():
    result = _result()
    schema = json.loads(
        (repo_root() / "data/schemas/experiment_result.schema.json").read_text(
            encoding="utf-8"
        )
    )
    assert list(Draft202012Validator(schema).iter_errors(result)) == []


def test_exp001_result_aggregates_match_raw_scores():
    result = _result()
    dimensions = [
        "semantic_compliance",
        "aesthetic_quality",
        "technical_defects",
        "pose_mechanics",
    ]

    for variant_id in ("control", "variant"):
        rows = [
            row for row in result["raw_scores"]
            if row["variant_id"] == variant_id
        ]
        assert len(rows) == 4

        for dimension in dimensions:
            mean = sum(row["scores"][dimension] for row in rows) / len(rows)
            assert mean == result["variants"][variant_id]["means"][dimension]

        overall = sum(row["overall"] for row in rows) / len(rows)
        assert overall == result["variants"][variant_id]["means"]["overall"]


def test_exp001_result_delta_and_classification():
    result = _result()
    assert result["primary_dimension"] == "pose_mechanics"
    assert result["deltas_variant_minus_control"]["pose_mechanics"] == -0.25
    assert result["deltas_variant_minus_control"]["overall"] == -0.125
    assert result["evidence_classification"] == "weakly_contradicts"


def test_exp001_definition_is_marked_executed():
    definition = json.loads(
        (repo_root() / "experiments/definitions/EXP-001.json").read_text(
            encoding="utf-8"
        )
    )
    assert definition["version"] == "1.0.1"
    assert definition["status"] == "executed"
    assert definition["latest_result"] == RESULT_REL.as_posix()


def test_exp001_pattern_is_mixed_and_not_compiler_eligible():
    pattern = get_pattern("pose-explicit-weight-distribution")
    assert pattern is not None
    assert pattern["validation_status"] == "mixed"
    assert pattern["compiler_usage"]["compiler_eligible"] is False
    assert "EXP-001-1.0.1-20260910T132045Z-DEQ4" in pattern["evidence"]["experiments"]

EXP002_RESULT_REL = Path(
    "experiments/results/EXP-002/"
    "EXP-002-1.0.1-20260910T181605Z-2GVM.result.json"
)


def _exp002_result():
    return json.loads((repo_root() / EXP002_RESULT_REL).read_text(encoding="utf-8"))


def test_exp002_result_schema_validates():
    result = _exp002_result()
    schema = json.loads(
        (repo_root() / "data/schemas/experiment_result.schema.json").read_text(
            encoding="utf-8"
        )
    )
    assert list(Draft202012Validator(schema).iter_errors(result)) == []


def test_exp002_result_aggregates_match_raw_scores():
    result = _exp002_result()
    dimensions = [
        "semantic_compliance",
        "aesthetic_quality",
        "technical_defects",
        "material_physics",
    ]

    for variant_id in ("control", "variant"):
        rows = [
            row for row in result["raw_scores"]
            if row["variant_id"] == variant_id
        ]
        assert len(rows) == 4

        for dimension in dimensions:
            mean = sum(row["scores"][dimension] for row in rows) / len(rows)
            assert mean == result["variants"][variant_id]["means"][dimension]

        overall = sum(row["overall"] for row in rows) / len(rows)
        assert overall == result["variants"][variant_id]["means"]["overall"]


def test_exp002_result_delta_and_classification():
    result = _exp002_result()
    assert result["primary_dimension"] == "material_physics"
    assert result["deltas_variant_minus_control"]["material_physics"] == -0.75
    assert result["deltas_variant_minus_control"]["aesthetic_quality"] == 0.25
    assert result["deltas_variant_minus_control"]["overall"] == -0.125
    assert result["evidence_classification"] == "contradicts"


def test_exp002_definition_is_marked_executed():
    definition = json.loads(
        (repo_root() / "experiments/definitions/EXP-002.json").read_text(
            encoding="utf-8"
        )
    )
    assert definition["version"] == "1.0.1"
    assert definition["status"] == "executed"
    assert definition["latest_result"] == EXP002_RESULT_REL.as_posix()


def test_exp002_pattern_is_mixed_and_not_compiler_eligible():
    pattern = get_pattern("material-satin-fold-response")
    assert pattern is not None
    assert pattern["validation_status"] == "mixed"
    assert pattern["compiler_usage"]["compiler_eligible"] is False
    assert "EXP-002-1.0.1-20260910T181605Z-2GVM" in pattern["evidence"]["experiments"]
