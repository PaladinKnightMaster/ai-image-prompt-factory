from aipf.experiment_runs import create_run_plan


def test_v33_run_plan_has_replicates():
    run = create_run_plan(
        "EXP-001",
        replicates=4,
    )

    assert run["experiment_id"] == "EXP-001"
    assert len(run["variants"]) == 2

    for variant in run["variants"]:
        assert len(variant["outputs"]) == 4


def test_v33_control_and_variant_prompts_differ():
    run = create_run_plan("EXP-001")

    prompts = {
        variant["variant_id"]: variant["prompt"]
        for variant in run["variants"]
    }

    assert prompts["control"] != prompts["variant"]


def test_v33_prompt_hashes_differ():
    run = create_run_plan("EXP-001")

    hashes = [
        variant["prompt_sha256"]
        for variant in run["variants"]
    ]

    assert len(set(hashes)) == 2


def test_v33_run_defaults_to_pinned_gpt_image_2():
    run = create_run_plan("EXP-001")

    assert run["model"] == "gpt-image-2"
    assert run["model_snapshot"] == "gpt-image-2-2026-04-21"