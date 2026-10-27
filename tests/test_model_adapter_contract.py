"""Offline GPT Image 2 request-contract tests (no network, no credentials)."""
from __future__ import annotations

import base64
import hashlib
import importlib.util
import io
import json
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]

from aipf.model_adapter import (
    SUPPORTED_MODEL_IDS,
    AdapterContractError,
    build_generation_metadata,
    build_sdk_kwargs,
    load_gpt_image_2_adapter,
    materialize_sdk_kwargs,
    normalize_request,
    persist_api_result,
)


def _load_generate_api():
    path = ROOT / "scripts" / "generate_api.py"
    spec = importlib.util.spec_from_file_location("generate_api_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


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
    assert meta["generation_completed"] is False
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


# --- CLI entry-point regressions (scripts/generate_api.py) ---


class _RecordingImages:
    def __init__(self, result):
        self.generate_calls = []
        self.edit_calls = []
        self._result = result

    def generate(self, **kwargs):
        self.generate_calls.append(dict(kwargs))
        return self._result

    def edit(self, **kwargs):
        image = kwargs.get("image")
        recorded = dict(kwargs)
        if isinstance(image, list):
            recorded["_image_kind"] = "list"
            recorded["_image_count"] = len(image)
            recorded["_image_are_binary_io"] = all(hasattr(h, "read") for h in image)
            for h in image:
                try:
                    h.close()
                except Exception:
                    pass
        elif image is not None:
            recorded["_image_kind"] = "single"
            recorded["_image_are_binary_io"] = hasattr(image, "read")
            try:
                image.close()
            except Exception:
                pass
        self.edit_calls.append(recorded)
        return self._result


class _RecordingClient:
    def __init__(self, result):
        self.images = _RecordingImages(result)


def _install_fake_openai(monkeypatch, client):
    fake = types.ModuleType("openai")
    fake.OpenAI = lambda: client
    monkeypatch.setitem(sys.modules, "openai", fake)
    return fake


def test_cli_default_invocation_is_dry_run(monkeypatch, capsys, tmp_path):
    gen = _load_generate_api()
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_IMAGE_MODEL_SNAPSHOT", raising=False)
    meta_path = tmp_path / "meta.json"
    client = _RecordingClient(SimpleNamespace(data=[]))
    _install_fake_openai(monkeypatch, client)
    gen.main([
        "--prompt", "  synthetic dry-run  ",
        "--metadata-output", str(meta_path),
    ])
    out = json.loads(capsys.readouterr().out)
    assert out["dry_run"] is True
    assert out["prompt"] == "synthetic dry-run"
    assert out["metadata"]["dry_run"] is True
    assert out["metadata"]["generation_completed"] is False
    assert out["metadata"]["provider_verified_model_id"] is None
    assert client.images.generate_calls == []
    assert client.images.edit_calls == []
    assert meta_path.is_file()


def test_cli_env_snapshot_is_not_explicit_declaration(monkeypatch, capsys, tmp_path):
    gen = _load_generate_api()
    monkeypatch.setenv("OPENAI_IMAGE_MODEL_SNAPSHOT", "gpt-image-2-2026-04-21")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    meta_path = tmp_path / "meta.json"
    gen.main(["--prompt", "env default", "--metadata-output", str(meta_path)])
    out = json.loads(capsys.readouterr().out)
    assert out["metadata"]["requested_model_id"] == "gpt-image-2"
    assert out["metadata"]["declared_model_snapshot"] is None
    assert out["metadata"]["model_snapshot"] is None
    assert out["metadata"]["provider_verified_model_id"] is None


def test_cli_explicit_model_snapshot_is_declared_not_provider_verified(monkeypatch, capsys):
    gen = _load_generate_api()
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_IMAGE_MODEL_SNAPSHOT", raising=False)
    gen.main([
        "--prompt", "explicit",
        "--model", "gpt-image-2",
        "--model-snapshot", "gpt-image-2-2026-04-21",
    ])
    out = json.loads(capsys.readouterr().out)
    assert out["metadata"]["requested_model_id"] == "gpt-image-2"
    assert out["metadata"]["declared_model_snapshot"] == "gpt-image-2-2026-04-21"
    assert out["metadata"]["model_snapshot"] == "gpt-image-2-2026-04-21"
    assert out["metadata"]["provider_verified_model_id"] is None


def test_cli_unsupported_model_exits_before_sdk(monkeypatch):
    gen = _load_generate_api()
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-real")
    client = _RecordingClient(SimpleNamespace(data=[]))
    _install_fake_openai(monkeypatch, client)
    with pytest.raises(SystemExit, match="unsupported model"):
        gen.main(["--prompt", "x", "--model", "gpt-image-2.5", "--execute"])
    assert client.images.generate_calls == []
    assert client.images.edit_calls == []


def test_cli_missing_reference_image_exits_before_sdk(monkeypatch, tmp_path):
    gen = _load_generate_api()
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-real")
    client = _RecordingClient(SimpleNamespace(data=[]))
    _install_fake_openai(monkeypatch, client)
    missing = tmp_path / "gone.png"
    with pytest.raises(SystemExit, match="reference image"):
        gen.main([
            "--prompt", "x",
            "--image", str(missing),
            "--execute",
        ])
    assert client.images.generate_calls == []
    assert client.images.edit_calls == []


def test_cli_mocked_generate_keeps_provider_verified_null(monkeypatch, tmp_path, capsys):
    gen = _load_generate_api()
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-real")
    monkeypatch.delenv("OPENAI_IMAGE_MODEL_SNAPSHOT", raising=False)
    result = SimpleNamespace(
        data=[SimpleNamespace(b64_json=base64.b64encode(b"PNGDATA").decode("ascii"), url=None)]
    )
    client = _RecordingClient(result)
    _install_fake_openai(monkeypatch, client)
    out = tmp_path / "out.png"
    meta_path = tmp_path / "meta.json"
    gen.main([
        "--prompt", "generate path",
        "--size", "1024x1024",
        "--quality", "high",
        "--execute",
        "--output", str(out),
        "--metadata-output", str(meta_path),
    ])
    printed = json.loads(capsys.readouterr().out)
    assert client.images.generate_calls
    assert printed["metadata"]["provider_verified_model_id"] is None
    assert printed["metadata"]["generation_completed"] is True
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta["provider_verified_model_id"] is None
    assert out.read_bytes() == b"PNGDATA"


def test_cli_url_only_output_exits_nonzero_incomplete(monkeypatch, tmp_path):
    gen = _load_generate_api()
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-real")
    result = SimpleNamespace(
        data=[SimpleNamespace(b64_json=None, url="https://example.test/img.png")]
    )
    client = _RecordingClient(result)
    _install_fake_openai(monkeypatch, client)
    out = tmp_path / "out.png"
    meta_path = tmp_path / "meta.json"
    with pytest.raises(SystemExit) as excinfo:
        gen.main([
            "--prompt", "url only",
            "--execute",
            "--output", str(out),
            "--metadata-output", str(meta_path),
        ])
    payload = json.loads(str(excinfo.value))
    assert payload["error"] == "generation_incomplete"
    assert payload["result"]["generation_completed"] is False
    assert payload["metadata"]["generation_completed"] is False
    assert "saved" not in payload["result"]
    assert not out.exists()
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta["generation_completed"] is False


def test_cli_multiple_images_sdk_handle_list_shape(monkeypatch, tmp_path, capsys):
    gen = _load_generate_api()
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-real")
    a = _write_png(tmp_path / "a.png")
    b = _write_png(tmp_path / "b.png")
    result = SimpleNamespace(
        data=[SimpleNamespace(b64_json=base64.b64encode(b"EDIT").decode("ascii"), url=None)]
    )
    client = _RecordingClient(result)
    _install_fake_openai(monkeypatch, client)
    out = tmp_path / "edit.png"
    gen.main([
        "--prompt", "edit many",
        "--image", str(a),
        "--image", str(b),
        "--execute",
        "--output", str(out),
    ])
    call = client.images.edit_calls[-1]
    assert call["_image_kind"] == "list"
    assert call["_image_count"] == 2
    assert call["_image_are_binary_io"] is True
    assert out.read_bytes() == b"EDIT"
    # Also verify materialize_sdk_kwargs shape independently.
    req = normalize_request(
        prompt="edit many",
        model="gpt-image-2",
        model_snapshot=None,
        size="auto",
        quality="auto",
        background=None,
        images=[str(a), str(b)],
        execute=True,
    )
    kwargs, handles = materialize_sdk_kwargs(req)
    try:
        assert isinstance(kwargs["image"], list)
        assert len(kwargs["image"]) == 2
        assert all(isinstance(h, io.BufferedReader) or hasattr(h, "read") for h in kwargs["image"])
    finally:
        for h in handles:
            h.close()
    _ = capsys.readouterr()
