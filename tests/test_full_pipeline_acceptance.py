import os
from agentos.plan_runner_full_pipeline import run_full_pipeline

def test_end_to_end_pipeline_acceptance():
    os.environ["AGENTOS_INTENT_SOURCE"] = "planspec_v1"
    try:
        payload = {
            "intent_text": "search for papers",
            "plan_spec": {"role": "scout", "action": "external_research", "metadata": {"query": "papers", "max_results": 3}},
        }
        result = run_full_pipeline(payload)
        assert result is not None
        assert getattr(result, "ok", None) is True
    finally:
        os.environ.pop("AGENTOS_INTENT_SOURCE", None)
