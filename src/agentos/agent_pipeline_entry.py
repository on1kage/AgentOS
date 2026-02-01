from __future__ import annotations

from typing import Any, Dict, Union

from agentos.chatgpt_planspec_adapter import chatgpt_nl_to_planspec
from agentos.plan_runner_full_pipeline import run_full_pipeline


def execute_agent_pipeline(input_data: Union[str, Dict[str, Any]]):

    if isinstance(input_data, dict):
        payload = input_data
    elif isinstance(input_data, str):
        payload = chatgpt_nl_to_planspec(input_data)
    else:
        raise TypeError("execute_agent_pipeline expects str or dict")

    return run_full_pipeline(payload)
