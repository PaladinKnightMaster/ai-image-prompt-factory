from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path

from .config import experiment_output_path
from .experiments import load_experiment, plan_experiment


DEFAULT_MODEL = "gpt-image-2"
DEFAULT_API_SNAPSHOT = "gpt-image-2-2026-04-21"
UNKNOWN_SNAPSHOT = "unknown"

# Avoid visually ambiguous characters such as I/1 and O/0.
BLIND_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
BLIND_ID_LENGTH = 6
ALLOWED_GENERATION_MODES = {
    "host_native",
    "api",
    "manual_import",
}


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


def make_blind_id(length: int = BLIND_ID_LENGTH) -> str:
    """Return an opaque reviewer-facing ID with no treatment information."""
    if length < 4:
        raise ValueError("blind ID length must be >= 4")

    return "".join(
        secrets.choice(BLIND_ALPHABET)
        for _ in range(length)
    )


def _next_unique_blind_id(
    used_ids: set[str],
    *,
    length: int = BLIND_ID_LENGTH,
) -> str:
    while True:
        value = make_blind_id(length)

        if value not in used_ids:
            used_ids.add(value)
            return value


def create_run_plan(
    experiment_id: str,
    *,
    replicates: int = 4,
    size: str = "1024x1536",
    quality: str = "medium",
    model: str = DEFAULT_MODEL,
    model_snapshot: str | None = None,
    generation_mode: str = "host_native",
) -> dict:
    """Create a run plan without generating images.

    ``host_native`` is the default because AIPF is intended to work inside
    ChatGPT/host environments without API billing. ``api`` remains available
    as an optional adapter, and ``manual_import`` supports externally produced
    first-party outputs.
    """
    if replicates < 1:
        raise ValueError("replicates must be >= 1")

    if generation_mode not in ALLOWED_GENERATION_MODES:
        raise ValueError(
            "generation_mode must be one of: "
            + ", ".join(sorted(ALLOWED_GENERATION_MODES))
        )

    if model_snapshot is None:
        model_snapshot = (
            DEFAULT_API_SNAPSHOT
            if generation_mode == "api"
            else UNKNOWN_SNAPSHOT
        )

    experiment = load_experiment(experiment_id)
    plan = plan_experiment(experiment)

    source_path = definition_path(experiment["experiment_id"])

    if not source_path.exists():
        raise FileNotFoundError(
            f"experiment definition not found: {source_path}"
        )

    created_at = datetime.now(timezone.utc)
    stamp = created_at.strftime("%Y%m%dT%H%M%SZ")
    nonce = make_blind_id(4)

    run_id = (
        f"{experiment['experiment_id']}-"
        f"{experiment['version']}-"
        f"{stamp}-{nonce}"
    )

    used_blind_ids: set[str] = set()
    variants: list[dict] = []

    for variant in plan["variants"]:
        prompt = variant["prompt"]
        outputs: list[dict] = []

        for replicate in range(1, replicates + 1):
            outputs.append(
                {
                    "replicate": replicate,
                    "blind_id": _next_unique_blind_id(
                        used_blind_ids
                    ),
                    "status": "planned",
                    "image": None,
                    "image_sha256": None,
                    "metadata": None,
                    "error": None,
                }
            )

        variants.append(
            {
                "variant_id": variant["id"],
                "factor": variant["factor"],
                "prompt": prompt,
                "prompt_sha256": sha256_text(prompt),
                "outputs": outputs,
            }
        )

    run = {
        "run_id": run_id,
        "experiment_id": experiment["experiment_id"],
        "experiment_version": experiment["version"],
        "experiment_definition_sha256": sha256_file(
            source_path
        ),
        "created_at_utc": created_at.isoformat(),
        "status": "planned",
        "generation_mode": generation_mode,
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

    validate_blind_ids(run)
    return run


def resolve_run_root(
    output: str | Path | None = None,
) -> Path:
    """Resolve the private experiment-run root.

    An explicit path wins over ``AIPF_EXPERIMENT_OUTPUT_PATH``.
    """
    if output:
        return Path(output).expanduser().resolve()

    configured = experiment_output_path()

    if configured is None:
        raise ValueError(
            "Experiment output path is not configured. "
            "Set AIPF_EXPERIMENT_OUTPUT_PATH in .env/environment "
            "or provide --output."
        )

    return configured


def write_run_plan(
    run: dict,
    output: str | Path | None = None,
) -> Path:
    """Persist a private experiment run plan and its variant prompts."""
    validate_blind_ids(run)

    root = resolve_run_root(output)
    root.mkdir(parents=True, exist_ok=True)

    destination = root / run["run_id"]
    destination.mkdir(parents=True, exist_ok=False)

    for variant in run["variants"]:
        variant_dir = destination / variant["variant_id"]
        variant_dir.mkdir(parents=True, exist_ok=True)

        (variant_dir / "prompt.txt").write_text(
            variant["prompt"].rstrip() + "\n",
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


def load_run_plan(run_file: str | Path) -> dict:
    path = Path(run_file).expanduser().resolve()

    if not path.exists():
        raise FileNotFoundError(path)

    run = json.loads(path.read_text(encoding="utf-8"))
    validate_blind_ids(run)
    return run


def blind_output_count(run: dict) -> int:
    return sum(
        len(variant.get("outputs", []))
        for variant in run.get("variants", [])
    )


def validate_blind_ids(run: dict) -> None:
    """Ensure blind IDs are present, unique, and do not expose roles."""
    blind_ids: list[str] = []
    forbidden_terms = {
        "control",
        "variant",
        "baseline",
        "treatment",
    }

    for variant in run.get("variants", []):
        for output in variant.get("outputs", []):
            blind_id = output.get("blind_id")

            if not blind_id:
                raise ValueError(
                    "Every planned output requires a blind_id."
                )

            lowered = blind_id.lower()

            for term in forbidden_terms:
                if term in lowered:
                    raise ValueError(
                        "blind_id exposes experiment role: "
                        f"{blind_id}"
                    )

            blind_ids.append(blind_id)

    if len(blind_ids) != len(set(blind_ids)):
        raise ValueError(
            "Blind IDs must be unique within a run."
        )
