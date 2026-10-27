#!/usr/bin/env python3
"""Explicit GPT Image 2 API executor with reproducibility metadata.

Compilation is separate from execution. Without --execute this script performs a dry run.
No unsupported seed or hidden parameter is invented.

Dry-run and SDK execution share the same normalized request representation from
aipf.model_adapter. Verified execution targets for this PR are only:
  - gpt-image-2
  - gpt-image-2-2026-04-21
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from aipf.model_adapter import (
    AdapterContractError,
    build_generation_metadata,
    materialize_sdk_kwargs,
    normalize_request,
    persist_api_result,
)


def read_prompt(args) -> str:
    # strip() preserved for backward-compatible CLI whitespace semantics;
    # normalize_request also strips so both paths stay consistent.
    if args.prompt_file:
        return Path(args.prompt_file).read_text(encoding="utf-8").strip()
    if args.prompt:
        return args.prompt.strip()
    raise SystemExit("Provide --prompt or --prompt-file")


def _snapshot_was_explicit(argv: list[str]) -> bool:
    return any(
        t == "--model-snapshot" or t.startswith("--model-snapshot=")
        for t in argv
    )


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="GPT Image 2 dry-run / execute helper (no network unless --execute)."
    )
    ap.add_argument("--prompt")
    ap.add_argument("--prompt-file")
    ap.add_argument(
        "--image",
        action="append",
        help="Reference image path; one or more switches API call to edit mode",
    )
    ap.add_argument(
        "--model",
        default=os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2"),
        help="Verified execution model id: gpt-image-2 or gpt-image-2-2026-04-21",
    )
    # Default remains the historical snapshot label for CLI compatibility.
    # Provenance marks a snapshot as declared only when --model-snapshot appears
    # on the argv (see _snapshot_was_explicit). An env/default label alone is not
    # an explicit declaration and is never treated as provider-verified.
    ap.add_argument(
        "--model-snapshot",
        default=os.getenv("OPENAI_IMAGE_MODEL_SNAPSHOT", "gpt-image-2-2026-04-21"),
        help=(
            "Optional snapshot label for provenance. A silent CLI/env default "
            "must not invent dated-snapshot verification for alias requests."
        ),
    )
    ap.add_argument("--size", default="auto")
    ap.add_argument(
        "--quality",
        choices=["low", "medium", "high", "auto"],
        default="auto",
    )
    ap.add_argument("--background", choices=["transparent", "opaque", "auto"])
    ap.add_argument("--output", default="aipf-output.png")
    ap.add_argument(
        "--prompt-profile",
        choices=["compact", "standard", "extended"],
        default="standard",
    )
    ap.add_argument("--compiler-version", default="3.2.0")
    ap.add_argument("--metadata-output", help="Write generation/dry-run metadata JSON")
    ap.add_argument(
        "--execute",
        action="store_true",
        help="Actually call the API. Omit for dry-run payload inspection.",
    )
    return ap


def _write_metadata_file(path: str | None, metadata: dict) -> None:
    if not path:
        return
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    args = build_parser().parse_args(argv)
    prompt = read_prompt(args)
    # Only an explicit --model-snapshot CLI flag counts as a declared snapshot.
    # Env/default labels must not make alias requests look dated-snapshot-verified.
    snapshot_explicit = _snapshot_was_explicit(argv)

    try:
        req = normalize_request(
            prompt=prompt,
            model=args.model,
            model_snapshot=args.model_snapshot,
            size=args.size,
            quality=args.quality,
            background=args.background,
            images=args.image,
            execute=bool(args.execute),
            snapshot_explicit=snapshot_explicit,
        )
    except AdapterContractError as exc:
        raise SystemExit(str(exc)) from exc

    payload = {
        "mode": req["mode"],
        "model": req["execution_model_id"],
        "model_snapshot": req["declared_model_snapshot"],
        "prompt": req["prompt"],
        "size": req["size"],
        "quality": req["quality"],
        "sdk_params": dict(req["effective_request"]),
    }
    if req.get("background") is not None:
        payload["background"] = req["background"]
    if req["image_paths"]:
        payload["images"] = list(req["image_paths"])

    if not args.execute:
        metadata = build_generation_metadata(
            req,
            prompt_profile=args.prompt_profile,
            compiler_version=args.compiler_version,
        )
        _write_metadata_file(args.metadata_output, metadata)
        print(json.dumps({"dry_run": True, **payload, "metadata": metadata}, ensure_ascii=False, indent=2))
        return

    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is required with --execute")
    try:
        from openai import OpenAI
    except ImportError as e:
        raise SystemExit("Install API support with: pip install -e .[api]") from e

    client = OpenAI()
    try:
        kwargs, handles = materialize_sdk_kwargs(req)
    except OSError as exc:
        raise SystemExit(f"reference image unreadable: {exc}") from exc
    try:
        if req["mode"] == "edit":
            result = client.images.edit(**kwargs)
        else:
            result = client.images.generate(**kwargs)
    finally:
        for handle in handles:
            handle.close()

    try:
        result_meta = persist_api_result(result, Path(args.output))
    except AdapterContractError as exc:
        raise SystemExit(str(exc)) from exc

    generation_completed = bool(result_meta.get("generation_completed"))
    metadata = build_generation_metadata(
        req,
        prompt_profile=args.prompt_profile,
        compiler_version=args.compiler_version,
        result_meta=result_meta,
        provider_verified_model_id=None,
    )
    _write_metadata_file(args.metadata_output, metadata)
    if not generation_completed:
        raise SystemExit(
            json.dumps(
                {
                    "error": "generation_incomplete",
                    "result": result_meta,
                    "metadata": metadata,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    print(json.dumps({"result": result_meta, "metadata": metadata}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
