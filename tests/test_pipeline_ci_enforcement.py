import os
import pytest
from agentos.plan_runner_full_pipeline import run_full_pipeline

def test_pipeline_fails_without_intent():
    payload = {}
    with pytest.raises(ValueError) as e:
        run_full_pipeline(payload)
    assert "missing_intent_text" in str(e.value)

def test_pipeline_blocks_legacy_intake_when_intent_source_unset(tmp_path):
    old_store = os.environ.get("AGENTOS_STORE_ROOT")
    os.environ["AGENTOS_STORE_ROOT"] = str(tmp_path / "store")
    try:
        payload = {"intent_text": "do something unknown"}
        res = run_full_pipeline(payload)
        assert res is not None
        assert getattr(res, "ok", None) is False
        assert res.decisions[0]["stage"] == "intent_source_gate"
        assert res.decisions[0]["reason"] == "legacy_path_blocked:intent_source_unset"
        assert getattr(res, "verification_manifest_sha256", None)
    finally:
        if old_store is None:
            os.environ.pop("AGENTOS_STORE_ROOT", None)
        else:
            os.environ["AGENTOS_STORE_ROOT"] = old_store

def test_pipeline_runs_valid_intent_planspec_v1(tmp_path):
    old_store = os.environ.get("AGENTOS_STORE_ROOT")
    os.environ["AGENTOS_INTENT_SOURCE"] = "planspec_v1"
    os.environ["AGENTOS_STORE_ROOT"] = str(tmp_path / "store")
    try:
        payload = {
            "intent_text": "search for papers",
            "plan_spec": {"role": "scout", "action": "external_research", "metadata": {"query": "papers", "max_results": 3}},
        }
        result = run_full_pipeline(payload)
        assert "compiled_intent" in payload
        assert "intent_compilation_manifest_sha256" in payload
        assert result is not None
        assert getattr(result, "ok", None) is True
    finally:
        os.environ.pop("AGENTOS_INTENT_SOURCE", None)
        if old_store is None:
            os.environ.pop("AGENTOS_STORE_ROOT", None)
        else:
            os.environ["AGENTOS_STORE_ROOT"] = old_store
