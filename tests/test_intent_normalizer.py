from pathlib import Path
from agentos.intent_evidence import IntentEvidence
from agentos.intent_normalizer import IntentNormalizer, IntentNormalizedReceipt
from agentos.store_fs import FSStore

def test_normalizer_produces_candidates(tmp_path: Path) -> None:
    store = FSStore(str(tmp_path / "store"))
    ev = IntentEvidence(store)
    norm = IntentNormalizer(store, evidence_root=str(store.root / "evidence"))

    text = "run ls and verify files exist"
    receipt: IntentNormalizedReceipt = norm.normalize(
        text,
        intent_sha256=None,
        normalized_at_utc="2026-01-27T00:00:00Z",
        idempotency_key="idem_test_norm_1",
    )

    assert receipt.bundle_dir.endswith(f"verify/{receipt.intent_sha256}")
    manifest_path = Path(receipt.bundle_dir) / "manifest.sha256.json"
    assert manifest_path.is_file()

    raw = manifest_path.read_text(encoding="utf-8")
    assert '"reason":"intent_normalized"' in raw
    assert f'"spec_sha256":"{receipt.intent_sha256}"' in raw
    assert '"stage":"intent_normalized"' in raw

def test_normalizer_collision_safety(tmp_path: Path) -> None:
    store = FSStore(str(tmp_path / "store"))
    norm = IntentNormalizer(store, evidence_root=str(store.root / "evidence"))

    intent = "search for papers and verify citations"
    r1: IntentNormalizedReceipt = norm.normalize(intent)
    r2: IntentNormalizedReceipt = norm.normalize(intent)

    assert r1.intent_sha256 == r2.intent_sha256
    assert r1.manifest_sha256 == r2.manifest_sha256
    assert r1.bundle_dir == r2.bundle_dir

def test_normalizer_handles_unmatched_intent(tmp_path: Path) -> None:
    store = FSStore(str(tmp_path / "store"))
    norm = IntentNormalizer(store, evidence_root=str(store.root / "evidence"))

    intent = "do something completely unknown"
    receipt: IntentNormalizedReceipt = norm.normalize(intent)

    manifest_path = Path(receipt.bundle_dir) / "manifest.sha256.json"
    raw = manifest_path.read_text(encoding="utf-8")
    assert "no_candidate_matches_v1_ruleset" in raw
