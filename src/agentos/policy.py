"""
AgentOS policy gate (minimal, deterministic, fail-closed).

Given (role, action) => allow/deny + reason.
No external calls. No state mutation.
"""

from __future__ import annotations

from dataclasses import dataclass

from agentos.roles import roles


@dataclass(frozen=True)
class Decision:
    allow: bool
    reason: str


# Canonical action labels (stringly typed by design for portability across subsystems)
def _known_actions_from_roles() -> set[str]:
    rmap = roles()
    out: set[str] = set()
    for r in rmap.values():
        out.update(set(r.authority))
        out.update(set(r.prohibited))
    return out


KNOWN_ACTIONS = _known_actions_from_roles()


def decide(role_name: str, action: str) -> Decision:
    """
    Deterministic decision function.
    Fail-closed on unknown role/action.
    """
    rmap = roles()

    if role_name not in rmap:
        return Decision(False, f"deny:unknown_role:{role_name}")

    if action not in KNOWN_ACTIONS:
        return Decision(False, f"deny:unknown_action:{action}")

    role = rmap[role_name]

    if action in role.prohibited:
        return Decision(False, f"deny:prohibited:{role_name}:{action}")

    if action in role.authority:
        return Decision(True, f"allow:authorized:{role_name}:{action}")

    # Not explicitly allowed: fail-closed
    return Decision(False, f"deny:not_authorized:{role_name}:{action}")
