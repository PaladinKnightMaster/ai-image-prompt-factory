"""EXP-019 v1.2 attempt lifecycle and terminal-state manager (PR-7).

This module implements the local attempt lifecycle from the merged G1
engineering contract and the admission/failure policy draft:

* slot states: ``planned`` -> ``invocation_started`` ->
  ``invocation_closed`` -> ``slot_closed`` (slot closure, invocation
  closure, and run closure are distinct events; closing a slot neither
  authorizes another generation nor completes the run);
* attempt states: ``opened``, ``evidence_returned`` (with retained
  output), ``no_result_confirmed``, ``PENDING_UNKNOWN`` (operational,
  strictly non-terminal), and ``indeterminate_pending_review``;
* exactly three terminal dispositions: ``ADMIT``, ``FAILURE``, and
  ``INDETERMINATE_FINAL``;
* monotonic attempt numbering with a frozen ceiling of two retries,
  retries only after terminal ``FAILURE`` and only once the predecessor
  terminal record is externally anchored;
* no retry for unknown or indeterminate outcomes, and no replacement of
  a technically evaluable image through regeneration;
* closing a permanently unresolved invocation as ``INDETERMINATE_FINAL``
  only with an explicit H3 authorization record.

Exactly-once durability. The full terminal-receipt builder and the
external Git checkpoint publisher belong to later PRs; this module keeps
only the local terminal record and its anchor state
(``recorded-unanchored`` -> ``externally-anchored``). All state is
rebuilt by replaying committed events. Every write is staged to a
``.tmp`` file, flushed, and atomically renamed; staged files that were
never renamed are recovery debris, are discarded by ``recover()``, and
are never accepted as events. Retained output bytes are committed under
their SHA-256 digest; bytes present in the output store without a
committed ``evidence_returned`` event referencing them are orphans and
are never accepted as a valid output. Repeating a terminal finalization
with the same disposition returns the existing local terminal record
without a duplicate event; a different disposition raises.

This module remains inactive without a registered v1.2 experiment: it
registers nothing in ``frozen_protocol()``, creates no experimental run
root, allocation, or checkpoint, and issues no host request. It is
driven only by synthetic lifecycle tests in this PR.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path

TERMINAL_DISPOSITIONS = ("ADMIT", "FAILURE", "INDETERMINATE_FINAL")
MAX_RETRIES = 2
MAX_ATTEMPTS = 1 + MAX_RETRIES

#: Affirmative no-result evidence kinds. An operator's belief that no
#: image appeared is not among them and never establishes ``FAILURE``.
AFFIRMATIVE_NO_RESULT_EVIDENCE = frozenset({
    "host_error_recorded",
    "host_completed_no_image",
    "request_not_accepted",
})

#: The H3-authorized procedure for terminalizing unresolved outcomes.
INDETERMINATE_PROCEDURE = "H3-indeterminate-disposition"

ANCHOR_RECORDED = "recorded-unanchored"
ANCHOR_ANCHORED = "externally-anchored"


class InvalidTransitionError(ValueError):
    """A lifecycle transition the contract does not permit."""


class AuthorizationError(ValueError):
    """A transition requiring an explicit authorization record."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


class LifecycleStore:
    """Durable, event-sourced lifecycle store with staged atomic writes.

    Layout under ``root``: ``events/`` (committed events, replayed in
    sequence order), ``staging/`` (never-committed ``.tmp`` debris),
    ``outputs/`` (retained bytes named by digest), and
    ``outputs_staging/``.
    """

    def __init__(self, root) -> None:
        self.root = Path(root)
        self.events_dir = self.root / "events"
        self.staging_dir = self.root / "staging"
        self.outputs_dir = self.root / "outputs"
        self.outputs_staging_dir = self.root / "outputs_staging"
        for directory in (self.events_dir, self.staging_dir,
                          self.outputs_dir, self.outputs_staging_dir):
            directory.mkdir(parents=True, exist_ok=True)
        self.events: list = []
        self.recover()

    # -- durable primitives ---------------------------------------------------

    def _stage_and_commit(self, staging_dir: Path, final_path: Path,
                          data: bytes) -> None:
        staging_path = staging_dir / (final_path.name + ".tmp")
        with open(staging_path, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(staging_path, final_path)

    def append_event(self, event: dict) -> dict:
        """Commit one event atomically; returns the committed event."""
        committed = dict(event)
        committed["seq"] = len(self.events) + 1
        committed["event_id"] = _sha256(_canonical(committed))
        final_path = self.events_dir / f"{committed['event_id']}.json"
        if final_path.exists():
            return committed
        self._stage_and_commit(self.staging_dir, final_path,
                               _canonical(committed))
        self.events.append(committed)
        return committed

    def retain_output(self, data: bytes) -> str:
        """Commit retained output bytes under their digest (idempotent)."""
        digest = _sha256(bytes(data))
        final_path = self.outputs_dir / f"{digest}.bin"
        if not final_path.exists():
            self._stage_and_commit(self.outputs_staging_dir, final_path,
                                   bytes(data))
        return digest

    def has_output(self, digest) -> bool:
        return digest is not None and \
            (self.outputs_dir / f"{digest}.bin").is_file()

    def read_output(self, digest) -> bytes:
        return (self.outputs_dir / f"{digest}.bin").read_bytes()

    def recover(self) -> int:
        """Discard staged debris and rebuild from committed events only."""
        for debris in list(self.staging_dir.glob("*.tmp")) + \
                list(self.outputs_staging_dir.glob("*.tmp")):
            debris.unlink()
        events = []
        for path in self.events_dir.glob("*.json"):
            events.append(json.loads(path.read_text(encoding="utf-8")))
        events.sort(key=lambda e: e["seq"])
        if [e["seq"] for e in events] != list(range(1, len(events) + 1)):
            raise InvalidTransitionError(
                "committed event sequence is not contiguous")
        self.events = events
        return len(events)

    def orphaned_outputs(self) -> tuple:
        """Committed bytes no committed event references; never valid."""
        referenced = {
            e.get("retained_artifact_sha256") for e in self.events
            if e.get("type") == "evidence_returned"
        }
        return tuple(sorted(
            path.stem for path in self.outputs_dir.glob("*.bin")
            if path.stem not in referenced))


class AttemptLifecycle:
    """Attempt lifecycle state machine over a :class:`LifecycleStore`."""

    def __init__(self, store: LifecycleStore) -> None:
        self.store = store
        self._slots: dict = {}
        self._run_closed = False
        self._run_complete = False
        self._replay()

    # -- state reconstruction ---------------------------------------------------

    def _replay(self) -> None:
        self._slots = {}
        self._run_closed = False
        self._run_complete = False
        for event in self.store.events:
            self._apply(event)

    def _apply(self, event: dict) -> None:
        kind = event["type"]
        slot_id = event.get("slot_id")
        if kind == "slot_planned":
            self._slots[slot_id] = {
                "slot_id": slot_id, "state": "planned", "attempts": {},
                "current_attempt": None,
            }
            return
        if kind == "run_closed":
            self._run_closed = True
            self._run_complete = event["complete"]
            return
        slot = self._slots[slot_id]
        if kind == "invocation_started":
            slot["state"] = "invocation_started"
            slot["attempts"][1] = self._new_attempt(1, None)
            slot["current_attempt"] = 1
        elif kind == "retry_started":
            number = event["attempt_number"]
            slot["attempts"][number] = self._new_attempt(
                number, event["predecessor_attempt"])
            slot["current_attempt"] = number
        elif kind == "evidence_returned":
            attempt = slot["attempts"][event["attempt_number"]]
            attempt["state"] = "evidence_returned"
            attempt["retained_artifact_sha256"] = \
                event["retained_artifact_sha256"]
            attempt["technically_evaluable"] = \
                event["technically_evaluable"]
        elif kind == "no_result_confirmed":
            slot["attempts"][event["attempt_number"]]["state"] = \
                "no_result_confirmed"
        elif kind == "pending_unknown_marked":
            slot["attempts"][event["attempt_number"]]["state"] = \
                "PENDING_UNKNOWN"
        elif kind == "contract_violation_recorded":
            slot["attempts"][event["attempt_number"]]["state"] = \
                "indeterminate_pending_review"
        elif kind == "invocation_resumed":
            attempt = slot["attempts"][event["attempt_number"]]
            if attempt["state"] == "PENDING_UNKNOWN":
                attempt["state"] = "evidence_returned"
        elif kind == "attempt_terminal":
            attempt = slot["attempts"][event["attempt_number"]]
            attempt["state"] = "terminal"
            attempt["terminal_record"] = event["terminal_record"]
        elif kind == "external_anchor_recorded":
            attempt = slot["attempts"][event["attempt_number"]]
            attempt["terminal_record"]["anchor_state"] = ANCHOR_ANCHORED
            attempt["terminal_record"]["anchor_ref"] = event["anchor_ref"]
        elif kind == "invocation_closed":
            slot["state"] = "invocation_closed"
        elif kind == "slot_closed":
            slot["state"] = "slot_closed"

    @staticmethod
    def _new_attempt(number: int, predecessor) -> dict:
        return {
            "attempt_number": number,
            "predecessor_attempt": predecessor,
            "state": "opened",
            "retained_artifact_sha256": None,
            "technically_evaluable": None,
            "terminal_record": None,
        }

    def _emit(self, event: dict) -> dict:
        committed = self.store.append_event(event)
        self._apply(committed)
        return committed

    # -- lookups -------------------------------------------------------------------

    def _slot(self, slot_id) -> dict:
        try:
            return self._slots[slot_id]
        except KeyError:
            raise InvalidTransitionError(
                f"unknown slot: {slot_id!r}") from None

    def _attempt(self, slot: dict, attempt_number=None) -> dict:
        number = slot["current_attempt"] if attempt_number is None \
            else attempt_number
        try:
            return slot["attempts"][number]
        except (KeyError, TypeError):
            raise InvalidTransitionError(
                "no such attempt for this slot") from None

    def slot_state(self, slot_id) -> dict:
        slot = self._slot(slot_id)
        return {
            "slot_id": slot_id,
            "state": slot["state"],
            "current_attempt": slot["current_attempt"],
            "attempts": {
                number: {
                    "state": attempt["state"],
                    "predecessor_attempt": attempt["predecessor_attempt"],
                    "retained_artifact_sha256":
                        attempt["retained_artifact_sha256"],
                    "disposition": (attempt["terminal_record"] or {}).get(
                        "disposition"),
                    "anchor_state": (attempt["terminal_record"] or {}).get(
                        "anchor_state"),
                }
                for number, attempt in sorted(slot["attempts"].items())
            },
        }

    # -- slot and invocation opening -------------------------------------------

    def plan_slot(self, slot_id, *, at_utc=None) -> dict:
        if slot_id in self._slots:
            raise InvalidTransitionError("slot is already planned")
        self._emit({"type": "slot_planned", "slot_id": slot_id,
                    "at_utc": at_utc})
        return self.slot_state(slot_id)

    def start_invocation(self, slot_id, *, at_utc=None) -> dict:
        slot = self._slot(slot_id)
        if slot["state"] != "planned":
            raise InvalidTransitionError(
                "an invocation may be started only from the planned state")
        self._emit({"type": "invocation_started", "slot_id": slot_id,
                    "attempt_number": 1, "at_utc": at_utc})
        return self.slot_state(slot_id)

    # -- evidence states -----------------------------------------------------------

    def record_output(self, slot_id, data: bytes, *,
                      technically_evaluable: bool = True,
                      at_utc=None) -> str:
        """Retain output bytes and bind them to the current attempt."""
        digest = self.store.retain_output(data)
        self.record_evidence_returned(
            slot_id, digest, technically_evaluable=technically_evaluable,
            at_utc=at_utc)
        return digest

    def record_evidence_returned(self, slot_id, artifact_sha256, *,
                                 technically_evaluable: bool = True,
                                 at_utc=None) -> dict:
        slot = self._slot(slot_id)
        attempt = self._attempt(slot)
        if attempt["state"] not in ("opened", "PENDING_UNKNOWN"):
            raise InvalidTransitionError(
                "evidence may be recorded only for an open attempt")
        if not self.store.has_output(artifact_sha256):
            raise InvalidTransitionError(
                "retained output bytes are not in the store; unretained "
                "or orphaned bytes cannot be accepted as valid output")
        self._emit({"type": "evidence_returned", "slot_id": slot_id,
                    "attempt_number": attempt["attempt_number"],
                    "retained_artifact_sha256": artifact_sha256,
                    "technically_evaluable": bool(technically_evaluable),
                    "at_utc": at_utc})
        return self.slot_state(slot_id)

    def confirm_no_result(self, slot_id, *, evidence: str,
                          at_utc=None) -> dict:
        slot = self._slot(slot_id)
        attempt = self._attempt(slot)
        if attempt["state"] != "opened":
            raise InvalidTransitionError(
                "a no-result outcome may be confirmed only for an open "
                "attempt")
        if evidence not in AFFIRMATIVE_NO_RESULT_EVIDENCE:
            raise InvalidTransitionError(
                "no-result confirmation requires affirmative evidence; "
                "an operator statement that no image was seen is not, by "
                "itself, affirmative evidence")
        self._emit({"type": "no_result_confirmed", "slot_id": slot_id,
                    "attempt_number": attempt["attempt_number"],
                    "evidence": evidence, "at_utc": at_utc})
        return self.slot_state(slot_id)

    def mark_pending_unknown(self, slot_id, *, reason: str = "",
                             at_utc=None) -> dict:
        slot = self._slot(slot_id)
        attempt = self._attempt(slot)
        if attempt["state"] not in ("opened", "evidence_returned",
                                    "no_result_confirmed"):
            raise InvalidTransitionError(
                "only an unresolved open attempt may be PENDING_UNKNOWN")
        self._emit({"type": "pending_unknown_marked", "slot_id": slot_id,
                    "attempt_number": attempt["attempt_number"],
                    "reason": reason, "at_utc": at_utc})
        return self.slot_state(slot_id)

    def record_contract_violation(self, slot_id, *, detail: str = "",
                                  at_utc=None) -> dict:
        slot = self._slot(slot_id)
        attempt = self._attempt(slot)
        if attempt["state"] != "evidence_returned":
            raise InvalidTransitionError(
                "a contract violation may be recorded only for a "
                "returned artifact")
        self._emit({"type": "contract_violation_recorded",
                    "slot_id": slot_id,
                    "attempt_number": attempt["attempt_number"],
                    "detail": detail, "at_utc": at_utc})
        return self.slot_state(slot_id)

    def resume_invocation(self, slot_id, *, at_utc=None) -> int:
        """Resume the same invocation when output bytes are retained.

        Returns the unchanged attempt number. Resumption never opens a
        new attempt and never authorizes a new generation.
        """
        slot = self._slot(slot_id)
        attempt = self._attempt(slot)
        retained = attempt["retained_artifact_sha256"]
        if retained is None or not self.store.has_output(retained):
            raise InvalidTransitionError(
                "resumption requires retained output bytes for the "
                "current attempt")
        if attempt["state"] == "PENDING_UNKNOWN":
            self._emit({"type": "invocation_resumed", "slot_id": slot_id,
                        "attempt_number": attempt["attempt_number"],
                        "at_utc": at_utc})
        return attempt["attempt_number"]

    # -- terminal decisions --------------------------------------------------------

    def finalize_attempt(self, slot_id, disposition, *,
                         authorization=None, evidence_digests=(),
                         class_d_conflict_count: int = 0,
                         at_utc=None) -> dict:
        """Commit exactly one terminal disposition for the current attempt.

        Returns the local terminal record. Repeating the same
        disposition returns the existing record without a duplicate
        event; a different disposition raises. The record's anchor state
        is tracked separately (see :meth:`record_external_anchor`).
        """
        if disposition not in TERMINAL_DISPOSITIONS:
            raise InvalidTransitionError(
                f"unknown terminal disposition: {disposition!r}")
        slot = self._slot(slot_id)
        attempt = self._attempt(slot)
        existing = attempt["terminal_record"]
        if existing is not None:
            if existing["disposition"] == disposition:
                return copy.deepcopy(existing)
            raise InvalidTransitionError(
                "attempt is already terminal with a different "
                "disposition; terminal records are never rewritten")
        if disposition == "ADMIT":
            if attempt["state"] != "evidence_returned":
                raise InvalidTransitionError(
                    "ADMIT requires a returned, retained artifact")
            if not attempt["technically_evaluable"]:
                raise InvalidTransitionError(
                    "ADMIT requires a technically evaluable artifact")
            if not self.store.has_output(
                    attempt["retained_artifact_sha256"]):
                raise InvalidTransitionError(
                    "ADMIT requires the retained output bytes to be "
                    "present in the store")
        elif disposition == "FAILURE":
            if attempt["state"] != "no_result_confirmed":
                raise InvalidTransitionError(
                    "FAILURE requires an affirmatively evidenced "
                    "no-result outcome")
        elif disposition == "INDETERMINATE_FINAL":
            if attempt["state"] not in ("PENDING_UNKNOWN",
                                        "indeterminate_pending_review"):
                raise InvalidTransitionError(
                    "INDETERMINATE_FINAL requires an unresolved "
                    "(PENDING_UNKNOWN or pending-review) outcome")
            self._require_indeterminate_authorization(authorization)
        record = {
            "slot_id": slot_id,
            "attempt_number": attempt["attempt_number"],
            "predecessor_attempt": attempt["predecessor_attempt"],
            "disposition": disposition,
            "retained_artifact_sha256":
                attempt["retained_artifact_sha256"],
            "evidence_digests": sorted(evidence_digests),
            "class_d_conflict_count": int(class_d_conflict_count),
            "anchor_state": ANCHOR_RECORDED,
            "anchor_ref": None,
        }
        self._emit({"type": "attempt_terminal", "slot_id": slot_id,
                    "attempt_number": attempt["attempt_number"],
                    "terminal_record": record, "at_utc": at_utc})
        return copy.deepcopy(record)

    @staticmethod
    def _require_indeterminate_authorization(authorization) -> None:
        if not isinstance(authorization, dict) or not authorization.get(
                "authorization_id") or not authorization.get(
                "authorized_by") or authorization.get(
                "procedure") != INDETERMINATE_PROCEDURE:
            raise AuthorizationError(
                "INDETERMINATE_FINAL requires an explicit authorization "
                "record under the H3 indeterminate-disposition procedure")

    def record_external_anchor(self, slot_id, attempt_number, anchor_ref,
                               *, at_utc=None) -> dict:
        """Mark a local terminal record externally anchored (idempotent).

        This records anchor *state* only; the external checkpoint
        publisher itself belongs to a later PR.
        """
        slot = self._slot(slot_id)
        attempt = self._attempt(slot, attempt_number)
        record = attempt["terminal_record"]
        if record is None:
            raise InvalidTransitionError(
                "only a terminal attempt may be anchored")
        if record["anchor_state"] == ANCHOR_ANCHORED:
            if record["anchor_ref"] == anchor_ref:
                return copy.deepcopy(record)
            raise InvalidTransitionError(
                "terminal record is already anchored under a different "
                "reference; it is never anchored twice")
        self._emit({"type": "external_anchor_recorded",
                    "slot_id": slot_id, "attempt_number": attempt_number,
                    "anchor_ref": anchor_ref, "at_utc": at_utc})
        return copy.deepcopy(
            self._attempt(self._slot(slot_id), attempt_number)[
                "terminal_record"])

    # -- retry -----------------------------------------------------------------------

    def request_retry(self, slot_id, *, at_utc=None) -> dict:
        """Open the next attempt after a terminal ``FAILURE``.

        Never permitted after ``ADMIT``, ``PENDING_UNKNOWN``, or
        ``INDETERMINATE_FINAL``; never beyond the frozen ceiling of two
        retries; and blocked until the predecessor terminal record is
        externally anchored.
        """
        slot = self._slot(slot_id)
        if slot["state"] in ("invocation_closed", "slot_closed"):
            raise InvalidTransitionError("the invocation is closed")
        attempt = self._attempt(slot)
        record = attempt["terminal_record"]
        if record is None:
            raise InvalidTransitionError(
                "a retry requires a terminal predecessor attempt; an "
                "unresolved (PENDING_UNKNOWN) outcome may never be "
                "retried away")
        if record["disposition"] != "FAILURE":
            raise InvalidTransitionError(
                "a retry is permitted only after terminal FAILURE")
        if attempt["attempt_number"] >= MAX_ATTEMPTS:
            raise InvalidTransitionError(
                "the frozen retry ceiling of two retries is exhausted")
        if record["anchor_state"] != ANCHOR_ANCHORED:
            raise InvalidTransitionError(
                "a retry is blocked until the predecessor terminal "
                "record is externally anchored")
        self._emit({"type": "retry_started", "slot_id": slot_id,
                    "attempt_number": attempt["attempt_number"] + 1,
                    "predecessor_attempt": attempt["attempt_number"],
                    "at_utc": at_utc})
        return self.slot_state(slot_id)

    # -- closure ---------------------------------------------------------------------

    def close_invocation(self, slot_id, *, at_utc=None) -> dict:
        slot = self._slot(slot_id)
        if slot["state"] == "invocation_closed":
            return self.slot_state(slot_id)
        attempt = self._attempt(slot)
        if attempt["terminal_record"] is None:
            raise InvalidTransitionError(
                "an invocation may close only when its current attempt "
                "is terminal; PENDING_UNKNOWN is not a closure")
        self._emit({"type": "invocation_closed", "slot_id": slot_id,
                    "at_utc": at_utc})
        return self.slot_state(slot_id)

    def close_slot(self, slot_id, *, at_utc=None) -> dict:
        """Close a slot whose invocation is closed.

        Slot closure authorizes no generation and does not, by itself,
        establish that the run is complete.
        """
        slot = self._slot(slot_id)
        if slot["state"] == "slot_closed":
            return self.slot_state(slot_id)
        if slot["state"] != "invocation_closed":
            raise InvalidTransitionError(
                "a slot may close only after its invocation is closed")
        self._emit({"type": "slot_closed", "slot_id": slot_id,
                    "at_utc": at_utc})
        return self.slot_state(slot_id)

    def close_run(self, *, at_utc=None) -> dict:
        """Close the run once every planned slot is closed.

        Exactly one run-closure event is committed; repeating the call
        returns the same summary. ``complete`` holds only when every
        slot admitted an attempt.
        """
        if self._run_closed:
            return self.run_summary()
        unclosed = [s for s in self._slots.values()
                    if s["state"] != "slot_closed"]
        if unclosed:
            raise InvalidTransitionError(
                "the run may close only when every slot is closed; "
                "unresolved slots remain open and visibly incomplete")
        complete = all(
            any(a["terminal_record"] and
                a["terminal_record"]["disposition"] == "ADMIT"
                for a in slot["attempts"].values())
            for slot in self._slots.values())
        self._emit({"type": "run_closed", "slot_id": None,
                    "complete": complete, "at_utc": at_utc})
        return self.run_summary()

    def run_summary(self) -> dict:
        dispositions = []
        for slot in self._slots.values():
            for attempt in slot["attempts"].values():
                if attempt["terminal_record"]:
                    dispositions.append(
                        attempt["terminal_record"]["disposition"])
        return {
            "run_closed": self._run_closed,
            "complete": self._run_complete if self._run_closed else False,
            "slots": {slot_id: self.slot_state(slot_id)["state"]
                      for slot_id in sorted(self._slots)},
            "terminal_dispositions": dispositions,
            "pending_unknown_attempts": sum(
                1 for slot in self._slots.values()
                for attempt in slot["attempts"].values()
                if attempt["state"] == "PENDING_UNKNOWN"),
        }
