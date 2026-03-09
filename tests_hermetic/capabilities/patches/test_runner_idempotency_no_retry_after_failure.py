import pytest

from agentos.adapter_registry import ADAPTERS
from agentos.canonical import sha256_hex
from agentos.runner import TaskRunner
from agentos.store_fs import FSStore
from agentos.task import Task, TaskState

import agentos.capabilities  # noqa: F401


def test_no_retry_after_failure_policy_b(tmp_path):
    old_cmd = list(ADAPTERS["envoy"]["cmd"])
    try:
        ADAPTERS["envoy"]["cmd"] = ["python3", "-c", "import sys; sys.exit(1)"]
        store_path = tmp_path / "store"
        store = FSStore(str(store_path))
        runner = TaskRunner(store, evidence_root=str(tmp_path / "evidence"))

        task_id = "task_idem_fail_no_retry"
        payload = {
            "exec_id": "exec_idem_fail_no_retry_0001",
            "kind": "shell",
            "cmd_argv": list(ADAPTERS["envoy"]["cmd"]) + ["system_status"],
            "cwd": str(tmp_path),
            "env_allowlist": list(ADAPTERS["envoy"]["env_allowlist"]),
            "timeout_s": 5,
            "inputs_manifest_sha256": sha256_hex(b"{}"),
            "paths_allowlist": [str(tmp_path)],
            "note": "policy B: no retry after failure",
        }

        t = Task(
            task_id=task_id,
            state=TaskState.CREATED,
            role="envoy",
            action="deterministic_local_execution",
            payload=payload,
            attempt=0,
        )

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

        summary1 = runner.run_dispatched(task_id)
        assert summary1.ok is False

        with pytest.raises(RuntimeError, match="Duplicate execution prevented"):
            runner.run_dispatched(task_id)
    finally:
        ADAPTERS["envoy"]["cmd"] = old_cmd
