import pytest
from agentos.runner import TaskRunner
from agentos.store_fs import FSStore
from agentos.canonical import sha256_hex

def test_runner_fails_closed_when_not_dispatched(tmp_path):
    store = FSStore(str(tmp_path / "store"))
    runner = TaskRunner(store, evidence_root=str(tmp_path / "evidence"))

    task_id = "t_not_dispatched"
    payload = {
        "exec_id": "exec_not_dispatched",
        "kind": "shell",
        "cmd_argv": ["/bin/echo", "ok"],
        "cwd": str(tmp_path),
        "env_allowlist": [],
        "timeout_s": 5,
        "inputs_manifest_sha256": sha256_hex(b"inputs"),
        "paths_allowlist": [str(tmp_path), "/bin/echo"],
    }

    store.append_event(
        task_id,
        "TASK_CREATED",
        {
            "role": "envoy",
            "action": "deterministic_local_execution",
            "payload": payload,
            "attempt": 0,
        },
    )

    with pytest.raises(RuntimeError, match="invalid_state:"):
        runner.run_dispatched(task_id)
