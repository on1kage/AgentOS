from __future__ import annotations
from pathlib import Path
from typing import Dict
import json
from agentos.canonical import canonical_json, sha256_hex
from agentos.execution import ExecutionSpec

class EvidenceBundle:
    def __init__(self, root: str = "evidence") -> None:
        self.root = Path(root)

    def write_bundle(self, *,
        spec: ExecutionSpec,
        stdout: bytes,
        stderr: bytes,
        outputs: Dict[str, bytes],
        status: str,
        idempotency_key: str | None = None
    ) -> Dict[str, str]:
        bundle_dir = self.root / spec.task_id / spec.exec_id
        bundle_dir.mkdir(parents=True, exist_ok=True)
        manifest: Dict[str, str] = {}
        exec_spec_path = bundle_dir / "exec_spec.json"
        exec_spec_path.write_text(spec.to_canonical_json(), encoding="utf-8")
        manifest["exec_spec.json"] = sha256_hex(exec_spec_path.read_bytes())
        stdout_path = bundle_dir / "stdout.txt"
        stdout_path.write_bytes(stdout)
        manifest["stdout.txt"] = sha256_hex(stdout)
        stderr_path = bundle_dir / "stderr.txt"
        stderr_path.write_bytes(stderr)
        manifest["stderr.txt"] = sha256_hex(stderr)
        outputs_dir = bundle_dir / "outputs"
        outputs_dir.mkdir(exist_ok=True)
        for name, data in outputs.items():
            p = outputs_dir / name
            p.write_bytes(data)
            manifest[f"outputs/{name}"] = sha256_hex(data)
        manifest_path = bundle_dir / "manifest.sha256.json"
        manifest_path.write_text(canonical_json({"files": manifest}), encoding="utf-8")
        summary = {
            "task_id": spec.task_id,
            "idempotency_key": idempotency_key,
            "exec_id": spec.exec_id,
            "status": status,
            "spec_sha256": spec.spec_sha256(),
            "manifest_sha256": sha256_hex(manifest_path.read_bytes()),
        }
        (bundle_dir / "run_summary.json").write_text(canonical_json(summary), encoding="utf-8")
        return manifest
