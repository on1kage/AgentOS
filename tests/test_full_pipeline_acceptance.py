import pytest
from agentos.agent_pipeline_entry import execute_agent_pipeline

def test_end_to_end_pipeline_acceptance():
    intent = "search for papers"
    result = execute_agent_pipeline(intent)
    assert result is not None
