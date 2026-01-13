from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from agentos.policy import decide
from agentos.store_fs import FSStore
from agentos.task import Task, TaskState


@dataclass(frozen=True)
class RouteResult:
    ok: bool
    reason: str
    task_id: str
    role: str
    action: str


class ExecutionRouter:
    """
    Deterministic execution router.

    Responsibilities:
    - Enforce policy before dispatch
    - Emit TASK_DISPATCHED event
    - Do NOT execute any code
    """

    def __init__(self, store: FSStore) -> None:
        self.store = store

    def route(self, task: Task) -> RouteResult:
        # Fail-closed: only VERIFIED tasks may be dispatched
        if task.state is not TaskState.VERIFIED:
            return RouteResult(
                ok=False,
                reason=f"invalid_state:{task.state}",
                task_id=task.task_id,
                role=task.role,
                action=task.action,
            )

        decision = decide(task.role, task.action)
        if not decision.allow:
            self.store.append_event(
                task.task_id,
                "TASK_REJECTED",
                {
                    "role": task.role,
                    "action": task.action,
                    "reason": decision.reason,
                },
            )
            return RouteResult(
                ok=False,
                reason=decision.reason,
                task_id=task.task_id,
                role=task.role,
                action=task.action,
            )

        # Authorized: emit dispatch event
        self.store.append_event(
            task.task_id,
            "TASK_DISPATCHED",
            {
                "role": task.role,
                "action": task.action,
                "attempt": task.attempt,
            },
        )

        return RouteResult(
            ok=True,
            reason="dispatched",
            task_id=task.task_id,
            role=task.role,
            action=task.action,
        )
