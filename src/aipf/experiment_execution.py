from __future__ import annotations

import base64
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .experiment_runs import (
    resolve_reference_input_source,
    sha256_file,
    validate_blind_ids,
)
from .execution_receipt import (
    normalized_reference_inputs,
    receipt_required,
    receipt_template,
    task_commitment_sha256,
    validate_execution_receipt,
)


HOST_PACKAGE_DIRNAME = "host-package"
OUTPUTS_DIRNAME = "outputs"


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



def _export_reference_inputs(
    destination: Path,
    run: dict,
) -> list[dict]:
    """Copy frozen private references into a blind-safe host package."""

    references = run.get("reference_inputs") or []
    references_dir = destination / "references"

    if references_dir.exists():
        shutil.rmtree(references_dir)

    if not references:
        return []

    references_dir.mkdir(parents=True, exist_ok=True)

    exported: list[dict] = []
    used_filenames: set[str] = set()

    for reference in references:
        source = resolve_reference_input_source(reference)

        slot = str(reference["slot"])
        stem = "".join(
            ch if ch.isalnum() else "_"
            for ch in slot
        ).strip("_")

        if not stem:
            stem = "Reference"

        suffix = source.suffix.lower() or ".png"
        filename = f"{stem}{suffix}"

        if filename in used_filenames:
            raise ValueError(
                f"duplicate exported reference filename: {filename}"
            )

        used_filenames.add(filename)

        target = references_dir / filename
        shutil.copy2(source, target)

        copied_sha256 = sha256_file(target)
        expected_sha256 = reference["fixture_sha256"]

        if copied_sha256 != expected_sha256:
            raise ValueError(
                "exported reference fixture SHA-256 mismatch: "
                f"{filename}"
            )

        exported.append(
            {
                "slot": slot,
                "role": reference["role"],
                "fixture_id": reference["fixture_id"],
                "fixture_version": reference[
                    "fixture_version"
                ],
                "fixture_sha256": expected_sha256,
                "file": f"references/{filename}",
            }
        )

    return exported

def export_host_package(
    run_file: str | Path,
    *,
    output: str | Path | None = None,
) -> dict:
    path, run = load_run(run_file)

    if run.get("generation_mode") not in {"host_native", "manual_import"}:
        raise ValueError(
            "host export requires generation_mode host_native or manual_import"
        )

    destination = (
        Path(output).expanduser().resolve()
        if output
        else path.parent / HOST_PACKAGE_DIRNAME
    )
    host_reference_inputs = _export_reference_inputs(destination, run)

    prompts_dir = destination / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)

    requires_receipt = receipt_required(run)
    receipts_dir = destination / "receipts"
    if requires_receipt:
        receipts_dir.mkdir(parents=True, exist_ok=True)

    tasks: list[dict] = []

    for variant in run["variants"]:
        for item in variant["outputs"]:
            blind_id = item["blind_id"]
            prompt_path = prompts_dir / f"{blind_id}.txt"
            prompt_path.write_text(
                variant["prompt"].rstrip() + "\n",
                encoding="utf-8",
            )

            commitment = task_commitment_sha256(run, variant, item)
            task = {
                "blind_id": blind_id,
                "status": item["status"],
                "prompt": variant["prompt"],
                "prompt_sha256": variant["prompt_sha256"],
                "task_commitment_sha256": commitment,
                "expected_filename": f"{blind_id}.png",
                "reference_inputs": host_reference_inputs,
                "settings": {
                    "size": run["settings"]["size"],
                    "quality": run["settings"]["quality"],
                    "background": run["settings"].get("background"),
                },
            }

            if requires_receipt:
                template_name = f"{blind_id}.receipt.template.json"
                template_path = receipts_dir / template_name
                template_path.write_text(
                    json.dumps(
                        receipt_template(run, variant, item),
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )
                task["receipt_template"] = f"receipts/{template_name}"

            tasks.append(task)

    tasks.sort(key=lambda task: task["blind_id"])

    manifest = {
        "run_id": run["run_id"],
        "experiment_id": run["experiment_id"],
        "experiment_version": run["experiment_version"],
        "generation_mode": run["generation_mode"],
        "model_target": run["model"],
        "model_snapshot": run["model_snapshot"],
        "task_commitment_schema_version": "1.0.0",
        "receipt_required": requires_receipt,
        "reference_inputs": host_reference_inputs,
        "task_count": len(tasks),
        "tasks": tasks,
    }

    _write_json_atomic(destination / "manifest.json", manifest)

    if requires_receipt:
        import_command = (
            "aipf experiment-import <run.json> --blind-id <ID> "
            "--image <image-file> --receipt <receipt-json>"
        )
        provenance_section = (
            "This run requires one provenance receipt per sample. Perform "
            "exactly one host invocation per blind ID, produce exactly one "
            "image, record the host generation ID and timestamp, hash the "
            "final image, and complete that blind ID's receipt template.\n"
        )
    else:
        import_command = (
            "aipf experiment-import <run.json> --blind-id <ID> "
            "--image <image-file>"
        )
        provenance_section = ""

    readme = (
        "# AIPF Host-Native Experiment Package\n\n"
        f"Run: `{run['run_id']}`\n"
        f"Experiment: `{run['experiment_id']}`\n"
        f"Tasks: `{len(tasks)}`\n"
        f"Receipt required: `{str(requires_receipt).lower()}`\n\n"
        "Generate exactly one image for each blind ID using its associated "
        "prompt and settings. When reference inputs are present, attach "
        "exactly the listed files in their declared order. Do not rename or "
        "merge blind IDs.\n\n"
        "The package intentionally omits treatment labels. The private run "
        "retains the control/variant mapping.\n\n"
        f"{provenance_section}\n"
        "After generation, import each result with:\n\n"
        "```text\n"
        f"{import_command}\n"
        "```\n"
    )
    (destination / "README.md").write_text(readme, encoding="utf-8")

    return {
        "run_id": run["run_id"],
        "task_count": len(tasks),
        "reference_count": len(host_reference_inputs),
        "receipt_required": requires_receipt,
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
    receipt: str | Path | None = None,
    overwrite: bool = False,
) -> dict:
    path, run = load_run(run_file)
    source = Path(image).expanduser().resolve()

    if not source.is_file():
        raise FileNotFoundError(source)

    variant, output = _find_output(run, blind_id)

    if output.get("status") == "generated" and not overwrite:
        raise ValueError(
            f"blind_id {output['blind_id']} already has a generated output; "
            "use overwrite=True to replace it"
        )

    effective_model = model or run.get("model") or "unknown"
    effective_snapshot = (
        model_snapshot or run.get("model_snapshot") or "unknown"
    )
    source_image_sha256 = sha256_file(source)

    receipt_source = None
    receipt_payload = None
    receipt_sha256 = None

    if receipt_required(run) and receipt is None:
        raise ValueError(
            "this run requires an execution receipt for every imported sample"
        )

    if receipt is not None:
        receipt_source, receipt_payload, receipt_sha256 = (
            validate_execution_receipt(
                receipt=receipt,
                run=run,
                variant=variant,
                output=output,
                image_sha256=source_image_sha256,
                provider=provider,
                model=effective_model,
                model_snapshot=effective_snapshot,
            )
        )

    suffix = source.suffix.lower() or ".png"
    outputs_dir = path.parent / OUTPUTS_DIRNAME
    outputs_dir.mkdir(parents=True, exist_ok=True)

    image_name = f"{output['blind_id']}{suffix}"
    metadata_name = f"{output['blind_id']}.json"
    image_path = outputs_dir / image_name
    metadata_path = outputs_dir / metadata_name

    shutil.copy2(source, image_path)
    image_hash = sha256_file(image_path)
    if image_hash != source_image_sha256:
        raise ValueError("imported image SHA-256 changed during copy")

    commitment = task_commitment_sha256(run, variant, output)

    receipt_name = None
    host_generation_id = None
    generated_at_utc = None

    if receipt_payload is not None:
        receipt_name = f"{output['blind_id']}.receipt.json"
        receipt_target = outputs_dir / receipt_name
        if receipt_source != receipt_target.resolve():
            shutil.copy2(receipt_source, receipt_target)
        if sha256_file(receipt_target) != receipt_sha256:
            raise ValueError(
                "execution receipt SHA-256 changed during copy"
            )
        host_generation_id = str(
            receipt_payload["invocation"]["host_generation_id"]
        ).strip()
        generated_at_utc = str(
            receipt_payload["invocation"]["generated_at_utc"]
        ).strip()

    metadata = {
        "run_id": run["run_id"],
        "experiment_id": run["experiment_id"],
        "blind_id": output["blind_id"],
        "replicate": output["replicate"],
        "generation_mode": run.get("generation_mode", "manual_import"),
        "provider": provider,
        "model": effective_model,
        "model_snapshot": effective_snapshot,
        "size": run["settings"]["size"],
        "quality": run["settings"]["quality"],
        "prompt_sha256": variant["prompt_sha256"],
        "task_commitment_sha256": commitment,
        "reference_inputs": normalized_reference_inputs(run),
        "imported_at_utc": _utc_now(),
        "source_image_name": source.name,
        "image_sha256": image_hash,
        "notes": notes,
    }

    if receipt_payload is not None:
        metadata.update(
            {
                "receipt": receipt_name,
                "receipt_sha256": receipt_sha256,
                "host_generation_id": host_generation_id,
                "generated_at_utc": generated_at_utc,
            }
        )

    _write_json_atomic(metadata_path, metadata)

    output["status"] = "generated"
    output["image"] = image_name
    output["image_sha256"] = image_hash
    output["metadata"] = metadata_name
    output["error"] = None
    output["task_commitment_sha256"] = commitment

    for key in (
        "receipt",
        "receipt_sha256",
        "host_generation_id",
        "generated_at_utc",
    ):
        output.pop(key, None)

    if receipt_payload is not None:
        output["receipt"] = receipt_name
        output["receipt_sha256"] = receipt_sha256
        output["host_generation_id"] = host_generation_id
        output["generated_at_utc"] = generated_at_utc

    status = _refresh_run_status(run)
    _write_json_atomic(path, run)

    result = {
        "run_id": run["run_id"],
        "blind_id": output["blind_id"],
        "image": str(image_path),
        "image_sha256": image_hash,
        "task_commitment_sha256": commitment,
        "status": status,
    }

    if receipt_payload is not None:
        result.update(
            {
                "receipt": str(outputs_dir / receipt_name),
                "receipt_sha256": receipt_sha256,
                "host_generation_id": host_generation_id,
            }
        )

    return result



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



def experiment_status(run_file: str | Path) -> dict:
    """Return a reviewer-safe run summary without treatment mapping."""
    _path, run = load_run(run_file)
    outputs = [
        output
        for variant in run.get("variants", [])
        for output in variant.get("outputs", [])
    ]

    counts = {
        state: sum(output.get("status") == state for output in outputs)
        for state in ("planned", "generated", "failed")
    }

    return {
        "run_id": run["run_id"],
        "experiment_id": run["experiment_id"],
        "status": run.get("status", "planned"),
        "generation_mode": run.get("generation_mode"),
        "total": len(outputs),
        **counts,
        "outputs": [
            {
                "blind_id": output["blind_id"],
                "status": output.get("status", "planned"),
                "image": output.get("image"),
                "image_sha256": output.get("image_sha256"),
            }
            for output in sorted(outputs, key=lambda item: item["blind_id"])
        ],
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
    outputs_dir = root / OUTPUTS_DIRNAME
    outputs_dir.mkdir(parents=True, exist_ok=True)
    generated = 0
    failed = 0
    skipped = 0
    attempted = 0
    run["status"] = "running"
    _write_json_atomic(path, run)

    for variant in run["variants"]:
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
            image_path = outputs_dir / image_name
            metadata_path = outputs_dir / metadata_name

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
