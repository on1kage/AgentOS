import json
import os
import subprocess
from pathlib import Path

def test_adapter_import_surface_is_stdlib_or_agentos_only():
    repo = Path.cwd()
    env = dict(os.environ)
    env["PYTHONPATH"] = str(repo / "src")
    p = subprocess.run(
        ["python3", "tools/import_surface_audit.py"],
        cwd=str(repo),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert p.returncode == 0, p.stdout + "\n" + p.stderr
    out = p.stdout.strip().splitlines()[-1]
    obj = json.loads(out)
    assert obj.get("ok") is True, obj
