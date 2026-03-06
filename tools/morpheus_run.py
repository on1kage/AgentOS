#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from typing import Any, Dict

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "onemind-FSM-Kernel" / "src"))

from agentos.role_assignments_loader import load_role_assignments, RoleAssignmentError
from agentos.json_utils import canonical_json

ADAPTER_ROLE = "morpheus"
ADAPTER_VERSION = "1.0.1"
ACTION_CLASS = "architecture"

SYSTEMS = ["morpheus", "envoy", "scout"]


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


def _one_paragraph(name: str) -> str:
    return (
        f"{name} is a subsystem in the OneMind stack with a defined contract surface. "
        "In this phase it is described deterministically from local registry context only. "
        "It must be routable through AgentOS, emit evidence bundles, and fail closed on drift. "
        "Its operational definition is the minimal description required to identify its purpose, "
        "its inputs/outputs, and its safety boundaries without implying unverified capabilities."
    )


def main() -> int:
    intent = sys.argv[1] if len(sys.argv) > 1 else ""

    try:
        ra = load_role_assignments(require_env_for_roles=[])
    except RoleAssignmentError as e:
        sys.stdout.write(canonical_json(_err(str(e))) + "\n")
        return 2

    morpheus = ra.get("morpheus") or {}
    provider = str(morpheus.get("provider") or "")
    model = str(morpheus.get("model") or "")
    api_env = morpheus.get("api_env")

    if provider not in ("openai", "local"):
        sys.stdout.write(canonical_json(_err(f"unsupported_provider:{provider}")) + "\n")
        return 2

    if api_env is not None:
        if not isinstance(api_env, str) or not api_env:
            sys.stdout.write(canonical_json(_err("invalid_api_env:morpheus")) + "\n")
            return 2
        if not os.getenv(api_env):
            sys.stdout.write(canonical_json(_err(f"missing_api_key_env:morpheus:{api_env}")) + "\n")
            return 1

    if intent != "onemind_stack_descriptions":
        sys.stdout.write(canonical_json(_err(f"unsupported_intent:{intent}")) + "\n")
        return 2

    result = {name: _one_paragraph(name) for name in SYSTEMS}
    payload = {
        "adapter_role": ADAPTER_ROLE,
        "adapter_version": ADAPTER_VERSION,
        "action_class": ACTION_CLASS,
        "ok": True,
        "result": {
            "schema_version": "morpheus-architecture/v1",
            "intent": intent,
            "systems": result,
            "provider": provider,
            "model": model,
        },
        "sources": [],
        "errors": [],
    }
    sys.stdout.write(canonical_json(payload) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
