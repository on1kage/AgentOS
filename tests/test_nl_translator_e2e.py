import os
from agentos.plan_runner_full_pipeline import run_full_pipeline

def test_planspec_research_dry_run(tmp_path):
    old_store = os.environ.get("AGENTOS_STORE_ROOT")
    os.environ["AGENTOS_INTENT_SOURCE"] = "planspec_v1"
    os.environ["AGENTOS_STORE_ROOT"] = str(tmp_path / "store")
    try:
        payload = {
            "intent_text": "find papers about transformers",
            "plan_spec": {"role": "scout", "action": "external_research", "metadata": {"query": "test query", "max_results": 3}},
        }
        res = run_full_pipeline(payload)
        assert res.ok is True
        assert hasattr(res, "steps")
        assert len(res.steps) == 1
    finally:
        os.environ.pop("AGENTOS_INTENT_SOURCE", None)
        if old_store is None:
            os.environ.pop("AGENTOS_STORE_ROOT", None)
        else:
            os.environ["AGENTOS_STORE_ROOT"] = old_store
