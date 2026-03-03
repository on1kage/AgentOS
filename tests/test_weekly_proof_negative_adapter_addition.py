import os
import sys
import subprocess
from pathlib import Path

FIXTURE_ARTIFACT = Path("store/weekly_proof/artifacts/utc_date_weekly_proof.json")
ADAPTER_REGISTRY_PATH = Path("src/agentos/adapter_registry.py")

def _run_verify() -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PYTHONPATH"] = "src"
    return subprocess.run(
        [sys.executable, "tools/weekly_proof_verify.py", "--artifact", str(FIXTURE_ARTIFACT)],
        capture_output=True,
        text=True,
        env=env,
    )

def test_weekly_proof_fails_closed_on_adapter_addition(tmp_path: Path):
    orig = ADAPTER_REGISTRY_PATH.read_text(encoding="utf-8")
    try:
        if '"x_added_adapter"' in orig:
            raise RuntimeError("unexpected_existing_marker")

        lines = orig.splitlines(True)
        insert_at = None
        for i, line in enumerate(lines):
            if line.strip().startswith("ADAPTERS") and "{" in line:
                insert_at = i + 1
                break
        if insert_at is None:
            raise RuntimeError("failed_to_find_ADAPTERS_dict")

        injection = '    "x_added_adapter": {"cmd": ["python3","-c","print(0)"], "env_allowlist": [], "description": "x", "adapter_version": "0.0.0"},\n'
        lines.insert(insert_at, injection)
        ADAPTER_REGISTRY_PATH.write_text("".join(lines), encoding="utf-8")

        p = _run_verify()
        assert p.returncode != 0
        out = (p.stdout or "") + (p.stderr or "")
        assert ("registry_contract_version_mismatch" in out) or ("FAIL:" in out)
    finally:
        ADAPTER_REGISTRY_PATH.write_text(orig, encoding="utf-8")
