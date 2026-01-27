import pytest
from agentos.plan_runner_full_pipeline import run_full_pipeline
from agentos.intent_compiler import CompilationRefusal

def test_pipeline_fails_without_intent():
    payload = {}
    with pytest.raises(ValueError):
        run_full_pipeline(payload)

def test_pipeline_refuses_ambiguous_intent():
    payload = {"intent_text": "do something unknown"}
    with pytest.raises(ValueError):
        run_full_pipeline(payload)

def test_pipeline_runs_valid_intent():
    payload = {"intent_text": "search for papers"}
    result = run_full_pipeline(payload)
    assert "compiled_intent" in payload
    assert result is not None or result is True
