"""
AgentOS Pipeline (verification + logging only)

Purpose:
- Accept a proposed plan (steps) OR a single Task.
- Validate via policy (fail-closed).
- Emit append-only lifecycle events into FSStore.
- Provide deterministic, replayable outputs.

No code execution. No scheduling. No background work.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from agentos.policy import decide
from agentos.store_fs import FSStore, EventRef
from agentos.task import Task


@dataclass(frozen=True)
class Step:
    role: str
    action: str


@dataclass(frozen=True)
class PipelineResult:
    ok: bool
    decisions: List[dict]

    def to_canonical_json(self) -> str:
        # Canonical JSON: sorted keys, no whitespace, deterministic ordering
        return json.dumps(
            {"ok": self.ok, "decisions": self.decisions},
            sort_keys=True,
            separators=(",", ":"),
        )


@dataclass(frozen=True)
class TaskVerifyResult:
    ok: bool
    reason: str
    task_id: str
    created_event: Optional[EventRef]
    decision_event: Optional[EventRef]

    def to_canonical_json(self) -> str:
        payload: Dict[str, Any] = {
            "ok": self.ok,
            "reason": self.reason,
            "task_id": self.task_id,
            "created_event": None if self.created_event is None else self.created_event.__dict__,
            "decision_event": None if self.decision_event is None else self.decision_event.__dict__,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def verify_plan(steps: List[Step]) -> PipelineResult:
    decisions: List[dict] = []
    ok = True

    for i, s in enumerate(steps):
        d = decide(s.role, s.action)
        decisions.append(
            {
                "i": i,
                "role": s.role,
                "action": s.action,
                "allow": d.allow,
                "reason": d.reason,
            }
        )
        if not d.allow:
            ok = False

    bundle = EvidenceBundle().write_verification_bundle(spec_sha256=sha256_hex(canonical_json([s.__dict__ for s in steps]).encode("utf-8")), decisions={i: {"role": s.role, "action": s.action, "allow": d.allow, "reason": d.reason} for i,s in enumerate(steps)}, reason="plan_verification"); return PipelineResult(ok=ok, decisions=decisions, verification_bundle_dir=bundle["bundle_dir"], verification_manifest_sha256=bundle["manifest_sha256"])


def verify_task(store: FSStore, task: Task) -> TaskVerifyResult:
    """
    Deterministic verification gate for a single Task.

    Event emission (append-only):
      - TASK_CREATED: emitted iff task stream is empty
      - TASK_VERIFIED: emitted iff policy allows
      - TASK_REJECTED: emitted iff policy denies

    Fail-closed:
      - Any store failure bubbles (no silent success)
      - Unknown roles/actions deny deterministically via policy.decide
    """
    created_ref: Optional[EventRef] = None
    decision_ref: Optional[EventRef] = None

    # Idempotent creation: only emit if no prior events exist.
    prior = store.list_events(task.task_id)
    if len(prior) == 0:
        created_ref = store.append_event(
            task.task_id,
            "TASK_CREATED",
            {
                "role": task.role,
                "action": task.action,
                "payload": task.payload,
                "attempt": task.attempt,
            },
        )

    d = decide(task.role, task.action)
    if d.allow:
        decision_ref = store.append_event(
            task.task_id,
            "TASK_VERIFIED",
            {
                "role": task.role,
                "action": task.action,
                "reason": d.reason,
                "attempt": task.attempt,
            },
        )
        return TaskVerifyResult(
            ok=True,
            reason=d.reason,
            task_id=task.task_id,
            created_event=created_ref,
            decision_event=decision_ref,
        )

    decision_ref = store.append_event(
        task.task_id,
        "TASK_REJECTED",
        {
            "role": task.role,
            "action": task.action,
            "reason": d.reason,
            "attempt": task.attempt,
        },
    )
    return TaskVerifyResult(
        ok=False,
        reason=d.reason,
        task_id=task.task_id,
        created_event=created_ref,
        decision_event=decision_ref,
    )
