from .plan_runner_intent_stage import run_intent_stage
from .plan_runner import verify_plan
from .pipeline import Step

def run_full_pipeline(payload: dict):
    run_intent_stage(payload)
    step = Step(
        role="intent_compiler",
        action="compile_intent",
    )
    return verify_plan([step])
