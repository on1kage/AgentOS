import sys; sys.modules.pop("agentos", None)
import tempfile
from pathlib import Path
import json
import pytest

from agentos.adapter_registry import ADAPTERS
from agentos.runner import TaskRunner
from agentos.task import Task, TaskState
from agentos.store_fs import FSStore
from agentos.canonical import sha256_hex

import agentos.capabilities.patches.runner_idempotency_patch  # noqa: F401


def test_runner_idempotency(tmp_path):
    store_path = tmp_path / "store"
    store = FSStore(str(tempfile.mkdtemp()))
    runner = TaskRunner(store, evidence_root=str(tmp_path / "evidence"))

    task_id = "task_idem"
    payload = {
        "exec_id": "exec_idem_0001",
        "kind": "shell",
        "cmd_argv": list(ADAPTERS["envoy"]["cmd"]) + ["system_status"],
        "cwd": ".",
        "env_allowlist": list(ADAPTERS["envoy"]["env_allowlist"]),
        "timeout_s": 5,
        "inputs_manifest_sha256": sha256_hex(b"{}"),
        "paths_allowlist": ["."],
        "note": "idempotent test",
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
    assert summary1.ok

    ev_dir = Path(tmp_path) / "evidence" / task_id / payload["exec_id"]
    assert (ev_dir / "exec_spec.json").is_file()
    assert (ev_dir / "stdout.txt").is_file()
    assert (ev_dir / "stderr.txt").is_file()

    with pytest.raises(RuntimeError, match="Duplicate execution prevented"):
        runner.run_dispatched(task_id)

    rej_id = sha256_hex(b"duplicate_execution")[:16]
    rej_dir = Path(tmp_path) / "evidence" / task_id / "rejections" / rej_id
    assert (rej_dir / "rejection.json").is_file()
    assert (rej_dir / "manifest.sha256.json").is_file()
    assert (rej_dir / "rejection.json").is_file()
    assert (rej_dir / "manifest.sha256.json").is_file()

    rej_obj = json.loads((rej_dir / "rejection.json").read_text(encoding="utf-8"))
    assert isinstance(rej_obj, dict)
    prior_exec_id = rej_obj.get("prior_exec_id")
    prior_manifest_sha256 = rej_obj.get("prior_manifest_sha256")
    assert isinstance(prior_exec_id, str) and prior_exec_id
    assert isinstance(prior_manifest_sha256, str) and prior_manifest_sha256

    prior_dir = Path(tmp_path) / "evidence" / task_id / prior_exec_id
    assert (prior_dir / "run_summary.json").is_file()
    prior_rs = json.loads((prior_dir / "run_summary.json").read_text(encoding="utf-8"))
    assert isinstance(prior_rs, dict)
    assert prior_rs.get("manifest_sha256") == prior_manifest_sha256
