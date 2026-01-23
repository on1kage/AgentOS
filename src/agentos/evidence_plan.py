from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import re

from agentos.canonical import canonical_json, sha256_hex


class PlanEvidenceBundle:
    def __init__(self, root: str = "evidence") -> None:
        self.root = Path(root)

    def write_plan_bundle(
        self,
        *,
        plan_spec_sha256: str,
        payload: Dict[str, Any],
    ) -> Dict[str, str]:
        if not isinstance(plan_spec_sha256, str) or not plan_spec_sha256:
            raise TypeError("plan_spec_sha256 must be a non-empty string")
        if not re.fullmatch(r"[0-9a-f]{64}", plan_spec_sha256):
            raise ValueError("plan_spec_sha256 must be 64 lowercase hex chars (sha256)")
        if not isinstance(payload, dict):
            raise TypeError("payload must be a dict")

        bundle_dir = self.root / "plan" / plan_spec_sha256
        bundle_dir.mkdir(parents=True, exist_ok=True)

        manifest_path = bundle_dir / "plan_manifest.sha256.json"
        new_bytes = canonical_json(payload).encode("utf-8")
        new_sha = sha256_hex(new_bytes)

        if manifest_path.exists():
            old_bytes = manifest_path.read_bytes()
            old_sha = sha256_hex(old_bytes)
            if old_sha != new_sha:
                raise RuntimeError("plan bundle collision: existing manifest differs")
        else:
            manifest_path.write_bytes(new_bytes)

        return {
            "bundle_dir": str(bundle_dir),
            "manifest_sha256": new_sha,
        }
