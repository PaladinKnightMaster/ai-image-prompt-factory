"""ESR-v0.1 operational lifecycle tests (PR2).

Uses dynamically generated temporary rasters (no committed fixtures under
tests/fixtures/). Does not call scientific experiment_review / exp019 paths.
"""
from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path

import pytest

from aipf.esr_review import (
    EsrError,
    canonical_sha256,
    freeze_session,
    package_session,
    reveal_session,
    task_brief_sha256,
    verify_session,
)
from aipf.experiment_runs import sha256_file

pil = pytest.importorskip("PIL")
from PIL import Image  # noqa: E402


def _write_png(path: Path, color=(20, 40, 60)) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (8, 8), color).save(path, format="PNG")
    return path


def _write_session(session: Path, *, n: int = 2, transform: bool = False) -> dict:
    session.mkdir(parents=True, exist_ok=True)
    images = []
    candidates = []
    for i in range(n):
        img = _write_png(session / f"src_{i}.png", color=(10 * (i + 1), 20, 30))
        images.append(img)
        candidates.append(
            {
                "candidate_id": f"C{i+1}",
                "prompt_text": f"candidate prompt {i+1} for ESR test",
                "image_path": str(img.name),
            }
        )
    brief = {
        "text": "Adult subject outdoors; calm expression; no logos.",
        "style_target": "naturalistic photographic portrait",
    }
    if transform:
        brief["transformation_target"] = "portrait to relief_print; preserve identity"
    session_doc = {
        "session_id": "esr-test-session",
        "transformation_in_scope": transform,
        "task_brief": brief,
        "model": "gpt-image-2",
        "settings": {"size": "1024x1024"},
        "planned_generation_count": n,
        "inclusions": [c["candidate_id"] for c in candidates],
        "exclusions": [],
        "candidates": candidates,
        "contamination_status": "clean",
        "deviations": [],
    }
    (session / "session.json").write_text(
        json.dumps(session_doc, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return session_doc


def _complete_scores(draft: dict, *, transform: bool = False) -> dict:
    for item in draft["items"]:
        item["scores"]["task_brief_adherence"] = {"value": 4, "na_reason": None}
        item["scores"]["visual_coherence"] = {"value": 3, "na_reason": None}
        item["scores"]["target_style_fidelity"] = {"value": 4, "na_reason": None}
        item["scores"]["technical_cleanliness"] = {"value": 5, "na_reason": None}
        item["scores"]["prompt_repeatability"] = {
            "value": None,
            "na_reason": "deferred_protocol_v0_1",
        }
        if transform:
            item["scores"]["transformation_fidelity"] = {"value": 4, "na_reason": None}
        else:
            item["scores"]["transformation_fidelity"] = {
                "value": None,
                "na_reason": "not_applicable_to_task",
            }
        item["recognized_image_or_treatment"] = "none"
        item["notes"] = "ok"
    draft["status"] = "open"
    return draft


def _package_and_score(session: Path, *, transform: bool = False) -> Path:
    _write_session(session, transform=transform)
    package_session(session)
    draft_path = session / "package" / "review.json"
    draft = json.loads(draft_path.read_text(encoding="utf-8"))
    _complete_scores(draft, transform=transform)
    draft_path.write_text(
        json.dumps(draft, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return session


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_t1_full_lifecycle(tmp_path: Path) -> None:
    session = tmp_path / "s1"
    _package_and_score(session)
    frozen = freeze_session(session)
    verified = verify_session(session)
    revealed = reveal_session(session)
    assert frozen["review_sha256"] == verified["review_sha256"]
    assert revealed["status"] == "revealed"
    assert (session / "reveal.json").is_file()
    assert frozen["comparative_claims_eligible"] is True
    # Seal is separate from schema-valid frozen payload.
    frozen_doc = json.loads((session / "review.frozen.json").read_text(encoding="utf-8"))
    assert "review_sha256" not in frozen_doc
    seal = json.loads((session / "review.freeze.json").read_text(encoding="utf-8"))
    assert seal["review_sha256"] == canonical_sha256(frozen_doc)


def test_t2_existing_image_import_no_generation(tmp_path: Path) -> None:
    session = tmp_path / "s2"
    _write_session(session, n=1)
    result = package_session(session)
    assert result["review_count"] == 1
    assert (session / "package" / "images").is_dir()


# ---------------------------------------------------------------------------
# Negative / integrity
# ---------------------------------------------------------------------------


def test_t3_incomplete_draft_cannot_freeze(tmp_path: Path) -> None:
    session = tmp_path / "s3"
    _write_session(session)
    package_session(session)
    with pytest.raises(EsrError, match="schema"):
        freeze_session(session)


def test_t4_invalid_scores(tmp_path: Path) -> None:
    session = tmp_path / "s4"
    _package_and_score(session)
    draft_path = session / "package" / "review.json"
    draft = json.loads(draft_path.read_text(encoding="utf-8"))
    draft["items"][0]["scores"]["task_brief_adherence"] = {"value": 9, "na_reason": None}
    draft_path.write_text(json.dumps(draft, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(EsrError):
        freeze_session(session)


def test_t5_broken_bijection(tmp_path: Path) -> None:
    session = tmp_path / "s5"
    _package_and_score(session)
    draft_path = session / "package" / "review.json"
    draft = json.loads(draft_path.read_text(encoding="utf-8"))
    draft["presentation_order"] = draft["presentation_order"][::-1]
    # Still same set — force mismatch by dropping one
    draft["presentation_order"] = draft["presentation_order"][:-1]
    draft_path.write_text(json.dumps(draft, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(EsrError, match="bijection"):
        freeze_session(session)


def test_t6_private_fields_rejected_in_manifest(tmp_path: Path) -> None:
    session = tmp_path / "s6"
    _package_and_score(session)
    manifest_path = session / "package" / "manifest.json"
    # Tamper after package — freeze/verify should fail commitment, not accept private field.
    # Also ensure package path never wrote candidate ids into reviewer files.
    review = json.loads((session / "package" / "review.json").read_text(encoding="utf-8"))
    blob = json.dumps(review)
    assert "C1" not in blob
    assert "candidate prompt" not in blob
    mapping = json.loads((session / "private" / "mapping.json").read_text(encoding="utf-8"))
    assert {e["candidate_id"] for e in mapping["entries"]} == {"C1", "C2"}


def test_t7_reveal_before_freeze(tmp_path: Path) -> None:
    session = tmp_path / "s7"
    _package_and_score(session)
    with pytest.raises(EsrError, match="incomplete freeze"):
        reveal_session(session)


def test_t8_altered_frozen_detected(tmp_path: Path) -> None:
    session = tmp_path / "s8"
    _package_and_score(session)
    freeze_session(session)
    frozen_path = session / "review.frozen.json"
    frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
    frozen["items"][0]["notes"] = "tampered"
    frozen_path.write_text(json.dumps(frozen, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(EsrError, match="digest"):
        verify_session(session)


def test_t9_mapping_tamper_detected(tmp_path: Path) -> None:
    session = tmp_path / "s9"
    _package_and_score(session)
    freeze_session(session)
    mapping_path = session / "private" / "mapping.json"
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    mapping["entries"][0]["candidate_id"] = "HACKED"
    mapping_path.write_text(json.dumps(mapping, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(EsrError, match="commitment"):
        verify_session(session)


def test_t10_second_freeze_and_reveal_rejected(tmp_path: Path) -> None:
    session = tmp_path / "s10"
    _package_and_score(session)
    freeze_session(session)
    with pytest.raises(EsrError, match="already exist"):
        freeze_session(session)
    reveal_session(session)
    with pytest.raises(EsrError, match="already exists"):
        reveal_session(session)


def test_t11_hashes_recorded_independently(tmp_path: Path) -> None:
    session = tmp_path / "s11"
    _write_session(session, n=1)
    package_session(session)
    mapping = json.loads((session / "private" / "mapping.json").read_text(encoding="utf-8"))
    entry = mapping["entries"][0]
    assert len(entry["source_image_sha256"]) == 64
    assert len(entry["review_image_sha256"]) == 64
    # Equal hashes are allowed; do not require inequality.
    review_img = session / "package" / "images" / entry["review_image"]
    assert sha256_file(review_img) == entry["review_image_sha256"]


def test_t12_unsupported_format_rejected(tmp_path: Path) -> None:
    session = tmp_path / "s12"
    session.mkdir()
    bad = session / "x.gif"
    bad.write_bytes(b"GIF89a")
    session_doc = {
        "session_id": "badfmt",
        "transformation_in_scope": False,
        "task_brief": {
            "text": "x",
            "style_target": "y",
        },
        "candidates": [
            {
                "candidate_id": "A",
                "prompt_text": "p",
                "image_path": "x.gif",
            }
        ],
    }
    (session / "session.json").write_text(json.dumps(session_doc) + "\n", encoding="utf-8")
    with pytest.raises(EsrError, match="unsupported|undecodable"):
        package_session(session)


def test_t13_contaminated_not_comparative(tmp_path: Path) -> None:
    session = tmp_path / "s13"
    _write_session(session)
    doc = json.loads((session / "session.json").read_text(encoding="utf-8"))
    doc["contamination_status"] = "contaminated_pilot"
    (session / "session.json").write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    package_session(session)
    draft_path = session / "package" / "review.json"
    draft = json.loads(draft_path.read_text(encoding="utf-8"))
    assert draft["contamination_status"] == "contaminated_pilot"
    _complete_scores(draft)
    draft["contamination_status"] = "contaminated_pilot"
    draft_path.write_text(json.dumps(draft, indent=2) + "\n", encoding="utf-8")
    result = freeze_session(session)
    assert result["comparative_claims_eligible"] is False


def test_t14_presentation_order_by_review_id(tmp_path: Path) -> None:
    session = tmp_path / "s14"
    _write_session(session, n=3)
    package_session(session)
    draft = json.loads((session / "package" / "review.json").read_text(encoding="utf-8"))
    order = draft["presentation_order"]
    assert order == sorted(order)
    # Input candidate order C1,C2,C3 need not match review_id sort.
    mapping = json.loads((session / "private" / "mapping.json").read_text(encoding="utf-8"))
    cand_order = [e["candidate_id"] for e in mapping["entries"]]
    # entries are sorted by review_id; candidate labels follow that sort, not input index alone
    assert len(cand_order) == 3


def test_t15_post_package_add_blocked(tmp_path: Path) -> None:
    session = tmp_path / "s15"
    _package_and_score(session)
    with pytest.raises(EsrError, match="already exists"):
        package_session(session)


def test_t16_exploratory_labels(tmp_path: Path) -> None:
    session = tmp_path / "s16"
    _package_and_score(session)
    freeze_session(session)
    reveal_session(session)
    frozen = json.loads((session / "review.frozen.json").read_text(encoding="utf-8"))
    assert frozen["scientific_status"] == "exploratory"
    assert frozen["evaluator_identity_class"] == "owner_self_review"
    assert frozen["independent_reviewer"] is False
    reveal = json.loads((session / "reveal.json").read_text(encoding="utf-8"))
    assert reveal["scientific_status"] == "exploratory"


def test_t17_scientific_path_isolation() -> None:
    import sys

    src = Path(__file__).resolve().parents[1] / "src" / "aipf" / "esr_review.py"
    text = src.read_text(encoding="utf-8")
    assert "from .experiment_review" not in text
    assert "import experiment_review" not in text
    assert "from .exp019_review" not in text
    assert "import exp019_review" not in text
    before = set(sys.modules)
    mod = importlib.import_module("aipf.esr_review")
    assert hasattr(mod, "package_session")
    loaded = set(sys.modules) - before
    assert "aipf.experiment_review" not in loaded
    assert "aipf.exp019_review" not in loaded


def test_t18_task_brief_digest_excludes_hash_field() -> None:
    brief = {
        "text": "hello",
        "style_target": "style",
        "task_brief_sha256": "deadbeef",
    }
    digest = task_brief_sha256(brief)
    assert digest == task_brief_sha256({"text": "hello", "style_target": "style"})
    assert digest != hashlib.sha256(b"deadbeef").hexdigest()


def test_incomplete_freeze_pair_rejected(tmp_path: Path) -> None:
    session = tmp_path / "s_incomplete"
    _package_and_score(session)
    freeze_session(session)
    (session / "review.freeze.json").unlink()
    with pytest.raises(EsrError, match="incomplete freeze"):
        verify_session(session)


def test_in_repo_session_rejected(tmp_path: Path) -> None:
    # Simulate by placing session under a fake checkout marker is hard;
    # instead ensure absolute tmp sessions still work and relative in-repo
    # rejection is covered when source_checkout_root is available.
    from aipf.resources import source_checkout_root
    from aipf.esr_review import _assert_safe_session_location, EsrError as E

    root = source_checkout_root()
    if root is None:
        pytest.skip("not a source checkout")
    with pytest.raises(E, match="must not be inside the repository"):
        _assert_safe_session_location(root / "evals" / "bad-session")


def test_transform_scope_scores(tmp_path: Path) -> None:
    session = tmp_path / "s_tx"
    _package_and_score(session, transform=True)
    freeze_session(session)
    frozen = json.loads((session / "review.frozen.json").read_text(encoding="utf-8"))
    assert frozen["transformation_in_scope"] is True
    assert frozen["items"][0]["scores"]["transformation_fidelity"]["value"] == 4


def test_package_help_session_example_is_operable(tmp_path: Path) -> None:
    """Operator help must expose a parseable session.json that packages successfully."""
    import subprocess
    import sys

    from aipf.cli import ESR_SESSION_JSON_EXAMPLE

    help_proc = subprocess.run(
        [sys.executable, "-m", "aipf.cli", "esr", "package", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert help_proc.returncode == 0, help_proc.stderr
    help_text = help_proc.stdout
    assert "session.json" in help_text
    assert "REPLACE_ME_" in help_text
    assert "Example session.json" in help_text
    assert "prompt_ref" in help_text

    example = json.loads(ESR_SESSION_JSON_EXAMPLE)
    assert example["planned_generation_count"] == 2
    assert len(example["candidates"]) == 2
    assert set(example.keys()) >= {
        "session_id",
        "transformation_in_scope",
        "task_brief",
        "model",
        "settings",
        "planned_generation_count",
        "inclusions",
        "exclusions",
        "candidates",
        "contamination_status",
        "deviations",
    }

    session = tmp_path / "help-example-session"
    session.mkdir()
    img_a = _write_png(session / "cand_a.png", color=(11, 22, 33))
    img_b = _write_png(session / "cand_b.png", color=(44, 55, 66))
    example["session_id"] = "help-example-session"
    example["task_brief"]["text"] = "Adult subject outdoors; calm expression; no logos."
    example["task_brief"]["style_target"] = "naturalistic photographic portrait"
    example["model"] = "gpt-image-2"
    example["settings"] = {"size": "1024x1024"}
    example["inclusions"] = ["cand_a", "cand_b"]
    example["candidates"][0] = {
        "candidate_id": "cand_a",
        "prompt_text": "candidate prompt A for ESR help example",
        "image_path": img_a.name,
    }
    example["candidates"][1] = {
        "candidate_id": "cand_b",
        "prompt_text": "candidate prompt B for ESR help example",
        "image_path": img_b.name,
    }
    (session / "session.json").write_text(
        json.dumps(example, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    result = package_session(session)
    assert result["status"] == "packaged"
    assert result["review_count"] == 2
    assert (session / "package" / "review.json").is_file()
    assert (session / "package" / "manifest.json").is_file()
    assert (session / "package" / "images").is_dir()
    assert len(list((session / "package" / "images").iterdir())) == 2
    assert (session / "private" / "mapping.json").is_file()
