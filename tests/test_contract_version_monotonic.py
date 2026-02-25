import json
import pytest
from pathlib import Path

from agentos.adapter_role_contract_checker import compute_sha256, verify_contract_binding

def _binding_fp(c: dict) -> dict:
    cv = c.get("contract_version")
    rrh = c.get("roles_registry_sha256") if isinstance(c.get("roles_registry_sha256"), str) else ""
    adapters = {}
    for k in sorted(c.keys()):
        if k in ("contract_version", "contract_binding_sha256", "roles_registry_sha256"):
            continue
        v = c.get(k)
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
    return {"contract_version": cv, "roles_registry_sha256": rrh, "adapters": adapters}

def test_contract_version_regression_fails_closed():
    p = Path("src/agentos/adapter_role_contract.json")
    c = json.loads(p.read_text(encoding="utf-8"))

    c["contract_version"] = "0.9.9-weekly-proof"
    c["contract_binding_sha256"] = compute_sha256(_binding_fp(c))

    with pytest.raises(ValueError) as e:
        verify_contract_binding(c)

    assert str(e.value) == "contract_version_regression"
