from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, Optional
import re
from agentos.canonical import canonical_json, sha256_hex
from agentos.execution import ExecutionSpec
from agentos.outcome import ExecutionOutcome, RUN_SUMMARY_SCHEMA_VERSION

class EvidenceBundle:
    def __init__(self, root: str = "evidence") -> None:
        self.root = Path(root)

    def write_bundle(self, *,
        spec: ExecutionSpec,
        stdout: bytes,
        stderr: bytes,
        outputs: Dict[str, bytes],
        outcome: ExecutionOutcome,
        reason: str,
        idempotency_key: str | None = None
    ) -> Dict[str, Any]:
        bundle_dir = self.root / spec.task_id / spec.exec_id
        bundle_dir.mkdir(parents=True, exist_ok=False)
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
            "schema_version": RUN_SUMMARY_SCHEMA_VERSION,
            "task_id": spec.task_id,
            "exec_id": spec.exec_id,
            "outcome": str(outcome.value),
            "reason": reason,
            "idempotency_key": idempotency_key,
            "spec_sha256": spec.spec_sha256(),
            "manifest_sha256": sha256_hex(manifest_path.read_bytes()),
        }
        (bundle_dir / "run_summary.json").write_text(canonical_json(summary), encoding="utf-8")
        return {
            "files": manifest,
            "bundle_dir": str(bundle_dir),
            "spec_sha256": summary["spec_sha256"],
            "manifest_sha256": summary["manifest_sha256"],
        }

    def write_verification_bundle(
        self,
        *,
        spec_sha256: str,
        decisions: dict,
        reason: str,
        idempotency_key: str | None = None,
    ) -> dict[str, str]:
        if not isinstance(spec_sha256, str) or not spec_sha256:
            raise TypeError("spec_sha256 must be a non-empty string")
        if not re.fullmatch(r"[0-9a-f]{64}", spec_sha256):
            raise ValueError("spec_sha256 must be 64 lowercase hex chars (sha256)")
        if not isinstance(decisions, dict):
            raise TypeError("decisions must be a dict")
        if not isinstance(reason, str) or not reason:
            raise TypeError("reason must be a non-empty string")

        bundle_dir = self.root / "verify" / spec_sha256
        bundle_dir.mkdir(parents=True, exist_ok=True)

        payload = {
            "spec_sha256": spec_sha256,
            "reason": reason,
            "idempotency_key": idempotency_key,
            "decisions": decisions,
        }

        manifest_path = bundle_dir / "manifest.sha256.json"
        new_bytes = canonical_json(payload).encode("utf-8")
        new_sha = sha256_hex(new_bytes)

        if manifest_path.exists():
            old_bytes = manifest_path.read_bytes()
            old_sha = sha256_hex(old_bytes)
            if old_sha != new_sha:
                raise RuntimeError("verification bundle collision: existing manifest differs")
        else:
            manifest_path.write_bytes(new_bytes)

        return {
            "bundle_dir": str(bundle_dir),
            "manifest_sha256": new_sha,
        }

    def write_rejection(
        self,
        task_id: str,
        *,
        reason: str,
        idempotency_key: str | None = None,
        prior_exec_id: str | None = None,
        prior_manifest_sha256: str | None = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Persist an auditable REJECTED outcome when an ExecutionSpec cannot be built
        (or when execution is blocked pre-run, e.g., idempotency).
        """
        if not isinstance(reason, str) or not reason:
            raise TypeError("reason must be a non-empty string")
        ctx = context if isinstance(context, dict) else {}

        rej_id = sha256_hex(reason.encode("utf-8"))[:16]
        bundle_dir = self.root / task_id / "rejections" / rej_id
        bundle_dir.mkdir(parents=True, exist_ok=False)

        manifest: Dict[str, str] = {}

        rejection = {
            "schema_version": RUN_SUMMARY_SCHEMA_VERSION,
            "task_id": task_id,
            "exec_id": None,
            "outcome": str(ExecutionOutcome.REJECTED.value),
            "reason": reason,
            "idempotency_key": idempotency_key,
            "prior_exec_id": prior_exec_id,
            "prior_manifest_sha256": prior_manifest_sha256,
            "context": ctx,
        }

        rej_path = bundle_dir / "rejection.json"
        rej_path.write_text(canonical_json(rejection), encoding="utf-8")
        manifest["rejection.json"] = sha256_hex(rej_path.read_bytes())

        manifest_path = bundle_dir / "manifest.sha256.json"
        manifest_path.write_text(canonical_json({"files": manifest}), encoding="utf-8")
        manifest_sha = sha256_hex(manifest_path.read_bytes())
        manifest["manifest.sha256.json"] = manifest_sha

        return {
            "files": manifest,
            "bundle_dir": str(bundle_dir),
            "rejection_id": rej_id,
            "manifest_sha256": manifest_sha,
        }
