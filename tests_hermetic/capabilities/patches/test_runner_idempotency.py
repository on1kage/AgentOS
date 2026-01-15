from agentos.runner import TaskRunner
from agentos.task import Task, TaskState
from agentos.store_fs import FSStore
from agentos.canonical import sha256_hex
import pytest

# Side-effect import: monkey-patches TaskRunner.run_dispatched
import agentos.capabilities.patches.runner_idempotency_patch  # noqa: F401


def test_runner_idempotency(tmp_path):
    store_path = tmp_path / "store"
    store = FSStore(str(store_path))
    runner = TaskRunner(store, evidence_root=str(tmp_path / "evidence"))

    task_id = "task_idem"
    payload = {
        "exec_id": "exec_idem_0001",
        "kind": "shell",
        "cmd_argv": ["/bin/echo", "ok"],
        "cwd": str(tmp_path),
        "env_allowlist": [],
        "timeout_s": 5,
        "inputs_manifest_sha256": sha256_hex(b"{}"),
        "paths_allowlist": [str(tmp_path), "/usr/bin/echo"],
        "note": "idempotent test",
    }

    t = Task(
        task_id=task_id,
        state=TaskState.CREATED,
        role="recon",
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

    # First run should succeed
    summary1 = runner.run_dispatched(task_id)
    assert summary1.ok

    # Second run should raise RuntimeError due to idempotency
    with pytest.raises(RuntimeError, match="Duplicate execution prevented"):
        runner.run_dispatched(task_id)
