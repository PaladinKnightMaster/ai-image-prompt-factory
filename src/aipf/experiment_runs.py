from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .config import experiment_output_path
from .experiments import load_experiment, plan_experiment


DEFAULT_MODEL = "gpt-image-2"
DEFAULT_SNAPSHOT = "gpt-image-2-2026-04-21"


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def definition_path(experiment_id: str) -> Path:
    from .io import repo_root

    return (
        repo_root()
        / "experiments"
        / "definitions"
        / f"{experiment_id}.json"
    )


def create_run_plan(
    experiment_id: str,
    *,
    replicates: int = 4,
    size: str = "1024x1536",
    quality: str = "medium",
    model: str = DEFAULT_MODEL,
    model_snapshot: str = DEFAULT_SNAPSHOT,
) -> dict:
    if replicates < 1:
        raise ValueError("replicates must be >= 1")

    experiment = load_experiment(experiment_id)
    plan = plan_experiment(experiment)

    source_path = definition_path(experiment["experiment_id"])

    created_at = datetime.now(timezone.utc)
    stamp = created_at.strftime("%Y%m%dT%H%M%SZ")

    run_id = (
        f"{experiment['experiment_id']}-"
        f"{experiment['version']}-"
        f"{stamp}"
    )

    variants = []

    for variant in plan["variants"]:
        prompt = variant["prompt"]

        outputs = [
            {
                "replicate": replicate,
                "status": "planned",
                "image": None,
                "image_sha256": None,
                "metadata": None,
                "error": None,
            }
            for replicate in range(1, replicates + 1)
        ]

        variants.append(
            {
                "variant_id": variant["id"],
                "factor": variant["factor"],
                "prompt": prompt,
                "prompt_sha256": sha256_text(prompt),
                "outputs": outputs,
            }
        )

    return {
        "run_id": run_id,
        "experiment_id": experiment["experiment_id"],
        "experiment_version": experiment["version"],
        "experiment_definition_sha256": sha256_file(source_path),
        "created_at_utc": created_at.isoformat(),
        "status": "planned",
        "model": model,
        "model_snapshot": model_snapshot,
        "settings": {
            "replicates": replicates,
            "size": size,
            "quality": quality,
            "background": None,
        },
        "variants": variants,
    }


def resolve_run_root(output: str | Path | None = None) -> Path:
    if output:
        return Path(output).expanduser().resolve()

    configured = experiment_output_path()

    if configured is None:
        raise ValueError(
            "Experiment output path is not configured. "
            "Set AIPF_EXPERIMENT_OUTPUT_PATH or provide --output."
        )

    return configured


def write_run_plan(
    run: dict,
    output: str | Path | None = None,
) -> Path:
    root = resolve_run_root(output)
    destination = root / run["run_id"]

    destination.mkdir(parents=True, exist_ok=False)

    for variant in run["variants"]:
        variant_dir = destination / variant["variant_id"]
        variant_dir.mkdir(parents=True)

        (variant_dir / "prompt.txt").write_text(
            variant["prompt"] + "\n",
            encoding="utf-8",
        )

    run_path = destination / "run.json"

    run_path.write_text(
        json.dumps(
            run,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    return run_path