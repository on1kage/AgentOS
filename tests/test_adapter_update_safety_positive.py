import json
from pathlib import Path
from agentos.adapter_role_contract_checker import verify_adapter_output

FIXTURE_PATH = Path('store/weekly_proof/artifacts/utc_date_weekly_proof.json')

def test_adapter_update_safety_positive_scout():
    d = json.loads(FIXTURE_PATH.read_text(encoding='utf-8'))
    assert verify_adapter_output('scout', d['results']['scout']) is True

def test_adapter_update_safety_positive_envoy():
    d = json.loads(FIXTURE_PATH.read_text(encoding='utf-8'))
    assert verify_adapter_output('envoy', d['results']['envoy']) is True
