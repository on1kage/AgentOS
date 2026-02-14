import os
from agentos.plan_runner_full_pipeline import run_full_pipeline

def test_planspec_ci_success():
    os.environ["AGENTOS_INTENT_SOURCE"] = "planspec_v1"
    try:
        payload = {
            "intent_text": "ci test intent",
            "plan_spec": {"role": "scout", "action": "external_research", "metadata": {}},
        }
        res = run_full_pipeline(payload)
        assert res.ok is True
        assert isinstance(res.decisions, list)
    finally:
        os.environ.pop("AGENTOS_INTENT_SOURCE", None)

def test_planspec_ci_failure_missing_planspec():
    os.environ["AGENTOS_INTENT_SOURCE"] = "planspec_v1"
    try:
        payload = {"intent_text": "ci test intent"}
        res = run_full_pipeline(payload)
        assert res.ok is False
        assert res.decisions[0]["stage"] == "planspec_refusal"
        assert res.decisions[0]["reason"] == "planspec_invalid:not_a_dict"
    finally:
        os.environ.pop("AGENTOS_INTENT_SOURCE", None)
