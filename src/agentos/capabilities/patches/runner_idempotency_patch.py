from agentos.runner import TaskRunner, RunSummary
from agentos.fsm import rebuild_task_state
from agentos.task import TaskState
from agentos.capabilities.idempotency import IdempotencyStore
from agentos.canonical import sha256_hex
import json
from pathlib import Path

# Original TaskRunner execution function
orig_run_dispatched = TaskRunner.run_dispatched


def run_dispatched_with_idempotency(self, task_id: str) -> RunSummary:
    snap = rebuild_task_state(self.store, task_id)
    derived_state = TaskState(str(snap["state"]))

    if not hasattr(self, "_idempotency_store"):
        self._idempotency_store = IdempotencyStore()

    # Build an audit-authoritative key from VERIFIED inputs manifest + created payload.
    try:
        created_payload = self._load_created_payload(task_id)
        role, action = self._load_created_role_action(task_id)

        verified_ims = self._load_verified_inputs_manifest_sha256(task_id)
        created_payload = dict(created_payload)
        created_payload["inputs_manifest_sha256"] = verified_ims

        spec = self._build_spec(task_id=task_id, role=role, action=action, payload=created_payload)
        key = sha256_hex(spec.to_canonical_json().encode("utf-8"))
    except Exception:
        # Preserve fail-closed semantics for tasks that were never VERIFIED / not well-formed.
        self.evidence.write_rejection(task_id, reason=f"invalid_state:{derived_state.value}")
        raise RuntimeError(f"invalid_state:{derived_state.value}")

    # If a record exists for this exact spec key, retries are forbidden (Policy B).
    # This must be checked regardless of derived_state.
    try:
        if self._idempotency_store.check(task_id, key):
            meta = None
            try:
                meta = self._idempotency_store.load_metadata(task_id, key)
            except Exception:
                meta = None

            prior_exec_id = meta.get("exec_id") if isinstance(meta, dict) else None
            prior_manifest_sha256 = meta.get("manifest_sha256") if isinstance(meta, dict) else None

            self.evidence.write_rejection(
                task_id,
                reason="duplicate_execution",
                idempotency_key=key,
                prior_exec_id=prior_exec_id,
                prior_manifest_sha256=prior_manifest_sha256,
                context={"exec_id": spec.exec_id},
            )
            raise RuntimeError(f"Duplicate execution prevented: {task_id} {key}")
    except RuntimeError:
        raise
    except Exception:
        # Fail-closed if idempotency store itself is unhealthy.
        self.evidence.write_rejection(task_id, reason="idempotency_store_error", idempotency_key=key, context={"exec_id": spec.exec_id})
        raise RuntimeError(f"Idempotency store error: {task_id} {key}")

    # Must be DISPATCHED to execute.
    if derived_state is not TaskState.DISPATCHED:
        self.evidence.write_rejection(task_id, reason=f"invalid_state:{derived_state.value}", idempotency_key=key, context={"exec_id": spec.exec_id})
        raise RuntimeError(f"invalid_state:{derived_state.value}")

    # Concurrency guard (in-flight mutex).
    self._idempotency_store.acquire_lock(task_id, key)

    status = "unknown"
    terminal_exec_id = spec.exec_id
    terminal_manifest_sha256 = ""

    try:
        # Thread idempotency key into evidence bundles (TaskRunner reads this).
        self._current_idempotency_key = key

        # Delegate to the original runner.
        res = orig_run_dispatched(self, task_id)

        status = "complete" if bool(res.ok) else "failed"
        terminal_exec_id = res.exec_id
        terminal_manifest_sha256 = res.evidence_manifest_sha256
        return res

    except Exception as e:
        # Ensure terminal evidence exists even when the original runner raises.
        reason = f"runner_exception:{e.__class__.__name__}:{e}"
        rej = self.evidence.write_rejection(
            task_id,
            reason=reason,
            idempotency_key=key,
            context={"exec_id": spec.exec_id},
        )
        status = "error"
        terminal_manifest_sha256 = str(rej.get("manifest_sha256") or "")
        raise

    finally:
        # Always clear per-run key and release lock.
        try:
            delattr(self, "_current_idempotency_key")
        except Exception:
            pass

        # Record the attempt ONLY after terminal evidence exists (or after we forced a rejection).
        # This enforces Policy B without creating permanent "started" tombstones.
        try:
            self._idempotency_store.record_if_absent(
                task_id,
                key,
                {
                    "status": str(status),
                    "exec_id": str(terminal_exec_id),
                    "manifest_sha256": str(terminal_manifest_sha256),
                },
            )
        finally:
            self._idempotency_store.release_lock(task_id, key)


# Patch TaskRunner
TaskRunner.run_dispatched = run_dispatched_with_idempotency
