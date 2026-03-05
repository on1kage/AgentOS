import json
import subprocess
import tempfile
from pathlib import Path


CONTRACT_PATH = Path("src/agentos/adapter_role_contract.json")


def _mutate_hex_last_char(h: str) -> str:
    if not isinstance(h, str) or len(h) != 64:
        return "0" * 64
    last = h[-1]
    flip = "0" if last != "0" else "1"
    return h[:-1] + flip


def test_contract_tamper_fails_weekly_proof_verify() -> None:
    original = CONTRACT_PATH.read_text(encoding="utf-8")
    try:
        contract = json.loads(original)
        contract["contract_binding_sha256"] = _mutate_hex_last_char(str(contract.get("contract_binding_sha256", "")))
        CONTRACT_PATH.write_text(json.dumps(contract, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")

        with tempfile.TemporaryDirectory() as td:
            artifact = Path(td) / "artifact.json"
            artifact.write_text("{}", encoding="utf-8")

            cmd = ["python3", "tools/weekly_proof_verify.py", "--artifact", str(artifact)]
            r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

        assert r.returncode == 2
        assert "FAIL:contract_binding_sha256_mismatch" in (r.stdout or "")
    finally:
        CONTRACT_PATH.write_text(original, encoding="utf-8")
