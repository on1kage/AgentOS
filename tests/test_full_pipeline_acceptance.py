import os
from agentos.plan_runner_full_pipeline import run_full_pipeline

def test_end_to_end_pipeline_acceptance(tmp_path):
    old_store = os.environ.get("AGENTOS_STORE_ROOT")
    old_source = os.environ.get("AGENTOS_INTENT_SOURCE")
    try:
        os.environ["AGENTOS_STORE_ROOT"] = str(tmp_path / "store")
        os.environ["AGENTOS_INTENT_SOURCE"] = "planspec_v1"
        payload = {
            "intent_text": "search for papers",
            "plan_spec": {"role": "scout", "action": "external_research", "metadata": {"query": "papers", "max_results": 3}},
        }
        result = run_full_pipeline(payload)
        assert result is not None
        assert getattr(result, "ok", None) is True
    finally:
        if old_store is None:
            os.environ.pop("AGENTOS_STORE_ROOT", None)
        else:
            os.environ["AGENTOS_STORE_ROOT"] = old_store
        if old_source is None:
            os.environ.pop("AGENTOS_INTENT_SOURCE", None)
        else:
            os.environ["AGENTOS_INTENT_SOURCE"] = old_source
