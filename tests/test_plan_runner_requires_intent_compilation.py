import pytest
from agentos.plan_runner_requires_intent_compilation import require_intent_compilation
from agentos.intent_compiler import CompilationRefusal

def test_compilation_success():
    payload = {"intent_text": "search for papers"}
    result = require_intent_compilation(payload)
    assert "compiled_intent" in payload
    assert result is True or result is not None

def test_compilation_refusal():
    payload = {"intent_text": "do something unknown"}
    with pytest.raises(ValueError) as e:
        require_intent_compilation(payload)
    assert "Intent compilation refused" in str(e.value)
