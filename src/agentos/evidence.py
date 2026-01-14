from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any

from agentos.canonical import canonical_json, sha256_hex
from agentos.execution import ExecutionSpec


class EvidenceBundle:
    """
    Deterministic evidence bundle writer.

    Produces an append-only directory per (task_id, exec_id).
    No execution logic. No FSM logic.
    """

    def __init__(self, root: str = "evidence") -> None:
        self.root = Path(root)

    def _bundle_dir(self, task_id: str, exec_id: str) -> Path:
        return self.root / task_id / exec_id

    def write_bundle(
        self,
        *,
        spec: ExecutionSpec,
        stdout: bytes,
        stderr: bytes,
        outputs: Dict[str, bytes],
        status: str,
    ) -> Dict[str, str]:
        """
        Write a complete evidence bundle and return the manifest (path -> sha256).
        """
        bd = self._bundle_dir(spec.task_id, spec.exec_id)
        bd.mkdir(parents=True, exist_ok=False)

        manifest: Dict[str, str] = {}

        # exec_spec.json
        exec_spec_path = bd / "exec_spec.json"
        exec_spec_path.write_text(spec.to_canonical_json(), encoding="utf-8")
        manifest["exec_spec.json"] = sha256_hex(exec_spec_path.read_bytes())

        # stdout / stderr
        stdout_path = bd / "stdout.txt"
        stdout_path.write_bytes(stdout)
        manifest["stdout.txt"] = sha256_hex(stdout)

        stderr_path = bd / "stderr.txt"
        stderr_path.write_bytes(stderr)
        manifest["stderr.txt"] = sha256_hex(stderr)

        # outputs
        outputs_dir = bd / "outputs"
        outputs_dir.mkdir()
        for name, data in outputs.items():
            p = outputs_dir / name
            p.write_bytes(data)
            manifest[f"outputs/{name}"] = sha256_hex(data)

        # manifest.sha256.json
        manifest_path = bd / "manifest.sha256.json"
        manifest_path.write_text(canonical_json({"files": manifest}), encoding="utf-8")

        # run_summary.json (hash-referenced only)
        summary = {
            "task_id": spec.task_id,
            "exec_id": spec.exec_id,
            "status": status,
            "spec_sha256": spec.spec_sha256(),
            "manifest_sha256": sha256_hex(manifest_path.read_bytes()),
        }
        (bd / "run_summary.json").write_text(canonical_json(summary), encoding="utf-8")

        return manifest
