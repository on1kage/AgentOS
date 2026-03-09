import tempfile

from agentos.adapter_registry import ADAPTERS
from agentos.store_fs import FSStore
from agentos.runner import TaskRunner


def test_runner_uses_verified_inputs_manifest():
    with tempfile.TemporaryDirectory() as tmp:
        store = FSStore(root=tmp)
        task_id = "t_verified_manifest"

        store.append_event(task_id, "TASK_CREATED", {
            "role": "envoy",
            "action": "deterministic_local_execution",
            "payload": {
                "exec_id": "exec1",
                "kind": "shell",
                "cmd_argv": list(ADAPTERS["envoy"]["cmd"]) + ["system_status"],
                "cwd": ".",
                "env_allowlist": list(ADAPTERS["envoy"]["env_allowlist"]),
                "timeout_s": 5,
                "inputs_manifest_sha256": "a" * 64,
                "paths_allowlist": ["."],
                "note": None
            },
            "attempt": 0
        })

        store.append_event(task_id, "TASK_VERIFIED", {
            "role": "envoy",
            "action": "deterministic_local_execution",
            "reason": "ok",
            "inputs_manifest_sha256": "b" * 64,
            "attempt": 0
        })

        store.append_event(task_id, "TASK_DISPATCHED", {
            "role": "envoy",
            "action": "deterministic_local_execution",
            "attempt": 0,
            "inputs_manifest_sha256": "b" * 64
        })

        runner = TaskRunner(store, evidence_root="evidence")
        res = runner.run_dispatched(task_id)
        assert res.ok

        events = store.list_events(task_id)
        rs = [e for e in events if e.get("type") == "RUN_STARTED"]
        assert len(rs) == 1
        body = rs[0].get("body") or {}
        assert body.get("inputs_manifest_sha256") == "b" * 64
