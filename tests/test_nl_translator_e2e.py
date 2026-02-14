import os
from agentos.plan_runner_full_pipeline import run_full_pipeline

def test_planspec_research_dry_run():
    os.environ["AGENTOS_INTENT_SOURCE"] = "planspec_v1"
    try:
        payload = {
            "intent_text": "find papers about transformers",
            "plan_spec": {"role": "scout", "action": "external_research", "metadata": {"query": "test query", "max_results": 3}},
        }
        res = run_full_pipeline(payload)
        assert res.ok is True
        assert isinstance(res.decisions, list)
    finally:
        os.environ.pop("AGENTOS_INTENT_SOURCE", None)
