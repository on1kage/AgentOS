import pytest
from agentos.plan_runner_intent_stage import run_intent_stage
from agentos.intent_compiler import CompilationRefusal

def test_intent_stage_success():
    payload = {"intent_text": "search for papers"}
    result = run_intent_stage(payload)
    assert "compiled_intent" in payload
    assert result is True or result is not None

def test_intent_stage_refusal():
    payload = {"intent_text": "do something unknown"}
    with pytest.raises(ValueError) as e:
        run_intent_stage(payload)
    assert "Intent compilation refused" in str(e.value)
