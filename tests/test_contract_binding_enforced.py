import json
from pathlib import Path

from agentos.adapter_role_contract_checker import load_contract, verify_contract_binding, verify_adapter_output

FIXTURE_PATH = Path('store/weekly_proof/artifacts/utc_date_weekly_proof.json')

def test_contract_binding_roundtrip_ok():
    c = load_contract()
    assert verify_contract_binding(c) is True

def test_contract_binding_missing_field_fails_closed():
    c = load_contract()
    c.pop("contract_binding_sha256", None)
    try:
        ok = verify_contract_binding(c)
    except ValueError:
        ok = False
    assert ok is False

def test_contract_binding_adapter_version_drift_fails_closed_on_verify_output():
    d = json.loads(FIXTURE_PATH.read_text(encoding='utf-8'))
    scout_out = dict(d["results"]["scout"])
    scout_out["adapter_version"] = "9.9.9"
    assert verify_adapter_output("scout", scout_out, expected_action="external_research") is False

def test_contract_binding_contract_adapter_version_drift_requires_binding_update():
    c = load_contract()
    c2 = json.loads(json.dumps(c))
    c2["scout"]["adapter_version"] = "9.9.9"
    assert verify_contract_binding(c2) is False

def test_registry_adapter_version_drift_fails_closed():
    from agentos.adapter_registry import ADAPTERS
    from agentos.adapter_role_contract_checker import verify_registry_versions
    c = load_contract()
    reg = json.loads(json.dumps(ADAPTERS))
    reg["scout"]["adapter_version"] = "9.9.9"
    assert verify_registry_versions(reg, c) is False

def test_contract_action_allowlist_enforced_envoy():
    import json as _json
    from pathlib import Path as _Path
    from agentos.adapter_role_contract_checker import verify_adapter_output
    d = _json.loads(_Path("store/weekly_proof/artifacts/utc_date_weekly_proof.json").read_text(encoding="utf-8"))
    out = dict(d["results"]["envoy"])
    out["action_class"] = "external_research"
    assert verify_adapter_output("envoy", out, expected_action="deterministic_local_execution") is False

def test_contract_action_allowlist_enforced_scout():
    import json as _json
    from pathlib import Path as _Path
    from agentos.adapter_role_contract_checker import verify_adapter_output
    d = _json.loads(_Path("store/weekly_proof/artifacts/utc_date_weekly_proof.json").read_text(encoding="utf-8"))
    out = dict(d["results"]["scout"])
    out["action_class"] = "deterministic_local_execution"
    assert verify_adapter_output("scout", out, expected_action="external_research") is False
