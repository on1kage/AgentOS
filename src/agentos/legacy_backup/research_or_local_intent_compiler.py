from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from agentos.canonical import canonical_json, sha256_hex
from agentos.intent_classes import (
    ACTION_FOR_MODE,
    DEFAULT_MAX_RESULTS,
    DEFAULT_NO_NETWORK,
    DEFAULT_READ_ONLY,
    LOCAL_EXEC_TRIGGERS,
    MAX_RESULTS_MAX,
    MAX_RESULTS_MIN,
    RESEARCH_TRIGGERS,
    REFUSAL_AMBIGUOUS_MODE,
    REFUSAL_FORBIDDEN_NO_NETWORK_FALSE,
    REFUSAL_FORBIDDEN_READ_ONLY_FALSE,
    REFUSAL_MISSING_QUERY,
    REFUSAL_NO_MODE_MATCH,
    REFUSAL_OUT_OF_BOUNDS_MAX_RESULTS,
    REFUSAL_UNSUPPORTED_CONSTRAINT_PREFIX,
    ROLE_FOR_MODE,
)
from agentos.intent_compiler_contract import CompiledIntent, CompilationRefusal


_COMPILER_VERSION = "research_or_local_v1"
_ALLOWED_CONSTRAINT_KEYS = {"max_results", "no_network", "read_only"}

_RE_KV = re.compile(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*[:=]\s*([^\s]+)")
_RE_MAX_RESULTS_WS = re.compile(r"\bmax_results\s+([0-9]{1,3})\b")
_RE_WS = re.compile(r"\s+")


def _norm(s: str) -> str:
    return _RE_WS.sub(" ", s.strip().lower())


def _ruleset_hash() -> str:
    ruleset = {
        "compiler_version": _COMPILER_VERSION,
        "research_triggers": list(RESEARCH_TRIGGERS),
        "local_exec_triggers": list(LOCAL_EXEC_TRIGGERS),
        "max_results_min": int(MAX_RESULTS_MIN),
        "max_results_max": int(MAX_RESULTS_MAX),
        "default_max_results": int(DEFAULT_MAX_RESULTS),
        "default_no_network": bool(DEFAULT_NO_NETWORK),
        "default_read_only": bool(DEFAULT_READ_ONLY),
        "role_for_mode": dict(ROLE_FOR_MODE),
        "action_for_mode": dict(ACTION_FOR_MODE),
        "refusals": [
            REFUSAL_NO_MODE_MATCH,
            REFUSAL_AMBIGUOUS_MODE,
            REFUSAL_MISSING_QUERY,
            REFUSAL_UNSUPPORTED_CONSTRAINT_PREFIX,
            REFUSAL_OUT_OF_BOUNDS_MAX_RESULTS,
            REFUSAL_FORBIDDEN_NO_NETWORK_FALSE,
            REFUSAL_FORBIDDEN_READ_ONLY_FALSE,
        ],
    }
    return sha256_hex(canonical_json(ruleset).encode("utf-8"))


def _intent_sha256_from_text(intent_text: str) -> str:
    return sha256_hex(canonical_json({"intent_text": intent_text}).encode("utf-8"))


def _has_trigger(norm_text: str, trig: str) -> bool:
    # Closed-set trigger matching must be token-safe.
    # Example bug we prevent: 'ls' matching inside 'false'.
    pat = r"(?<![a-z0-9_])" + re.escape(trig) + r"(?![a-z0-9_])"
    return re.search(pat, norm_text) is not None


def _has_any_trigger(norm_text: str, triggers: Tuple[str, ...]) -> bool:
    for t in triggers:
        if _has_trigger(norm_text, t):
            return True
    return False


def _detect_mode(norm_text: str) -> Optional[str]:
    has_research = _has_any_trigger(norm_text, RESEARCH_TRIGGERS)
    has_local = _has_any_trigger(norm_text, LOCAL_EXEC_TRIGGERS)
    if has_research and has_local:
        return "ambiguous"
    if has_research:
        return "research"
    if has_local:
        return "local_exec"
    return None



def _parse_bool(v: str) -> Optional[bool]:
    if v == "true":
        return True
    if v == "false":
        return False
    return None


def _strip_constraints(norm_text: str) -> Tuple[str, Dict[str, Any], Optional[str]]:
    """
    Returns: (text_without_constraints, parsed_constraints, refusal_reason_or_none)
    """
    parsed: Dict[str, Any] = {}

    for m in _RE_KV.finditer(norm_text):
        k = m.group(1)
        v = m.group(2)
        if k not in _ALLOWED_CONSTRAINT_KEYS:
            return norm_text, {}, f"{REFUSAL_UNSUPPORTED_CONSTRAINT_PREFIX}{k}"
        if k == "max_results":
            if not v.isdigit():
                return norm_text, {}, f"{REFUSAL_UNSUPPORTED_CONSTRAINT_PREFIX}{k}"
            parsed["max_results"] = int(v)
        elif k in ("no_network", "read_only"):
            bv = _parse_bool(v)
            if bv is None:
                return norm_text, {}, f"{REFUSAL_UNSUPPORTED_CONSTRAINT_PREFIX}{k}"
            parsed[k] = bv

    m2 = _RE_MAX_RESULTS_WS.search(norm_text)
    if m2 and "max_results" not in parsed:
        parsed["max_results"] = int(m2.group(1))

    text2 = _RE_KV.sub(" ", norm_text)
    text2 = _RE_MAX_RESULTS_WS.sub(" ", text2)
    text2 = _RE_WS.sub(" ", text2).strip()
    return text2, parsed, None


def _strip_triggers(mode: str, norm_text: str) -> str:
    t = norm_text
    if mode == "research":
        for trig in RESEARCH_TRIGGERS:
            t = t.replace(trig, " ")
    if mode == "local_exec":
        for trig in LOCAL_EXEC_TRIGGERS:
            t = t.replace(trig, " ")
    return _RE_WS.sub(" ", t).strip()


@dataclass(frozen=True)
class ResearchOrLocalIntentCompiler:
    """
    Pure deterministic compiler:
      - natural language -> CompiledIntent (PlanSpec) OR CompilationRefusal
      - no evidence writing
      - no delegation
      - no policy decisions
    """

    compiler_version: str = _COMPILER_VERSION
    compiler_ruleset_hash: str = _ruleset_hash()

    def compile(self, intent_text: str, *, intent_sha256: Optional[str] = None) -> CompiledIntent | CompilationRefusal:
        if not isinstance(intent_text, str) or not intent_text.strip():
            ish = intent_sha256 if isinstance(intent_sha256, str) and intent_sha256 else _intent_sha256_from_text(str(intent_text))
            return CompilationRefusal(
                intent_sha256=ish,
                compiler_version=self.compiler_version,
                compiler_ruleset_hash=self.compiler_ruleset_hash,
                refusal_reason=REFUSAL_MISSING_QUERY,
            )

        norm_text = _norm(intent_text)
        ish = intent_sha256 if isinstance(intent_sha256, str) and intent_sha256 else _intent_sha256_from_text(intent_text)

        mode = _detect_mode(norm_text)
        if mode == "ambiguous":
            return CompilationRefusal(
                intent_sha256=ish,
                compiler_version=self.compiler_version,
                compiler_ruleset_hash=self.compiler_ruleset_hash,
                refusal_reason=REFUSAL_AMBIGUOUS_MODE,
            )
        if mode is None:
            return CompilationRefusal(
                intent_sha256=ish,
                compiler_version=self.compiler_version,
                compiler_ruleset_hash=self.compiler_ruleset_hash,
                refusal_reason=REFUSAL_NO_MODE_MATCH,
            )

        text_wo_constraints, constraints, refusal = _strip_constraints(norm_text)
        if refusal is not None:
            return CompilationRefusal(
                intent_sha256=ish,
                compiler_version=self.compiler_version,
                compiler_ruleset_hash=self.compiler_ruleset_hash,
                refusal_reason=refusal,
            )

        max_results = constraints.get("max_results", DEFAULT_MAX_RESULTS)
        if not isinstance(max_results, int) or max_results < int(MAX_RESULTS_MIN) or max_results > int(MAX_RESULTS_MAX):
            return CompilationRefusal(
                intent_sha256=ish,
                compiler_version=self.compiler_version,
                compiler_ruleset_hash=self.compiler_ruleset_hash,
                refusal_reason=REFUSAL_OUT_OF_BOUNDS_MAX_RESULTS,
            )

        no_network = constraints.get("no_network", DEFAULT_NO_NETWORK)
        read_only = constraints.get("read_only", DEFAULT_READ_ONLY)

        if no_network is False:
            return CompilationRefusal(
                intent_sha256=ish,
                compiler_version=self.compiler_version,
                compiler_ruleset_hash=self.compiler_ruleset_hash,
                refusal_reason=REFUSAL_FORBIDDEN_NO_NETWORK_FALSE,
            )
        if read_only is False:
            return CompilationRefusal(
                intent_sha256=ish,
                compiler_version=self.compiler_version,
                compiler_ruleset_hash=self.compiler_ruleset_hash,
                refusal_reason=REFUSAL_FORBIDDEN_READ_ONLY_FALSE,
            )

        query_text = _strip_triggers(mode, text_wo_constraints)
        if not isinstance(query_text, str) or not query_text.strip():
            return CompilationRefusal(
                intent_sha256=ish,
                compiler_version=self.compiler_version,
                compiler_ruleset_hash=self.compiler_ruleset_hash,
                refusal_reason=REFUSAL_MISSING_QUERY,
            )

        role = ROLE_FOR_MODE[mode]
        action = ACTION_FOR_MODE[mode]

        plan_spec: Dict[str, Any] = {
            "intent_class": "ResearchOrLocalIntentV1",
            "intent_class_version": 1,
            "mode": mode,
            "query": query_text,
            "constraints": {
                "max_results": int(max_results),
                "no_network": True,
                "read_only": True,
            },
            "delegate": {
                "role": role,
                "action": action,
            },
        }

        out_hash = sha256_hex(canonical_json(plan_spec).encode("utf-8"))
        return CompiledIntent(
            plan_spec=plan_spec,
            intent_sha256=ish,
            compiler_version=self.compiler_version,
            compiler_ruleset_hash=self.compiler_ruleset_hash,
            output_hash=out_hash,
        )
