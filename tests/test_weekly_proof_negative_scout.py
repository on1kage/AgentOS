from pathlib import Path
import importlib.util
import pytest
import os
from agentos.intents import intent_spec

# Dynamically load weekly_proof_run.py
spec_path = Path(__file__).parent.parent / "tools/weekly_proof_run.py"
spec = importlib.util.spec_from_file_location("weekly_proof_run", spec_path)
wpr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wpr)

def test_scout_intent_failure_is_captured():
    intent_name = "utc_date"
    run_id = "failtest"
    spec_obj = intent_spec(intent_name)

    # Temporarily remove all Scout-required environment variables to force failure
    old_env = dict(os.environ)
    for key in wpr.ADAPTERS["scout"]["env_allowlist"]:
        os.environ.pop(key, None)

    try:
        # Expect RuntimeError due to missing required env
        with pytest.raises(RuntimeError, match="missing_required_env_for_role:scout"):
            wpr._run_role(
                intent_name=intent_name,
                intent_spec_obj=spec_obj,
                run_id=run_id,
                role="scout",
                store_root=Path("store") / "weekly_proof" / intent_name / run_id,
                cwd=str(Path.cwd()),
                paths_allowlist=[str(Path.cwd())],
                require_env=True
            )
    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(old_env)
