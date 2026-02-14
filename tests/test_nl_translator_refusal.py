import os
import tempfile
from agentos.plan_runner_full_pipeline import run_full_pipeline

def _run_with_temp_store(payload):
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["AGENTOS_INTENT_SOURCE"] = "planspec_v1"
        os.environ["AGENTOS_STORE_ROOT"] = tmpdir
        try:
            return run_full_pipeline(payload)
        finally:
            os.environ.pop("AGENTOS_INTENT_SOURCE", None)
            os.environ.pop("AGENTOS_STORE_ROOT", None)

def test_planspec_refusal_missing_planspec():
    res = _run_with_temp_store({"intent_text": "any intent text"})
    assert res.ok is False
    assert res.decisions[0]["stage"] == "planspec_refusal"
    assert res.decisions[0]["reason"] == "planspec_invalid:not_a_dict"

def test_planspec_refusal_unknown_keys():
    res = _run_with_temp_store({
        "intent_text": "any intent text",
        "plan_spec": {"role": "scout", "action": "external_research", "wat": 1, "metadata": {}},
    })
    assert res.ok is False
    assert res.decisions[0]["stage"] == "planspec_refusal"
    assert res.decisions[0]["reason"] == "planspec_invalid:unknown_keys"

def test_planspec_refusal_invalid_metadata():
    res = _run_with_temp_store({
        "intent_text": "any intent text",
        "plan_spec": {"role": "scout", "action": "external_research", "metadata": "nope"},
    })
    assert res.ok is False
    assert res.decisions[0]["stage"] == "planspec_refusal"
    assert res.decisions[0]["reason"] == "planspec_invalid:metadata_not_dict"
