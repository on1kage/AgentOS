from hashlib import sha256
from typing import Union
from .intent_ingest import ingest_intent
from .intent_compiler_contract import CompiledIntent, CompilationRefusal

COMPILER_VERSION = "0.2"
COMPILER_RULESET_HASH = sha256(b"basic_ruleset_v0.2").hexdigest()

def compile_intent(intent_text: str) -> Union[CompiledIntent, CompilationRefusal]:
    ingested = ingest_intent(intent_text)
    normalized = intent_text.strip().lower()
    allowed_phrases = ["search", "report"]
    if not any(phrase in normalized for phrase in allowed_phrases):
        return CompilationRefusal(
            intent_sha256=ingested["intent_sha256"],
            compiler_version=COMPILER_VERSION,
            compiler_ruleset_hash=COMPILER_RULESET_HASH,
            refusal_reason="Ambiguous or unsupported intent"
        )
    plan_spec = {"actions": ["noop"], "agents": ["scout","envoy"]}
    output_hash = sha256(str(plan_spec).encode("utf-8")).hexdigest()
    return CompiledIntent(
        plan_spec=plan_spec,
        intent_sha256=ingested["intent_sha256"],
        compiler_version=COMPILER_VERSION,
        compiler_ruleset_hash=COMPILER_RULESET_HASH,
        output_hash=output_hash
    )
