import os
import tempfile
from agentos.agent_pipeline_entry import execute_agent_pipeline

def _run_with_temp_evidence(intent_source, payload_json, intent_text):
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["AGENTOS_INTENT_SOURCE"] = intent_source
        os.environ["AGENTOS_NL_TRANSLATOR_INPUT_JSON"] = payload_json
        os.environ["AGENTOS_STORE_ROOT"] = tmpdir
        os.environ["AGENTOS_ALLOW_LEGACY_NL_TRANSLATOR"] = "1"
        try:
            return execute_agent_pipeline(intent_text)
        finally:
            os.environ.pop("AGENTOS_INTENT_SOURCE", None)
            os.environ.pop("AGENTOS_NL_TRANSLATOR_INPUT_JSON", None)
            os.environ.pop("AGENTOS_STORE_ROOT", None)
            os.environ.pop("AGENTOS_ALLOW_LEGACY_NL_TRANSLATOR", None)

def test_nl_translator_disabled_refusal():
    res = _run_with_temp_evidence("nl_translator_v1", "", "any intent text")
    assert res.ok is False
    assert res.decisions[0]["stage"] == "nl_translator_refusal"
    assert res.decisions[0]["reason"] == "refusal:nl_translator:disabled"

def test_nl_translator_invalid_json():
    res = _run_with_temp_evidence("nl_translator_v1", "{bad json}", "any intent text")
    assert res.ok is False
    assert res.decisions[0]["stage"] == "nl_translator_refusal"
    assert res.decisions[0]["reason"] == "refusal:nl_translator:invalid_json"
