"""
AgentOS Pipeline (minimal scaffold)

Purpose:
- Accept a proposed plan (steps).
- Validate each step via policy (fail-closed).
- Emit a deterministic JSON log record.

No code execution of steps. This is verification + logging only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import List

from agentos.policy import decide


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

    return PipelineResult(ok=ok, decisions=decisions)
