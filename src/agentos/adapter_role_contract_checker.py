import json
from pathlib import Path
from typing import Dict
import hashlib

def compute_sha256(obj: Dict) -> str:
    s = json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    return hashlib.sha256(s.encode('utf-8')).hexdigest()

CONTRACT_PATH = Path('src/agentos/adapter_role_contract.json')

def load_contract() -> Dict:
    return json.loads(CONTRACT_PATH.read_text(encoding='utf-8'))

def contract_sha256() -> str:
    return compute_sha256(load_contract())

def verify_adapter_output(adapter_name: str, outputs: Dict) -> bool:
    contract = load_contract()
    if adapter_name not in contract:
        raise ValueError(f'Unknown adapter: {adapter_name}')
    expected_hash = contract[adapter_name]['output_schema_sha256']
    actual_hash = compute_sha256(outputs)
    return expected_hash == actual_hash

if __name__ == '__main__':
    import sys
    outputs_file = Path(sys.argv[2])
    adapter_name = sys.argv[1]
    outputs = json.loads(outputs_file.read_text(encoding='utf-8'))
    ok = verify_adapter_output(adapter_name, outputs)
    print(f'{adapter_name} output verification:', ok)
