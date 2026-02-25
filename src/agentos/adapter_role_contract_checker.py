import json
import hashlib
from pathlib import Path
from typing import Any, Dict

CONTRACT_PATH = Path("src/agentos/adapter_role_contract.json")

def _canonical_dumps(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def compute_sha256(obj: Any) -> str:
    return hashlib.sha256(_canonical_dumps(obj).encode("utf-8")).hexdigest()

def load_contract() -> Dict[str, Any]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

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

def _binding_fingerprint(contract: Dict[str, Any]) -> Dict[str, Any]:
    cv = contract.get("contract_version")
    if not isinstance(cv, str) or not cv:
        raise ValueError("missing_or_invalid_contract_version")

    adapters: Dict[str, Any] = {}
    for k in sorted(contract.keys()):
        if k in ("contract_version", "contract_binding_sha256"):
            continue
        v = contract.get(k)
        if isinstance(v, dict):
            av = v.get("adapter_version")
            sh = v.get("output_schema_sha256")
            if isinstance(av, str) and av:
                al = v.get("allowed_actions")
                pr = v.get("prohibited_actions")
                adapters[k] = {
                    "adapter_version": av,
                    "output_schema_sha256": sh if isinstance(sh, str) and sh else "",
                    "allowed_actions": sorted([str(x) for x in al]) if isinstance(al, list) else [],
                    "prohibited_actions": sorted([str(x) for x in pr]) if isinstance(pr, list) else [],
                }
    return {"contract_version": cv, "adapters": adapters}

def verify_contract_binding(contract: Dict[str, Any]) -> bool:
    expected = contract.get("contract_binding_sha256")
    if not isinstance(expected, str) or not expected:
        raise ValueError("missing_contract_binding_sha256")
    actual = compute_sha256(_binding_fingerprint(contract))
    return expected == actual

def verify_adapter_output(adapter_name: str, outputs: Dict[str, Any], expected_action: str | None = None) -> bool:
    contract = load_contract()
    if not verify_contract_binding(contract):
        return False
    if adapter_name not in contract:
        raise ValueError(f"Unknown adapter: {adapter_name}")

    expected_hash = contract[adapter_name].get("output_schema_sha256")
    if not isinstance(expected_hash, str) or not expected_hash:
        raise ValueError(f"missing_output_schema_sha256_in_contract:{adapter_name}")

    expected_adapter_version = contract[adapter_name].get("adapter_version")
    if not isinstance(expected_adapter_version, str) or not expected_adapter_version:
        raise ValueError(f"missing_adapter_version_in_contract:{adapter_name}")
    if outputs.get("adapter_version") != expected_adapter_version:
        return False

    if outputs.get("adapter_role") != adapter_name:
        return False

    action = outputs.get("action_class")
    if not isinstance(action, str) or not action:
        return False
    if expected_action is not None:
        if not isinstance(expected_action, str) or not expected_action:
            return False
        if action != expected_action:
            return False
    allowed = contract[adapter_name].get("allowed_actions")
    prohibited = contract[adapter_name].get("prohibited_actions")
    if isinstance(prohibited, list) and action in prohibited:
        return False
    if isinstance(allowed, list) and allowed and action not in allowed:
        return False

    fp = output_schema_fingerprint(outputs)
    actual_hash = compute_sha256(fp)
    return expected_hash == actual_hash

if __name__ == "__main__":
    import sys
    outputs_file = Path(sys.argv[2])
    adapter_name = sys.argv[1]
    outputs = json.loads(outputs_file.read_text(encoding="utf-8"))
    ok = verify_adapter_output(adapter_name, outputs)
    print(f"{adapter_name} output verification:", ok)

def verify_registry_versions(registry: Dict[str, Any], contract: Dict[str, Any]) -> bool:
    if not isinstance(registry, dict) or not isinstance(contract, dict):
        raise TypeError("registry_and_contract_must_be_dicts")
    if not verify_contract_binding(contract):
        return False
    for role, meta in registry.items():
        if role not in contract or not isinstance(contract.get(role), dict):
            return False
        rv = meta.get("adapter_version") if isinstance(meta, dict) else None
        cv = contract[role].get("adapter_version")
        if not isinstance(rv, str) or not rv:
            return False
        if not isinstance(cv, str) or not cv:
            return False
        if rv != cv:
            return False
    return True
