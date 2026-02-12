import json
import os
import subprocess
import sys

def _run_weekly_proof() -> dict:
    env = dict(os.environ)
    env["PYTHONPATH"] = "./src"
    p = subprocess.run(
        [sys.executable, "tools/weekly_proof_run.py", "--intent", "utc_date", "--roles", "envoy,scout"],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    return json.loads(p.stdout)

def test_weekly_proof_double_run_reproducible():
    a = _run_weekly_proof()
    b = _run_weekly_proof()

    assert a["results"]["envoy"]["spec_sha256"] == b["results"]["envoy"]["spec_sha256"]
    assert a["results"]["envoy"]["manifest_sha256"] == b["results"]["envoy"]["manifest_sha256"]
    assert a["results"]["scout"]["spec_sha256"] == b["results"]["scout"]["spec_sha256"]
    assert a["results"]["scout"]["manifest_sha256"] == b["results"]["scout"]["manifest_sha256"]
