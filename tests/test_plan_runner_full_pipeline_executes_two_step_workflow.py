import os

from agentos.plan_runner_full_pipeline import run_full_pipeline


def test_full_pipeline_executes_two_step_workflow(tmp_path):
    old_store = os.environ.get("AGENTOS_STORE_ROOT")
    old_source = os.environ.get("AGENTOS_INTENT_SOURCE")
    old_key = os.environ.get("OPENAI_API_KEY")
    try:
        os.environ["AGENTOS_STORE_ROOT"] = str(tmp_path / "store")
        os.environ["AGENTOS_INTENT_SOURCE"] = "planspec_v1"
        os.environ["OPENAI_API_KEY"] = "test-key"

        payload = {
            "intent_text": "describe stack then get system status",
            "plan_spec": {
                "role": "morpheus",
                "action": "architecture",
                "metadata": {
                    "intent_name": "onemind_stack_descriptions",
                    "workflow_steps": [
                        {
                            "role": "envoy",
                            "action": "deterministic_local_execution",
                            "intent_name": "system_status",
                        }
                    ],
                },
            },
        }

        result = run_full_pipeline(payload)

        assert result is not None
        assert getattr(result, "ok", None) is True
        assert hasattr(result, "steps")
        assert len(result.steps) == 2

        assert result.steps[0].role == "morpheus"
        assert result.steps[0].action == "architecture"
        assert result.steps[0].run_ok is True

        assert result.steps[1].role == "envoy"
        assert result.steps[1].action == "deterministic_local_execution"
        assert result.steps[1].run_ok is True
    finally:
        if old_store is None:
            os.environ.pop("AGENTOS_STORE_ROOT", None)
        else:
            os.environ["AGENTOS_STORE_ROOT"] = old_store
        if old_source is None:
            os.environ.pop("AGENTOS_INTENT_SOURCE", None)
        else:
            os.environ["AGENTOS_INTENT_SOURCE"] = old_source
        if old_key is None:
            os.environ.pop("OPENAI_API_KEY", None)
        else:
            os.environ["OPENAI_API_KEY"] = old_key
