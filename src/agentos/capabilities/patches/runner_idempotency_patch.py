from agentos.runner import TaskRunner
from agentos.capabilities.idempotency import IdempotencyStore
from agentos.canonical import sha256_hex

# Patch strategy:
# - Compute a stable idempotency key from the intended ExecutionSpec (derived from TASK_CREATED payload).
# - If the key exists, fail immediately with a deterministic error (before any FSM/state inspection).
# - Otherwise call the original runner unmodified.
# - Record the key only after successful completion (orig_run_dispatched returns).

orig_run_dispatched = TaskRunner.run_dispatched


def run_dispatched_with_idempotency(self, task_id: str):
    created_payload = self._load_created_payload(task_id)
    role, action = self._load_created_role_action(task_id)
    spec = self._build_spec(task_id=task_id, role=role, action=action, payload=created_payload)

    if not hasattr(self, "_idempotency_store"):
        self._idempotency_store = IdempotencyStore()

    key = sha256_hex(spec.to_canonical_json().encode("utf-8"))

    # Idempotency MUST be checked before any FSM/state validation so duplicates do not
    # surface as invalid_state errors after the first successful execution.
    if self._idempotency_store.check(task_id, key):
        raise RuntimeError(f"Duplicate execution prevented: {task_id} {key}")

    res = orig_run_dispatched(self, task_id)

    # Record only after successful execution (no record on exception).
    self._idempotency_store.record(task_id, key, {"exec_id": spec.exec_id})
    return res


TaskRunner.run_dispatched = run_dispatched_with_idempotency
