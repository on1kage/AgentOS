from pathlib import Path
from tools.import_surface_audit import audit_adapter_import_surface

def test_adapter_import_surface_is_stdlib_or_agentos_only():
    repo = Path.cwd()
    r = audit_adapter_import_surface(repo)
    assert r.get("ok") is True, r
