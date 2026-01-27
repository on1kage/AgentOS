import pytest
from agentos.plan_runner_full_pipeline import run_full_pipeline
from agentos.intent_compiler import CompilationRefusal

def test_full_pipeline_success():
    payload = {"intent_text": "search for papers"}
    result = run_full_pipeline(payload)
    assert "compiled_intent" in payload
    assert result is True or result is not None

def test_full_pipeline_refusal():
    payload = {"intent_text": "do something unknown"}
    with pytest.raises(ValueError) as e:
        run_full_pipeline(payload)
    assert "Intent compilation refused" in str(e.value)
