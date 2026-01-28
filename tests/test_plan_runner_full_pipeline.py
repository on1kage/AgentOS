import pytest
from agentos.plan_runner_full_pipeline import run_full_pipeline

def test_full_pipeline_success():
    payload = {"intent_text": "search for papers"}
    result = run_full_pipeline(payload)
    assert "compiled_intent" in payload
    assert "intent_compilation_manifest_sha256" in payload
    assert result is not None

def test_full_pipeline_refusal():
    payload = {"intent_text": "do something unknown"}
    with pytest.raises(ValueError) as e:
        run_full_pipeline(payload)
    assert "intent_compilation_refused" in str(e.value)
