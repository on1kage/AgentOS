import os
import sys
import subprocess
from pathlib import Path

FIXTURE_ARTIFACT = Path("store/weekly_proof/artifacts/utc_date_weekly_proof.json")
ROLES_PATH = Path("src/agentos/roles.py")

def _run_verify() -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PYTHONPATH"] = "src"
    return subprocess.run(
        [sys.executable, "tools/weekly_proof_verify.py", "--artifact", str(FIXTURE_ARTIFACT)],
        capture_output=True,
        text=True,
        env=env,
    )

def test_weekly_proof_fails_closed_on_roles_registry_mutation(tmp_path: Path):
    orig = ROLES_PATH.read_text(encoding="utf-8")
    try:
        mutated = orig.replace(
            'authority=["architecture", "verification", "protocol_enforcement"],',
            'authority=["architecture", "verification", "protocol_enforcement", "x_mutation"],',
        )
        if mutated == orig:
            raise RuntimeError("failed_to_mutate_roles_file")
        ROLES_PATH.write_text(mutated, encoding="utf-8")

        p = _run_verify()
        assert p.returncode != 0
        out = (p.stdout or "") + (p.stderr or "")
        assert ("role_contract_action_parity_mismatch" in out) or ("FAIL:" in out)
    finally:
        ROLES_PATH.write_text(orig, encoding="utf-8")
