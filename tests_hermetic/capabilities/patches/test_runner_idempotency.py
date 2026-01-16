from agentos.runner import TaskRunner
from agentos.task import Task, TaskState
from agentos.store_fs import FSStore
from agentos.canonical import sha256_hex
from pathlib import Path
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

    # Evidence footprint must exist for the successful run (auditable, fail-closed)
    ev_dir = Path(tmp_path) / "evidence" / task_id / payload["exec_id"]
    assert (ev_dir / "exec_spec.json").is_file()
    assert (ev_dir / "stdout.txt").is_file()
    assert (ev_dir / "stderr.txt").is_file()

    # Second run should raise RuntimeError due to idempotency
    with pytest.raises(RuntimeError, match="Duplicate execution prevented"):
        runner.run_dispatched(task_id)

    # Rejection must leave an auditable evidence footprint
    rej_id = sha256_hex(b"duplicate_execution")[:16]
    rej_dir = Path(tmp_path) / "evidence" / task_id / "rejections" / rej_id
    assert (rej_dir / "rejection.json").is_file()
    assert (rej_dir / "manifest.sha256.json").is_file()
