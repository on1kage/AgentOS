from agentos.plan_runner_full_pipeline import run_full_pipeline


def test_end_to_end_pipeline_acceptance():
    payload = {"intent_text": "search for papers"}
    result = run_full_pipeline(payload)
    assert result is not None
    assert getattr(result, "ok", None) is True
