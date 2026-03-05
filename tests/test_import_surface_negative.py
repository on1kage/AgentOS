import json
import subprocess
from pathlib import Path


TARGET = Path("tools/scout_run.py")


def test_import_surface_audit_fails_on_disallowed_import() -> None:
    original = TARGET.read_text(encoding="utf-8")
    try:
        TARGET.write_text(original + "\nimport requests\n", encoding="utf-8")

        r = subprocess.run(
            ["python3", "tools/import_surface_audit.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        assert r.returncode == 2
        out = (r.stdout or "").strip().splitlines()[-1]
        data = json.loads(out)

        assert data.get("ok") is False
        files = data.get("files") or {}
        rel = "tools/scout_run.py"
        assert rel in files
        assert files[rel].get("ok") is False
        dis = files[rel].get("disallowed_imports") or []
        assert "requests" in dis
    finally:
        TARGET.write_text(original, encoding="utf-8")
