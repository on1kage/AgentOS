import pytest
from agentos.plan_runner_full_pipeline import run_full_pipeline

def test_pipeline_fails_without_intent():
    payload = {}
    with pytest.raises(ValueError) as e:
        run_full_pipeline(payload)
    assert "missing_intent_text" in str(e.value)

def test_pipeline_refuses_ambiguous_intent():
    payload = {"intent_text": "do something unknown"}
    with pytest.raises(ValueError) as e:
        run_full_pipeline(payload)
    assert "intent_compilation_refused" in str(e.value)

def test_pipeline_runs_valid_intent():
    payload = {"intent_text": "search for papers"}
    result = run_full_pipeline(payload)
    assert "compiled_intent" in payload
    assert "intent_compilation_manifest_sha256" in payload
    assert result is not None
