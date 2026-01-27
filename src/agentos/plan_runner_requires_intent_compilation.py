from .intent_compiler_evidence import write_compilation_evidence
from .plan_runner import verify_plan
from .pipeline import Step

def require_intent_compilation(payload: dict):
    intent_text = payload.get("intent_text")
    if not intent_text:
        raise ValueError("Missing intent_text for compilation")
    path, result = write_compilation_evidence(intent_text)
    if type(result).__name__ == "CompilationRefusal":
        raise ValueError(f"Intent compilation refused: {result.refusal_reason}")
    payload["compiled_intent"] = result
    step = Step(
        role="intent_compiler",
        action="compile_intent",
    )
    return verify_plan([step])
