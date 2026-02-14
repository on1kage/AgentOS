import json
from pathlib import Path
from typing import Any, Dict
import hashlib

CONTRACT_PATH = Path('src/agentos/adapter_role_contract.json')

def _canonical_dumps(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False)

def compute_sha256(obj: Any) -> str:
    return hashlib.sha256(_canonical_dumps(obj).encode('utf-8')).hexdigest()

def load_contract() -> Dict[str, Any]:
    return json.loads(CONTRACT_PATH.read_text(encoding='utf-8'))

def contract_sha256() -> str:
    return compute_sha256(load_contract())

def _type_tag(v: Any) -> str:
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, int) and not isinstance(v, bool):
        return "int"
    if isinstance(v, float):
        return "float"
    if isinstance(v, str):
        return "str"
    if v is None:
        return "null"
    if isinstance(v, list):
        return "list"
    if isinstance(v, dict):
        return "dict"
    return type(v).__name__

def output_schema_fingerprint(outputs: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(outputs, dict):
        raise TypeError("outputs must be a dict")
    return {
        "keys": {k: _type_tag(outputs.get(k)) for k in sorted(outputs.keys())},
        "required": sorted(outputs.keys()),
    }

def verify_adapter_output(adapter_name: str, outputs: Dict[str, Any]) -> bool:
    contract = load_contract()
    if adapter_name not in contract:
        raise ValueError(f'Unknown adapter: {adapter_name}')

    expected_hash = contract[adapter_name].get('output_schema_sha256')
    if not isinstance(expected_hash, str) or not expected_hash:
        raise ValueError(f'missing_output_schema_sha256_in_contract:{adapter_name}')

    fp = output_schema_fingerprint(outputs)
    actual_hash = compute_sha256(fp)
    return expected_hash == actual_hash

if __name__ == '__main__':
    import sys
    outputs_file = Path(sys.argv[2])
    adapter_name = sys.argv[1]
    outputs = json.loads(outputs_file.read_text(encoding='utf-8'))
    ok = verify_adapter_output(adapter_name, outputs)
    print(f'{adapter_name} output verification:', ok)
