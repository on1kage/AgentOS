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
    assert verify_adapter_output("scout", scout_out) is False
