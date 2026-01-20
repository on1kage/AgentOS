import json
from pathlib import Path

import pytest

from agentos.canonical import sha256_hex
from agentos.runner import TaskRunner
from agentos.store_fs import FSStore
from agentos.task import Task, TaskState

# Ensure runtime patches are loaded (import-time side effect)
import agentos.capabilities  # noqa: F401


def test_timeout_emits_failed_evidence_and_retry_is_rejected_with_linkage(tmp_path):
    store_path = tmp_path / "store"
    store = FSStore(str(store_path))
    runner = TaskRunner(store, evidence_root=str(tmp_path / "evidence"))

    task_id = "task_timeout_evidence"
    payload = {
        "exec_id": "exec_timeout_0001",
        "kind": "shell",
        "cmd_argv": ["/bin/sleep", "2"],
        "cwd": str(tmp_path),
        "env_allowlist": [],
        "timeout_s": 1,
        "inputs_manifest_sha256": sha256_hex(b"{}"),
        "paths_allowlist": [str(tmp_path), "/bin/sleep"],
        "note": "timeout must be FAILED with evidence; retry must be REJECTED with linkage",
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

    # First run deterministically times out -> FAILED (exit_code 124)
    summary1 = runner.run_dispatched(task_id)
    assert summary1.ok is False
    assert summary1.exit_code == 124

    ev_dir = Path(tmp_path) / "evidence" / task_id / payload["exec_id"]
    assert (ev_dir / "exec_spec.json").is_file()
    assert (ev_dir / "stdout.txt").is_file()
    assert (ev_dir / "stderr.txt").is_file()
    assert (ev_dir / "manifest.sha256.json").is_file()
    assert (ev_dir / "run_summary.json").is_file()

    rs = json.loads((ev_dir / "run_summary.json").read_text(encoding="utf-8"))
    assert isinstance(rs, dict)
    assert rs.get("outcome") == "FAILED"
    assert rs.get("reason") == "exit_code:124"
    prior_manifest_sha256 = rs.get("manifest_sha256")
    assert isinstance(prior_manifest_sha256, str) and prior_manifest_sha256

    # Second run forbidden under Policy B -> REJECTED evidence + linkage to prior bundle
    with pytest.raises(RuntimeError, match="Duplicate execution prevented"):
        runner.run_dispatched(task_id)

    rej_id = sha256_hex(b"duplicate_execution")[:16]
    rej_dir = Path(tmp_path) / "evidence" / task_id / "rejections" / rej_id
    assert (rej_dir / "rejection.json").is_file()
    assert (rej_dir / "manifest.sha256.json").is_file()

    rej_obj = json.loads((rej_dir / "rejection.json").read_text(encoding="utf-8"))
    assert isinstance(rej_obj, dict)
    assert rej_obj.get("outcome") == "REJECTED"
    assert rej_obj.get("reason") == "duplicate_execution"

    prior_exec_id = rej_obj.get("prior_exec_id")
    linked_manifest_sha256 = rej_obj.get("prior_manifest_sha256")
    assert prior_exec_id == payload["exec_id"]
    assert linked_manifest_sha256 == prior_manifest_sha256
