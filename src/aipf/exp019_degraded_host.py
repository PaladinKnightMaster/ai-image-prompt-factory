"""Explicit, narrow repository-derived qualification; never normalize a host response."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator

from .experiment_runs import sha256_file
from .exp019_host_metadata import (
    QUERY_ATTESTATION, SCHEMA_PATH, bind_sidecar_to_receipt,
    validate_receipt_observation_fields, validate_run_timestamp_plausibility,
)
from .exp019_metadata_recovery import (
    RECOVERY_DIR, _eligible, _regular, _schema_errors, _write_new,
    frozen_amendment as recovery_amendment,
)
from .io import load_json, repo_root

AMENDMENT_ID = "EXP-019-DHP-20260928-01"
AMENDMENT_PATH = "experiments/amendments/EXP-019.v1.1.1.DEGRADED-HOST-PROVENANCE-01.md"
AMENDMENT_SHA256 = "9d6fb9e7ba6e8f38729d980cb04f612957b26c42518d27f9ff781d03a0f7dc91"
DEGRADED_DIR = Path(".degraded-host-private")
STATE = "degraded_host_provenance"
ATTESTATION_SCHEMA = "data/schemas/exp019_degraded_host_attestation.schema.json"
WRAPPER_SCHEMA = "data/schemas/exp019_degraded_host_evidence.schema.json"
QUALIFICATION = (
    "This amended run used a second post-start degraded-host-provenance addendum. "
    "Affected original rasters and image/query/receipt/treatment bindings were preserved and verified. "
    "The unchanged initial host response had an invalid empty observed output path; the original "
    "conversation was permanently unavailable. Host-output-path traceability and provenance strength "
    "are reduced. Numerical weights and registered interpretation rules are unchanged; any supportive "
    "interpretation is qualified as evidence from an amended run with degraded-host-provenance samples."
)


def frozen_amendment() -> dict:
    if sha256_file(repo_root() / AMENDMENT_PATH) != AMENDMENT_SHA256:
        raise ValueError("EXP-019 degraded-host amendment is not byte-frozen")
    return {"id": AMENDMENT_ID, "file": AMENDMENT_PATH, "sha256": AMENDMENT_SHA256}


def _validate(value: dict, schema: str) -> None:
    if list(Draft202012Validator(load_json(schema)).iter_errors(value)):
        raise ValueError("EXP-019 degraded evidence schema invalid")


def _authorize(amendment_id: str | None) -> dict:
    if amendment_id != AMENDMENT_ID:
        raise ValueError("EXP-019 explicit degraded amendment authorization required")
    return frozen_amendment()


def _no_outcome_evidence(root: Path) -> None:
    if any((root / name).exists() or (root / name).is_symlink()
           for name in ("blind-review", ".review-private", "analysis-private")):
        raise ValueError("EXP-019 degraded admission must precede review, reveal and analysis")


def allowlisted_sidecar(path: Path, run: dict, slot_id: str, recorded_at: str) -> dict:
    """Check the original parsed values, including every non-path schema/semantic gate."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(load_json(SCHEMA_PATH)).iter_errors(raw))
    if (not isinstance(raw, dict) or raw.get("generated_file_path_status") != "observed"
            or raw.get("generated_file_path") != "" or len(errors) != 2
            or {e.validator for e in errors} != {"anyOf", "minLength"}
            or any(list(e.absolute_path) != ["generated_file_path"] for e in errors)):
        raise ValueError("EXP-019 metadata defect is outside the exact degraded allowlist")
    receipt = {"slot_id": slot_id, "metadata_query_attestation": dict(QUERY_ATTESTATION),
               "host_returned_output_count": 1}
    for host, operator in (("invoked_at_utc", "invoked_at_utc"),
                           ("generation_completed_at_utc", "generation_completed_at_utc"),
                           ("generation_id", "provider_generation_id"),
                           ("backend_model_snapshot", "backend_snapshot")):
        receipt[operator] = raw[host]
        receipt[operator + "_status"] = raw[host + "_status"]
    validate_receipt_observation_fields(receipt)
    bind_sidecar_to_receipt(raw, receipt, opaque_slot_id=slot_id, image_present=True)
    validate_run_timestamp_plausibility(receipt, run["created_at_utc"], recorded_at)
    return raw


def prepare_degraded_host(run_file: str | Path, *, blind_id: str,
                          expected_image_sha256: str, expected_raw_sha256: str,
                          attestations: str | Path, amendment_id: str | None = None) -> dict:
    """Reserve an immutable qualification only; no attempt, promotion or checkpoint."""
    from .exp019_host import RECEIPT_DIR, _packaged_query
    amendment = _authorize(amendment_id)
    root, run, image, sidecar = _eligible(run_file, blind_id)
    _no_outcome_evidence(root)
    area = root / DEGRADED_DIR / blind_id
    if any(p.exists() or p.is_symlink() for p in (area, root / RECOVERY_DIR / blind_id)):
        raise ValueError("EXP-019 metadata exception already reserved; no path switching")
    if (sha256_file(image) != expected_image_sha256
            or sha256_file(sidecar) != expected_raw_sha256):
        raise ValueError("EXP-019 original capture hashes differ")
    attestation_bytes = Path(attestations).read_bytes()
    attestation = json.loads(attestation_bytes)
    _validate(attestation, ATTESTATION_SCHEMA)
    if attestation["opaque_slot_id"] != blind_id:
        raise ValueError("EXP-019 degraded attestation slot differs")
    prepared_at = datetime.now(timezone.utc).isoformat()
    allowlisted_sidecar(sidecar, run, blind_id, prepared_at)
    query, query_hash = _packaged_query(root, run, blind_id)
    if (root / DEGRADED_DIR).exists():
        _regular(root / DEGRADED_DIR, root, directory=True)
    area.mkdir(parents=True, exist_ok=False)
    for name, content in (("raw.host-session.json", sidecar.read_bytes()),
                          ("metadata-query.txt", query), ("attestations.json", attestation_bytes)):
        with (area / name).open("xb") as handle:
            handle.write(content)
    _write_new(area / "rejection.json", {
        "reason": "EXP-019 host-session metadata sidecar schema invalid",
        "validator_failures": _schema_errors(sidecar),
    })
    wrapper = {"schema_version": "1.0.0", "source_kind": "repository_derived",
               "host_provenance_state": STATE, "run_id": run["run_id"], "slot_id": blind_id,
               "prepared_at_utc": prepared_at, "attempt_number": 1, "prior_attempts": 0,
               "raw_sidecar_schema_valid": False, "scientific_bindings_valid": True,
               "image_sha256": expected_image_sha256, "raw_sidecar_sha256": expected_raw_sha256,
               "query_sha256": query_hash, "amendment": amendment,
               "preceding_amendment": recovery_amendment(),
               "intended_attempt_receipt": (RECEIPT_DIR / f"{blind_id}.attempt-1.receipt.json").as_posix(),
               "files": {name: sha256_file(area / name) for name in
                         ("raw.host-session.json", "metadata-query.txt", "attestations.json", "rejection.json")}}
    _validate(wrapper, WRAPPER_SCHEMA)
    _write_new(area / "degraded-evidence.json", wrapper)
    return {"slot_id": blind_id, "host_provenance_state": STATE,
            "wrapper": str(area / "degraded-evidence.json"), "attempts_consumed": 0,
            "checkpoint_created": False}


def degraded_binding(root: Path, run: dict, slot_id: str, image_hash: str,
                     raw_hash: str, wrapper_path: str | Path) -> tuple[dict, dict]:
    """Revalidate private evidence, independently of mutable generation packages."""
    from .exp019_host import RECEIPT_DIR, _expected_query
    area = _regular(root / DEGRADED_DIR / slot_id, root, directory=True)
    expected_path = area / "degraded-evidence.json"
    if Path(wrapper_path).resolve() != expected_path:
        raise ValueError("EXP-019 degraded wrapper path is not canonical")
    wrapper_file = _regular(expected_path, root)
    wrapper = json.loads(wrapper_file.read_text(encoding="utf-8"))
    _validate(wrapper, WRAPPER_SCHEMA)
    prepared_time = datetime.fromisoformat(wrapper["prepared_at_utc"])
    if prepared_time.tzinfo is None:
        raise ValueError("EXP-019 degraded preparation timestamp requires timezone")
    expected_receipt = (RECEIPT_DIR / f"{slot_id}.attempt-1.receipt.json").as_posix()
    if (wrapper["run_id"] != run["run_id"] or wrapper["slot_id"] != slot_id
            or wrapper["image_sha256"] != image_hash or wrapper["raw_sidecar_sha256"] != raw_hash
            or wrapper["intended_attempt_receipt"] != expected_receipt
            or wrapper["amendment"] != frozen_amendment()
            or wrapper["preceding_amendment"] != recovery_amendment()
            or (root / RECOVERY_DIR / slot_id).exists()):
        raise ValueError("EXP-019 degraded wrapper scientific/amendment binding differs")
    for name, expected_hash in wrapper["files"].items():
        if sha256_file(_regular(area / name, root)) != expected_hash:
            raise ValueError("EXP-019 immutable degraded evidence changed")
    raw_path = area / "raw.host-session.json"
    _, expected_query_hash = _expected_query(slot_id)
    if (sha256_file(raw_path) != raw_hash or wrapper["query_sha256"] != expected_query_hash
            or sha256_file(area / "metadata-query.txt") != expected_query_hash):
        raise ValueError("EXP-019 degraded raw/query binding differs")
    raw = allowlisted_sidecar(raw_path, run, slot_id, wrapper["prepared_at_utc"])
    rejection = json.loads((area / "rejection.json").read_text(encoding="utf-8"))
    if rejection != {"reason": "EXP-019 host-session metadata sidecar schema invalid",
                     "validator_failures": _schema_errors(raw_path)}:
        raise ValueError("EXP-019 original rejection evidence differs")
    attestation = json.loads((area / "attestations.json").read_text(encoding="utf-8"))
    _validate(attestation, ATTESTATION_SCHEMA)
    if attestation["opaque_slot_id"] != slot_id:
        raise ValueError("EXP-019 original conversation-loss attestation differs")
    return raw, {"wrapper_file": wrapper_file.relative_to(root).as_posix(),
                 "wrapper_sha256": sha256_file(wrapper_file), "amendment": wrapper["amendment"]}


def finalize_binding(root: Path, record: dict, receipt_path: Path) -> None:
    """Append the actual receipt link without mutating the prepared wrapper or a hash cycle."""
    _write_new(root / DEGRADED_DIR / record["slot_id"] / "finalization.json", {
        "run_id": record["run_id"], "slot_id": record["slot_id"], "attempt_number": 1,
        "wrapper_sha256": record["degraded_host_provenance"]["wrapper_sha256"],
        "receipt_file": receipt_path.relative_to(root).as_posix(),
        "receipt_sha256": sha256_file(receipt_path),
    })


def verify_degraded_receipt(root: Path, run: dict, record: dict, receipt_path: Path) -> dict:
    if (record.get("host_provenance_state") != STATE or record.get("attempt_number") != 1
            or record.get("status") != "generated" or record.get("metadata_recovery") is not None):
        raise ValueError("EXP-019 degraded receipt marker/attempt invalid")
    binding = record.get("degraded_host_provenance", {})
    raw, expected = degraded_binding(root, run, record["slot_id"], record["output_image_sha256"],
                                     record["host_session_metadata_sha256"],
                                     root / str(binding.get("wrapper_file", "")))
    if binding != expected:
        raise ValueError("EXP-019 degraded canonical receipt binding differs")
    final = json.loads(_regular(root / DEGRADED_DIR / record["slot_id"] / "finalization.json",
                               root).read_text(encoding="utf-8"))
    if final != {"run_id": run["run_id"], "slot_id": record["slot_id"], "attempt_number": 1,
                 "wrapper_sha256": binding["wrapper_sha256"],
                 "receipt_file": receipt_path.relative_to(root).as_posix(),
                 "receipt_sha256": sha256_file(receipt_path)}:
        raise ValueError("EXP-019 degraded final receipt link differs")
    return raw


def import_degraded_host(run_file: str | Path, *, blind_id: str, image: str | Path,
                         host_metadata: str | Path, receipt: str | Path, wrapper: str | Path,
                         amendment_id: str | None = None) -> dict:
    from .exp019_host import record_attempt
    _authorize(amendment_id)
    root, _run, original, raw = _eligible(run_file, blind_id)
    _no_outcome_evidence(root)
    if Path(image).resolve() != original or Path(host_metadata).resolve() != raw:
        raise ValueError("EXP-019 degraded import requires the original staged evidence")
    return record_attempt(run_file, blind_id=blind_id, image=image, host_metadata=host_metadata,
                          receipt=receipt, degraded_evidence=wrapper)


def result_provenance(root: Path, run: dict) -> dict:
    """Call only after canonical attempt verification; no treatment-dependent decision."""
    count = 0
    for variant in run["variants"]:
        for output in variant["outputs"]:
            for history in output.get("receipt_history", []):
                record = json.loads((root / history["file"]).read_text(encoding="utf-8"))
                count += record.get("host_provenance_state") == STATE
    return {"state": STATE if count else "normal_host_provenance", "normal_sample_count": 12 - count,
            "degraded_sample_count": count, "binding_integrity_valid": True,
            "raw_sidecar_schema_conformant": count == 0,
            "amendment_ids": [AMENDMENT_ID] if count else [],
            "qualification": QUALIFICATION if count else "Normal host provenance; all admitted raw sidecars pass canonical validation."}


def sanitize_exp019_result(run_file: str | Path, *, output: str | Path | None = None) -> dict:
    """Recompute verified analysis, then export aggregate fields by explicit allowlist."""
    from .exp019_analysis import analyze_exp019
    from .experiment_execution import load_run
    path, run = load_run(run_file)
    if run["experiment_version"] != "1.1.1":
        raise ValueError("EXP-019 sanitized host result requires v1.1.1")
    result = analyze_exp019(run_file)
    public = {"schema_version": "1.0.0", "experiment_id": "EXP-019", "experiment_version": "1.1.1",
              "condition_means": result["condition_means"], "contrasts": result["contrasts"],
              "initial_evidence_classification": result["initial_evidence_classification"],
              "evidence_classification": result["evidence_classification"],
              "statistical_significance_claim": False,
              "host_provenance": result_provenance(path.parent, run),
              "safeguards": {k: result["safeguards"][k] for k in
                  ("ceiling", "floor", "reviewer_ambiguity", "reviewer_ambiguity_sample_count",
                   "side_effect_veto", "side_effects")}}
    _validate(public, "data/schemas/exp019_public_result_v1_1_1.schema.json")
    if output is not None:
        destination = Path(output).resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        _write_new(destination, public)
    return public
