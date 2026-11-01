"""ESR-v0.1 operational package → freeze → verify → reveal lifecycle.

Exploratory owner self-review only. Does not call ``experiment_review`` or
``exp019_review`` scientific paths. Local hashes are integrity checks for the
owner-controlled session directory, not external custody.
"""
from __future__ import annotations

import hashlib
import json
import secrets
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .esr_images import EsrImageError, sanitize_to_metadata_free_png
from .experiment_runs import sha256_file
from .io import load_json
from .resources import source_checkout_root

SESSION_NAME = "session.json"
PACKAGE_DIRNAME = "package"
PRIVATE_DIRNAME = "private"
ORIGINALS_DIRNAME = "originals"
IMAGES_DIRNAME = "images"
MAPPING_NAME = "mapping.json"
MANIFEST_NAME = "manifest.json"
REVIEW_DRAFT_NAME = "review.json"
TASK_BRIEF_NAME = "task_brief.json"
FROZEN_REVIEW_NAME = "review.frozen.json"
FREEZE_SEAL_NAME = "review.freeze.json"
REVEAL_NAME = "reveal.json"

REVIEW_ID_LENGTH = 8
REVIEW_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

SCHEMA_REL = "data/schemas/esr_review.schema.json"


class EsrError(ValueError):
    """ESR lifecycle contract failure."""


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
    ) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temp_path = Path(handle.name)
    temp_path.replace(path)


def canonical_sha256(payload: dict) -> str:
    """V3.3-compatible canonical JSON SHA-256."""
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def task_brief_sha256(brief: dict) -> str:
    """Digest brief content excluding any embedded ``task_brief_sha256`` field."""
    core = {k: v for k, v in brief.items() if k != "task_brief_sha256"}
    return canonical_sha256(core)


def _new_review_id(used: set[str]) -> str:
    while True:
        review_id = "R" + "".join(
            secrets.choice(REVIEW_ALPHABET) for _ in range(REVIEW_ID_LENGTH - 1)
        )
        if review_id not in used:
            used.add(review_id)
            return review_id


def _session_dir(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def _assert_safe_session_location(session: Path) -> None:
    checkout = source_checkout_root()
    if checkout is None:
        return
    try:
        session.relative_to(checkout.resolve())
    except ValueError:
        return
    raise EsrError(
        f"ESR session directory must not be inside the repository checkout "
        f"({checkout}). Use a path outside the repo (for example under a "
        f"private evals workspace)."
    )


def _load_session(session: Path) -> dict:
    path = session / SESSION_NAME
    if not path.is_file():
        raise EsrError(f"missing session manifest: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise EsrError("session.json must be a JSON object")
    return data


def _resolve_image_path(session: Path, raw: str) -> Path:
    p = Path(raw)
    if not p.is_absolute():
        p = (session / p).resolve()
    else:
        p = p.resolve()
    if not p.is_file():
        raise EsrError(f"candidate image missing: {raw}")
    return p


def _score_placeholder(transform_in_scope: bool) -> dict:
    scores = {
        "task_brief_adherence": {"value": None, "na_reason": None},
        "visual_coherence": {"value": None, "na_reason": None},
        "target_style_fidelity": {"value": None, "na_reason": None},
        "technical_cleanliness": {"value": None, "na_reason": None},
        "prompt_repeatability": {
            "value": None,
            "na_reason": "deferred_protocol_v0_1",
        },
    }
    if transform_in_scope:
        scores["transformation_fidelity"] = {"value": None, "na_reason": None}
    else:
        scores["transformation_fidelity"] = {
            "value": None,
            "na_reason": "not_applicable_to_task",
        }
    return scores


def _build_task_brief_doc(session_data: dict) -> dict:
    raw = session_data.get("task_brief")
    if not isinstance(raw, dict):
        raise EsrError("session.task_brief must be an object")
    transform = bool(session_data.get("transformation_in_scope"))
    brief: dict[str, Any] = {
        "text": raw.get("text"),
        "style_target": raw.get("style_target"),
    }
    if not isinstance(brief["text"], str) or not brief["text"].strip():
        raise EsrError("task_brief.text is required")
    if not isinstance(brief["style_target"], str) or not brief["style_target"].strip():
        raise EsrError("task_brief.style_target is required")
    if transform:
        target = raw.get("transformation_target")
        if not isinstance(target, str) or not target.strip():
            raise EsrError(
                "task_brief.transformation_target is required when "
                "transformation_in_scope is true"
            )
        brief["transformation_target"] = target
    digest = task_brief_sha256(brief)
    return {**brief, "task_brief_sha256": digest}


def _private_fields_forbidden(obj: Any, path: str = "") -> None:
    forbidden = {
        "candidate_id",
        "prompt_text",
        "prompt_sha256",
        "prompt_ref",
        "source_path",
        "treatment",
        "variant_id",
        "blind_id",
    }
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in forbidden:
                raise EsrError(
                    f"reviewer-facing artifact must not contain private field "
                    f"{key!r} at {path or '/'}"
                )
            _private_fields_forbidden(value, f"{path}/{key}")
    elif isinstance(obj, list):
        for i, value in enumerate(obj):
            _private_fields_forbidden(value, f"{path}[{i}]")


def package_session(session_dir: str | Path) -> dict:
    """Build reviewer package + private mapping from a manual session manifest."""
    session = _session_dir(session_dir)
    _assert_safe_session_location(session)
    data = _load_session(session)

    package_dir = session / PACKAGE_DIRNAME
    private_dir = session / PRIVATE_DIRNAME
    if package_dir.exists() or private_dir.exists():
        raise EsrError(
            "package/ or private/ already exists; refuse to overwrite. "
            "Use a fresh session directory for a new package."
        )
    if (session / FROZEN_REVIEW_NAME).exists() or (session / FREEZE_SEAL_NAME).exists():
        raise EsrError("session already has freeze artifacts")

    candidates = data.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise EsrError("session.candidates must be a non-empty array")
    transform = bool(data.get("transformation_in_scope"))
    task_brief = _build_task_brief_doc(data)
    session_id = data.get("session_id") or session.name

    inclusions = data.get("inclusions")
    if inclusions is not None and not isinstance(inclusions, list):
        raise EsrError("session.inclusions must be an array when present")
    exclusions = data.get("exclusions")
    if exclusions is not None and not isinstance(exclusions, list):
        raise EsrError("session.exclusions must be an array when present")

    used: set[str] = set()
    mapping_entries: list[dict] = []
    review_items: list[dict] = []
    manifest_items: list[dict] = []

    originals = session / ORIGINALS_DIRNAME
    originals.mkdir(parents=True, exist_ok=True)
    images_dir = package_dir / IMAGES_DIRNAME
    # Build into a temp package tree then move atomically-ish
    staging = session / f".package-staging-{secrets.token_hex(4)}"
    staging_images = staging / IMAGES_DIRNAME
    staging_images.mkdir(parents=True)

    try:
        for index, cand in enumerate(candidates):
            if not isinstance(cand, dict):
                raise EsrError(f"candidates[{index}] must be an object")
            candidate_id = cand.get("candidate_id")
            if not isinstance(candidate_id, str) or not candidate_id.strip():
                raise EsrError(f"candidates[{index}].candidate_id is required")
            image_path = cand.get("image_path")
            if not isinstance(image_path, str) or not image_path.strip():
                raise EsrError(f"candidates[{index}].image_path is required")
            source = _resolve_image_path(session, image_path)
            source_sha = sha256_file(source)

            prompt_text = cand.get("prompt_text")
            prompt_ref = cand.get("prompt_ref")
            prompt_sha = cand.get("prompt_sha256")
            if isinstance(prompt_text, str) and prompt_text:
                prompt_sha = hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()
            elif isinstance(prompt_ref, dict):
                ref_path = prompt_ref.get("path")
                ref_sha = prompt_ref.get("sha256")
                if not isinstance(ref_path, str) or not isinstance(ref_sha, str):
                    raise EsrError(
                        f"candidates[{index}].prompt_ref requires path and sha256"
                    )
                p = Path(ref_path)
                if not p.is_absolute():
                    p = (session / p).resolve()
                else:
                    p = p.resolve()
                if not p.is_file():
                    raise EsrError(f"prompt_ref path missing: {ref_path}")
                actual = sha256_file(p)
                if actual != ref_sha:
                    raise EsrError(
                        f"prompt_ref sha256 mismatch for {ref_path}: "
                        f"expected {ref_sha}, got {actual}"
                    )
                prompt_text = p.read_text(encoding="utf-8")
                prompt_sha = actual
            else:
                raise EsrError(
                    f"candidates[{index}] must provide prompt_text or "
                    f"verified prompt_ref"
                )

            review_id = _new_review_id(used)
            try:
                png_bytes = sanitize_to_metadata_free_png(source)
            except EsrImageError as exc:
                raise EsrError(str(exc)) from exc

            # Preserve original bytes under opaque name (not candidate id).
            original_name = f"{review_id}.source{source.suffix.lower() or '.bin'}"
            original_dest = originals / original_name
            shutil.copy2(source, original_dest)
            if sha256_file(original_dest) != source_sha:
                raise EsrError("failed to preserve original image bytes")

            review_name = f"{review_id}.png"
            review_path = staging_images / review_name
            review_path.write_bytes(png_bytes)
            review_sha = sha256_file(review_path)

            mapping_entries.append(
                {
                    "review_id": review_id,
                    "candidate_id": candidate_id,
                    "prompt_text": prompt_text,
                    "prompt_sha256": prompt_sha,
                    "source_image_sha256": source_sha,
                    "review_image_sha256": review_sha,
                    "review_image": review_name,
                    "original_image": original_name,
                }
            )
            review_items.append(
                {
                    "review_id": review_id,
                    "scores": _score_placeholder(transform),
                    "recognized_image_or_treatment": "none",
                    "notes": "",
                }
            )
            manifest_items.append({"review_id": review_id, "image": review_name})

        mapping_entries.sort(key=lambda e: e["review_id"])
        review_items.sort(key=lambda e: e["review_id"])
        manifest_items.sort(key=lambda e: e["review_id"])
        presentation_order = [e["review_id"] for e in mapping_entries]

        mapping_core = {
            "session_id": session_id,
            "entries": [
                {
                    "review_id": e["review_id"],
                    "candidate_id": e["candidate_id"],
                    "prompt_sha256": e["prompt_sha256"],
                    "source_image_sha256": e["source_image_sha256"],
                    "review_image_sha256": e["review_image_sha256"],
                    "review_image": e["review_image"],
                }
                for e in mapping_entries
            ],
        }
        mapping_commitment = canonical_sha256(mapping_core)

        # Full private mapping retains prompt_text for owner custody.
        private_mapping = {
            "session_id": session_id,
            "mapping_commitment_sha256": mapping_commitment,
            "entries": mapping_entries,
            "inclusions": inclusions,
            "exclusions": exclusions,
            "model": data.get("model"),
            "settings": data.get("settings"),
            "planned_generation_count": data.get("planned_generation_count"),
        }

        review_draft = {
            "protocol_version": "ESR-v0.1",
            "rubric_version": "ESR-IQ-v0.1",
            "scientific_status": "exploratory",
            "evaluator_identity_class": "owner_self_review",
            "independent_reviewer": False,
            "blindness_claim": "partial_anonymization_only",
            "transformation_in_scope": transform,
            "task_brief": task_brief,
            "presentation_order": presentation_order,
            "items": review_items,
            "status": "open",
            "contamination_status": data.get("contamination_status", "clean"),
            "deviations": list(data.get("deviations") or []),
        }

        manifest_core = {
            "session_id": session_id,
            "created_at_utc": _utc_now(),
            "mapping_commitment_sha256": mapping_commitment,
            "task_brief_sha256": task_brief["task_brief_sha256"],
            "presentation_order": presentation_order,
            "items": manifest_items,
            "transformation_in_scope": transform,
        }
        package_sha = canonical_sha256(manifest_core)
        manifest = {**manifest_core, "review_package_sha256": package_sha}
        private_mapping["review_package_sha256"] = package_sha

        _private_fields_forbidden(manifest)
        _private_fields_forbidden(
            {k: v for k, v in review_draft.items() if k != "items"}
        )
        for item in review_draft["items"]:
            _private_fields_forbidden(item)

        # Promote staging → package/
        staging.rename(package_dir)
        _write_json_atomic(package_dir / TASK_BRIEF_NAME, task_brief)
        _write_json_atomic(package_dir / REVIEW_DRAFT_NAME, review_draft)
        _write_json_atomic(package_dir / MANIFEST_NAME, manifest)
        private_dir.mkdir(parents=True, exist_ok=True)
        _write_json_atomic(private_dir / MAPPING_NAME, private_mapping)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        if package_dir.exists() and not (package_dir / MANIFEST_NAME).is_file():
            shutil.rmtree(package_dir, ignore_errors=True)
        raise

    return {
        "session_id": session_id,
        "status": "packaged",
        "review_count": len(mapping_entries),
        "mapping_commitment_sha256": mapping_commitment,
        "review_package_sha256": package_sha,
        "task_brief_sha256": task_brief["task_brief_sha256"],
        "package": str(package_dir),
    }


def _load_json(path: Path) -> dict:
    if not path.is_file():
        raise EsrError(f"missing required file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _bijection_ok(review: dict) -> None:
    order = review.get("presentation_order")
    items = review.get("items")
    if not isinstance(order, list) or not isinstance(items, list):
        raise EsrError("presentation_order and items are required")
    ids = [it.get("review_id") for it in items]
    if any(not isinstance(i, str) for i in ids):
        raise EsrError("every item requires review_id")
    if len(ids) != len(set(ids)):
        raise EsrError("duplicate review_id in items")
    if len(order) != len(set(order)):
        raise EsrError("duplicate review_id in presentation_order")
    if set(order) != set(ids) or len(order) != len(ids):
        raise EsrError("items and presentation_order are not a bijection")


def _validate_frozen_schema(review: dict) -> None:
    schema = load_json(SCHEMA_REL)
    errors = list(Draft202012Validator(schema).iter_errors(review))
    if errors:
        messages = "; ".join(e.message for e in errors[:5])
        raise EsrError(f"frozen review failed esr_review.schema.json: {messages}")


def _verify_package_bindings(session: Path, mapping: dict, manifest: dict) -> None:
    mapping_core = {
        "session_id": mapping["session_id"],
        "entries": [
            {
                "review_id": e["review_id"],
                "candidate_id": e["candidate_id"],
                "prompt_sha256": e["prompt_sha256"],
                "source_image_sha256": e["source_image_sha256"],
                "review_image_sha256": e["review_image_sha256"],
                "review_image": e["review_image"],
            }
            for e in mapping["entries"]
        ],
    }
    actual_commit = canonical_sha256(mapping_core)
    if actual_commit != mapping.get("mapping_commitment_sha256"):
        raise EsrError("private mapping commitment mismatch")
    if actual_commit != manifest.get("mapping_commitment_sha256"):
        raise EsrError("manifest mapping commitment mismatch")

    manifest_core = {
        k: manifest[k]
        for k in (
            "session_id",
            "created_at_utc",
            "mapping_commitment_sha256",
            "task_brief_sha256",
            "presentation_order",
            "items",
            "transformation_in_scope",
        )
    }
    if canonical_sha256(manifest_core) != manifest.get("review_package_sha256"):
        raise EsrError("review package commitment mismatch")
    if mapping.get("review_package_sha256") != manifest.get("review_package_sha256"):
        raise EsrError("mapping/package commitment disagreement")

    images_dir = session / PACKAGE_DIRNAME / IMAGES_DIRNAME
    for entry in mapping["entries"]:
        image_path = images_dir / entry["review_image"]
        if not image_path.is_file():
            raise EsrError(f"missing reviewer image: {entry['review_image']}")
        if sha256_file(image_path) != entry["review_image_sha256"]:
            raise EsrError(
                f"reviewer image digest mismatch for {entry['review_id']}"
            )


def freeze_session(session_dir: str | Path) -> dict:
    """Validate completed draft and write write-once frozen + seal artifacts."""
    session = _session_dir(session_dir)
    frozen_path = session / FROZEN_REVIEW_NAME
    seal_path = session / FREEZE_SEAL_NAME
    if frozen_path.exists() or seal_path.exists():
        raise EsrError("freeze artifacts already exist; refuse overwrite")

    draft_path = session / PACKAGE_DIRNAME / REVIEW_DRAFT_NAME
    manifest_path = session / PACKAGE_DIRNAME / MANIFEST_NAME
    mapping_path = session / PRIVATE_DIRNAME / MAPPING_NAME
    draft = _load_json(draft_path)
    manifest = _load_json(manifest_path)
    mapping = _load_json(mapping_path)

    _verify_package_bindings(session, mapping, manifest)

    brief = draft.get("task_brief")
    if not isinstance(brief, dict):
        raise EsrError("draft missing task_brief")
    expected_brief = task_brief_sha256(brief)
    if brief.get("task_brief_sha256") != expected_brief:
        raise EsrError("task_brief_sha256 does not match brief content")
    if expected_brief != manifest.get("task_brief_sha256"):
        raise EsrError("task brief digest disagrees with package manifest")

    _bijection_ok(draft)
    if draft.get("presentation_order") != manifest.get("presentation_order"):
        raise EsrError("draft presentation_order disagrees with manifest")

    contamination = draft.get("contamination_status", "clean")
    if contamination not in {"clean", "contaminated_pilot"}:
        raise EsrError("invalid contamination_status")
    if "deviations" in draft and not isinstance(draft["deviations"], list):
        raise EsrError("deviations must be an array")

    frozen = dict(draft)
    frozen["status"] = "frozen"
    _validate_frozen_schema(frozen)
    # Ensure recognition recorded (schema requires enum on each item).
    for item in frozen["items"]:
        if item.get("recognized_image_or_treatment") not in {
            "none",
            "suspected",
            "certain",
        }:
            raise EsrError("recognized_image_or_treatment required on every item")

    review_sha = canonical_sha256(frozen)
    seal = {
        "session_id": mapping["session_id"],
        "review_sha256": review_sha,
        "mapping_commitment_sha256": mapping["mapping_commitment_sha256"],
        "review_package_sha256": manifest["review_package_sha256"],
        "task_brief_sha256": expected_brief,
        "frozen_at_utc": _utc_now(),
        "contamination_status": contamination,
        "comparative_claims_eligible": contamination == "clean",
    }

    # Write frozen first, then seal. Incomplete pairs fail verify/reveal.
    _write_json_atomic(frozen_path, frozen)
    _write_json_atomic(seal_path, seal)
    return {
        "session_id": seal["session_id"],
        "status": "frozen",
        "review_sha256": review_sha,
        "comparative_claims_eligible": seal["comparative_claims_eligible"],
        "frozen": str(frozen_path),
        "seal": str(seal_path),
    }


def verify_session(session_dir: str | Path) -> dict:
    """Recompute commitments; never repair altered evidence."""
    session = _session_dir(session_dir)
    frozen_path = session / FROZEN_REVIEW_NAME
    seal_path = session / FREEZE_SEAL_NAME
    if not frozen_path.is_file() or not seal_path.is_file():
        raise EsrError(
            "incomplete freeze artifacts: both review.frozen.json and "
            "review.freeze.json are required"
        )

    frozen = _load_json(frozen_path)
    seal = _load_json(seal_path)
    manifest = _load_json(session / PACKAGE_DIRNAME / MANIFEST_NAME)
    mapping = _load_json(session / PRIVATE_DIRNAME / MAPPING_NAME)

    if frozen.get("status") != "frozen":
        raise EsrError("review.frozen.json status must be 'frozen'")
    _validate_frozen_schema(frozen)
    _bijection_ok(frozen)
    _verify_package_bindings(session, mapping, manifest)

    brief = frozen["task_brief"]
    brief_digest = task_brief_sha256(brief)
    if brief.get("task_brief_sha256") != brief_digest:
        raise EsrError("frozen task_brief_sha256 mismatch")
    if brief_digest != seal.get("task_brief_sha256"):
        raise EsrError("seal task_brief_sha256 mismatch")

    actual_review_sha = canonical_sha256(frozen)
    if actual_review_sha != seal.get("review_sha256"):
        raise EsrError("frozen review digest does not match review.freeze.json seal")
    if seal.get("mapping_commitment_sha256") != mapping.get("mapping_commitment_sha256"):
        raise EsrError("seal mapping commitment mismatch")
    if seal.get("review_package_sha256") != manifest.get("review_package_sha256"):
        raise EsrError("seal package commitment mismatch")

    return {
        "session_id": seal.get("session_id"),
        "status": "verified",
        "review_sha256": actual_review_sha,
        "comparative_claims_eligible": seal.get("comparative_claims_eligible"),
    }


def reveal_session(session_dir: str | Path) -> dict:
    """Reveal private mapping only after verified freeze seal."""
    session = _session_dir(session_dir)
    reveal_path = session / REVEAL_NAME
    if reveal_path.exists():
        raise EsrError("reveal.json already exists; refuse overwrite")

    verified = verify_session(session)
    mapping = _load_json(session / PRIVATE_DIRNAME / MAPPING_NAME)
    seal = _load_json(session / FREEZE_SEAL_NAME)

    reveal = {
        "session_id": mapping["session_id"],
        "revealed_at_utc": _utc_now(),
        "review_sha256": seal["review_sha256"],
        "mapping_commitment_sha256": seal["mapping_commitment_sha256"],
        "review_package_sha256": seal["review_package_sha256"],
        "contamination_status": seal.get("contamination_status"),
        "comparative_claims_eligible": seal.get("comparative_claims_eligible"),
        "scientific_status": "exploratory",
        "evaluator_identity_class": "owner_self_review",
        "items": [
            {
                "review_id": e["review_id"],
                "candidate_id": e["candidate_id"],
                "prompt_sha256": e["prompt_sha256"],
                "source_image_sha256": e["source_image_sha256"],
                "review_image_sha256": e["review_image_sha256"],
            }
            for e in mapping["entries"]
        ],
    }
    _write_json_atomic(reveal_path, reveal)
    return {
        **verified,
        "status": "revealed",
        "reveal": str(reveal_path),
    }
