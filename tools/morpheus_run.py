import sys, os, json
from pathlib import Path
from agentos.json_utils import canonical_json

ADAPTER_ROLE = "morpheus"
ADAPTER_VERSION = "1.0.0"
ACTION_CLASS = "architecture"

SYSTEMS = ["morpheus", "envoy", "scout"]

def _err(msg):
    return {"adapter_role": ADAPTER_ROLE, "adapter_version": ADAPTER_VERSION, "action_class": ACTION_CLASS, "ok": False, "result": {}, "sources": [], "errors": [msg]}

def _one_paragraph(name: str) -> str:
    return (
        f"{name} is a subsystem in the OneMind stack with a defined contract surface. "
        "In this phase it is described deterministically from local registry context only. "
        "It must be routable through AgentOS, emit evidence bundles, and fail closed on drift. "
        "Its operational definition is the minimal description required to identify its purpose, "
        "its inputs/outputs, and its safety boundaries without implying unverified capabilities."
    )

def main():
    intent = sys.argv[1] if len(sys.argv) > 1 else ""
    if intent != "onemind_stack_descriptions":
        print(canonical_json(_err(f"unsupported_intent:{intent}")))
        return 2

    result = {name: _one_paragraph(name) for name in SYSTEMS}
    payload = {
        "adapter_role": ADAPTER_ROLE,
        "adapter_version": ADAPTER_VERSION,
        "action_class": ACTION_CLASS,
        "ok": True,
        "result": {"schema_version": "morpheus-architecture/v1", "intent": intent, "systems": result},
        "sources": [],
        "errors": [],
    }
    print(canonical_json(payload))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
