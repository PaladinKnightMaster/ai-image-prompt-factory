"""Static, versioned PromptRecipe foundation (v1.0 / v1.1).

A recipe is a thin identity/revision wrapper around an existing semantic
specification. The V3.4 compiler remains the sole semantic authority:
recipes do not choose packs, interpolate free-form templates, or
post-process compiled prompts.

v1.1 adds a closed set of constrained enum variables that may replace only
three authorized scalar destinations before compilation.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json
import re
import unicodedata

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from .compiler import compile_result
from .io import ResourceError, load_json
from .linting import lint_spec

RECIPE_SCHEMA_PATH_V10 = "data/schemas/prompt_recipe.schema.json"
RECIPE_SCHEMA_PATH_V11 = "data/schemas/prompt_recipe_v1_1.schema.json"
RECIPE_SCHEMA_VERSION_V10 = "1.0"
RECIPE_SCHEMA_VERSION_V11 = "1.1"

# Back-compat aliases used by older imports/tests.
RECIPE_SCHEMA_PATH = RECIPE_SCHEMA_PATH_V10
RECIPE_SCHEMA_VERSION = RECIPE_SCHEMA_VERSION_V10

_OMITTED = object()

_ALLOWED_TARGETS = frozenset(
    {
        "director.camera",
        "director.light_source",
        "output.aspect_ratio",
    }
)
_ASPECT_RATIO_VOCABULARY = frozenset({"1:1", "4:5"})
_VARIABLE_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_MAX_DIRECTOR_CHARS = 240
_MAX_DIRECTOR_UTF8_BYTES = 720
_DIAGNOSTIC_VALUE_LIMIT = 80
# C0/C1 controls, DEL, and common bidirectional controls.
_FORBIDDEN_UNICODE_RE = re.compile(
    r"[\x00-\x08\x0a-\x1f\x7f-\x9f\u202a-\u202e\u2066-\u2069\ufeff]"
)
_SUPPORTED_RECIPE_SCHEMA_VERSIONS = frozenset(
    {RECIPE_SCHEMA_VERSION_V10, RECIPE_SCHEMA_VERSION_V11}
)


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
    try:
        return sha256_bytes(canonical_json_bytes(obj))
    except UnicodeEncodeError as exc:
        raise RecipeError(
            "canonical serialization failed: value is not UTF-8 encodable"
        ) from exc


def _finding(level: str, code: str, message: str) -> dict:
    return {"level": level, "code": code, "message": message}


def _preview_value(value: str, *, limit: int = _DIAGNOSTIC_VALUE_LIMIT) -> str:
    """Bounded diagnostic preview; does not silently normalize the value."""
    if not isinstance(value, str):
        return repr(value)
    if len(value) <= limit:
        return repr(value)
    return repr(value[:limit] + "…") + f" (length {len(value)})"


def _reject_nonstandard_constant(value: str):
    raise ValueError(f"nonstandard JSON constant rejected: {value}")


def _object_pairs_no_duplicates(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate JSON key: {key!r}")
        out[key] = value
    return out


def _loads_strict_json(text: str, *, label: str):
    try:
        data = json.loads(
            text,
            object_pairs_hook=_object_pairs_no_duplicates,
            parse_constant=_reject_nonstandard_constant,
        )
    except ValueError as exc:
        raise RecipeError(f"invalid {label} JSON: {exc}") from exc
    return data


def _load_recipe_schema(version: str) -> dict:
    if not isinstance(version, str):
        raise RecipeError(
            f"unsupported recipe_schema_version type {type(version).__name__}"
        )
    if version == RECIPE_SCHEMA_VERSION_V10:
        path = RECIPE_SCHEMA_PATH_V10
    elif version == RECIPE_SCHEMA_VERSION_V11:
        path = RECIPE_SCHEMA_PATH_V11
    else:
        raise RecipeError(f"unsupported recipe_schema_version {version!r}")
    try:
        data = load_json(path)
    except ResourceError as exc:
        raise RecipeError(f"missing packaged schema: {path}: {exc}") from exc
    except FileNotFoundError as exc:
        raise RecipeError(f"missing packaged schema: {path}: {exc}") from exc
    except OSError as exc:
        raise RecipeError(f"unreadable packaged schema: {path}: {exc}") from exc
    except (ValueError, json.JSONDecodeError, TypeError, UnicodeError) as exc:
        raise RecipeError(f"malformed packaged schema: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise RecipeError(f"malformed packaged schema: {path}: root must be an object")
    try:
        Draft202012Validator.check_schema(data)
    except SchemaError as exc:
        raise RecipeError(f"invalid packaged schema definition: {path}: {exc}") from exc
    return data


def _recipe_schema() -> dict:
    """v1.0 schema loader retained for callers expecting the PR3 helper."""
    return _load_recipe_schema(RECIPE_SCHEMA_VERSION_V10)


def _read_text_utf8(path: Path, *, label: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise RecipeError(f"invalid UTF-8 in {label} file: {path}: {exc}") from exc
    except OSError as exc:
        raise RecipeError(f"cannot read {label} file: {path}: {exc}") from exc


def load_recipe(path: str | Path) -> dict:
    """Load a recipe JSON file. Does not validate semantics or compile."""
    p = Path(path)
    text = _read_text_utf8(p, label="recipe")
    data = _loads_strict_json(text, label=f"recipe in {p}")
    if not isinstance(data, dict):
        raise RecipeError(f"recipe root must be a JSON object, got {type(data).__name__}")
    return data


def load_bindings(path: str | Path) -> dict:
    """Load an invocation bindings JSON object."""
    p = Path(path)
    text = _read_text_utf8(p, label="bindings")
    data = _loads_strict_json(text, label=f"bindings in {p}")
    if not isinstance(data, dict):
        raise RecipeError(f"bindings root must be a JSON object, got {type(data).__name__}")
    return data


def _non_string_key_findings(obj: dict, *, path: str) -> list[dict]:
    """Small guard: reject non-string mapping keys without recursive validation."""
    out: list[dict] = []
    for key in obj:
        if not isinstance(key, str):
            out.append(
                _finding(
                    "error",
                    "recipe_key_type",
                    f"{path}: non-string key {key!r} ({type(key).__name__})",
                )
            )
    return out


def _target_parts(target: str) -> tuple[str, str]:
    section, field = target.split(".", 1)
    return section, field


def _read_target(spec: dict, target: str):
    section, field = _target_parts(target)
    container = spec.get(section)
    if not isinstance(container, dict) or field not in container:
        return None, False
    return container[field], True


def _write_target(spec: dict, target: str, value: str) -> None:
    section, field = _target_parts(target)
    spec[section][field] = value


def _director_value_ok(value: str) -> str | None:
    if not isinstance(value, str):
        return "value must be a string"
    try:
        if unicodedata.normalize("NFC", value) != value:
            return "value must be Unicode NFC"
    except (TypeError, ValueError) as exc:
        return f"value failed Unicode NFC check ({exc})"
    if _FORBIDDEN_UNICODE_RE.search(value) or "\r" in value or "\n" in value or "\t" in value:
        return "value contains forbidden control or bidirectional characters"
    if len(value) > _MAX_DIRECTOR_CHARS:
        return f"value exceeds {_MAX_DIRECTOR_CHARS} characters"
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError:
        return "value is not UTF-8 encodable"
    if len(encoded) > _MAX_DIRECTOR_UTF8_BYTES:
        return f"value exceeds {_MAX_DIRECTOR_UTF8_BYTES} UTF-8 bytes"
    return None


def _validate_variable_definitions(recipe: dict) -> list[dict]:
    out: list[dict] = []
    variables = recipe.get("variables")
    if variables is None:
        return out
    if not isinstance(variables, dict):
        return [_finding("error", "recipe_variables", "variables must be an object")]
    out.extend(_non_string_key_findings(variables, path="variables"))
    if any(f["code"] == "recipe_key_type" for f in out):
        return out
    if len(variables) > 3:
        out.append(_finding("error", "recipe_variables", "at most three variables are permitted"))

    owned: dict[str, str] = {}
    spec = recipe.get("semantic_spec")
    if not isinstance(spec, dict):
        return out

    for name, definition in variables.items():
        if not isinstance(name, str) or not _VARIABLE_NAME_RE.fullmatch(name):
            out.append(
                _finding(
                    "error",
                    "recipe_variable_name",
                    f"invalid variable name {name!r}; expected lowercase ASCII identifier",
                )
            )
            continue
        if not isinstance(definition, dict):
            out.append(_finding("error", "recipe_variable", f"variables.{name}: must be an object"))
            continue

        target = definition.get("target")
        choices = definition.get("choices")
        if not isinstance(target, str):
            out.append(
                _finding(
                    "error",
                    "recipe_variable_target",
                    f"variables.{name}: target must be a string, got {type(target).__name__}",
                )
            )
            continue
        if target not in _ALLOWED_TARGETS:
            out.append(
                _finding(
                    "error",
                    "recipe_variable_target",
                    f"variables.{name}: target {target!r} is not an approved destination",
                )
            )
            continue
        if target in owned:
            out.append(
                _finding(
                    "error",
                    "recipe_variable_target",
                    f"variables.{name}: target {target!r} already owned by {owned[target]!r}",
                )
            )
            continue
        owned[target] = name

        if not isinstance(choices, list):
            out.append(_finding("error", "recipe_variable_choices", f"variables.{name}: choices must be an array"))
            continue

        baseline, present = _read_target(spec, target)
        if not present:
            out.append(
                _finding(
                    "error",
                    "recipe_variable_baseline",
                    f"variables.{name}: baseline target {target} is missing from semantic_spec",
                )
            )
        elif not isinstance(baseline, str):
            out.append(
                _finding(
                    "error",
                    "recipe_variable_baseline",
                    f"variables.{name}: baseline target {target} must be a string",
                )
            )
        elif baseline not in choices:
            out.append(
                _finding(
                    "error",
                    "recipe_variable_baseline",
                    f"variables.{name}: baseline value {_preview_value(baseline)} must be included in choices",
                )
            )

        if target == "output.aspect_ratio":
            for choice in choices:
                if not isinstance(choice, str):
                    continue
                if choice not in _ASPECT_RATIO_VOCABULARY:
                    out.append(
                        _finding(
                            "error",
                            "recipe_variable_aspect_ratio",
                            f"variables.{name}: aspect_ratio choice {_preview_value(choice)} is outside the approved vocabulary",
                        )
                    )
        elif target.startswith("director."):
            for choice in choices:
                if not isinstance(choice, str):
                    continue
                reason = _director_value_ok(choice)
                if reason:
                    out.append(
                        _finding(
                            "error",
                            "recipe_variable_unicode",
                            f"variables.{name}: choice {_preview_value(choice)}: {reason}",
                        )
                    )
    return out


def _validate_bindings(recipe: dict, bindings: dict) -> list[dict]:
    out: list[dict] = []
    if not isinstance(bindings, dict):
        return [_finding("error", "recipe_bindings_type", "bindings must be a JSON object")]
    out.extend(_non_string_key_findings(bindings, path="bindings"))
    if out:
        return out

    variables = recipe.get("variables") or {}
    if not isinstance(variables, dict):
        variables = {}

    for name in bindings:
        if name not in variables:
            out.append(
                _finding(
                    "error",
                    "recipe_binding_unknown",
                    f"unknown binding variable {name!r}",
                )
            )

    for name, definition in variables.items():
        if not isinstance(definition, dict):
            continue
        required = bool(definition.get("required", False))
        if required and name not in bindings:
            out.append(
                _finding(
                    "error",
                    "recipe_binding_required",
                    f"required variable {name!r} was not provided",
                )
            )
            continue
        if name not in bindings:
            continue
        value = bindings[name]
        if not isinstance(value, str):
            out.append(
                _finding(
                    "error",
                    "recipe_binding_type",
                    f"binding {name!r} must be a string, got {type(value).__name__}",
                )
            )
            continue
        target = definition.get("target")
        # Reject oversized / malformed Director values before echoing payloads.
        if isinstance(target, str) and target.startswith("director."):
            reason = _director_value_ok(value)
            if reason:
                out.append(
                    _finding(
                        "error",
                        "recipe_variable_unicode",
                        f"binding {name!r}: {reason}",
                    )
                )
                continue
        choices = definition.get("choices") or []
        if value not in choices:
            out.append(
                _finding(
                    "error",
                    "recipe_binding_choice",
                    f"binding {name!r} value {_preview_value(value)} is not a declared choice",
                )
            )
            continue
    return out


def _effective_bindings(recipe: dict, bindings: dict) -> dict:
    variables = recipe.get("variables") or {}
    effective: dict[str, str] = {}
    spec = recipe["semantic_spec"]
    for name, definition in variables.items():
        if name in bindings:
            effective[name] = bindings[name]
        else:
            target = definition["target"]
            baseline, _ = _read_target(spec, target)
            effective[name] = baseline
    # Stable key order for receipt serialization, independent of definition order.
    return {name: effective[name] for name in sorted(effective)}


def _apply_bindings(spec: dict, recipe: dict, effective: dict) -> dict:
    resolved = deepcopy(spec)
    variables = recipe.get("variables") or {}
    for name, value in effective.items():
        target = variables[name]["target"]
        _write_target(resolved, target, value)
    return resolved


def _promote_v11_lint_findings(findings: list[dict]) -> list[dict]:
    """For v1.1, any evidence_retrieval_failure warning blocks compilation."""
    out = []
    for finding in findings:
        if finding.get("code") == "evidence_retrieval_failure" and finding.get("level") == "warning":
            promoted = dict(finding)
            promoted["level"] = "error"
            out.append(promoted)
        else:
            out.append(finding)
    return out


def validate_recipe(recipe: dict, bindings=_OMITTED) -> list[dict]:
    """Validate recipe envelope and embedded semantic_spec without compiling.

    When ``bindings`` is omitted, validates the recipe definition and baseline
    specification only. An explicitly supplied bindings object (including ``{}``)
    validates that invocation against v1.1 variable rules. v1.0 rejects any
    explicitly submitted bindings object.

    Returns lint-style findings. Errors block compilation; warnings/info do not.
    Does not mutate ``recipe`` or ``bindings``.
    """
    if not isinstance(recipe, dict):
        return [_finding("error", "recipe_type", "recipe must be a JSON object")]

    out: list[dict] = []
    out.extend(_non_string_key_findings(recipe, path="$"))
    if out:
        return out

    version = recipe.get("recipe_schema_version")

    if not isinstance(version, str) or version not in _SUPPORTED_RECIPE_SCHEMA_VERSIONS:
        # Still attempt schema validation against v1.0 for path messages, then report.
        try:
            schema = _load_recipe_schema(RECIPE_SCHEMA_VERSION_V10)
            for err in sorted(Draft202012Validator(schema).iter_errors(recipe), key=lambda e: list(e.path)):
                loc = ".".join(str(x) for x in err.path) or "$"
                out.append(_finding("error", "recipe_schema", f"{loc}: {err.message}"))
        except RecipeError as exc:
            out.append(_finding("error", "recipe_schema_resource", str(exc)))
        if version is not None and not any(
            f["code"] == "recipe_schema" and "recipe_schema_version" in f["message"] for f in out
        ):
            out.append(
                _finding(
                    "error",
                    "recipe_schema_version",
                    f"unsupported recipe_schema_version {version!r}; expected "
                    f"{RECIPE_SCHEMA_VERSION_V10!r} or {RECIPE_SCHEMA_VERSION_V11!r}",
                )
            )
        return out

    # Reject non-string variables keys before jsonschema patternProperties
    # (which TypeErrors on non-string property names).
    variables = recipe.get("variables")
    if isinstance(variables, dict):
        var_key_findings = _non_string_key_findings(variables, path="variables")
        if var_key_findings:
            out.extend(var_key_findings)
            return out

    # Missing/corrupt packaged schemas fail closed (do not soft-degrade).
    schema = _load_recipe_schema(version)

    for err in sorted(Draft202012Validator(schema).iter_errors(recipe), key=lambda e: list(e.path)):
        loc = ".".join(str(x) for x in err.path) or "$"
        out.append(_finding("error", "recipe_schema", f"{loc}: {err.message}"))

    if version == RECIPE_SCHEMA_VERSION_V11:
        out.extend(_validate_variable_definitions(recipe))

    spec = recipe.get("semantic_spec")
    if isinstance(spec, dict):
        lint_findings = lint_spec(spec)
        if version == RECIPE_SCHEMA_VERSION_V11:
            lint_findings = _promote_v11_lint_findings(lint_findings)
        out.extend(lint_findings)
    elif "semantic_spec" in recipe and not any(f["code"] == "recipe_schema" for f in out):
        out.append(_finding("error", "recipe_schema", "semantic_spec: must be an object"))

    if bindings is _OMITTED:
        return out

    if version == RECIPE_SCHEMA_VERSION_V10:
        out.append(
            _finding(
                "error",
                "recipe_bindings_unsupported",
                "recipe_schema_version 1.0 does not support bindings",
            )
        )
        return out

    out.extend(_validate_bindings(recipe, bindings))
    if any(f["level"] == "error" for f in out):
        return out

    # Validate the resolved semantic specification when the invocation is usable.
    effective = _effective_bindings(recipe, bindings)
    resolved = _apply_bindings(recipe["semantic_spec"], recipe, effective)
    resolved_findings = _promote_v11_lint_findings(lint_spec(resolved))
    # Avoid duplicating identical baseline lint findings already reported.
    baseline_msgs = {(f.get("code"), f.get("message")) for f in out}
    for finding in resolved_findings:
        key = (finding.get("code"), finding.get("message"))
        if key not in baseline_msgs:
            out.append(finding)
    return out


def resolve_recipe(recipe: dict, bindings=_OMITTED) -> dict:
    """Return a deep copy of the (possibly variable-resolved) semantic_spec.

    For v1.0, ``bindings`` must be omitted. For v1.1, omitted bindings are
    treated as an empty invocation. Does not inject recipe metadata into the
    specification. Non-dictionary recipes are rejected via validation findings
    (PR3 controlled rejection), never AttributeError.
    """
    if not isinstance(recipe, dict):
        raise RecipeValidationError(validate_recipe(recipe))

    if recipe.get("recipe_schema_version") == RECIPE_SCHEMA_VERSION_V11:
        invocation = {} if bindings is _OMITTED else bindings
        findings = validate_recipe(recipe, invocation)
    else:
        if bindings is not _OMITTED:
            findings = validate_recipe(recipe, bindings)
        else:
            findings = validate_recipe(recipe)
    errors = [f for f in findings if f["level"] == "error"]
    if errors:
        raise RecipeValidationError(findings)

    if recipe.get("recipe_schema_version") != RECIPE_SCHEMA_VERSION_V11:
        return deepcopy(recipe["semantic_spec"])

    invocation = {} if bindings is _OMITTED else bindings
    effective = _effective_bindings(recipe, invocation)
    return _apply_bindings(recipe["semantic_spec"], recipe, effective)


def compile_recipe(recipe: dict, bindings=_OMITTED) -> dict:
    """Compile via ``compile_result`` and return a deterministic receipt envelope.

    The compiler result is embedded unchanged under ``compilation``.
    Non-dictionary recipes are rejected via validation findings (PR3 controlled
    rejection), never AttributeError.
    """
    if not isinstance(recipe, dict):
        raise RecipeValidationError(validate_recipe(recipe))

    version = recipe.get("recipe_schema_version")
    if version == RECIPE_SCHEMA_VERSION_V11:
        invocation = {} if bindings is _OMITTED else bindings
        findings = validate_recipe(recipe, invocation)
    else:
        if bindings is not _OMITTED:
            findings = validate_recipe(recipe, bindings)
        else:
            findings = validate_recipe(recipe)
    errors = [f for f in findings if f["level"] == "error"]
    if errors:
        raise RecipeValidationError(findings)

    recipe_sha = sha256_canonical(recipe)
    semantic_sha = sha256_canonical(recipe["semantic_spec"])

    if version == RECIPE_SCHEMA_VERSION_V11:
        invocation = {} if bindings is _OMITTED else bindings
        if not isinstance(invocation, dict):
            raise RecipeValidationError(
                [_finding("error", "recipe_bindings_type", "bindings must be a JSON object")]
            )
        submitted = dict(invocation)
        effective = _effective_bindings(recipe, submitted)
        resolved = _apply_bindings(recipe["semantic_spec"], recipe, effective)
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
            "variable_resolution": {
                "submitted_bindings_sha256": sha256_canonical(submitted),
                "effective_bindings_sha256": sha256_canonical(effective),
                "resolved_semantic_spec_sha256": sha256_canonical(resolved),
                "effective_bindings": effective,
                "submitted_variable_names": sorted(submitted.keys()),
            },
            "compilation": compilation,
            "prompt_sha256": sha256_bytes(prompt.encode("utf-8")),
            "compiler_version": compilation["compiler_version"],
            "evidence_snapshot_sha256": compilation["evidence_snapshot"]["snapshot_sha256"],
        }

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
