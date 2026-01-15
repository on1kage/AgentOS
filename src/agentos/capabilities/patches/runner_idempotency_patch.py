from agentos.runner import TaskRunner
from agentos.capabilities.idempotency import IdempotencyStore
from agentos.canonical import sha256_hex

# Policy B: retry forbidden after any attempt.
# - Acquire lock
# - Atomically record "started" BEFORE execution
# - If record exists -> block
# - Run
# - Release lock (record persists regardless of outcome)

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

    # Attempt marker (authoritative for Policy B)
    created = self._idempotency_store.record_if_absent(
        task_id,
        key,
        {"status": "started", "exec_id": spec.exec_id},
    )
    if not created:
        self._idempotency_store.release_lock(task_id, key)
        raise RuntimeError(f"Duplicate execution prevented: {task_id} {key}")

    try:
        res = orig_run_dispatched(self, task_id)
    finally:
        # Lock always released; record persists regardless of outcome
        self._idempotency_store.release_lock(task_id, key)

    return res


TaskRunner.run_dispatched = run_dispatched_with_idempotency
