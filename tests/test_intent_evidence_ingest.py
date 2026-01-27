from __future__ import annotations

from pathlib import Path

from agentos.intent_evidence import IntentEvidence
from agentos.store_fs import FSStore


def test_intent_ingest_writes_verification_bundle_under_store_root(tmp_path: Path) -> None:
    store = FSStore(str(tmp_path / "store"))
    ev = IntentEvidence(store)

    receipt = ev.write_intent_ingest(
        "run ls in the current directory and capture stdout",
        submitted_at_utc="2026-01-27T00:00:00Z",
        submitter_id="alex",
        idempotency_key="idem_test_1",
    )

    assert isinstance(receipt.intent_sha256, str) and len(receipt.intent_sha256) == 64
    assert receipt.bundle_dir.endswith(f"verify/{receipt.intent_sha256}")

    manifest_path = Path(receipt.bundle_dir) / "manifest.sha256.json"
    assert manifest_path.is_file()

    raw = manifest_path.read_text(encoding="utf-8")
    assert raw.startswith("{")
    assert '"reason":"intent_ingest"' in raw
    assert f'"spec_sha256":"{receipt.intent_sha256}"' in raw
    assert '"stage":"intent_ingest"' in raw


def test_intent_ingest_is_collision_safe(tmp_path: Path) -> None:
    store = FSStore(str(tmp_path / "store"))
    ev = IntentEvidence(store)

    r1 = ev.write_intent_ingest(
        "do thing",
        submitted_at_utc="2026-01-27T00:00:00Z",
        submitter_id=None,
        idempotency_key=None,
    )

    r2 = ev.write_intent_ingest(
        "do thing",
        submitted_at_utc="2026-01-27T00:00:00Z",
        submitter_id=None,
        idempotency_key=None,
    )

    assert r1.intent_sha256 == r2.intent_sha256
    assert r1.manifest_sha256 == r2.manifest_sha256
    assert r1.bundle_dir == r2.bundle_dir
