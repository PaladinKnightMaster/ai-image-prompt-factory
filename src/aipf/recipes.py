"""Static, versioned PromptRecipe foundation (v1).

A recipe is a thin identity/revision wrapper around an existing semantic
specification. The V3.4 compiler remains the sole semantic authority:
recipes do not transform fields, choose packs, interpolate variables, or
post-process compiled prompts.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json

from jsonschema import Draft202012Validator

from .compiler import compile_result
from .io import load_json
from .linting import lint_spec

RECIPE_SCHEMA_PATH = "data/schemas/prompt_recipe.schema.json"
RECIPE_SCHEMA_VERSION = "1.0"


class RecipeError(ValueError):
    """Raised for unreadable or structurally unusable recipe inputs."""


class RecipeValidationError(RecipeError):
    """Raised when recipe compilation is blocked by validation errors."""

    def __init__(self, findings: list[dict]):
        self.findings = list(findings)
        messages = "; ".join(f["message"] for f in self.findings if f.get("level") == "error")
        super().__init__(messages or "recipe validation failed")


def canonical_json_bytes(obj) -> bytes:
    """Deterministic UTF-8 JSON bytes used for recipe and semantic hashes."""
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def sha256_canonical(obj) -> str:
    return sha256_bytes(canonical_json_bytes(obj))


def _finding(level: str, code: str, message: str) -> dict:
    return {"level": level, "code": code, "message": message}


def _recipe_schema() -> dict:
    return load_json(RECIPE_SCHEMA_PATH)


def load_recipe(path: str | Path) -> dict:
    """Load a recipe JSON file. Does not validate semantics or compile."""
    p = Path(path)
    try:
        text = p.read_text(encoding="utf-8")
    except OSError as exc:
        raise RecipeError(f"cannot read recipe file: {p}: {exc}") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RecipeError(f"invalid recipe JSON in {p}: {exc}") from exc
    if not isinstance(data, dict):
        raise RecipeError(f"recipe root must be a JSON object, got {type(data).__name__}")
    return data


def validate_recipe(recipe: dict) -> list[dict]:
    """Validate recipe envelope and embedded semantic_spec without compiling.

    Returns lint-style findings. Errors block compilation; warnings/info do not.
    Does not mutate ``recipe``.
    """
    if not isinstance(recipe, dict):
        return [_finding("error", "recipe_type", "recipe must be a JSON object")]

    out: list[dict] = []
    schema = _recipe_schema()
    for err in sorted(Draft202012Validator(schema).iter_errors(recipe), key=lambda e: list(e.path)):
        loc = ".".join(str(x) for x in err.path) or "$"
        out.append(_finding("error", "recipe_schema", f"{loc}: {err.message}"))

    version = recipe.get("recipe_schema_version")
    if version is not None and version != RECIPE_SCHEMA_VERSION and not any(
        f["code"] == "recipe_schema" and "recipe_schema_version" in f["message"] for f in out
    ):
        out.append(
            _finding(
                "error",
                "recipe_schema_version",
                f"unsupported recipe_schema_version {version!r}; expected {RECIPE_SCHEMA_VERSION!r}",
            )
        )

    spec = recipe.get("semantic_spec")
    if isinstance(spec, dict):
        out.extend(lint_spec(spec))
    elif "semantic_spec" in recipe and not any(f["code"] == "recipe_schema" for f in out):
        out.append(_finding("error", "recipe_schema", "semantic_spec: must be an object"))
    return out


def resolve_recipe(recipe: dict) -> dict:
    """Return a deep copy of the embedded semantic_spec (value-identical).

    Does not inject defaults, recipe metadata, or alter field values.
    """
    findings = validate_recipe(recipe)
    errors = [f for f in findings if f["level"] == "error"]
    if errors:
        raise RecipeValidationError(findings)
    return deepcopy(recipe["semantic_spec"])


def compile_recipe(recipe: dict) -> dict:
    """Compile via ``compile_result`` and return a deterministic receipt envelope.

    The compiler result is embedded unchanged under ``compilation``.
    """
    findings = validate_recipe(recipe)
    errors = [f for f in findings if f["level"] == "error"]
    if errors:
        raise RecipeValidationError(findings)

    # Hash the complete validated recipe object; do not mutate the caller input.
    recipe_sha = sha256_canonical(recipe)
    semantic_sha = sha256_canonical(recipe["semantic_spec"])
    resolved = deepcopy(recipe["semantic_spec"])
    compilation = compile_result(resolved)
    prompt = compilation["prompt"]
    return {
        "recipe": {
            "recipe_id": recipe["recipe_id"],
            "recipe_version": recipe["recipe_version"],
            "recipe_schema_version": recipe["recipe_schema_version"],
            "recipe_sha256": recipe_sha,
            "semantic_spec_sha256": semantic_sha,
        },
        "compilation": compilation,
        "prompt_sha256": sha256_bytes(prompt.encode("utf-8")),
        "compiler_version": compilation["compiler_version"],
        "evidence_snapshot_sha256": compilation["evidence_snapshot"]["snapshot_sha256"],
    }
