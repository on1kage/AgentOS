from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional


class TaskState(str, Enum):
    CREATED = "CREATED"
    VERIFIED = "VERIFIED"
    DISPATCHED = "DISPATCHED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class Task:
    """
    Canonical immutable task definition.

    Execution is NOT performed here.
    This is a state + intent container only.
    """
    task_id: str
    state: TaskState
    role: str
    action: str
    payload: Dict[str, object]
    attempt: int = 0
    error: Optional[str] = None
