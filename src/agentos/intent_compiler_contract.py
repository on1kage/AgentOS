from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass(frozen=True)
class IntentInput:
    intent_text: str
    metadata: Optional[Dict[str, Any]] = None

@dataclass(frozen=True)
class CompiledIntent:
    plan_spec: Dict[str, Any]
    intent_sha256: str
    compiler_version: str
    compiler_ruleset_hash: str
    output_hash: str

@dataclass(frozen=True)
class CompilationRefusal:
    intent_sha256: str
    compiler_version: str
    compiler_ruleset_hash: str
    refusal_reason: str
