#!/usr/bin/env python3
"""Prepare / verify private creative recipe → generation provenance bundles.

Offline only. Does not call image providers. Live generation remains a separate
authorized use of scripts/generate_api.py.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from aipf.creative_provenance import (
    CreativeProvenanceError,
    import_chatgpt_web_manual,
    prepare_recipe_generation_bundle,
    verify_chatgpt_web_manual,
    verify_recipe_generation_bundle,
)
from aipf.recipes import load_bindings


def _dump(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def cmd_prepare(args: argparse.Namespace) -> int:
    bindings = None
    if args.bindings:
        bindings = load_bindings(args.bindings)
    try:
        result = prepare_recipe_generation_bundle(
            recipe_path=args.recipe,
            output_dir=args.output_dir,
            bindings=bindings,
            model=args.model,
            model_snapshot=args.model_snapshot,
            snapshot_explicit=args.model_snapshot_explicit,
            size=args.size,
            quality=args.quality,
            background=args.background,
            prompt_profile=args.prompt_profile,
            force=args.force,
        )
    except (CreativeProvenanceError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    _dump(
        {
            "ok": True,
            "stage_dir": result["stage_dir"],
            "prompt_sha256": result["prompt_sha256"],
            "evidence_level": result["manifest"]["evidence_level"],
            "manifest": result["manifest"],
        }
    )
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    try:
        report = verify_recipe_generation_bundle(
            args.bundle_dir,
            expect_recipe_id=args.expect_recipe_id,
            expect_recipe_version=args.expect_recipe_version,
            expect_recipe_sha256=args.expect_recipe_sha256,
            output_name=args.output_name,
        )
    except (CreativeProvenanceError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    _dump(report)
    return 0 if report.get("ok") else 1


def cmd_import_chatgpt_web(args: argparse.Namespace) -> int:
    try:
        result = import_chatgpt_web_manual(
            prep_dir=args.prep_dir,
            image_path=args.image,
            output_dir=args.output_dir,
            expect_image_sha256=args.expect_image_sha256.lower(),
            custody_path=args.custody,
            submitted_prompt_path=args.submitted_prompt,
            operator_attests_prompt_submission=args.operator_attests_prompt_submission,
            attestation_note=args.attestation_note,
            conversation_reference=args.conversation_reference,
            expect_recipe_id=args.expect_recipe_id,
            expect_recipe_version=args.expect_recipe_version,
            expect_recipe_sha256=args.expect_recipe_sha256,
        )
    except (CreativeProvenanceError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    _dump(
        {
            "ok": True,
            "stage_dir": result["stage_dir"],
            "evidence_level": result["evidence_level"],
            "image_sha256": result["image_sha256"],
            "manifest": result["manifest"],
        }
    )
    return 0


def cmd_verify_chatgpt_web(args: argparse.Namespace) -> int:
    try:
        report = verify_chatgpt_web_manual(args.bundle_dir)
    except (CreativeProvenanceError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    _dump(report)
    return 0 if report.get("ok") else 1


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description=(
            "Creative recipe provenance prepare/verify (no network). "
            "Does not execute image generation."
        )
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("prepare", help="Compile recipe and write private dry-run bundle")
    p.add_argument("recipe", help="Path to PromptRecipe JSON")
    p.add_argument(
        "--output-dir",
        required=True,
        help=(
            "Absolute staging directory, or relative under AIPF_CREATIVE_OUTPUT_PATH. "
            "Must not be under website/generated."
        ),
    )
    p.add_argument("--bindings", help="Optional v1.1 bindings JSON object")
    p.add_argument("--model", default="gpt-image-2")
    p.add_argument("--model-snapshot", default=None)
    p.add_argument(
        "--model-snapshot-explicit",
        action="store_true",
        help="Treat --model-snapshot as an explicit declaration",
    )
    p.add_argument("--size", default="auto")
    p.add_argument("--quality", choices=["low", "medium", "high", "auto"], default="auto")
    p.add_argument("--background", choices=["transparent", "opaque", "auto"])
    p.add_argument(
        "--prompt-profile",
        choices=["compact", "standard", "extended"],
        default="standard",
    )
    p.add_argument("--force", action="store_true", help="Allow overwriting bundle files")
    p.set_defaults(func=cmd_prepare)

    v = sub.add_parser("verify", help="Verify an existing private provenance bundle")
    v.add_argument("bundle_dir", help="Directory containing receipt.json / prompt.txt / generation.json")
    v.add_argument("--expect-recipe-id")
    v.add_argument("--expect-recipe-version")
    v.add_argument("--expect-recipe-sha256")
    v.add_argument("--output-name", default="output.png")
    v.set_defaults(func=cmd_verify)

    i = sub.add_parser(
        "import-chatgpt-web",
        help=(
            "Import a manually downloaded ChatGPT Images PNG into a private "
            "chatgpt_web_manual bundle (no network; no API transport claims)"
        ),
    )
    i.add_argument("--prep-dir", required=True, help="Existing preparation bundle directory")
    i.add_argument("--image", required=True, help="Absolute path to preserved original PNG")
    i.add_argument(
        "--output-dir",
        required=True,
        help=(
            "Absolute empty destination directory, or relative under "
            "AIPF_CREATIVE_OUTPUT_PATH. Must not be under website/generated."
        ),
    )
    i.add_argument(
        "--expect-image-sha256",
        required=True,
        help="Expected SHA-256 of the original PNG (64 hex)",
    )
    i.add_argument(
        "--custody",
        help="Optional custody text file declaring SHA256 of the download",
    )
    i.add_argument(
        "--submitted-prompt",
        help=(
            "Independently captured prompt bytes submitted to ChatGPT. "
            "Must exactly match preparation prompt.txt when provided."
        ),
    )
    i.add_argument(
        "--operator-attests-prompt-submission",
        action="store_true",
        help=(
            "Operator attestation that the ChatGPT submission matched the "
            "preparation prompt when no independent capture file exists"
        ),
    )
    i.add_argument(
        "--attestation-note",
        help="Optional note stored with operator prompt-submission attestation",
    )
    i.add_argument(
        "--conversation-reference",
        help="Optional ChatGPT conversation URL or id (not provider attestation)",
    )
    i.add_argument("--expect-recipe-id")
    i.add_argument("--expect-recipe-version")
    i.add_argument("--expect-recipe-sha256")
    i.set_defaults(func=cmd_import_chatgpt_web)

    vw = sub.add_parser(
        "verify-chatgpt-web",
        help="Verify a private chatgpt_web_manual import bundle",
    )
    vw.add_argument(
        "bundle_dir",
        help="Directory containing source.json / original.png / manifest.json",
    )
    vw.set_defaults(func=cmd_verify_chatgpt_web)
    return ap


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
