import json
import re
from pathlib import Path
from agentos.adapter_role_contract_checker import load_contract
from agentos.evidence_schema import bundle_schema_sha256

_SHA = re.compile(r'^[0-9a-f]{64}$')
FIXTURE_PATH = Path('store/weekly_proof/artifacts/utc_date_weekly_proof.json')

def test_weekly_proof_artifact_includes_bundle_schema_sha256_and_matches_contract():
    d = json.loads(FIXTURE_PATH.read_text(encoding='utf-8'))
    c = load_contract()
    pinned = c.get('evidence_bundle_schema_sha256')
    assert isinstance(pinned, str) and _SHA.fullmatch(pinned)
    for role in ('envoy','scout'):
        r = dict(d['results'][role])
        bsh = r.get('bundle_schema_sha256')
        assert isinstance(bsh, str) and _SHA.fullmatch(bsh)
        bd = str(r.get('bundle_dir') or '')
        if bd:
            assert bsh == pinned
            assert bundle_schema_sha256(bd) == pinned
        else:
            assert bsh == '0'*64
