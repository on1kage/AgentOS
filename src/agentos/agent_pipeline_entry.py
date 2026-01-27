from .plan_runner_full_pipeline import run_full_pipeline

def execute_agent_pipeline(intent_text: str):
    payload = {"intent_text": intent_text}
    return run_full_pipeline(payload)
