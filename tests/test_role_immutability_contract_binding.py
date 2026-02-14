import json
import hashlib
from pathlib import Path
from agentos.canonical import canonical_json

CONTRACT_PATH = Path('src/agentos/adapter_role_contract.json')

def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def test_contract_sha256_binding_changes_verify_spec():
    c = json.loads(CONTRACT_PATH.read_text(encoding='utf-8'))
    payload1 = {'inputs_manifest_sha256':'x','role':'envoy','action':'weekly_proof','adapter_role_contract_sha256': sha256_hex(canonical_json(c).encode('utf-8'))}
    v1 = sha256_hex(canonical_json(payload1).encode('utf-8'))
    c2 = json.loads(CONTRACT_PATH.read_text(encoding='utf-8'))
    c2['envoy']['allowed_actions'] = list(c2['envoy']['allowed_actions']) + ['x_mutation']
    payload2 = {'inputs_manifest_sha256':'x','role':'envoy','action':'weekly_proof','adapter_role_contract_sha256': sha256_hex(canonical_json(c2).encode('utf-8'))}
    v2 = sha256_hex(canonical_json(payload2).encode('utf-8'))
    assert v1 != v2
