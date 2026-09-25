from __future__ import annotations

import hashlib
import json
import os
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



def _environment_value(name: str) -> str | None:
    """Resolve an environment value, falling back to the repository .env."""

    value = os.getenv(name)

    if value:
        return value

    from .io import repo_root

    env_file = repo_root() / ".env"

    if not env_file.exists():
        return None

    for raw_line in env_file.read_text(
        encoding="utf-8-sig"
    ).splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)

        if key.strip() != name:
            continue

        return value.strip().strip('"').strip("'")

    return None


def resolve_reference_input_source(
    reference_input: dict,
) -> Path:
    """Resolve and verify one private frozen reference fixture."""

    required = (
        "fixture_root_env",
        "fixture_relpath",
        "fixture_sha256",
    )

    missing = [
        key
        for key in required
        if not reference_input.get(key)
    ]

    if missing:
        raise ValueError(
            "reference fixture is missing required fields: "
            + ", ".join(missing)
        )

    env_name = reference_input["fixture_root_env"]
    root_value = _environment_value(env_name)

    if not root_value:
        raise ValueError(
            f"reference fixture root is not configured: {env_name}"
        )

    root = Path(root_value).expanduser().resolve()
    source = (
        root / reference_input["fixture_relpath"]
    ).resolve()

    try:
        source.relative_to(root)
    except ValueError as exc:
        raise ValueError(
            "reference fixture path escapes configured fixture root: "
            f"{source}"
        ) from exc

    if not source.exists() or not source.is_file():
        raise FileNotFoundError(
            f"reference fixture not found: {source}"
        )

    actual_sha256 = sha256_file(source)
    expected_sha256 = str(
        reference_input["fixture_sha256"]
    ).lower()

    if actual_sha256 != expected_sha256:
        raise ValueError(
            "reference fixture SHA-256 mismatch for "
            f"{reference_input.get('fixture_id', source.name)}: "
            f"expected {expected_sha256}, got {actual_sha256}"
        )

    return source


def resolve_reference_inputs(
    experiment: dict,
) -> list[dict]:
    """Validate and freeze reference declarations for a run plan."""

    requirements = (
        experiment.get("requires_reference_inputs") or []
    )

    if not requirements:
        return []

    readiness = (
        experiment.get("transfer_benchmark", {})
        .get("execution_readiness")
    )

    if readiness != "ready":
        raise ValueError(
            f"{experiment.get('experiment_id', 'experiment')} "
            "requires reference fixtures but is not execution-ready"
        )

    required_metadata = (
        "slot",
        "role",
        "fixture_id",
        "fixture_version",
        "fixture_root_env",
        "fixture_relpath",
        "fixture_sha256",
    )

    resolved: list[dict] = []

    for requirement in requirements:
        missing = [
            key
            for key in required_metadata
            if not requirement.get(key)
        ]

        if missing:
            raise ValueError(
                "reference fixture declaration is incomplete: "
                + ", ".join(missing)
            )

        # This performs file existence + frozen hash verification.
        resolve_reference_input_source(requirement)

        item = dict(requirement)
        item["fixture_sha256"] = str(
            item["fixture_sha256"]
        ).lower()

        resolved.append(item)

    return resolved

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
    size: str | None = None,
    quality: str | None = None,
    model: str | None = None,
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

    experiment = load_experiment(experiment_id)
    is_exp019_host = experiment["experiment_id"] == "EXP-019" and experiment["version"] == "1.1.0"
    size = size if size is not None else ("portrait_2:3" if is_exp019_host else "1024x1536")
    quality = quality if quality is not None else ("unavailable" if is_exp019_host else "medium")
    model = model if model is not None else ("ChatGPT Images" if is_exp019_host else DEFAULT_MODEL)
    if model_snapshot is None:
        model_snapshot = UNKNOWN_SNAPSHOT if is_exp019_host or generation_mode != "api" else DEFAULT_API_SNAPSHOT

    execution_readiness = (
        experiment
        .get("transfer_benchmark", {})
        .get("execution_readiness")
    )

    if (
        execution_readiness is not None
        and execution_readiness != "ready"
    ):
        raise ValueError(
            f"experiment {experiment_id} execution_readiness is "
            f"{execution_readiness!r}; expected 'ready'"
        )
    plan = plan_experiment(experiment)
    reference_inputs = resolve_reference_inputs(experiment)

    if reference_inputs and generation_mode == "api":
        raise ValueError(
            "reference-image experiment execution is currently "
            "supported through host_native/manual_import only"
        )

    explicit_path = Path(experiment_id)
    source_path = explicit_path if explicit_path.is_file() else definition_path(experiment["experiment_id"])

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
        "reference_inputs": reference_inputs,
        "settings": {
            "replicates": replicates,
            "size": size,
            "quality": quality,
            "background": None,
        },
        "variants": variants,
    }

    execution_provenance = experiment.get(
        "execution_provenance"
    )

    if execution_provenance is not None:
        run["execution_provenance"] = json.loads(
            json.dumps(execution_provenance)
        )

    if experiment["experiment_id"] == "EXP-019":
        from .exp019_protocol import configure_run
        configure_run(run)

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
    if run.get("experiment_id") == "EXP-019":
        from .exp019_protocol import validate_run
        validate_run(run)

    root = resolve_run_root(output)
    is_exp019_host = run.get("experiment_id") == "EXP-019" and run.get("experiment_version") == "1.1.0"
    if is_exp019_host:
        from .io import repo_root
        if root.parts[-2:] != ("experiments", "generated-images"):
            raise ValueError("EXP-019 private run root must end with experiments/generated-images")
        if root == repo_root() or repo_root() in root.parents:
            raise ValueError("EXP-019 private run root must be outside the public repository")
        if any(part.lower() in {"release", "release-artifacts", "release-build", "release-verify"}
               for part in root.parts):
            raise ValueError("EXP-019 empirical evidence cannot use a release directory")
    root.mkdir(parents=True, exist_ok=True)

    destination = root / run["run_id"]
    destination.mkdir(parents=True, exist_ok=False)

    if is_exp019_host:
        prompts_dir = destination / "generation-inputs" / "prompts"
        prompts_dir.mkdir(parents=True)
        for variant in run["variants"]:
            for item in variant["outputs"]:
                (prompts_dir / f"{item['blind_id']}.txt").write_bytes(variant["prompt"].encode("utf-8"))
        reference_dir = destination / "generation-inputs" / "reference-manifest"
        reference_dir.mkdir(parents=True)
        (reference_dir / "references.json").write_text("[]\n", encoding="utf-8")
        hashes = sorted(f"{sha256_file(path)}  {path.relative_to(destination).as_posix()}"
                        for path in (destination / "generation-inputs").rglob("*") if path.is_file())
        (destination / "generation-inputs" / "generation-inputs.sha256.txt").write_text("\n".join(hashes) + "\n", encoding="utf-8")
        run_path = destination / "run-private.json"
        run_path.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return run_path

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
    if run.get("experiment_id") == "EXP-019":
        from .exp019_protocol import validate_run
        validate_run(run)
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
