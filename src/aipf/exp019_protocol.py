"""Frozen EXP-019 execution bindings. No experiment data is authored here."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .experiments import plan_experiment
from .io import repo_root

DEFINITION_SHA256 = "c5ced96c0357fbecb43169b96ea438aa7fd7e7fd739f1fb34381a3fded72bfe7"
FIXTURE_SHA256 = "a47d5cb22b3ee0b83bc585db310cfe3e4a9facc2e9227777503248156d93a1b0"
DEFINITION_PATH = "experiments/definitions/EXP-019.json"
FIXTURE_PATH = "experiments/fixtures/EXP-019/EXP-019-BOKASHI-01.fixture.json"
REVIEWERS = ("R1", "R2")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_sha256(value: dict) -> str:
    return _sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def append_attempt_event(output: dict, event: dict) -> None:
    """Append a chained event; never rewrite an earlier attempt event."""
    prior = output["attempt_events"][-1]["event_sha256"] if output["attempt_events"] else None
    payload = {**event, "previous_event_sha256": prior}
    output["attempt_events"].append({**payload, "event_sha256": _canonical_sha256(payload)})


def _validate_attempt_events(output: dict) -> None:
    prior = None
    events = output["attempt_events"]
    for event in events:
        payload = dict(event)
        digest = payload.pop("event_sha256", None)
        if payload.get("previous_event_sha256") != prior or digest != _canonical_sha256(payload):
            raise ValueError("EXP-019 append-only attempt event chain mismatch")
        prior = digest
    if len(events) % 2:
        if events[-1].get("event") != "started":
            raise ValueError("EXP-019 attempt ledger has incomplete outcome")
    for index, event in enumerate(events):
        if event.get("attempt_number") != index // 2 + 1 or (event.get("event") == "started") != (index % 2 == 0):
            raise ValueError("EXP-019 attempt event sequence mismatch")
    if len(events) > 6:
        raise ValueError("EXP-019 retry limit exceeded")
    outcomes = [event["event"] for event in events[1::2]]
    if any(event not in {"technical_failure", "safety_refusal", "provider_failure", "protocol_failure", "success"} for event in outcomes):
        raise ValueError("EXP-019 invalid attempt outcome")
    if any(event != "technical_failure" for event in outcomes[:-1]):
        raise ValueError("EXP-019 reroll after terminal outcome")
    if output.get("status") == "generated" and (not outcomes or outcomes[-1] != "success"):
        raise ValueError("EXP-019 generated slot lacks successful attempt")
    if output.get("status") == "planned" and events and len(events) % 2 == 0:
        raise ValueError("EXP-019 planned slot has completed attempt")
    if output.get("status") == "failed" and not outcomes:
        raise ValueError("EXP-019 failed slot lacks completed attempt")


def frozen_protocol() -> tuple[dict, dict]:
    """Fail closed if either frozen byte artifact or prompt binding drifts."""
    definition_bytes = (repo_root() / DEFINITION_PATH).read_bytes()
    fixture_bytes = (repo_root() / FIXTURE_PATH).read_bytes()
    if _sha256(definition_bytes) != DEFINITION_SHA256 or _sha256(fixture_bytes) != FIXTURE_SHA256:
        raise ValueError("EXP-019 frozen definition or fixture hash mismatch")
    definition, fixture = json.loads(definition_bytes), json.loads(fixture_bytes)
    if definition["version"] != "1.0.0" or definition["status"] != "planned":
        raise ValueError("EXP-019 frozen version/status mismatch")
    planned = {row["id"]: row["prompt"] for row in plan_experiment(definition)["variants"]}
    if set(planned) != {"C", "A", "B"}:
        raise ValueError("EXP-019 condition set mismatch")
    for condition, prompt in planned.items():
        binding = definition["prompt_bindings"]["conditions"][condition]
        if prompt != fixture["common_prompt"] + " " + fixture["treatment_clauses"][condition]:
            raise ValueError(f"EXP-019 {condition} prompt differs from fixture")
        if (len(prompt), len(prompt.split()), _sha256(prompt.encode("utf-8"))) != (
            binding["characters"], binding["whitespace_delimited_words"], binding["sha256"]
        ):
            raise ValueError(f"EXP-019 {condition} prompt binding mismatch")
    return definition, fixture


def _plan_core(run: dict) -> dict:
    return {
        "run_id": run["run_id"],
        "experiment_id": run["experiment_id"],
        "experiment_version": run["experiment_version"],
        "experiment_definition_sha256": run["experiment_definition_sha256"],
        "fixture_sha256": run["fixture_sha256"],
        "generation_mode": run["generation_mode"],
        "model": run["model"],
        "model_snapshot": run["model_snapshot"],
        "reference_inputs": run["reference_inputs"],
        "settings": run["settings"],
        "variants": [
            {
                "variant_id": v["variant_id"], "factor": v["factor"],
                "prompt": v["prompt"], "prompt_sha256": v["prompt_sha256"],
                "slots": [(o["blind_id"], o["replicate"]) for o in v["outputs"]],
            }
            for v in run["variants"]
        ],
        "invocation_order": run["invocation_order"],
    }


def configure_run(run: dict) -> None:
    definition, _fixture = frozen_protocol()
    config = definition["generation_config"]
    expected = ("api", config["requested_model"], config["model_snapshot"], config["size"], config["quality"], 4)
    actual = (run["generation_mode"], run["model"], run["model_snapshot"], run["settings"]["size"], run["settings"]["quality"], run["settings"]["replicates"])
    if actual != expected:
        raise ValueError(f"EXP-019 requires exact generation settings {expected}; received {actual}")
    run["settings"].update(background="opaque", seed=None, image_count_per_invocation=1)
    run["fixture_sha256"] = FIXTURE_SHA256
    run["execution_provenance"] = {
        "receipt_required": True,
        "receipt_schema_version": "1.0.0",
        "required_reviewers": list(REVIEWERS),
    }
    by_condition = {v["variant_id"]: v for v in run["variants"]}
    order = []
    for replicate, block in enumerate(definition["preregistration"]["invocation_blocks"], start=1):
        for condition in block:
            output = by_condition[condition]["outputs"][replicate - 1]
            output["attempt_events"] = []
            order.append({
                "position": len(order) + 1,
                "blind_id": output["blind_id"],
                "variant_id": condition,
                "replicate": replicate,
            })
    run["invocation_order"] = order
    run["plan_commitment_sha256"] = _canonical_sha256(_plan_core(run))
    validate_run(run)


def validate_run(run: dict) -> None:
    if run.get("experiment_id") != "EXP-019":
        return
    definition, _fixture = frozen_protocol()
    config = definition["generation_config"]
    if run.get("experiment_version") != "1.0.0" or run.get("experiment_definition_sha256") != DEFINITION_SHA256 or run.get("fixture_sha256") != FIXTURE_SHA256:
        raise ValueError("EXP-019 run frozen artifact binding mismatch")
    if run.get("generation_mode") != "api" or run.get("model") != config["requested_model"] or run.get("model_snapshot") != config["model_snapshot"]:
        raise ValueError("EXP-019 run model/mode mismatch")
    if run.get("reference_inputs") != [] or run.get("settings") != {
        "replicates": 4, "size": "1024x1536", "quality": "high", "background": "opaque",
        "seed": None, "image_count_per_invocation": 1,
    }:
        raise ValueError("EXP-019 run generation configuration mismatch")
    if run.get("execution_provenance") != {"receipt_required": True, "receipt_schema_version": "1.0.0", "required_reviewers": list(REVIEWERS)}:
        raise ValueError("EXP-019 run provenance policy mismatch")
    variants = run.get("variants", [])
    planned = plan_experiment(definition)["variants"]
    if [v.get("variant_id") for v in variants] != ["C", "A", "B"]:
        raise ValueError("EXP-019 run conditions mismatch")
    output_index = {}
    for variant, expected in zip(variants, planned):
        prompt = expected["prompt"]
        if variant.get("prompt") != prompt or variant.get("prompt_sha256") != _sha256(prompt.encode("utf-8")) or variant.get("factor") != expected["factor"]:
            raise ValueError("EXP-019 run prompt or hash mismatch")
        outputs = variant.get("outputs", [])
        if len(outputs) != 4 or [o.get("replicate") for o in outputs] != [1, 2, 3, 4]:
            raise ValueError("EXP-019 run replicate mismatch")
        for output in outputs:
            blind_id = output.get("blind_id")
            if not blind_id or blind_id in output_index or not isinstance(output.get("attempt_events"), list):
                raise ValueError("EXP-019 run slot/attempt ledger mismatch")
            _validate_attempt_events(output)
            output_index[blind_id] = (variant["variant_id"], output["replicate"])
    order = run.get("invocation_order", [])
    expected_order = sum(definition["preregistration"]["invocation_blocks"], [])
    if len(order) != 12 or len({o.get("blind_id") for o in order}) != 12:
        raise ValueError("EXP-019 requires exactly 12 distinct invocation slots")
    for position, (slot, condition) in enumerate(zip(order, expected_order), start=1):
        if slot != {
            "position": position, "blind_id": slot.get("blind_id"),
            "variant_id": condition, "replicate": (position - 1) // 3 + 1,
        } or output_index.get(slot.get("blind_id")) != (condition, (position - 1) // 3 + 1):
            raise ValueError("EXP-019 frozen invocation order mismatch")
    if run.get("plan_commitment_sha256") != _canonical_sha256(_plan_core(run)):
        raise ValueError("EXP-019 run plan commitment mismatch")


def find_slot(run: dict, blind_id: str) -> tuple[dict, dict]:
    for variant in run["variants"]:
        for output in variant["outputs"]:
            if output["blind_id"] == blind_id:
                return variant, output
    raise ValueError(f"unknown EXP-019 slot: {blind_id}")
