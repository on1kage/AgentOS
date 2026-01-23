from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping

from agentos.canonical import canonical_json, sha256_hex


@dataclass(frozen=True)
class PlanStep:
    step_id: str
    role: str
    action: str
    task_id: str

    def to_obj(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "role": self.role,
            "step_id": self.step_id,
            "task_id": self.task_id,
        }


@dataclass(frozen=True)
class Plan:
    plan_id: str
    steps: List[PlanStep]

    def to_canonical_obj(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "steps": [s.to_obj() for s in self.steps],
        }

    def to_canonical_json(self) -> str:
        return canonical_json(self.to_canonical_obj())

    def spec_sha256(self) -> str:
        return sha256_hex(self.to_canonical_json().encode("utf-8"))


def require_payload_map(payloads_by_task_id: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for k, v in payloads_by_task_id.items():
        if not isinstance(k, str) or not k:
            raise TypeError("payloads_by_task_id keys must be non-empty strings")
        if not isinstance(v, dict):
            raise TypeError("payloads_by_task_id values must be dict payloads")
        out[k] = dict(v)
    return out
