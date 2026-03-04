import os
import sys
import subprocess
from pathlib import Path
import json

FIXTURE_ARTIFACT = Path("store/weekly_proof/artifacts/utc_date_weekly_proof.json")
CONTRACT_PATH = Path("src/agentos/adapter_role_contract.json")

def _run_verify() -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PYTHONPATH"] = "src"
    return subprocess.run(
        [sys.executable, "tools/weekly_proof_verify.py", "--artifact", str(FIXTURE_ARTIFACT)],
        capture_output=True,
        text=True,
        env=env,
    )

def test_weekly_proof_fails_closed_on_morpheus_roles_tamper(tmp_path: Path):
    orig = CONTRACT_PATH.read_text(encoding="utf-8")
    try:
        c = json.loads(orig)
        # Tamper: add an unauthorized action to Morpheus
        c["morpheus"]["allowed_actions"].append("x_tamper")
        from agentos.adapter_role_contract_checker import compute_sha256, _binding_fingerprint
        c["contract_binding_sha256"] = compute_sha256(_binding_fingerprint(c))

        CONTRACT_PATH.write_text(
            json.dumps(c, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n",
            encoding="utf-8"
        )

        p = _run_verify()
        assert p.returncode != 0
        out = (p.stdout or "") + (p.stderr or "")
        assert "role_contract_action_parity_mismatch" in out or "FAIL:" in out
    finally:
        # Restore original contract
        CONTRACT_PATH.write_text(orig, encoding="utf-8")
