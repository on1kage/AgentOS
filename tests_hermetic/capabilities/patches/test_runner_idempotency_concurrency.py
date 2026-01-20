import threading
from typing import Any, List

import pytest

from agentos.canonical import sha256_hex
from agentos.runner import TaskRunner
from agentos.store_fs import FSStore
from agentos.task import Task, TaskState

# Ensure runtime patch is loaded (import-time side effect)
import agentos.capabilities  # noqa: F401


def test_runner_idempotency_concurrent(tmp_path):
    store_path = tmp_path / "store"
    store = FSStore(str(store_path))
    runner = TaskRunner(store, evidence_root=str(tmp_path / "evidence"))

    task_id = "task_idem_concurrent"
    payload = {
        "exec_id": "exec_idem_concurrent_0001",
        "kind": "shell",
        "cmd_argv": ["/bin/echo", "ok"],
        "cwd": str(tmp_path),
        "env_allowlist": [],
        "timeout_s": 5,
        "inputs_manifest_sha256": sha256_hex(b"{}"),
        "paths_allowlist": [str(tmp_path), "/usr/bin/echo"],
        "note": "idempotent concurrent test",
    }

    t = Task(
        task_id=task_id,
        state=TaskState.CREATED,
        role="envoy",
        action="deterministic_local_execution",
        payload=payload,
        attempt=0,
    )

    # Verify and dispatch
    from agentos.pipeline import verify_task
    from agentos.router import ExecutionRouter

    router = ExecutionRouter(store)
    assert verify_task(store, t).ok
    assert router.route(
        Task(
            task_id=task_id,
            state=TaskState.VERIFIED,
            role=t.role,
            action=t.action,
            payload=t.payload,
            attempt=0,
        )
    ).ok

    results: List[Any] = []
    errors: List[str] = []
    lock = threading.Lock()

    def worker():
        try:
            r = runner.run_dispatched(task_id)
            with lock:
                results.append(r)
        except Exception as e:
            with lock:
                errors.append(str(e))

    th1 = threading.Thread(target=worker)
    th2 = threading.Thread(target=worker)
    th1.start()
    th2.start()
    th1.join()
    th2.join()

    # Exactly one should succeed.
    assert len(results) == 1
    assert results[0].ok

    # Exactly one should fail, and it must be for idempotency reasons.
    assert len(errors) == 1
    msg = errors[0]
    assert ("Idempotent lock held" in msg) or ("Duplicate execution prevented" in msg)
