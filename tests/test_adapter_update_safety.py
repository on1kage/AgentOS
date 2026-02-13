import json
from pathlib import Path
from agentos.adapter_role_contract_checker import verify_adapter_output

CONTRACT_PATH = Path('src/agentos/adapter_role_contract.json')

def test_adapter_update_safety_scout():
    contract = json.loads(CONTRACT_PATH.read_text(encoding='utf-8'))
    expected_hash = contract['scout']['output_schema_sha256']
    assert expected_hash
    sample_output = {}
    assert verify_adapter_output('scout', sample_output) is False

def test_adapter_update_safety_envoy():
    contract = json.loads(CONTRACT_PATH.read_text(encoding='utf-8'))
    expected_hash = contract['envoy']['output_schema_sha256']
    assert expected_hash
    sample_output = {}
    assert verify_adapter_output('envoy', sample_output) is False
