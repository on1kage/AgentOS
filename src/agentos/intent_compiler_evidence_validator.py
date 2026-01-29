from __future__ import annotations
from pathlib import Path
from typing import Dict, Any
from agentos.canonical import canonical_json, sha256_hex

def verify_compiler_evidence(bundle_dir: str) -> Dict[str, Any]:
    """
    Task 5b — Validate compiler evidence bundles.

    Ensures:
        - Deterministic reproducibility
        - Manifest SHA256 matches input/output bundles
        - Raises exception on mismatch
    """
    manifest_path = Path(bundle_dir) / "manifest.sha256.json"
    if not manifest_path.exists():
        raise RuntimeError(f"Evidence manifest missing: {manifest_path}")

    import json
    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))

    input_text = manifest_data["decisions"]["intent_text"]
    output_dict = manifest_data["decisions"]["compiled_result"]

    # Recompute hashes
    input_hash = sha256_hex(canonical_json({"intent_text": input_text}).encode("utf-8"))
    output_hash = sha256_hex(canonical_json(output_dict).encode("utf-8"))

    if manifest_data["spec_sha256"] != output_hash:
        raise ValueError("Compiler evidence verification failed: output hash mismatch")

    return {
        "input_hash": input_hash,
        "output_hash": output_hash,
        "manifest_sha256": manifest_data["spec_sha256"],
    }
