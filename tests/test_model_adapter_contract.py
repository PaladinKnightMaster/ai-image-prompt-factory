"""Offline GPT Image 2 request-contract tests (no network, no credentials)."""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from aipf.model_adapter import (
    SUPPORTED_MODEL_IDS,
    AdapterContractError,
    build_generation_metadata,
    build_sdk_kwargs,
    load_gpt_image_2_adapter,
    normalize_request,
    persist_api_result,
)


def _png_bytes() -> bytes:
    # Minimal valid 1x1 PNG
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )


def _write_png(path: Path) -> Path:
    path.write_bytes(_png_bytes())
    return path


class FakeImages:
    def __init__(self):
        self.generate_calls = []
        self.edit_calls = []

    def generate(self, **kwargs):
        self.generate_calls.append(dict(kwargs))
        return SimpleNamespace(
            data=[SimpleNamespace(b64_json=base64.b64encode(b"fake-png").decode("ascii"), url=None)]
        )

    def edit(self, **kwargs):
        self.edit_calls.append(dict(kwargs))
        return SimpleNamespace(
            data=[SimpleNamespace(b64_json=base64.b64encode(b"fake-edit").decode("ascii"), url=None)]
        )


class FakeClient:
    def __init__(self):
        self.images = FakeImages()


def test_adapter_record_loads_and_lists_verified_targets():
    adapter = load_gpt_image_2_adapter()
    assert adapter["model"] == "gpt-image-2"
    assert set(SUPPORTED_MODEL_IDS) == {"gpt-image-2", "gpt-image-2-2026-04-21"}
    assert set(adapter["request_contract"]["verified_model_ids"]) == set(SUPPORTED_MODEL_IDS)


def test_default_path_is_dry_run_normalize():
    req = normalize_request(
        prompt="  hello world  ",
        model="gpt-image-2",
        model_snapshot="gpt-image-2-2026-04-21",
        size="auto",
        quality="auto",
        background=None,
        images=None,
        execute=False,
    )
    assert req["dry_run"] is True
    assert req["mode"] == "generate"
    assert req["prompt"] == "hello world"
    assert req["prompt_sha256"] == hashlib.sha256(b"hello world").hexdigest()
    assert "image" not in build_sdk_kwargs(req)


def test_generate_normalization_omits_auto_transport_fields():
    req = normalize_request(
        prompt="subject",
        model="gpt-image-2",
        model_snapshot="gpt-image-2-2026-04-21",
        size="auto",
        quality="auto",
        background="auto",
        images=None,
        execute=False,
    )
    kwargs = build_sdk_kwargs(req)
    assert kwargs == {"model": "gpt-image-2", "prompt": "subject"}
    assert req["effective_request"]["model"] == "gpt-image-2"
    assert req["effective_request"]["prompt"] == "subject"
    assert "size" not in req["effective_request"]
    assert "quality" not in req["effective_request"]
    assert "background" not in req["effective_request"]


def test_edit_normalization_one_image(tmp_path):
    image = _write_png(tmp_path / "ref.png")
    req = normalize_request(
        prompt="edit me",
        model="gpt-image-2-2026-04-21",
        model_snapshot="gpt-image-2-2026-04-21",
        size="1024x1024",
        quality="high",
        background="opaque",
        images=[str(image)],
        execute=False,
    )
    assert req["mode"] == "edit"
    assert req["image_paths"] == [str(image.resolve())]
    kwargs = build_sdk_kwargs(req)
    assert kwargs["model"] == "gpt-image-2-2026-04-21"
    assert kwargs["prompt"] == "edit me"
    assert kwargs["size"] == "1024x1024"
    assert kwargs["quality"] == "high"
    assert kwargs["background"] == "opaque"
    assert kwargs["image"] == str(image.resolve())


def test_edit_normalization_multiple_images(tmp_path):
    a = _write_png(tmp_path / "a.png")
    b = _write_png(tmp_path / "b.png")
    req = normalize_request(
        prompt="compose",
        model="gpt-image-2",
        model_snapshot="gpt-image-2-2026-04-21",
        size="auto",
        quality="medium",
        background=None,
        images=[str(a), str(b)],
        execute=False,
    )
    kwargs = build_sdk_kwargs(req)
    assert kwargs["image"] == [str(a.resolve()), str(b.resolve())]
    assert kwargs["quality"] == "medium"
    assert "background" not in kwargs


def test_alias_versus_exact_snapshot_provenance():
    # Default CLI/env snapshot label must not make an alias look like a dated-snapshot request.
    alias_default = normalize_request(
        prompt="p",
        model="gpt-image-2",
        model_snapshot="gpt-image-2-2026-04-21",
        size="auto",
        quality="auto",
        background=None,
        images=None,
        execute=False,
        snapshot_explicit=False,
    )
    alias_explicit = normalize_request(
        prompt="p",
        model="gpt-image-2",
        model_snapshot="gpt-image-2-2026-04-21",
        size="auto",
        quality="auto",
        background=None,
        images=None,
        execute=False,
        snapshot_explicit=True,
    )
    exact = normalize_request(
        prompt="p",
        model="gpt-image-2-2026-04-21",
        model_snapshot="gpt-image-2-2026-04-21",
        size="auto",
        quality="auto",
        background=None,
        images=None,
        execute=False,
        snapshot_explicit=True,
    )
    alias_meta = build_generation_metadata(alias_default, prompt_profile="standard", compiler_version="3.2.0")
    alias_explicit_meta = build_generation_metadata(
        alias_explicit, prompt_profile="standard", compiler_version="3.2.0"
    )
    exact_meta = build_generation_metadata(exact, prompt_profile="standard", compiler_version="3.2.0")

    assert alias_meta["requested_model_id"] == "gpt-image-2"
    assert alias_meta["declared_model_snapshot"] is None
    assert alias_meta["model_snapshot"] is None
    assert alias_meta["provider_verified_model_id"] is None
    assert alias_meta["model"] == "gpt-image-2"
    assert alias_meta["dry_run"] is True
    assert alias_meta["generation_completed"] is False

    assert alias_explicit_meta["declared_model_snapshot"] == "gpt-image-2-2026-04-21"
    assert exact_meta["requested_model_id"] == "gpt-image-2-2026-04-21"
    assert exact_meta["declared_model_snapshot"] == "gpt-image-2-2026-04-21"
    assert exact_meta["provider_verified_model_id"] is None


def test_prompt_hash_matches_transmitted_prompt():
    req = normalize_request(
        prompt="  spaced  ",
        model="gpt-image-2",
        model_snapshot="gpt-image-2-2026-04-21",
        size="auto",
        quality="auto",
        background=None,
        images=None,
        execute=False,
    )
    kwargs = build_sdk_kwargs(req)
    meta = build_generation_metadata(req, prompt_profile="standard", compiler_version="3.2.0")
    assert kwargs["prompt"] == "spaced"
    assert meta["prompt_sha256"] == hashlib.sha256(kwargs["prompt"].encode("utf-8")).hexdigest()
    assert meta["prompt_sha256"] == req["prompt_sha256"]


def test_mocked_sdk_argument_equivalence(tmp_path):
    image = _write_png(tmp_path / "ref.png")
    client = FakeClient()
    req = normalize_request(
        prompt="go",
        model="gpt-image-2",
        model_snapshot="gpt-image-2-2026-04-21",
        size="1024x1536",
        quality="low",
        background="opaque",
        images=[str(image)],
        execute=True,
    )
    assert req["dry_run"] is False
    kwargs = build_sdk_kwargs(req)
    # Transport may open handles later; normalized image paths must match kwargs paths.
    assert kwargs["image"] == str(image.resolve())
    with open(kwargs["image"], "rb") as handle:
        client.images.edit(**{**kwargs, "image": handle})
    call = client.images.edit_calls[0]
    for key in ("model", "prompt", "size", "quality", "background"):
        assert call[key] == kwargs[key]
    assert call["image"] is not None


def test_unknown_model_rejected():
    with pytest.raises(AdapterContractError, match="unsupported model"):
        normalize_request(
            prompt="x",
            model="gpt-image-2.5",
            model_snapshot="gpt-image-2-2026-04-21",
            size="auto",
            quality="auto",
            background=None,
            images=None,
            execute=False,
        )


def test_unsupported_parameter_rejected():
    with pytest.raises(AdapterContractError, match="unsupported"):
        normalize_request(
            prompt="x",
            model="gpt-image-2",
            model_snapshot="gpt-image-2-2026-04-21",
            size="auto",
            quality="ultra",
            background=None,
            images=None,
            execute=False,
        )


def test_missing_image_rejected(tmp_path):
    missing = tmp_path / "gone.png"
    with pytest.raises(AdapterContractError, match="reference image"):
        normalize_request(
            prompt="x",
            model="gpt-image-2",
            model_snapshot="gpt-image-2-2026-04-21",
            size="auto",
            quality="auto",
            background=None,
            images=[str(missing)],
            execute=False,
        )


def test_unreadable_image_rejected(tmp_path):
    path = tmp_path / "dir_not_file"
    path.mkdir()
    with pytest.raises(AdapterContractError, match="reference image"):
        normalize_request(
            prompt="x",
            model="gpt-image-2",
            model_snapshot="gpt-image-2-2026-04-21",
            size="auto",
            quality="auto",
            background=None,
            images=[str(path)],
            execute=False,
        )


def test_empty_api_output_not_success(tmp_path):
    out = tmp_path / "out.png"
    with pytest.raises(AdapterContractError, match="empty"):
        persist_api_result(SimpleNamespace(data=[]), out)


def test_malformed_base64_not_success(tmp_path):
    out = tmp_path / "out.png"
    result = SimpleNamespace(data=[SimpleNamespace(b64_json="%%%not-base64%%%", url=None)])
    with pytest.raises(AdapterContractError, match="base64"):
        persist_api_result(result, out)
    assert not out.exists()


def test_unrecognized_response_structure_not_success(tmp_path):
    out = tmp_path / "out.png"
    result = SimpleNamespace(data=[SimpleNamespace()])
    with pytest.raises(AdapterContractError, match="recognized"):
        persist_api_result(result, out)
    assert not out.exists()


def test_url_only_output_recorded_without_claiming_saved_file(tmp_path):
    out = tmp_path / "out.png"
    result = SimpleNamespace(data=[SimpleNamespace(b64_json=None, url="https://example.test/img.png")])
    meta = persist_api_result(result, out)
    assert meta["transport"] == "url"
    assert meta["url"] == "https://example.test/img.png"
    assert "saved" not in meta
    assert not out.exists()


def test_failed_local_write_not_success(tmp_path, monkeypatch):
    out = tmp_path / "blocked" / "out.png"
    payload = base64.b64encode(b"ok").decode("ascii")
    result = SimpleNamespace(data=[SimpleNamespace(b64_json=payload, url=None)])

    def boom(*_a, **_k):
        raise OSError("disk full")

    monkeypatch.setattr(Path, "write_bytes", boom)
    with pytest.raises(AdapterContractError, match="write"):
        persist_api_result(result, out)


def test_dry_run_and_execute_share_effective_request(tmp_path):
    image = _write_png(tmp_path / "ref.png")
    common = dict(
        prompt="same",
        model="gpt-image-2",
        model_snapshot="gpt-image-2-2026-04-21",
        size="1024x1024",
        quality="medium",
        background="opaque",
        images=[str(image)],
    )
    dry = normalize_request(**common, execute=False)
    live = normalize_request(**common, execute=True)
    assert dry["effective_request"] == live["effective_request"]
    assert build_sdk_kwargs(dry) == build_sdk_kwargs(live)


def test_legacy_whitespace_strip_semantics_preserved():
    req = normalize_request(
        prompt="\n  line  \n",
        model="gpt-image-2",
        model_snapshot="gpt-image-2-2026-04-21",
        size="auto",
        quality="auto",
        background=None,
        images=None,
        execute=False,
    )
    assert req["prompt"] == "line"


def test_generation_completed_flag_on_saved_b64(tmp_path):
    out = tmp_path / "out.png"
    payload = base64.b64encode(b"img-bytes").decode("ascii")
    result = SimpleNamespace(data=[SimpleNamespace(b64_json=payload, url=None)])
    result_meta = persist_api_result(result, out)
    req = normalize_request(
        prompt="p",
        model="gpt-image-2",
        model_snapshot="gpt-image-2-2026-04-21",
        size="auto",
        quality="auto",
        background=None,
        images=None,
        execute=True,
    )
    meta = build_generation_metadata(
        req,
        prompt_profile="standard",
        compiler_version="3.2.0",
        result_meta=result_meta,
        provider_verified_model_id=None,
    )
    assert meta["dry_run"] is False
    assert meta["generation_completed"] is True
    assert out.exists()
    assert result_meta["output_sha256"] == hashlib.sha256(b"img-bytes").hexdigest()


def test_adapter_json_roundtrip_fields_present():
    adapter = load_gpt_image_2_adapter()
    contract = adapter["request_contract"]
    assert "modes" in contract
    assert set(contract["modes"]) == {"generate", "edit"}
    assert "quality" in contract["parameters"]
    assert "size" in contract["parameters"]
    assert "background" in contract["parameters"]
    assert contract.get("seed_supported") is False
