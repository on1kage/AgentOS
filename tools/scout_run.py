#!/usr/bin/env python3
from __future__ import annotations

import sys
import os
import json
from typing import Any, Dict
from datetime import datetime, timezone

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "onemind-FSM-Kernel" / "src"))

from agentos.role_assignments_loader import load_role_assignments, RoleAssignmentError
from agentos.json_utils import canonical_json

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
        ra = load_role_assignments(require_env_for_roles=[])
    except RoleAssignmentError as e:
        sys.stdout.write(canonical_json(_err(str(e))) + "\n")
        return 2

    scout = ra.get("scout") or {}
    provider = str(scout.get("provider") or "")
    model = str(scout.get("model") or "")

    if intent not in ("utc_date", "system_status"):
        sys.stdout.write(canonical_json(_err(f"unsupported_intent:{intent}")) + "\n")
        return 2

    # ---- LOCAL PROVIDER (deterministic, no network) ----
    if provider == "local":
        if intent == "utc_date":
            answer = datetime.now(timezone.utc).date().isoformat()
        else:
            answer = (
                datetime.now(timezone.utc)
                .replace(microsecond=0)
                .isoformat()
                .replace("+00:00", "Z")
            )

        payload: Dict[str, Any] = {
            "adapter_role": ADAPTER_ROLE,
            "adapter_version": ADAPTER_VERSION,
            "action_class": ACTION_CLASS,
            "ok": True,
            "result": {
                "schema_version": "scout-intel/v1",
                "question": "",
                "answer": answer,
                "model": "local",
                "usage": None,
            },
            "sources": [],
            "errors": [],
        }

        sys.stdout.write(canonical_json(payload) + "\n")
        return 0

    # ---- OPENAI PROVIDER ----
    if provider == "openai":
        from onemind.scout.openai_chat import ask_openai

        if not os.getenv("OPENAI_API_KEY"):
            sys.stdout.write(canonical_json(_err("missing_api_key_env:scout:OPENAI_API_KEY")) + "\n")
            return 1

        if intent == "utc_date":
            question = "What is today's UTC date? Respond with a single ISO date string (YYYY-MM-DD)."
            context = "Return a single ISO date string only."
        else:
            question = "What is the current UTC date and time right now? Respond with a single ISO 8601 UTC timestamp ending with Z."
            context = "Return a single ISO 8601 UTC timestamp only."

        try:
            r = ask_openai(question=question, context=context, timeout=30.0)
        except Exception as e:
            sys.stdout.write(canonical_json(_err(f"provider_error:openai:{type(e).__name__}:{e}")) + "\n")
            return 1

        payload = {
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

    # ---- PERPLEXITY PROVIDER ----
    if provider == "perplexity":
        from onemind.scout.perplexity import ask_perplexity

        if not os.getenv("PPLX_API_KEY"):
            sys.stdout.write(canonical_json(_err("missing_api_key_env:scout:PPLX_API_KEY")) + "\n")
            return 1

        if intent == "utc_date":
            question = "What is today's UTC date? Respond with a single ISO date string (YYYY-MM-DD)."
            context = "Return a single ISO date string only."
        else:
            question = "What is the current UTC date and time right now? Respond with a single ISO 8601 UTC timestamp ending with Z."
            context = "Return a single ISO 8601 UTC timestamp only."

        try:
            r = ask_perplexity(question=question, context=context, timeout=30.0)
        except Exception as e:
            sys.stdout.write(canonical_json(_err(f"provider_error:perplexity:{type(e).__name__}:{e}")) + "\n")
            return 1

        payload = {
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
