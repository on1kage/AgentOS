#!/usr/bin/env python3
"""
Scout role adapter entrypoint.

Goal:
- Make Scout swappable via src/agentos/role_assignments.json
- Keep authority boundary: research-only, no execution.

This tool is invoked by AgentOS via adapter_registry cmd for role "scout".
It must:
- Accept intent as argv[1] (default: "utc_date")
- Emit deterministic JSON to stdout (canonical_json)
- Exit nonzero on hard failure (missing provider support, missing key when required by caller, etc.)
"""
from __future__ import annotations

import sys
from typing import Any, Dict

from agentos.canonical import canonical_json
from agentos.role_assignments_loader import load_role_assignments, RoleAssignmentError

ADAPTER_ROLE = "scout"
ADAPTER_VERSION = "1.0.0"
ACTION_CLASS = "external_research"


def _err(msg: str) -> Dict[str, Any]:
    return {
        "adapter_role": ADAPTER_ROLE,
        "adapter_version": ADAPTER_VERSION,
        "action_class": ACTION_CLASS,
        "ok": False,
        "result": {},
        "sources": [],
        "errors": [msg],
    }


def main() -> int:
    intent = sys.argv[1] if len(sys.argv) > 1 else "utc_date"

    try:
        # If we're running, caller decided Scout is required; enforce env for scout.
        ra = load_role_assignments(require_env_for_roles=["scout"])
    except RoleAssignmentError as e:
        sys.stdout.write(canonical_json(_err(str(e))) + "\n")
        return 2

    scout = ra.get("scout") or {}
    provider = str(scout.get("provider") or "")
    model = str(scout.get("model") or "")

    if intent != "utc_date":
        sys.stdout.write(canonical_json(_err(f"unsupported_intent:{intent}")) + "\n")
        return 2

    if provider == "perplexity":
        from onemind.scout.perplexity import ask_perplexity

        question = "What is today's UTC date? Respond with a single ISO date string."
        r = ask_perplexity(
            question=question,
            context="Return a single ISO date string only.",
            timeout=30.0,
            model=(model or None),
        )

        payload: Dict[str, Any] = {
            "adapter_role": ADAPTER_ROLE,
            "adapter_version": ADAPTER_VERSION,
            "action_class": ACTION_CLASS,
            "ok": True,
            "result": {
                "schema_version": getattr(r, "schema_version", None),
                "question": getattr(r, "question", question),
                "answer": getattr(r, "answer", ""),
                "model": getattr(r, "model", model),
                "usage": getattr(r, "usage", None),
            },
            "sources": list(getattr(r, "citations", []) or []),
            "errors": [],
        }
        sys.stdout.write(canonical_json(payload) + "\n")
        return 0

    sys.stdout.write(canonical_json(_err(f"unsupported_provider:{provider}")) + "\n")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
