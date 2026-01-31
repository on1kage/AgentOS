import os
from agentos.agent_pipeline_entry import execute_agent_pipeline

def test_nl_translator_ci_success():
    os.environ["AGENTOS_INTENT_SOURCE"] = "nl_translator_v1"
    os.environ["AGENTOS_ALLOW_LEGACY_NL_TRANSLATOR"] = "1"
    os.environ["AGENTOS_NL_TRANSLATOR_INPUT_JSON"] = '{"mode":"research","query":"ci test"}'
    try:
        res = execute_agent_pipeline("ci test intent")
        assert res.ok is True
    finally:
        os.environ.pop("AGENTOS_INTENT_SOURCE", None)
        os.environ.pop("AGENTOS_ALLOW_LEGACY_NL_TRANSLATOR", None)
        os.environ.pop("AGENTOS_NL_TRANSLATOR_INPUT_JSON", None)

def test_nl_translator_ci_failure():
    os.environ["AGENTOS_INTENT_SOURCE"] = "nl_translator_v1"
    os.environ["AGENTOS_ALLOW_LEGACY_NL_TRANSLATOR"] = "1"
    os.environ["AGENTOS_NL_TRANSLATOR_INPUT_JSON"] = ""
    try:
        res = execute_agent_pipeline("ci test intent")
        assert res.ok is False
    finally:
        os.environ.pop("AGENTOS_INTENT_SOURCE", None)
        os.environ.pop("AGENTOS_NL_TRANSLATOR_INPUT_JSON", None)
