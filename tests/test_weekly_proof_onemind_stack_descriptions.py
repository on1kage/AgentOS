import os
import sys
import subprocess
from pathlib import Path
import json

INTENT = "onemind_stack_descriptions"
FIXTURE_ARTIFACT = Path("store/weekly_proof/artifacts/utc_date_weekly_proof.json")

def _run_morpheus() -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PYTHONPATH"] = "src"
    return subprocess.run(
        [sys.executable, "tools/morpheus_run.py", INTENT],
        capture_output=True,
        text=True,
        env=env,
    )

def test_onemind_stack_descriptions_positive():
    p = _run_morpheus()
    assert p.returncode == 0
    out = p.stdout.strip()
    data = json.loads(out)
    # Basic schema checks
    assert data.get("ok") is True
    assert "result" in data
    systems = data["result"].get("systems", {})
    assert isinstance(systems, dict)
    # At least Morpheus, Envoy, Scout should be described
    for name in ("morpheus", "envoy", "scout"):
        assert name in systems
        desc = systems[name]
        assert isinstance(desc, str)
        assert len(desc) > 20  # sanity check on paragraph length
