"""EXP-019 v1.2 external provenance checkpoint publisher and verifier (PR-9).

Publishes and verifies the existing six-field public checkpoint records
against an isolated Git remote. This module is version-specific: it does
not modify v1.1.1 ``exp019_anchor`` semantics or the historical chain.

Public record fields (exactly these six)::

    schema_version, run_id, sequence, event_type,
    evidence_sha256, previous_anchor_commit

Approved v1.2 ``event_type`` values::

    run_root, attempt, review_freeze, run_disposition

Opaque slot identifiers, treatment assignments, prompt contents,
conflict details, reviewer mappings, and private evidence paths never
appear in public checkpoint fields; they stay in authorized private
bindings only.

Activation boundaries (G4/G5 remain unauthorized):

* Production publication against the real EXP-019 provenance remote is
  refused while v1.2 is unregistered / scientifically inactive.
* Synthetic exercise requires an explicit synthetic remote backend and
  never interprets a caller boolean as external anchoring proof.
* An anchored digest proves remote binding of bytes, never that host-side
  factual claims are true.

Lifecycle integration consumes the immutable terminal receipt binding
from PR-8; this module does not create a competing terminal receipt or
attempt-state manager.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Optional, Sequence

from .exp019_protocol import frozen_protocol

# Public six-field contract — identical field set to v1.1.1.
PUBLIC_FIELDS = frozenset({
    "schema_version", "run_id", "sequence", "event_type",
    "evidence_sha256", "previous_anchor_commit",
})
PUBLIC_SCHEMA_VERSION = "1.0.0"
V12_EVENT_TYPES = frozenset({
    "run_root", "attempt", "review_freeze", "run_disposition",
})

# Synthetic-only exercise. Production uses AIPF_EXP019_PROVENANCE_REMOTE
# for v1.1.1; v1.2 must not publish there while scientifically inactive.
SYNTHETIC_ENV = "AIPF_EXP019_V12_SYNTHETIC_PROVENANCE"
PRODUCTION_REMOTE_ENV = "AIPF_EXP019_PROVENANCE_REMOTE"

_STATE_DIR_NAME = "v1_2-checkpoint-state"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Mapping) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False,
                       separators=(",", ":")) + "\n").encode("utf-8")


def _git(*args: str, git_dir: Path | None = None,
         input_bytes: bytes | None = None) -> str:
    command = ["git"] + ([f"--git-dir={git_dir}"] if git_dir else []) + list(
        args)
    environment = os.environ.copy()
    environment.update(
        GIT_AUTHOR_NAME="AIPF provenance",
        GIT_AUTHOR_EMAIL="provenance@aipf.invalid",
        GIT_COMMITTER_NAME="AIPF provenance",
        GIT_COMMITTER_EMAIL="provenance@aipf.invalid",
        GIT_TERMINAL_PROMPT="0",
    )
    result = subprocess.run(
        command, input=input_bytes, capture_output=True, env=environment)
    if result.returncode:
        # Remote URLs can contain credentials; never echo arguments.
        raise ValueError(
            f"EXP-019 v1.2 provenance Git {args[0]} failed "
            f"(exit {result.returncode})")
    return result.stdout.decode("utf-8").strip()


def _ref(run_id: str) -> str:
    if not run_id or any(
            c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
                     "0123456789._-"
            for c in run_id):
        raise ValueError("EXP-019 v1.2 run ID is unsafe for a provenance ref")
    return f"refs/heads/exp-provenance/{run_id}"


def _normalize_remote_identity(remote: str) -> str:
    """Normalize Git remote URLs/paths for equivalence comparison.

    Collapses https/ssh/scp-style forms of the same host+path so that
    ``https://github.com/org/repo.git`` and ``git@github.com:org/repo.git``
    compare equal. Local filesystem paths are resolved canonically.
    """
    value = (remote or "").strip()
    if not value:
        return ""
    lowered = value.replace("\\", "/")
    # Strip credentials: scheme://user:pass@host/...
    if "://" in lowered:
        scheme, rest = lowered.split("://", 1)
        if "@" in rest and "/" in rest.split("@", 1)[1]:
            rest = rest.split("@", 1)[1]
        lowered = f"{scheme}://{rest}"
    # scp-style: git@host:path
    if "://" not in lowered and "@" in lowered and ":" in lowered.split(
            "@", 1)[1]:
        user_host, path = lowered.split(":", 1)
        host = user_host.split("@", 1)[-1]
        lowered = f"ssh://{host}/{path.lstrip('/')}"
    # https://host/path or ssh://host/path
    if "://" in lowered:
        _, rest = lowered.split("://", 1)
        host_path = rest.lower().rstrip("/")
        if host_path.endswith(".git"):
            host_path = host_path[:-4]
        return host_path
    # Local filesystem path — resolve when possible.
    try:
        return str(Path(value).expanduser().resolve()).replace("\\", "/").lower()
    except OSError:
        return lowered.lower()


def _is_network_remote(remote: str) -> bool:
    lowered = (remote or "").strip().lower().replace("\\", "/")
    if "://" in lowered:
        scheme = lowered.split("://", 1)[0]
        return scheme in {"http", "https", "ssh", "git"}
    if "@" in lowered and ":" in lowered.split("@", 1)[-1]:
        return True
    return False


def _assert_synthetic_remote_allowed(remote: str) -> None:
    """Refuse network/production remotes for pre-G5 synthetic publication.

    Synthetic exercise is limited to existing local bare Git directories.
    Network URLs (including URL-form mismatches against the production
    env) cannot bypass this boundary. The AST activation guard is
    defense-in-depth only — this check is mandatory.
    """
    if not remote or remote.startswith("-"):
        raise ValueError(
            "EXP-019 v1.2 requires an explicit synthetic Git remote")
    if _is_network_remote(remote):
        raise PermissionError(
            "synthetic v1.2 publication refuses network Git remotes; "
            "use an isolated local temporary bare repository only")
    path = Path(remote).expanduser()
    try:
        resolved = path.resolve()
    except OSError as exc:
        raise PermissionError(
            "synthetic v1.2 remote path cannot be resolved") from exc
    if not resolved.exists() or not resolved.is_dir():
        raise PermissionError(
            "synthetic v1.2 remote must be an existing local bare Git "
            "directory")
    # Refuse if the path identity matches the configured production remote
    # under any URL/path normalization.
    production = os.environ.get(PRODUCTION_REMOTE_ENV)
    if production:
        if _normalize_remote_identity(str(resolved)) == \
                _normalize_remote_identity(production):
            raise PermissionError(
                "refusing to publish v1.2 checkpoints to the configured "
                "production EXP-019 provenance remote")
        # Also refuse when production is a local path that is the same dir.
        try:
            prod_path = Path(production).expanduser().resolve()
            if prod_path == resolved:
                raise PermissionError(
                    "refusing to publish v1.2 checkpoints to the configured "
                    "production EXP-019 provenance remote")
        except OSError:
            pass


def v12_scientifically_active() -> bool:
    """True only when a frozen v1.2 protocol is registered (G5)."""
    try:
        frozen_protocol("1.2.0")
        return True
    except ValueError:
        return False


def assert_production_publication_refused() -> None:
    """Fail closed: production v1.2 publication is unauthorized pre-G5."""
    if not v12_scientifically_active():
        raise PermissionError(
            "EXP-019 v1.2 external checkpoint publication is refused: "
            "v1.2 remains unregistered and scientifically inactive "
            "(G4/G5 unauthorized)")


def build_public_record(*, run_id: str, sequence: int, event_type: str,
                        evidence_sha256: str,
                        previous_anchor_commit: Optional[str]) -> dict:
    """Construct the six-field public checkpoint record."""
    if event_type not in V12_EVENT_TYPES:
        raise ValueError(
            f"unsupported v1.2 checkpoint event_type: {event_type!r}; "
            "provenance_adjudication and other speculative types are "
            "not implemented")
    if not isinstance(evidence_sha256, str) or len(evidence_sha256) != 64:
        raise ValueError("evidence_sha256 must be a 64-char hex digest")
    record = {
        "schema_version": PUBLIC_SCHEMA_VERSION,
        "run_id": run_id,
        "sequence": sequence,
        "event_type": event_type,
        "evidence_sha256": evidence_sha256,
        "previous_anchor_commit": previous_anchor_commit,
    }
    if set(record) != PUBLIC_FIELDS:
        raise ValueError("public checkpoint must contain exactly six fields")
    return record


def attempt_evidence_digest(receipt_sha256: str) -> str:
    """Bind an attempt checkpoint to the immutable terminal receipt."""
    if not isinstance(receipt_sha256, str) or len(receipt_sha256) != 64:
        raise ValueError("receipt_sha256 must be a 64-char hex digest")
    return _sha256(_canonical({
        "binding": "terminal_attempt_receipt",
        "receipt_sha256": receipt_sha256,
        "experiment_version": "1.2.0",
    }))


def run_root_evidence_digest(run_id: str, plan_commitment_sha256: str) -> str:
    return _sha256(_canonical({
        "binding": "run_root",
        "run_id": run_id,
        "plan_commitment_sha256": plan_commitment_sha256,
        "experiment_version": "1.2.0",
    }))


def review_freeze_evidence_digest(reviewer_id: str,
                                  freeze_commitment_sha256: str) -> str:
    return _sha256(_canonical({
        "binding": "review_freeze",
        "reviewer_id": reviewer_id,
        "freeze_commitment_sha256": freeze_commitment_sha256,
        "experiment_version": "1.2.0",
    }))


def run_disposition_evidence_digest(run_id: str, disposition: str,
                                    closure_commitment_sha256: str) -> str:
    return _sha256(_canonical({
        "binding": "run_disposition",
        "run_id": run_id,
        "disposition": disposition,
        "closure_commitment_sha256": closure_commitment_sha256,
        "experiment_version": "1.2.0",
    }))


@dataclass(frozen=True)
class OrderingFinding:
    code: str
    message: str


def verify_event_ordering(
        records: Sequence[Mapping], *,
        expected_attempt_keys: Sequence[tuple] | None = None,
        run_closed: bool = False,
        incomplete_closure: bool = False,
        review_freeze_reviewers: Sequence[str] | None = None,
) -> tuple[bool, tuple[OrderingFinding, ...]]:
    """Verify deterministic v1.2 checkpoint ordering (B2).

    ``expected_attempt_keys`` is an ordered sequence of
    ``(slot_id, attempt_number)`` private keys — never placed in public
    fields; callers supply them from private state for verification.
    """
    findings: list[OrderingFinding] = []

    def add(code: str, message: str) -> None:
        findings.append(OrderingFinding(code, message))

    if not records:
        add("EMPTY_CHAIN", "checkpoint chain is empty")
        return False, tuple(findings)

    for index, record in enumerate(records):
        if set(record) != PUBLIC_FIELDS:
            add("FIELD_SET", f"sequence {index} is not a six-field record")
        if record.get("schema_version") != PUBLIC_SCHEMA_VERSION:
            add("SCHEMA_VERSION", f"sequence {index} schema_version invalid")
        if record.get("sequence") != index:
            add("SEQUENCE_GAP",
                f"sequence must be contiguous; expected {index}")
        if record.get("event_type") not in V12_EVENT_TYPES:
            add("EVENT_TYPE", f"sequence {index} has unsupported event_type")
        if index == 0:
            if record.get("event_type") != "run_root":
                add("RUN_ROOT_FIRST", "exactly one run_root must be first")
            if record.get("previous_anchor_commit") is not None:
                add("ROOT_PARENT", "run_root previous_anchor_commit must be null")
        else:
            if record.get("event_type") == "run_root":
                add("RUN_ROOT_DUPLICATE", "exactly one run_root is permitted")
            prev = records[index - 1]
            if record.get("previous_anchor_commit") is None:
                add("PARENT_MISSING",
                    f"sequence {index} missing previous_anchor_commit")

    run_roots = [r for r in records if r.get("event_type") == "run_root"]
    if len(run_roots) != 1:
        add("RUN_ROOT_COUNT", "exactly one run_root is required")

    dispositions = [
        (i, r) for i, r in enumerate(records)
        if r.get("event_type") == "run_disposition"]
    if len(dispositions) > 1:
        add("DISPOSITION_DUPLICATE",
            "run_disposition may appear at most once")
    if dispositions:
        disp_index = dispositions[0][0]
        if disp_index != len(records) - 1:
            add("DISPOSITION_NOT_TERMINAL",
                "no event may be appended after run_disposition")
        if not run_closed:
            add("DISPOSITION_WITHOUT_CLOSURE",
                "run_disposition requires a formally closed run")

    attempt_records = [
        r for r in records if r.get("event_type") == "attempt"]
    review_records = [
        r for r in records if r.get("event_type") == "review_freeze"]

    # Review-freeze only after the attempt phase has completed.
    if review_records:
        first_review = next(
            i for i, r in enumerate(records)
            if r.get("event_type") == "review_freeze")
        later_attempt = any(
            r.get("event_type") == "attempt"
            for r in records[first_review + 1:])
        if later_attempt:
            add("REVIEW_BEFORE_ATTEMPTS_DONE",
                "review_freeze may not precede completion of the "
                "permitted attempt phase")
        if expected_attempt_keys is not None and \
                len(attempt_records) < len(expected_attempt_keys):
            add("REVIEW_BEFORE_ATTEMPTS_DONE",
                "review_freeze before all finalized attempts are "
                "checkpointed")

    if expected_attempt_keys is not None:
        if len(attempt_records) > len(expected_attempt_keys):
            add("ATTEMPT_WITHOUT_INVOCATION",
                "attempt checkpoint without a finalized generation "
                "invocation")
        if len(attempt_records) < len(expected_attempt_keys) and \
                (run_closed and not incomplete_closure):
            add("ATTEMPT_MISSING",
                "completed run missing attempt checkpoints")

    if run_closed and not incomplete_closure and not dispositions:
        add("DISPOSITION_MISSING",
            "formally closed completed run requires run_disposition")

    if incomplete_closure and review_records and not dispositions:
        # Incomplete closure may omit review-freeze; if reviews exist they
        # must still obey ordering — no extra finding.
        pass

    if review_freeze_reviewers is not None:
        # Private reviewer ids are counted, never published.
        if len(review_records) > len(set(review_freeze_reviewers)):
            add("REVIEW_DUPLICATE", "duplicate review_freeze checkpoints")

    return (not findings), tuple(findings)


@dataclass(frozen=True)
class PublicationResult:
    """Outcome of a publication attempt (separate from verification)."""

    published: bool
    commit: Optional[str]
    recognized_existing: bool
    expected_head: Optional[str]
    remote_head: Optional[str]
    record: Mapping
    message: str = ""


@dataclass(frozen=True)
class VerificationResult:
    """Authenticated/verifiable anchoring result after remote checks.

    ``verified`` is set only after inspecting the expected remote Git
    history and bound evidence digest. A caller boolean is never enough.
    An externally anchored digest does not prove host-side factual claims.
    """

    verified: bool
    head_commit: Optional[str]
    evidence_sha256: Optional[str]
    codes: tuple[str, ...] = ()
    message: str = ""
    factual_claim_proven: bool = False  # always False by design


class SyntheticGitBackend:
    """Fast-forward Git backend for isolated temporary remotes only."""

    def __init__(self, remote: str):
        _assert_synthetic_remote_allowed(remote)
        self.remote = remote

    def head(self, ref: str) -> Optional[str]:
        lines = _git("ls-remote", self.remote, ref).splitlines()
        matches = [
            line.split()[0] for line in lines
            if len(line.split()) == 2 and line.split()[1] == ref]
        if len(matches) > 1:
            raise ValueError("EXP-019 v1.2 remote provenance ref is ambiguous")
        return matches[0] if matches else None

    def _fetch(self, repo: Path, ref: str) -> str:
        _git("fetch", "--no-tags", self.remote, ref, git_dir=repo)
        return _git("rev-parse", "FETCH_HEAD", git_dir=repo)

    def _commit(self, repo: Path, record: dict, parent: Optional[str]) -> str:
        blob = _git("hash-object", "-w", "--stdin", git_dir=repo,
                    input_bytes=_canonical(record))
        tree = _git(
            "mktree", git_dir=repo,
            input_bytes=f"100644 blob {blob}\tcheckpoint.json\n".encode())
        args = ["commit-tree", tree]
        if parent:
            args += ["-p", parent]
        return _git(*args, "-m", "EXP-019 v1.2 provenance checkpoint",
                    git_dir=repo)

    def read_record(self, ref: str, commit: str) -> dict:
        with tempfile.TemporaryDirectory(prefix="aipf-v12-git-") as directory:
            repo = Path(directory) / "objects.git"
            _git("init", "--bare", "-q", str(repo))
            if self._fetch(repo, ref) != commit and self.head(ref) != commit:
                # Head may have moved; still try to materialize the commit
                # via fetch of the ref tip first.
                tip = self.head(ref)
                if tip is None:
                    raise ValueError("EXP-019 v1.2 remote ref missing")
                self._fetch(repo, ref)
            entries = _git("ls-tree", "--name-only", commit,
                           git_dir=repo).splitlines()
            if entries != ["checkpoint.json"]:
                raise ValueError(
                    "EXP-019 v1.2 provenance commit contains unexpected files")
            return json.loads(
                _git("show", f"{commit}:checkpoint.json", git_dir=repo))

    def append(self, ref: str, expected_head: Optional[str],
               record: dict) -> PublicationResult:
        """Durable append with expected-head and idempotent recognition."""
        with tempfile.TemporaryDirectory(prefix="aipf-v12-git-") as directory:
            repo = Path(directory) / "objects.git"
            _git("init", "--bare", "-q", str(repo))
            head = self.head(ref)
            if head != expected_head:
                # Ambiguous / unexpected movement — stop safely unless the
                # remote already holds the intended record (interrupted
                # push whose remote commit succeeded).
                if head is not None:
                    try:
                        existing = self.read_record(ref, head)
                    except ValueError:
                        return PublicationResult(
                            published=False, commit=None,
                            recognized_existing=False,
                            expected_head=expected_head, remote_head=head,
                            record=record,
                            message="remote head moved unexpectedly; "
                                    "publication stopped safely")
                    if existing == record and \
                            existing.get("previous_anchor_commit") == \
                            expected_head:
                        return PublicationResult(
                            published=True, commit=head,
                            recognized_existing=True,
                            expected_head=expected_head, remote_head=head,
                            record=record,
                            message="recognized existing remote checkpoint "
                                    "after interrupted publication")
                return PublicationResult(
                    published=False, commit=None,
                    recognized_existing=False,
                    expected_head=expected_head, remote_head=head,
                    record=record,
                    message="remote head moved or disappeared; "
                            "publication stopped safely")

            if head and self._fetch(repo, ref) != head:
                return PublicationResult(
                    published=False, commit=None,
                    recognized_existing=False,
                    expected_head=expected_head, remote_head=head,
                    record=record,
                    message="fetched provenance head changed; stopped")

            commit = self._commit(repo, record, head)
            push = subprocess.run(
                ["git", f"--git-dir={repo}", "push", self.remote,
                 f"{commit}:{ref}"],
                capture_output=True,
                env={**os.environ,
                     "GIT_TERMINAL_PROMPT": "0",
                     "GIT_AUTHOR_NAME": "AIPF provenance",
                     "GIT_AUTHOR_EMAIL": "provenance@aipf.invalid",
                     "GIT_COMMITTER_NAME": "AIPF provenance",
                     "GIT_COMMITTER_EMAIL": "provenance@aipf.invalid"},
            )
            # A failed network request is not proof the push failed.
            remote_after = self.head(ref)
            if push.returncode != 0:
                if remote_after == commit:
                    return PublicationResult(
                        published=True, commit=commit,
                        recognized_existing=True,
                        expected_head=expected_head, remote_head=remote_after,
                        record=record,
                        message="push reported failure but remote already "
                                "contains the intended checkpoint")
                if remote_after == expected_head or remote_after is None:
                    return PublicationResult(
                        published=False, commit=None,
                        recognized_existing=False,
                        expected_head=expected_head, remote_head=remote_after,
                        record=record,
                        message="push failed and remote lacks the intended "
                                "checkpoint; safe to retry")
                return PublicationResult(
                    published=False, commit=None,
                    recognized_existing=False,
                    expected_head=expected_head, remote_head=remote_after,
                    record=record,
                    message="push outcome ambiguous; publication stopped")

            # Fetch-back verification.
            try:
                fetched = self._fetch(repo, ref)
            except ValueError:
                return PublicationResult(
                    published=False, commit=commit,
                    recognized_existing=False,
                    expected_head=expected_head, remote_head=remote_after,
                    record=record,
                    message="push succeeded locally but fetch-back failed; "
                            "state ambiguous — stop safely")
            if remote_after != commit or fetched != commit:
                return PublicationResult(
                    published=False, commit=commit,
                    recognized_existing=False,
                    expected_head=expected_head, remote_head=remote_after,
                    record=record,
                    message="remote push was not verified on fetch-back")
            return PublicationResult(
                published=True, commit=commit, recognized_existing=False,
                expected_head=expected_head, remote_head=commit,
                record=record, message="published and fetch-back verified")

    def verify_chain(self, ref: str,
                     checkpoints: Sequence[Mapping]) -> VerificationResult:
        """Verify linear remote history against expected checkpoint records.

        ``checkpoints`` entries are ``{"commit": str, "record": dict}``.
        """
        if not checkpoints:
            return VerificationResult(
                verified=False, head_commit=None, evidence_sha256=None,
                codes=("NO_ROOT",), message="no remote provenance root")
        head = self.head(ref)
        expected_head = checkpoints[-1]["commit"]
        if head is None or head != expected_head:
            return VerificationResult(
                verified=False, head_commit=head, evidence_sha256=None,
                codes=("HEAD_MISMATCH",),
                message="remote provenance ref missing or unexpectedly moved")
        with tempfile.TemporaryDirectory(prefix="aipf-v12-git-") as directory:
            repo = Path(directory) / "objects.git"
            _git("init", "--bare", "-q", str(repo))
            try:
                if self._fetch(repo, ref) != head:
                    return VerificationResult(
                        verified=False, head_commit=head,
                        evidence_sha256=None, codes=("FETCH_MISMATCH",),
                        message="fetched remote provenance differs from "
                                "advertised head")
            except ValueError as exc:
                return VerificationResult(
                    verified=False, head_commit=head, evidence_sha256=None,
                    codes=("FETCH_FAILED",), message=str(exc))
            commit = head
            for checkpoint in reversed(list(checkpoints)):
                if commit != checkpoint["commit"]:
                    return VerificationResult(
                        verified=False, head_commit=head,
                        evidence_sha256=None, codes=("COMMIT_MISMATCH",),
                        message="provenance chain commit mismatch")
                entries = _git("ls-tree", "--name-only", commit,
                               git_dir=repo).splitlines()
                if entries != ["checkpoint.json"]:
                    return VerificationResult(
                        verified=False, head_commit=head,
                        evidence_sha256=None, codes=("UNEXPECTED_TREE",),
                        message="provenance commit contains unexpected files")
                record = json.loads(
                    _git("show", f"{commit}:checkpoint.json", git_dir=repo))
                if set(record) != PUBLIC_FIELDS or \
                        record != checkpoint["record"]:
                    return VerificationResult(
                        verified=False, head_commit=head,
                        evidence_sha256=None, codes=("RECORD_MISMATCH",),
                        message="remote checkpoint differs from expectation")
                parents = _git("rev-list", "--parents", "-n", "1", commit,
                               git_dir=repo).split()
                if len(parents) not in (1, 2):
                    return VerificationResult(
                        verified=False, head_commit=head,
                        evidence_sha256=None, codes=("NONLINEAR",),
                        message="provenance history is not linear")
                parent = parents[1] if len(parents) == 2 else None
                if parent != record["previous_anchor_commit"]:
                    return VerificationResult(
                        verified=False, head_commit=head,
                        evidence_sha256=None, codes=("PARENT_MISMATCH",),
                        message="checkpoint parent mismatch")
                commit = parent
            if commit is not None:
                return VerificationResult(
                    verified=False, head_commit=head, evidence_sha256=None,
                    codes=("UNEXPECTED_ANCESTOR",),
                    message="provenance history has an unexpected earlier "
                            "checkpoint")
        return VerificationResult(
            verified=True, head_commit=head,
            evidence_sha256=checkpoints[-1]["record"]["evidence_sha256"],
            codes=(), message="remote history and evidence digest verified",
            factual_claim_proven=False)


@dataclass
class PrivateCheckpointState:
    """Authorized private provenance index (never published)."""

    run_id: str
    ref: str
    remote_sha256: str
    root_commit: Optional[str] = None
    head_commit: Optional[str] = None
    closed: bool = False
    incomplete_closure: bool = False
    checkpoints: list = field(default_factory=list)
    # Private attempt keys in frozen order: (slot_id, attempt_number, receipt_sha256)
    finalized_attempts: list = field(default_factory=list)
    review_freeze_reviewers: list = field(default_factory=list)

    def public_records(self) -> list:
        return [entry["record"] for entry in self.checkpoints]

    def to_dict(self) -> dict:
        return {
            "backend": "remote_git_v1_2_synthetic",
            "run_id": self.run_id,
            "ref": self.ref,
            "remote_sha256": self.remote_sha256,
            "root_commit": self.root_commit,
            "head_commit": self.head_commit,
            "closed": self.closed,
            "incomplete_closure": self.incomplete_closure,
            "checkpoints": self.checkpoints,
            "finalized_attempts": self.finalized_attempts,
            "review_freeze_reviewers": self.review_freeze_reviewers,
        }

    @classmethod
    def from_dict(cls, data: Mapping) -> "PrivateCheckpointState":
        return cls(
            run_id=data["run_id"],
            ref=data["ref"],
            remote_sha256=data["remote_sha256"],
            root_commit=data.get("root_commit"),
            head_commit=data.get("head_commit"),
            closed=bool(data.get("closed")),
            incomplete_closure=bool(data.get("incomplete_closure")),
            checkpoints=list(data.get("checkpoints") or []),
            finalized_attempts=list(data.get("finalized_attempts") or []),
            review_freeze_reviewers=list(
                data.get("review_freeze_reviewers") or []),
        )


class CheckpointPublisher:
    """v1.2 external checkpoint publisher (synthetic remotes only pre-G5)."""

    def __init__(self, remote: str, *, synthetic: bool = False,
                 state_dir: Path | None = None):
        if not synthetic:
            assert_production_publication_refused()
            raise PermissionError(
                "non-synthetic v1.2 publication is unauthorized while "
                "G4/G5 remain closed")
        if os.environ.get(SYNTHETIC_ENV) != "1":
            raise PermissionError(
                f"synthetic v1.2 publication requires {SYNTHETIC_ENV}=1")
        # Local-only synthetic remote; never a network URL and never the
        # production provenance target under any URL-form alias.
        _assert_synthetic_remote_allowed(remote)
        self.backend = SyntheticGitBackend(remote)
        self.remote = remote
        self.state_dir = Path(state_dir) if state_dir else None

    def _state_path(self, run_id: str) -> Path:
        if self.state_dir is None:
            raise ValueError("state_dir is required for durable private state")
        # One private state file per run_id — never share across runs.
        safe = _ref(run_id).rsplit("/", 1)[-1]
        return (self.state_dir / ".provenance-private" / _STATE_DIR_NAME /
                f"{safe}.json")

    def load_state(self, run_id: str) -> Optional[PrivateCheckpointState]:
        path = self._state_path(run_id)
        if not path.is_file():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("run_id") != run_id:
            raise ValueError("private checkpoint state run_id mismatch")
        if data.get("remote_sha256") != _sha256(self.remote.encode("utf-8")):
            raise ValueError("private checkpoint remote configuration changed")
        return PrivateCheckpointState.from_dict(data)

    def save_state(self, state: PrivateCheckpointState) -> None:
        path = self._state_path(state.run_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(state.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8", newline="\n")

    def _reject_if_closed(self, state: PrivateCheckpointState) -> None:
        if state.closed or any(
                c["record"]["event_type"] == "run_disposition"
                for c in state.checkpoints):
            raise ValueError(
                "no event may be appended after terminal run disposition")

    def publish_run_root(self, run_id: str,
                         plan_commitment_sha256: str) -> PublicationResult:
        existing = self.load_state(run_id)
        if existing is not None:
            if existing.checkpoints and \
                    existing.checkpoints[0]["record"]["event_type"] == \
                    "run_root":
                return PublicationResult(
                    published=True, commit=existing.root_commit,
                    recognized_existing=True,
                    expected_head=None, remote_head=existing.head_commit,
                    record=existing.checkpoints[0]["record"],
                    message="run_root already present; idempotent")
            raise ValueError("private state exists without a run_root")
        if self.backend.head(_ref(run_id)) is not None:
            raise ValueError(
                "remote already has a provenance ref for this run_id")
        evidence = run_root_evidence_digest(run_id, plan_commitment_sha256)
        record = build_public_record(
            run_id=run_id, sequence=0, event_type="run_root",
            evidence_sha256=evidence, previous_anchor_commit=None)
        result = self.backend.append(_ref(run_id), None, record)
        if not result.published or result.commit is None:
            return result
        state = PrivateCheckpointState(
            run_id=run_id, ref=_ref(run_id),
            remote_sha256=_sha256(self.remote.encode("utf-8")),
            root_commit=result.commit, head_commit=result.commit,
            checkpoints=[{
                "commit": result.commit, "record": record,
                "private_binding": {},
            }],
        )
        self.save_state(state)
        return result

    def register_finalized_attempt(self, run_id: str, slot_id: str,
                                   attempt_number: int,
                                   receipt_sha256: str) -> None:
        """Record a finalized invocation in private state (pre-publish)."""
        state = self.load_state(run_id)
        if state is None:
            raise ValueError("run_root checkpoint required before attempts")
        self._reject_if_closed(state)
        key = [slot_id, attempt_number, receipt_sha256]
        if key in state.finalized_attempts:
            return
        # Distinct retries: same slot + different attempt_number OK.
        for prior in state.finalized_attempts:
            if prior[0] == slot_id and prior[1] == attempt_number:
                if prior[2] != receipt_sha256:
                    raise ValueError(
                        "finalized attempt already bound to a different "
                        "receipt; never regenerate evidence to repair "
                        "publication")
                return
        state.finalized_attempts.append(key)
        self.save_state(state)

    def publish_attempt(self, run_id: str, slot_id: str, attempt_number: int,
                        receipt_sha256: str) -> PublicationResult:
        state = self.load_state(run_id)
        if state is None:
            raise ValueError("run_root checkpoint required before attempts")
        self._reject_if_closed(state)
        key = [slot_id, attempt_number, receipt_sha256]
        if key not in state.finalized_attempts:
            raise ValueError(
                "attempt checkpoint requires an actual finalized generation "
                "invocation bound to a terminal receipt")
        # Exactly one attempt checkpoint per finalized invocation.
        for entry in state.checkpoints:
            binding = entry.get("private_binding") or {}
            if binding.get("slot_id") == slot_id and \
                    binding.get("attempt_number") == attempt_number:
                if binding.get("receipt_sha256") == receipt_sha256:
                    return PublicationResult(
                        published=True, commit=entry["commit"],
                        recognized_existing=True,
                        expected_head=state.head_commit,
                        remote_head=state.head_commit,
                        record=entry["record"],
                        message="attempt checkpoint already present")
                raise ValueError("duplicate attempt checkpoint binding")
        expected_keys = [
            (a[0], a[1]) for a in state.finalized_attempts]
        published_keys = [
            (e["private_binding"]["slot_id"],
             e["private_binding"]["attempt_number"])
            for e in state.checkpoints
            if e["record"]["event_type"] == "attempt"]
        next_key = (slot_id, attempt_number)
        if published_keys + [next_key] != expected_keys[:len(published_keys) + 1]:
            raise ValueError(
                "attempt checkpoints must follow approved frozen slot and "
                "attempt order")
        evidence = attempt_evidence_digest(receipt_sha256)
        record = build_public_record(
            run_id=run_id, sequence=len(state.checkpoints),
            event_type="attempt", evidence_sha256=evidence,
            previous_anchor_commit=state.head_commit)
        # Duplicate-event rejection: identical public record already tip.
        if state.checkpoints and state.checkpoints[-1]["record"] == record:
            raise ValueError("duplicate checkpoint append rejected")
        result = self.backend.append(
            state.ref, state.head_commit, record)
        if not result.published or result.commit is None:
            return result
        state.checkpoints.append({
            "commit": result.commit, "record": record,
            "private_binding": {
                "slot_id": slot_id,
                "attempt_number": attempt_number,
                "receipt_sha256": receipt_sha256,
            },
        })
        state.head_commit = result.commit
        self.save_state(state)
        return result

    def publish_review_freeze(self, run_id: str, reviewer_id: str,
                              freeze_commitment_sha256: str
                              ) -> PublicationResult:
        state = self.load_state(run_id)
        if state is None:
            raise ValueError("run_root required before review_freeze")
        self._reject_if_closed(state)
        attempt_count = sum(
            1 for c in state.checkpoints
            if c["record"]["event_type"] == "attempt")
        if attempt_count < len(state.finalized_attempts):
            raise ValueError(
                "review_freeze before permitted attempt phase completion")
        if reviewer_id in state.review_freeze_reviewers:
            for entry in state.checkpoints:
                binding = entry.get("private_binding") or {}
                if binding.get("reviewer_id") == reviewer_id:
                    return PublicationResult(
                        published=True, commit=entry["commit"],
                        recognized_existing=True,
                        expected_head=state.head_commit,
                        remote_head=state.head_commit,
                        record=entry["record"],
                        message="review_freeze already present")
        evidence = review_freeze_evidence_digest(
            reviewer_id, freeze_commitment_sha256)
        record = build_public_record(
            run_id=run_id, sequence=len(state.checkpoints),
            event_type="review_freeze", evidence_sha256=evidence,
            previous_anchor_commit=state.head_commit)
        result = self.backend.append(state.ref, state.head_commit, record)
        if not result.published or result.commit is None:
            return result
        state.checkpoints.append({
            "commit": result.commit, "record": record,
            "private_binding": {"reviewer_id": reviewer_id},
        })
        state.review_freeze_reviewers.append(reviewer_id)
        state.head_commit = result.commit
        self.save_state(state)
        return result

    def publish_run_disposition(self, run_id: str, disposition: str,
                                closure_commitment_sha256: str, *,
                                incomplete: bool = False
                                ) -> PublicationResult:
        state = self.load_state(run_id)
        if state is None:
            raise ValueError("run_root required before run_disposition")
        self._reject_if_closed(state)
        if disposition not in ("completed", "incomplete"):
            raise ValueError("run disposition must be completed or incomplete")
        if incomplete != (disposition == "incomplete"):
            raise ValueError("incomplete flag disagrees with disposition")
        # Completed closure requires every finalized attempt checkpointed.
        # Incomplete closure may omit review-freeze and unpublished slots,
        # but never invents admitted samples (admission lives in receipts).
        published_attempts = [
            (e["private_binding"]["slot_id"],
             e["private_binding"]["attempt_number"])
            for e in state.checkpoints
            if e["record"]["event_type"] == "attempt"]
        expected_attempts = [
            (a[0], a[1]) for a in state.finalized_attempts]
        if not incomplete and published_attempts != expected_attempts:
            raise ValueError(
                "completed run_disposition requires every finalized "
                "attempt checkpoint before closure")
        # Incomplete closure may omit unpublished attempts and review-freeze;
        # this publisher never invents attempt checkpoints or ADMIT samples.
        evidence = run_disposition_evidence_digest(
            run_id, disposition, closure_commitment_sha256)
        record = build_public_record(
            run_id=run_id, sequence=len(state.checkpoints),
            event_type="run_disposition", evidence_sha256=evidence,
            previous_anchor_commit=state.head_commit)
        result = self.backend.append(state.ref, state.head_commit, record)
        if not result.published or result.commit is None:
            return result
        state.checkpoints.append({
            "commit": result.commit, "record": record,
            "private_binding": {
                "disposition": disposition,
                "incomplete": incomplete,
            },
        })
        state.head_commit = result.commit
        state.closed = True
        state.incomplete_closure = incomplete
        self.save_state(state)
        return result


class CheckpointVerifier:
    """Trusted external verification against actual remote Git history."""

    def __init__(self, publisher: CheckpointPublisher):
        self.publisher = publisher

    def verify_run(self, run_id: str) -> VerificationResult:
        state = self.publisher.load_state(run_id)
        if state is None:
            return VerificationResult(
                verified=False, head_commit=None, evidence_sha256=None,
                codes=("NO_STATE",), message="private checkpoint state absent")
        ok, findings = verify_event_ordering(
            state.public_records(),
            expected_attempt_keys=[
                (a[0], a[1]) for a in state.finalized_attempts],
            run_closed=state.closed,
            incomplete_closure=state.incomplete_closure,
            review_freeze_reviewers=state.review_freeze_reviewers,
        )
        if not ok:
            return VerificationResult(
                verified=False, head_commit=state.head_commit,
                evidence_sha256=None,
                codes=tuple(f.code for f in findings),
                message=findings[0].message if findings else "ordering failed")
        remote = self.publisher.backend.verify_chain(
            state.ref, state.checkpoints)
        return remote

    def verify_attempt_anchor(self, run_id: str, receipt_sha256: str,
                              anchor_ref: str) -> VerificationResult:
        """Verify a specific attempt checkpoint binds the terminal receipt.

        Used as the lifecycle ``anchor_verifier`` boundary. Requires the
        remote chain tip (or matching entry) to carry the receipt digest.
        """
        state = self.publisher.load_state(run_id)
        if state is None:
            return VerificationResult(
                verified=False, head_commit=None, evidence_sha256=None,
                codes=("NO_STATE",), message="private state absent")
        match = None
        for entry in state.checkpoints:
            binding = entry.get("private_binding") or {}
            if binding.get("receipt_sha256") == receipt_sha256 and \
                    entry["commit"] == anchor_ref:
                match = entry
                break
        if match is None:
            return VerificationResult(
                verified=False, head_commit=state.head_commit,
                evidence_sha256=None, codes=("ANCHOR_NOT_FOUND",),
                message="anchor_ref does not match a bound attempt checkpoint")
        expected_digest = attempt_evidence_digest(receipt_sha256)
        if match["record"]["evidence_sha256"] != expected_digest:
            return VerificationResult(
                verified=False, head_commit=state.head_commit,
                evidence_sha256=match["record"]["evidence_sha256"],
                codes=("RECEIPT_DIGEST_MISMATCH",),
                message="checkpoint evidence digest does not bind the "
                        "terminal receipt")
        chain = self.publisher.backend.verify_chain(
            state.ref, state.checkpoints)
        if not chain.verified:
            return chain
        # Confirm the specific commit still exists with the expected record.
        try:
            remote_record = self.publisher.backend.read_record(
                state.ref, anchor_ref)
        except ValueError as exc:
            return VerificationResult(
                verified=False, head_commit=chain.head_commit,
                evidence_sha256=None, codes=("COMMIT_READ_FAILED",),
                message=str(exc))
        if remote_record != match["record"]:
            return VerificationResult(
                verified=False, head_commit=chain.head_commit,
                evidence_sha256=None, codes=("RECORD_MISMATCH",),
                message="remote attempt checkpoint does not match binding")
        return VerificationResult(
            verified=True, head_commit=chain.head_commit,
            evidence_sha256=expected_digest, codes=(),
            message="attempt checkpoint externally verified against remote "
                    "history; digest binding is not a factual-truth claim",
            factual_claim_proven=False)


def make_lifecycle_anchor_verifier(verifier: CheckpointVerifier, run_id: str):
    """Return a lifecycle-compatible anchor_verifier callable.

    The callable accepts ``(terminal_record, anchor_ref)`` and returns
    True only after trusted remote verification of the bound receipt.
    """

    def _verify(terminal_record: Mapping, anchor_ref: str) -> bool:
        receipt_sha256 = (terminal_record or {}).get("receipt_sha256")
        if not receipt_sha256 or not anchor_ref:
            return False
        result = verifier.verify_attempt_anchor(
            run_id, receipt_sha256, anchor_ref)
        return bool(result.verified)

    return _verify


def production_publish_checkpoint(*_args, **_kwargs):
    """Explicit production entry point — always fails closed pre-G5."""
    assert_production_publication_refused()
    raise PermissionError("unreachable")
