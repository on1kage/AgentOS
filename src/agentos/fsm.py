"""
AgentOS Persistent Task FSM

Design goals:
- Deterministic replay: state is derived ONLY from an append-only event stream.
- Fail-closed: unknown events or illegal transitions raise an exception and emit
  a deterministic violation evidence object.
- No execution logic: this module never runs commands, spawns threads, or schedules work.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
import json


class TaskState(str, Enum):
    NEW = "NEW"
    READY = "READY"
    DISPATCHED = "DISPATCHED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"
    VIOLATION = "VIOLATION"


class EventType(str, Enum):
    TASK_CREATED = "TASK_CREATED"
    TASK_READY = "TASK_READY"
    TASK_DISPATCHED = "TASK_DISPATCHED"
    RUN_STARTED = "RUN_STARTED"
    RUN_SUCCEEDED = "RUN_SUCCEEDED"
    RUN_FAILED = "RUN_FAILED"
    TASK_CANCELED = "TASK_CANCELED"


# Allowed transitions are keyed by (current_state, event_type) -> next_state.
# Fail-closed default: anything not in this table is illegal.
_ALLOWED: Dict[Tuple[TaskState, EventType], TaskState] = {
    (TaskState.NEW, EventType.TASK_CREATED): TaskState.NEW,
    (TaskState.NEW, EventType.TASK_READY): TaskState.READY,
    (TaskState.READY, EventType.TASK_DISPATCHED): TaskState.DISPATCHED,
    (TaskState.DISPATCHED, EventType.RUN_STARTED): TaskState.RUNNING,
    (TaskState.RUNNING, EventType.RUN_SUCCEEDED): TaskState.SUCCEEDED,
    (TaskState.RUNNING, EventType.RUN_FAILED): TaskState.FAILED,
    # Cancel is allowed from non-terminal pre-run states (deterministic, no side effects).
    (TaskState.NEW, EventType.TASK_CANCELED): TaskState.CANCELED,
    (TaskState.READY, EventType.TASK_CANCELED): TaskState.CANCELED,
    (TaskState.DISPATCHED, EventType.TASK_CANCELED): TaskState.CANCELED,
}

_TERMINAL: Tuple[TaskState, ...] = (
    TaskState.SUCCEEDED,
    TaskState.FAILED,
    TaskState.CANCELED,
    TaskState.VIOLATION,
)


def _canonical_json(obj: Any) -> str:
    # Deterministic JSON (no float NaN allowance).
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _hash_evidence(evidence: Mapping[str, Any]) -> str:
    return sha256(_canonical_json(evidence).encode("utf-8")).hexdigest()


def _event_key(e: Mapping[str, Any], i: int) -> Tuple[Any, Any, Any, int]:
    """
    Deterministic ordering key.
    Preference order:
      1) ts (string or numeric)
      2) seq (numeric)
      3) event_id (string)
      4) fallback to stable position i
    """
    ts = e.get("ts", "")
    seq = e.get("seq", 0)
    event_id = e.get("event_id", "")
    return (ts, seq, event_id, i)


@dataclass(frozen=True)
class FSMViolation:
    task_id: str
    prev_state: str
    event_type: str
    reason: str
    event: Dict[str, Any]
    violation_hash: str


class FSMViolationError(RuntimeError):
    def __init__(self, violation: FSMViolation):
        super().__init__(f"FSM violation for task_id={violation.task_id}: {violation.reason}")
        self.violation = violation


class TaskFSM:
    """
    Replay-only FSM.

    Event schema expectations (minimal):
      - task_id: str
      - type: str (must match EventType)
    Optional but recommended for determinism:
      - ts: sortable timestamp (string or number)
      - seq: monotonically increasing integer per task stream
      - event_id: stable identifier
    """

    def __init__(self, task_id: str, initial_state: TaskState = TaskState.NEW):
        if not task_id or not isinstance(task_id, str):
            raise ValueError("task_id must be a non-empty string")
        self.task_id = task_id
        self.state: TaskState = initial_state
        self.history: List[Dict[str, Any]] = []

    def apply(self, event: Mapping[str, Any]) -> TaskState:
        if event.get("task_id") != self.task_id:
            self._violate(
                prev=self.state,
                event=event,
                reason=f"event.task_id mismatch (expected {self.task_id}, got {event.get('task_id')})",
            )

        raw_type = event.get("type")
        try:
            et = EventType(str(raw_type))
        except Exception:
            self._violate(prev=self.state, event=event, reason=f"unknown event type: {raw_type!r}")

        if self.state in _TERMINAL:
            self._violate(
                prev=self.state,
                event=event,
                reason=f"event applied after terminal state {self.state.value}",
            )

        nxt = _ALLOWED.get((self.state, et))
        if nxt is None:
            self._violate(
                prev=self.state,
                event=event,
                reason=f"illegal transition: {self.state.value} --{et.value}--> ?",
            )

        # Deterministic: store a plain dict snapshot of the event.
        self.history.append(dict(event))
        self.state = nxt
        return self.state

    def replay(self, events: Iterable[Mapping[str, Any]]) -> TaskState:
        # Deterministic replay ordering: sort using stable keys. If caller already ordered,
        # sorting is still deterministic and idempotent.
        ev_list: List[Mapping[str, Any]] = list(events)
        ev_list_sorted = sorted(ev_list, key=lambda e_i: _event_key(e_i, ev_list.index(e_i)))
        for e in ev_list_sorted:
            self.apply(e)
        return self.state

    def snapshot(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "state": self.state.value,
            "events": list(self.history),
        }

    def _violate(self, prev: TaskState, event: Mapping[str, Any], reason: str) -> None:
        evidence = {
            "task_id": self.task_id,
            "prev_state": prev.value,
            "event_type": str(event.get("type")),
            "reason": reason,
            "event": dict(event),
        }
        vhash = _hash_evidence(evidence)
        violation = FSMViolation(
            task_id=self.task_id,
            prev_state=prev.value,
            event_type=str(event.get("type")),
            reason=reason,
            event=dict(event),
            violation_hash=vhash,
        )
        raise FSMViolationError(violation)


def rebuild_task_state(store: Any, task_id: str) -> Dict[str, Any]:
    """
    Rebuild task state from append-only store events.

    Store interface (duck-typed; fail-closed if missing):
      - store.iter_task_events(task_id) -> Iterable[Mapping]
        OR
      - store.read_task_events(task_id) -> Sequence[Mapping]
        OR
      - store.load_task_events(task_id) -> Sequence[Mapping]
    """
    if hasattr(store, "iter_task_events"):
        events = list(store.iter_task_events(task_id))
    elif hasattr(store, "read_task_events"):
        events = list(store.read_task_events(task_id))
    elif hasattr(store, "load_task_events"):
        events = list(store.load_task_events(task_id))
    else:
        raise TypeError("store does not expose iter_task_events/read_task_events/load_task_events")

    fsm = TaskFSM(task_id=task_id)
    # Ensure deterministic ordering even if store yields arbitrary order.
    events_sorted = sorted([dict(e) for e in events], key=lambda e: _event_key(e, 0))
    fsm.replay(events_sorted)
    return fsm.snapshot()
