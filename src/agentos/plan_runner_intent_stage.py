from .plan_runner_requires_intent_compilation import require_intent_compilation

def run_intent_stage(payload: dict):
    return require_intent_compilation(payload)
