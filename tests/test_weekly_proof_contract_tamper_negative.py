import json
import importlib.util
from pathlib import Path

from agentos.adapter_role_contract_checker import compute_sha256

FIXTURE_ARTIFACT = Path("store/weekly_proof/artifacts/utc_date_weekly_proof.json")
CONTRACT_PATH = Path("src/agentos/adapter_role_contract.json")

def _load_weekly_proof_verify():
    mod_path = Path("tools/weekly_proof_verify.py")
    spec = importlib.util.spec_from_file_location("weekly_proof_verify", str(mod_path))
    if spec is None or spec.loader is None:
        raise RuntimeError("failed_to_load_weekly_proof_verify")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

def _binding_fp(c: dict) -> dict:
    cv = c.get("contract_version")
    rrh = c.get("roles_registry_sha256") if isinstance(c.get("roles_registry_sha256"), str) else ""
    arh = c.get("adapter_registry_sha256") if isinstance(c.get("adapter_registry_sha256"), str) else ""
    adapters = {}
    for k in sorted(c.keys()):
        if k in ("contract_version", "contract_binding_sha256", "roles_registry_sha256", "adapter_registry_sha256"):
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
    return {"contract_version": cv, "roles_registry_sha256": rrh, "adapter_registry_sha256": arh, "adapters": adapters}

def test_weekly_proof_fails_closed_on_contract_allowed_actions_tamper(tmp_path: Path):
    m = _load_weekly_proof_verify()

    artifact_path = tmp_path / "tampered_artifact.json"
    artifact_path.write_text(FIXTURE_ARTIFACT.read_text(encoding="utf-8"), encoding="utf-8")

    original = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    tampered = json.loads(json.dumps(original))

    tampered["envoy"]["allowed_actions"] = ["deterministic_local_execution", "evidence_capture", "external_research"]
    tampered["contract_binding_sha256"] = compute_sha256(_binding_fp(tampered))

    try:
        CONTRACT_PATH.write_text(json.dumps(tampered, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")
        ok, reason = m.verify_weekly_proof_artifact(artifact_path)
        assert ok is False
        assert reason == "role_contract_action_parity_mismatch"
    finally:
        CONTRACT_PATH.write_text(json.dumps(original, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")
