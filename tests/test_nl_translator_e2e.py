import os
from agentos.agent_pipeline_entry import execute_agent_pipeline

def test_nl_translator_research_dry_run():
    os.environ["AGENTOS_INTENT_SOURCE"] = "nl_translator_v1"
    os.environ["AGENTOS_NL_TRANSLATOR_INPUT_JSON"] = '{"mode":"research","query":"test query","max_results":3}'
    try:
        res = execute_agent_pipeline("find papers about transformers")
        assert res.ok is True
        assert isinstance(res.decisions, list)
    finally:
        os.environ.pop("AGENTOS_INTENT_SOURCE", None)
        os.environ.pop("AGENTOS_NL_TRANSLATOR_INPUT_JSON", None)
