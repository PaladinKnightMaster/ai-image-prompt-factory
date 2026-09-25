"""Remote, append-only Git commitments for private EXP-019 evidence.

Only opaque digests are pushed. The run, prompts, mappings, reviews and rasters
remain in private run storage. A local checkpoint file is an index, never the
trust root: every operation fetches and verifies the remote ref.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

from .exp019_protocol import _canonical_sha256, _plan_core, find_slot, validate_run
from .experiment_runs import sha256_file

REMOTE_ENV = "AIPF_EXP019_PROVENANCE_REMOTE"
STATE_NAME = "anchor-state.json"
_FIELDS = {"schema_version", "run_id", "sequence", "event_type", "evidence_sha256", "previous_anchor_commit"}


def _git(*args: str, git_dir: Path | None = None, input_bytes: bytes | None = None) -> str:
    command = ["git"] + ([f"--git-dir={git_dir}"] if git_dir else []) + list(args)
    environment = os.environ.copy()
    environment.update(GIT_AUTHOR_NAME="AIPF provenance", GIT_AUTHOR_EMAIL="provenance@aipf.invalid",
                       GIT_COMMITTER_NAME="AIPF provenance", GIT_COMMITTER_EMAIL="provenance@aipf.invalid",
                       GIT_TERMINAL_PROMPT="0")
    result = subprocess.run(command, input=input_bytes, capture_output=True, env=environment)
    if result.returncode:
        # Remote URLs can contain credentials; never include arguments or Git's
        # echoed URL in a user-visible error.
        raise ValueError(f"EXP-019 remote provenance Git {args[0]} failed (exit {result.returncode})")
    return result.stdout.decode("utf-8").strip()


def _bytes(value: dict) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _ref(run_id: str) -> str:
    if not run_id or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-" for c in run_id):
        raise ValueError("EXP-019 run ID is unsafe for a provenance ref")
    return f"refs/heads/exp-provenance/{run_id}"


class GitRemoteProvenanceBackend:
    """Production backend; ordinary push enforces fast-forward remote updates."""

    def __init__(self, remote: str):
        if not remote or remote.startswith("-"):
            raise ValueError("EXP-019 requires an explicit remote Git provenance target")
        self.remote = remote

    def _head(self, ref: str) -> str | None:
        lines = _git("ls-remote", self.remote, ref).splitlines()
        matches = [line.split()[0] for line in lines if len(line.split()) == 2 and line.split()[1] == ref]
        if len(matches) > 1:
            raise ValueError("EXP-019 remote provenance ref is ambiguous")
        return matches[0] if matches else None

    def _fetch(self, repo: Path, ref: str) -> str:
        _git("fetch", "--no-tags", self.remote, ref, git_dir=repo)
        return _git("rev-parse", "FETCH_HEAD", git_dir=repo)

    def _commit(self, repo: Path, record: dict, parent: str | None) -> str:
        blob = _git("hash-object", "-w", "--stdin", git_dir=repo, input_bytes=_bytes(record))
        tree = _git("mktree", git_dir=repo, input_bytes=f"100644 blob {blob}\tcheckpoint.json\n".encode())
        args = ["commit-tree", tree]
        if parent:
            args += ["-p", parent]
        return _git(*args, "-m", "EXP-019 provenance checkpoint", git_dir=repo)

    def _temporary_repo(self):
        return tempfile.TemporaryDirectory(prefix="aipf-exp019-git-")

    def append(self, ref: str, expected_head: str | None, record: dict) -> str:
        with self._temporary_repo() as directory:
            repo = Path(directory) / "objects.git"
            _git("init", "--bare", "-q", str(repo))
            head = self._head(ref)
            if head != expected_head:
                raise ValueError("EXP-019 remote provenance head moved or disappeared")
            if head and self._fetch(repo, ref) != head:
                raise ValueError("EXP-019 fetched provenance head changed")
            commit = self._commit(repo, record, head)
            _git("push", self.remote, f"{commit}:{ref}", git_dir=repo)
            if self._head(ref) != commit or self._fetch(repo, ref) != commit:
                raise ValueError("EXP-019 remote provenance push was not verified")
            return commit

    def verify(self, ref: str, checkpoints: list[dict]) -> str:
        if not checkpoints:
            raise ValueError("EXP-019 has no remote provenance root")
        head = self._head(ref)
        if head is None or head != checkpoints[-1]["commit"]:
            raise ValueError("EXP-019 remote provenance ref missing or unexpectedly moved")
        with self._temporary_repo() as directory:
            repo = Path(directory) / "objects.git"
            _git("init", "--bare", "-q", str(repo))
            if self._fetch(repo, ref) != head:
                raise ValueError("EXP-019 fetched remote provenance differs from advertised head")
            commit = head
            for checkpoint in reversed(checkpoints):
                if commit != checkpoint["commit"]:
                    raise ValueError("EXP-019 provenance chain commit mismatch")
                entries = _git("ls-tree", "--name-only", commit, git_dir=repo).splitlines()
                if entries != ["checkpoint.json"]:
                    raise ValueError("EXP-019 provenance commit contains unexpected files")
                record = json.loads(_git("show", f"{commit}:checkpoint.json", git_dir=repo))
                if set(record) != _FIELDS or record != checkpoint["record"]:
                    raise ValueError("EXP-019 remote checkpoint differs from local expectation")
                parents = _git("rev-list", "--parents", "-n", "1", commit, git_dir=repo).split()
                if len(parents) not in (1, 2):
                    raise ValueError("EXP-019 provenance history is not linear")
                parent = parents[1] if len(parents) == 2 else None
                if parent != record["previous_anchor_commit"]:
                    raise ValueError("EXP-019 provenance checkpoint parent mismatch")
                commit = parent
            if commit is not None:
                raise ValueError("EXP-019 provenance history has an unexpected earlier checkpoint")
        return head


def _backend() -> GitRemoteProvenanceBackend:
    remote = os.environ.get(REMOTE_ENV)
    if not remote:
        raise ValueError(f"EXP-019 production execution requires {REMOTE_ENV}")
    return GitRemoteProvenanceBackend(remote)


def _state_path(root: Path) -> Path:
    return root / ".provenance-private" / STATE_NAME


def _load_state(root: Path, run: dict, backend: GitRemoteProvenanceBackend) -> dict:
    path = _state_path(root)
    if not path.is_file():
        raise ValueError("EXP-019 external provenance state missing; never reinitialize an existing run")
    state = json.loads(path.read_text(encoding="utf-8"))
    if (state.get("backend") != "remote_git" or state.get("run_id") != run["run_id"]
            or state.get("ref") != _ref(run["run_id"])
            or state.get("remote_sha256") != _sha(backend.remote.encode("utf-8"))):
        raise ValueError("EXP-019 external provenance configuration changed")
    return state


def _save_state(root: Path, state: dict, *, new: bool = False) -> None:
    path = _state_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    if new:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(state, handle, indent=2)
            handle.write("\n")
    else:
        from .experiment_execution import _write_json_atomic
        _write_json_atomic(path, state)


def _attempt_digest(root: Path, run: dict, slot_id: str, number: int) -> str:
    variant, output = find_slot(run, slot_id)
    position = next(s["position"] for s in run["invocation_order"] if s["blind_id"] == slot_id)
    if run["experiment_version"] == "1.1.0":
        from .exp019_host import verify_host_attempts
        verify_host_attempts(root, run, output, position)
    else:
        from .exp019_execution import _verify_prior_receipts
        _verify_prior_receipts(root, run, variant, output, position)
    if number < 1 or number > len(output.get("receipt_history", [])):
        raise ValueError("EXP-019 anchored attempt is absent from canonical ledger")
    binding = output["receipt_history"][number - 1]
    events = output["attempt_events"][:number * 2]
    if len(events) != number * 2:
        raise ValueError("EXP-019 anchored attempt event prefix is incomplete")
    outcome = events[-1]
    evidence = {"run_id": run["run_id"], "slot_id": slot_id, "attempt_number": number,
                "receipt_file_sha256": sha256_file(root / binding["file"]),
                "attempt_events": events, "output_image_sha256": outcome.get("image_sha256")}
    if run["experiment_version"] == "1.1.0":
        evidence["operator_receipt_sha256"] = sha256_file(root / binding["operator_file"])
    else:
        evidence["commitment_file_sha256"] = sha256_file(root / binding["commitment_file"])
    if outcome["event"] == "success":
        image = root / "outputs" / str(output.get("image"))
        metadata = root / "outputs" / str(output.get("metadata"))
        if not image.is_file() or not metadata.is_file():
            raise ValueError("EXP-019 successful output evidence missing")
        evidence["output_image_sha256"] = sha256_file(image)
        evidence["output_metadata_sha256"] = sha256_file(metadata)
    return _canonical_sha256(evidence)


def _review_digest(root: Path, reviewer_id: str) -> str:
    if reviewer_id not in ("R1", "R2"):
        raise ValueError("EXP-019 unknown reviewer")
    from .exp019_review import verify_freeze_commitment
    verify_freeze_commitment(root, reviewer_id)
    evidence = {"reviewer_id": reviewer_id}
    paths = {"frozen_review_sha256": root / "blind-review" / reviewer_id / "review.frozen.json",
             "mapping_sha256": root / ".review-private" / f"{reviewer_id}.mapping.json",
             "local_commitment_sha256": root / ".review-private" / f"{reviewer_id}.freeze.commitment.json"}
    evidence.update({key: sha256_file(path) for key, path in paths.items()})
    return _canonical_sha256(evidence)


def _evidence_digest(root: Path, run: dict, checkpoint: dict) -> str:
    kind = checkpoint["record"]["event_type"]
    binding = checkpoint["private_binding"]
    if kind == "run_root":
        if binding != {}:
            raise ValueError("EXP-019 root checkpoint has private binding")
        return _canonical_sha256(_plan_core(run))
    if kind == "attempt":
        if set(binding) != {"slot_id", "attempt_number"}:
            raise ValueError("EXP-019 attempt checkpoint binding invalid")
        return _attempt_digest(root, run, binding["slot_id"], binding["attempt_number"])
    if kind == "review_freeze":
        if set(binding) != {"reviewer_id"}:
            raise ValueError("EXP-019 review checkpoint binding invalid")
        return _review_digest(root, binding["reviewer_id"])
    raise ValueError("EXP-019 unknown provenance event type")


def verify_external(run_file: str | Path, run: dict, *, pending: tuple | None = None,
                    require_reviews: bool = False) -> dict:
    """Fetch the remote chain, then bind every local checkpoint to current evidence."""
    validate_run(run)
    if run.get("external_provenance_initialized") is not True:
        raise ValueError("EXP-019 external provenance was not initialized")
    root = Path(run_file).expanduser().resolve().parent
    backend = _backend()
    state = _load_state(root, run, backend)
    checkpoints = state.get("checkpoints", [])
    if not checkpoints or state.get("head_commit") != checkpoints[-1].get("commit") or state.get("root_commit") != checkpoints[0].get("commit"):
        raise ValueError("EXP-019 local provenance checkpoint index invalid")
    attempt_keys = []
    for slot in run["invocation_order"]:
        _variant, output = find_slot(run, slot["blind_id"])
        history = output.get("receipt_history", [])
        if len(history) != sum(event.get("event") != "started" for event in output["attempt_events"]):
            raise ValueError("EXP-019 attempt event lacks an external-checkpointable receipt")
        attempt_keys += [("attempt", slot["blind_id"], n) for n in range(1, len(history) + 1)]
    frozen_reviews = {reviewer for reviewer in ("R1", "R2")
                      if (root / "blind-review" / reviewer / "review.frozen.json").exists()}
    indexed_keys = []
    for index, checkpoint in enumerate(checkpoints):
        record = checkpoint.get("record", {})
        if (set(record) != _FIELDS or record.get("schema_version") != "1.0.0"
                or record.get("run_id") != run["run_id"] or record.get("sequence") != index
                or record.get("previous_anchor_commit") != (checkpoints[index - 1]["commit"] if index else None)
                or record.get("evidence_sha256") != _evidence_digest(root, run, checkpoint)):
            raise ValueError("EXP-019 local evidence differs from external checkpoint expectation")
        if index:
            binding = checkpoint["private_binding"]
            if record["event_type"] == "attempt":
                indexed_keys.append(("attempt", binding["slot_id"], binding["attempt_number"]))
            elif record["event_type"] == "review_freeze":
                indexed_keys.append(("review_freeze", binding["reviewer_id"]))
            else:
                raise ValueError("EXP-019 invalid checkpoint event order")
    if checkpoints[0]["record"]["event_type"] != "run_root":
        raise ValueError("EXP-019 remote provenance checkpoint sequence differs from evidence")
    if indexed_keys[:min(len(indexed_keys), len(attempt_keys))] != attempt_keys[:len(indexed_keys)]:
        raise ValueError("EXP-019 attempt checkpoints differ from frozen order")
    anchored_reviews = indexed_keys[len(attempt_keys):]
    if (len(indexed_keys) < len(attempt_keys) and anchored_reviews
            or any(key[0] != "review_freeze" for key in anchored_reviews)
            or len(set(anchored_reviews)) != len(anchored_reviews)
            or {key[1] for key in anchored_reviews} - frozen_reviews):
        raise ValueError("EXP-019 reviewer checkpoint sequence invalid")
    expected_keys = attempt_keys + anchored_reviews + (
        [pending] if pending and pending[0] == "review_freeze" else []
    )
    if pending is None and (indexed_keys != expected_keys or {key[1] for key in anchored_reviews} != frozen_reviews):
        raise ValueError("EXP-019 local evidence has no external checkpoint")
    if pending is not None and pending[0] == "attempt" and indexed_keys + [pending] != attempt_keys:
        raise ValueError("EXP-019 unexpected unanchored attempt before append")
    if pending is not None and pending[0] == "review_freeze" and (
            indexed_keys != attempt_keys + anchored_reviews or expected_keys != attempt_keys + anchored_reviews + [pending]
            or {key[1] for key in anchored_reviews + [pending]} != frozen_reviews):
        raise ValueError("EXP-019 unexpected unanchored evidence before append")
    if require_reviews and not all(("review_freeze", reviewer) in indexed_keys for reviewer in ("R1", "R2")):
        raise ValueError("both EXP-019 reviews need externally verified freeze checkpoints")
    backend.verify(state["ref"], checkpoints)
    return state


def ensure_run_root(run_file: str | Path, run: dict) -> dict:
    root = Path(run_file).expanduser().resolve().parent
    backend = _backend()
    path = _state_path(root)
    if path.exists():
        if run.get("external_provenance_initialized") is not True:
            raise ValueError("EXP-019 run lost its external-provenance initialization marker")
        return verify_external(run_file, run)
    if (run.get("external_provenance_initialized") is True or run.get("status") != "planned"
            or any(o.get("attempt_events") for v in run["variants"] for o in v["outputs"])):
        raise ValueError("EXP-019 cannot initialize provenance after execution started")
    ref = _ref(run["run_id"])
    if backend._head(ref) is not None:
        raise ValueError("EXP-019 run ID already has a remote provenance ref")
    record = {"schema_version": "1.0.0", "run_id": run["run_id"], "sequence": 0,
              "event_type": "run_root", "evidence_sha256": _canonical_sha256(_plan_core(run)),
              "previous_anchor_commit": None}
    commit = backend.append(ref, None, record)
    state = {"backend": "remote_git", "run_id": run["run_id"], "ref": ref,
             "remote_sha256": _sha(backend.remote.encode("utf-8")),
             "root_commit": commit, "head_commit": commit,
             "checkpoints": [{"commit": commit, "record": record, "private_binding": {}}]}
    _save_state(root, state, new=True)
    run["external_provenance_initialized"] = True
    from .experiment_execution import _write_json_atomic
    _write_json_atomic(Path(run_file).expanduser().resolve(), run)
    return verify_external(run_file, run)


def _append(run_file: str | Path, run: dict, event_type: str, private_binding: dict,
            pending: tuple) -> dict:
    root = Path(run_file).expanduser().resolve().parent
    state = verify_external(run_file, run, pending=pending)
    backend = _backend()
    record = {"schema_version": "1.0.0", "run_id": run["run_id"],
              "sequence": len(state["checkpoints"]), "event_type": event_type,
              "evidence_sha256": _evidence_digest(root, run, {"record": {"event_type": event_type}, "private_binding": private_binding}),
              "previous_anchor_commit": state["head_commit"]}
    commit = backend.append(state["ref"], state["head_commit"], record)
    state["checkpoints"].append({"commit": commit, "record": record, "private_binding": private_binding})
    state["head_commit"] = commit
    _save_state(root, state)
    return verify_external(run_file, run)


def append_attempt_checkpoint(run_file: str | Path, run: dict, slot_id: str, number: int) -> dict:
    return _append(run_file, run, "attempt", {"slot_id": slot_id, "attempt_number": number},
                   ("attempt", slot_id, number))


def append_review_checkpoint(run_file: str | Path, run: dict, reviewer_id: str) -> dict:
    return _append(run_file, run, "review_freeze", {"reviewer_id": reviewer_id},
                   ("review_freeze", reviewer_id))


def run_receipt_provenance(run_file: str | Path, run: dict) -> dict:
    state = verify_external(run_file, run)
    attempts = [c for c in state["checkpoints"] if c["record"]["event_type"] in {"run_root", "attempt"}]
    return {"backend": "remote_git", "ref": state["ref"],
            "root_anchor_commit": state["root_commit"],
            "terminal_anchor_commit": attempts[-1]["commit"],
            "checkpoints": [{"commit": c["commit"], "sequence": c["record"]["sequence"],
                             "event_type": c["record"]["event_type"],
                             "evidence_sha256": c["record"]["evidence_sha256"]} for c in attempts]}
