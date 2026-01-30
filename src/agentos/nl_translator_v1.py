from __future__ import annotations

import os
import json
from typing import Any, Dict

from .canonical import canonical_json, sha256_hex
from .intent_compiler_contract import CompilationRefusal

def _deterministic_intent_sha256(raw_nl: str) -> str:
    return sha256_hex(canonical_json({"nl": raw_nl}).encode("utf-8"))

def translate_nl_to_proposed(raw_nl: str) -> Dict[str, Any] | CompilationRefusal:
    intent_sha256 = _deterministic_intent_sha256(raw_nl)
    payload = os.environ.get("AGENTOS_NL_TRANSLATOR_INPUT_JSON")
    if payload is None or payload == "":
        return CompilationRefusal(
            intent_sha256=intent_sha256,
            compiler_version="nl_translator_v1",
            compiler_ruleset_hash="nl_translator_v1",
            refusal_reason="refusal:nl_translator:disabled",
        )
    try:
        obj = json.loads(payload)
    except Exception as e:
        return CompilationRefusal(
            intent_sha256=intent_sha256,
            compiler_version="nl_translator_v1",
            compiler_ruleset_hash="nl_translator_v1",
            refusal_reason="refusal:nl_translator:invalid_json",
        )
    if not isinstance(obj, dict):
        return CompilationRefusal(
            intent_sha256=intent_sha256,
            compiler_version="nl_translator_v1",
            compiler_ruleset_hash="nl_translator_v1",
            refusal_reason="refusal:nl_translator:non_dict",
        )
    return obj
