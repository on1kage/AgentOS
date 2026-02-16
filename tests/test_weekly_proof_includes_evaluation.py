import json
import re
from pathlib import Path

FIXTURE_PATH = Path("store/weekly_proof/artifacts/utc_date_weekly_proof.json")

_SHA = re.compile(r"^[0-9a-f]{64}$")

def test_weekly_proof_artifact_includes_evaluation_fields():
    d = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    for role in ("scout", "envoy"):
        o = d["results"][role]
        assert o.get("evaluation_decision") in ("accept", "refine")
        assert isinstance(o.get("evaluation_spec_sha256"), str) and _SHA.fullmatch(o["evaluation_spec_sha256"])
        assert isinstance(o.get("evaluation_manifest_sha256"), str) and _SHA.fullmatch(o["evaluation_manifest_sha256"])
