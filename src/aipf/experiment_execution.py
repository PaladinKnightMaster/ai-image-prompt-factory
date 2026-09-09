from __future__ import annotations

import base64
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .experiment_runs import sha256_file, validate_blind_ids


HOST_PACKAGE_DIRNAME = "host-package"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        delete=False,
        dir=path.parent,
        suffix=".tmp",
    ) as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
        temp_path = Path(f.name)

    temp_path.replace(path)


def load_run(run_file: str | Path) -> tuple[Path, dict]:
    path = Path(run_file).expanduser().resolve()

    if not path.exists():
        raise FileNotFoundError(path)

    run = json.loads(path.read_text(encoding="utf-8"))
    validate_blind_ids(run)
    return path, run


def _find_output(run: dict, blind_id: str) -> tuple[dict, dict]:
    target = blind_id.upper()

    for variant in run.get("variants", []):
        for output in variant.get("outputs", []):
            if str(output.get("blind_id", "")).upper() == target:
                return variant, output

    raise ValueError(f"unknown blind_id: {blind_id}")


def _refresh_run_status(run: dict) -> str:
    statuses = [
        output.get("status", "planned")
        for variant in run.get("variants", [])
        for output in variant.get("outputs", [])
    ]

    if statuses and all(status == "generated" for status in statuses):
        status = "completed"
    elif any(status == "generated" for status in statuses):
        status = "partial"
    elif statuses and all(status == "failed" for status in statuses):
        status = "failed"
    elif any(status == "failed" for status in statuses):
        status = "partial"
    else:
        status = "planned"

    run["status"] = status
    return status


def export_host_package(
    run_file: str | Path,
    *,
    output: str | Path | None = None,
) -> dict:
    """Export blind-safe generation tasks for ChatGPT/host-native use.

    The exported manifest intentionally omits variant/control labels. It is
    suitable for generation operators and later blind review, while the
    private ``run.json`` retains the treatment mapping.
    """
    path, run = load_run(run_file)

    if run.get("generation_mode") not in {
        "host_native",
        "manual_import",
    }:
        raise ValueError(
            "host export requires generation_mode host_native or "
            "manual_import"
        )

    destination = (
        Path(output).expanduser().resolve()
        if output
        else path.parent / HOST_PACKAGE_DIRNAME
    )
    prompts_dir = destination / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)

    tasks: list[dict] = []

    for variant in run["variants"]:
        for item in variant["outputs"]:
            blind_id = item["blind_id"]
            prompt_path = prompts_dir / f"{blind_id}.txt"
            prompt_path.write_text(
                variant["prompt"].rstrip() + "\n",
                encoding="utf-8",
            )

            tasks.append(
                {
                    "blind_id": blind_id,
                    "status": item["status"],
                    "prompt": variant["prompt"],
                    "prompt_sha256": variant["prompt_sha256"],
                    "expected_filename": f"{blind_id}.png",
                    "settings": {
                        "size": run["settings"]["size"],
                        "quality": run["settings"]["quality"],
                        "background": run["settings"].get(
                            "background"
                        ),
                    },
                }
            )

    # Blind IDs are random, so sorting by them produces a stable-looking order
    # without exposing the underlying variant grouping.
    tasks.sort(key=lambda task: task["blind_id"])

    manifest = {
        "run_id": run["run_id"],
        "experiment_id": run["experiment_id"],
        "generation_mode": run["generation_mode"],
        "model_target": run["model"],
        "model_snapshot": run["model_snapshot"],
        "task_count": len(tasks),
        "tasks": tasks,
    }

    _write_json_atomic(destination / "manifest.json", manifest)

    readme = f"""# AIPF Host-Native Experiment Package

Run: `{run['run_id']}`  
Experiment: `{run['experiment_id']}`  
Tasks: `{len(tasks)}`

Generate exactly one image for each blind ID using the associated prompt and
settings. Do not rename or merge IDs. Save the resulting image using the
blind ID, for example `ABC234.png`.

The manifest deliberately omits control/variant labels. Treatment mappings
remain only in the private `run.json` so downstream visual review can stay
blind.

After generation, import each result with:

```text
aipf experiment-import <run.json> --blind-id <ID> --image <image-file>
```
"""
    (destination / "README.md").write_text(
        readme,
        encoding="utf-8",
    )

    return {
        "run_id": run["run_id"],
        "task_count": len(tasks),
        "output": str(destination),
        "manifest": str(destination / "manifest.json"),
    }


def import_output(
    run_file: str | Path,
    *,
    blind_id: str,
    image: str | Path,
    provider: str = "chatgpt",
    model: str | None = None,
    model_snapshot: str | None = None,
    notes: str | None = None,
    overwrite: bool = False,
) -> dict:
    """Attach a host-native/manual image to its blind experiment slot."""
    path, run = load_run(run_file)
    source = Path(image).expanduser().resolve()

    if not source.exists() or not source.is_file():
        raise FileNotFoundError(source)

    variant, output = _find_output(run, blind_id)

    if output.get("status") == "generated" and not overwrite:
        raise ValueError(
            f"blind_id {output['blind_id']} already has a generated output; "
            "use overwrite=True to replace it"
        )

    suffix = source.suffix.lower() or ".png"
    variant_dir = path.parent / variant["variant_id"]
    variant_dir.mkdir(parents=True, exist_ok=True)

    image_name = f"{output['blind_id']}{suffix}"
    metadata_name = f"{output['blind_id']}.json"
    image_path = variant_dir / image_name
    metadata_path = variant_dir / metadata_name

    shutil.copy2(source, image_path)
    image_hash = sha256_file(image_path)

    metadata = {
        "run_id": run["run_id"],
        "experiment_id": run["experiment_id"],
        "blind_id": output["blind_id"],
        "replicate": output["replicate"],
        "generation_mode": run.get(
            "generation_mode",
            "manual_import",
        ),
        "provider": provider,
        "model": model or run.get("model") or "unknown",
        "model_snapshot": (
            model_snapshot
            or run.get("model_snapshot")
            or "unknown"
        ),
        "size": run["settings"]["size"],
        "quality": run["settings"]["quality"],
        "prompt_sha256": variant["prompt_sha256"],
        "imported_at_utc": _utc_now(),
        "source_image_name": source.name,
        "image_sha256": image_hash,
        "notes": notes,
    }

    metadata_path.write_text(
        json.dumps(
            metadata,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    output["status"] = "generated"
    output["image"] = image_name
    output["image_sha256"] = image_hash
    output["metadata"] = metadata_name
    output["error"] = None

    status = _refresh_run_status(run)
    _write_json_atomic(path, run)

    return {
        "run_id": run["run_id"],
        "blind_id": output["blind_id"],
        "image": str(image_path),
        "image_sha256": image_hash,
        "status": status,
    }


def record_failed_output(
    run_file: str | Path,
    *,
    blind_id: str,
    error: str,
) -> dict:
    """Record a host/manual generation failure without dropping the slot."""
    path, run = load_run(run_file)
    _variant, output = _find_output(run, blind_id)

    output["status"] = "failed"
    output["error"] = error

    status = _refresh_run_status(run)
    _write_json_atomic(path, run)

    return {
        "run_id": run["run_id"],
        "blind_id": output["blind_id"],
        "status": status,
    }


def execute_run(
    run_file: str | Path,
    *,
    limit: int | None = None,
    dry_run: bool = False,
) -> dict:
    """Execute an API-mode experiment run.

    API execution is optional and imported lazily. Host-native users should
    use ``experiment-export`` and ``experiment-import`` instead.
    """
    path, run = load_run(run_file)

    if dry_run:
        planned = sum(
            output["status"] == "planned"
            for variant in run["variants"]
            for output in variant["outputs"]
        )
        return {
            "run_id": run["run_id"],
            "generation_mode": run.get("generation_mode"),
            "planned": planned,
            "generated": 0,
            "failed": 0,
            "status": run.get("status", "planned"),
            "dry_run": True,
        }

    if run.get("generation_mode") != "api":
        raise RuntimeError(
            "experiment-run only executes generation_mode=api. "
            "For ChatGPT/host-native generation use experiment-export, "
            "generate the blind tasks in the host, then use "
            "experiment-import."
        )

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is required only for generation_mode=api."
        )

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "API execution requires the optional dependency: "
            "pip install -e '.[api]'"
        ) from exc

    client = OpenAI()
    root = path.parent
    generated = 0
    failed = 0
    skipped = 0
    attempted = 0
    run["status"] = "running"
    _write_json_atomic(path, run)

    for variant in run["variants"]:
        variant_dir = root / variant["variant_id"]
        variant_dir.mkdir(parents=True, exist_ok=True)

        for output in variant["outputs"]:
            if output["status"] != "planned":
                skipped += 1
                continue

            if limit is not None and attempted >= limit:
                status = _refresh_run_status(run)
                _write_json_atomic(path, run)
                return {
                    "run_id": run["run_id"],
                    "generated": generated,
                    "failed": failed,
                    "skipped": skipped,
                    "status": status,
                }

            attempted += 1
            blind_id = output["blind_id"]
            image_name = f"{blind_id}.png"
            metadata_name = f"{blind_id}.json"
            image_path = variant_dir / image_name
            metadata_path = variant_dir / metadata_name

            try:
                response = client.images.generate(
                    model=run["model_snapshot"],
                    prompt=variant["prompt"],
                    size=run["settings"]["size"],
                    quality=run["settings"]["quality"],
                    n=1,
                )

                item = response.data[0]

                if not item.b64_json:
                    raise RuntimeError(
                        "Image response did not contain b64_json."
                    )

                image_path.write_bytes(
                    base64.b64decode(item.b64_json)
                )
                image_hash = sha256_file(image_path)

                metadata = {
                    "run_id": run["run_id"],
                    "experiment_id": run["experiment_id"],
                    "blind_id": blind_id,
                    "replicate": output["replicate"],
                    "generation_mode": "api",
                    "provider": "openai_api",
                    "model": run["model"],
                    "model_snapshot": run["model_snapshot"],
                    "size": run["settings"]["size"],
                    "quality": run["settings"]["quality"],
                    "prompt_sha256": variant["prompt_sha256"],
                    "generated_at_utc": _utc_now(),
                    "image_sha256": image_hash,
                }

                metadata_path.write_text(
                    json.dumps(
                        metadata,
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )

                output["status"] = "generated"
                output["image"] = image_name
                output["image_sha256"] = image_hash
                output["metadata"] = metadata_name
                output["error"] = None
                generated += 1

            except Exception as exc:
                output["status"] = "failed"
                output["error"] = (
                    f"{type(exc).__name__}: {exc}"
                )
                failed += 1

            _refresh_run_status(run)
            _write_json_atomic(path, run)

    status = _refresh_run_status(run)
    _write_json_atomic(path, run)

    return {
        "run_id": run["run_id"],
        "generated": generated,
        "failed": failed,
        "skipped": skipped,
        "status": status,
    }
