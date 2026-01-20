from pathlib import Path
import pytest
from agentos.evidence import EvidenceBundle
from agentos.canonical import canonical_json, sha256_hex

def test_verification_bundle_creates_sha256_manifest_only(tmp_path):
    ev = EvidenceBundle(root=str(tmp_path))
    spec = sha256_hex(b"spec-A")
    out = ev.write_verification_bundle(
        spec_sha256=spec,
        decisions={"a": {"allow": True}},
        reason="test",
        idempotency_key=None,
    )
    bundle_dir = Path(out["bundle_dir"])
    assert (bundle_dir / "manifest.sha256.json").exists()
    assert not (bundle_dir / "manifest.json").exists()

def test_verification_bundle_collision_detected(tmp_path):
    ev = EvidenceBundle(root=str(tmp_path))
    spec = sha256_hex(b"spec-B")
    ev.write_verification_bundle(
        spec_sha256=spec,
        decisions={"a": {"allow": True}},
        reason="test",
        idempotency_key=None,
    )
    with pytest.raises(RuntimeError):
        ev.write_verification_bundle(
            spec_sha256=spec,
            decisions={"a": {"allow": False}},
            reason="test",
            idempotency_key=None,
        )
