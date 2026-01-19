from agentos.runner import TaskRunner
from agentos.capabilities.idempotency import IdempotencyStore
from agentos.canonical import sha256_hex
import json
from pathlib import Path

# Original TaskRunner execution function
orig_run_dispatched = TaskRunner.run_dispatched


def run_dispatched_with_idempotency(self, task_id: str):
    created_payload = self._load_created_payload(task_id)
    role, action = self._load_created_role_action(task_id)
    spec = self._build_spec(task_id=task_id, role=role, action=action, payload=created_payload)

    if not hasattr(self, "_idempotency_store"):
        self._idempotency_store = IdempotencyStore()

    key = sha256_hex(spec.to_canonical_json().encode("utf-8"))

    # Concurrency guard
    self._idempotency_store.acquire_lock(task_id, key)

    # Attempt marker (Policy B)
    created = self._idempotency_store.record_if_absent(
        task_id,
        key,
        {"status": "started", "exec_id": spec.exec_id},
    )
    if not created:
        # Persist auditable REJECTED evidence
        meta = self._idempotency_store.load_metadata(task_id, key)
        prior_exec_id = meta.get("exec_id") if meta else None
        prior_manifest_sha256 = None
        if prior_exec_id:
            rs_path = Path(self.evidence.root) / task_id / prior_exec_id / "run_summary.json"
            if rs_path.is_file():
                obj = json.loads(rs_path.read_text(encoding="utf-8"))
                prior_manifest_sha256 = obj.get("manifest_sha256") if isinstance(obj, dict) else None

        self.evidence.write_rejection(
            task_id,
            reason="duplicate_execution",
            idempotency_key=key,
            prior_exec_id=prior_exec_id,
            prior_manifest_sha256=prior_manifest_sha256,
            context={"exec_id": spec.exec_id},
        )
        self._idempotency_store.release_lock(task_id, key)
        raise RuntimeError(f"Duplicate execution prevented: {task_id} {key}")

    # ---- SINGLE clean try/except/finally ----
    try:
        # Thread idempotency key into evidence bundles
        self._current_idempotency_key = key
        res = orig_run_dispatched(self, task_id)
    except RuntimeError as e:
        if str(e).startswith("unsupported_execution_kind:"):
            self.evidence.write_rejection(
                task_id,
                reason=str(e),
                idempotency_key=getattr(self, "_current_idempotency_key", None),
                prior_exec_id=None,
                prior_manifest_sha256=None,
                context={"exec_id": getattr(self, "_current_idempotency_key", None)},
            )
        raise
    finally:
        # Clear per-run key and release lock
        try:
            delattr(self, "_current_idempotency_key")
        except Exception:
            pass
        self._idempotency_store.release_lock(task_id, key)

    return res


# Patch TaskRunner
TaskRunner.run_dispatched = run_dispatched_with_idempotency
