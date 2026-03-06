import os
from pathlib import Path

from agentos.plan_runner_full_pipeline import run_full_pipeline


def test_full_pipeline_executes_morpheus_through_planrunner(tmp_path):
    old_store = os.environ.get("AGENTOS_STORE_ROOT")
    old_source = os.environ.get("AGENTOS_INTENT_SOURCE")
    old_key = os.environ.get("OPENAI_API_KEY")
    try:
        os.environ["AGENTOS_STORE_ROOT"] = str(tmp_path / "store")
        os.environ["AGENTOS_INTENT_SOURCE"] = "planspec_v1"
        os.environ["OPENAI_API_KEY"] = "test-key"

        payload = {
            "intent_text": "describe the OneMind stack",
            "plan_spec": {
                "role": "morpheus",
                "action": "architecture",
                "metadata": {"intent_name": "onemind_stack_descriptions"},
            },
        }

        result = run_full_pipeline(payload)

        assert result is not None
        assert getattr(result, "ok", None) is True
        assert hasattr(result, "steps")
        assert len(result.steps) == 1

        step = result.steps[0]
        assert step.role == "morpheus"
        assert step.action == "architecture"
        assert step.verified_ok is True
        assert step.routed_ok is True
        assert step.run_ok is True
        assert isinstance(step.run_evidence_manifest_sha256, str) and len(step.run_evidence_manifest_sha256) == 64

        evidence_root = Path(os.environ["AGENTOS_STORE_ROOT"]) / "evidence"
        assert evidence_root.exists()
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
