from agentos.runner import TaskRunner
from agentos.capabilities.idempotency import IdempotencyStore
from agentos.canonical import sha256_hex

# Patch strategy:
# - Compute a stable idempotency key from the intended ExecutionSpec (derived from TASK_CREATED payload).
# - If a completed record exists, fail immediately (before any FSM/state inspection).
# - Acquire an atomic in-flight lock to prevent concurrent double-runs.
# - Call the original runner unmodified.
# - Record the key only after successful completion.
# - Always release the in-flight lock (fail-closed).

orig_run_dispatched = TaskRunner.run_dispatched


def run_dispatched_with_idempotency(self, task_id: str):
    created_payload = self._load_created_payload(task_id)
    role, action = self._load_created_role_action(task_id)
    spec = self._build_spec(task_id=task_id, role=role, action=action, payload=created_payload)

    if not hasattr(self, "_idempotency_store"):
        self._idempotency_store = IdempotencyStore()

    key = sha256_hex(spec.to_canonical_json().encode("utf-8"))

    # Completed idempotency record check first: duplicates must not surface as invalid_state.
    if self._idempotency_store.check(task_id, key):
        raise RuntimeError(f"Duplicate execution prevented: {task_id} {key}")

    # Concurrency guard: prevent two runners from executing the same spec concurrently.
    self._idempotency_store.acquire_lock(task_id, key)

    try:
        res = orig_run_dispatched(self, task_id)
    except Exception:
        # No record on exception, but lock must be released so a policy-defined retry can occur.
        self._idempotency_store.release_lock(task_id, key)
        raise

    # Record only after successful execution.
    self._idempotency_store.record(task_id, key, {"exec_id": spec.exec_id})
    self._idempotency_store.release_lock(task_id, key)
    return res


TaskRunner.run_dispatched = run_dispatched_with_idempotency
