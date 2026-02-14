import os
from agentos.plan_runner_full_pipeline import run_full_pipeline

def test_planspec_live_execution():
    os.environ["AGENTOS_INTENT_SOURCE"] = "planspec_v1"
    try:
        payload = {
            "intent_text": "find papers about transformers",
            "plan_spec": {"role": "scout", "action": "external_research", "metadata": {"query": "transformers", "max_results": 3}},
        }
        res = run_full_pipeline(payload)
        assert res.ok is True
        assert isinstance(res.decisions, list)
        first_decision = res.decisions[0]
        assert first_decision["role"] == "scout"
        assert first_decision["action"] == "external_research"
    finally:
        os.environ.pop("AGENTOS_INTENT_SOURCE", None)
