from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Set

from .intent_classes import Mode, MAX_RESULTS_MAX, MAX_RESULTS_MIN
from .intent_compiler_contract import CompilationRefusal
from .canonical import canonical_json, sha256_hex

@dataclass(frozen=True)
class ProposedIntentV1:
    mode: Mode
    query: str
    max_results: Optional[int] = None
    no_network: Optional[bool] = None
    read_only: Optional[bool] = None

_ALLOWED_KEYS: Set[str] = {"mode", "query", "max_results", "no_network", "read_only"}

def _refusal(intent_sha256: str, reason: str) -> CompilationRefusal:
    return CompilationRefusal(
        intent_sha256=intent_sha256,
        compiler_version="nl_translator_v1",
        compiler_ruleset_hash="nl_translator_v1",
        refusal_reason=reason,
    )

def _deterministic_intent_sha256(raw_nl: str) -> str:
    return sha256_hex(canonical_json({"nl": raw_nl}).encode("utf-8"))

def parse_proposed_intent_v1(raw_nl: str, obj: Any) -> ProposedIntentV1 | CompilationRefusal:
    intent_sha256 = _deterministic_intent_sha256(raw_nl)
    if not isinstance(obj, dict):
        return _refusal(intent_sha256, "refusal:proposed_intent:not_dict")
    unknown = sorted({k for k in obj.keys() if isinstance(k, str) and k not in _ALLOWED_KEYS} | { "__non_string_key__" for k in obj.keys() if not isinstance(k, str) })
    if unknown:
        return _refusal(intent_sha256, "refusal:proposed_intent:unknown_keys:" + ",".join(unknown))
    mode = obj.get("mode")
    query = obj.get("query")
    if mode not in ("research", "local_exec"):
        return _refusal(intent_sha256, "refusal:proposed_intent:invalid_mode")
    if not isinstance(query, str) or not query:
        return _refusal(intent_sha256, "refusal:proposed_intent:missing_query")
    max_results = obj.get("max_results")
    if max_results is not None:
        if not isinstance(max_results, int):
            return _refusal(intent_sha256, "refusal:proposed_intent:max_results_not_int")
        if max_results < MAX_RESULTS_MIN or max_results > MAX_RESULTS_MAX:
            return _refusal(intent_sha256, "refusal:proposed_intent:max_results_out_of_bounds")
    no_network = obj.get("no_network")
    if no_network is not None and not isinstance(no_network, bool):
        return _refusal(intent_sha256, "refusal:proposed_intent:no_network_not_bool")
    read_only = obj.get("read_only")
    if read_only is not None and not isinstance(read_only, bool):
        return _refusal(intent_sha256, "refusal:proposed_intent:read_only_not_bool")
    return ProposedIntentV1(
        mode=mode,
        query=query,
        max_results=max_results,
        no_network=no_network,
        read_only=read_only,
    )
