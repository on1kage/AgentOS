from agentos.legacy_backup.research_or_local_intent_compiler import CompilationRefusal
import os
from agentos.agent_pipeline_entry import execute_agent_pipeline

def test_morpheus_live_nl_execution():
    os.environ["AGENTOS_INTENT_SOURCE"] = "nl_translator_v1"
    os.environ["AGENTOS_ALLOW_LEGACY_NL_TRANSLATOR"] = "1"
    os.environ["AGENTOS_NL_TRANSLATOR_INPUT_JSON"] = '{"mode":"research","query":"transformers","max_results":3}'
    try:
        res = execute_agent_pipeline("find papers about transformers")
        assert res.ok is True
        assert isinstance(res.decisions, list)
        # Optional: validate first step role/action matches expected mapping
        first_decision = res.decisions[0]
        assert first_decision["role"] == "scout"
        assert first_decision["action"] == "external_research"
    finally:
        os.environ.pop("AGENTOS_INTENT_SOURCE", None)
        os.environ.pop("AGENTOS_ALLOW_LEGACY_NL_TRANSLATOR", None)
        os.environ.pop("AGENTOS_NL_TRANSLATOR_INPUT_JSON", None)
