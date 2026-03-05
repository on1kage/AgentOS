import tempfile
import pytest

from agentos.store_fs import FSStore
from agentos.runner import TaskRunner


def test_runner_rejects_unsupported_execution_kind_and_emits_no_run_started():
    with tempfile.TemporaryDirectory() as tmp:
        store = FSStore(root=tmp)
        task_id = "t_reject_kind_1"

        store.append_event(
            task_id,
            "TASK_CREATED",
            {
                "role": "envoy",
                "action": "deterministic_local_execution",
                "payload": {
                    "exec_id": "exec-1",
                    "kind": "python",
                    "cmd_argv": ["python3", "-c", "print('x')"],
                    "cwd": tmp,
                    "env_allowlist": [],
                    "timeout_s": 1,
                    "inputs_manifest_sha256": "b" * 64,
                    "paths_allowlist": [tmp],
                    "note": None,
                },
                "attempt": 0,
            },
        )
        store.append_event(
            task_id,
            "TASK_VERIFIED",
            {
                "role": "envoy",
                "action": "deterministic_local_execution",
                "reason": "ok",
                "inputs_manifest_sha256": "b" * 64,
                "attempt": 0,
            },
        )
        store.append_event(
            task_id,
            "TASK_DISPATCHED",
            {
                "role": "envoy",
                "action": "deterministic_local_execution",
                "attempt": 0,
                "inputs_manifest_sha256": "b" * 64,
            },
        )

        runner = TaskRunner(store, evidence_root="evidence")

        with pytest.raises(RuntimeError) as ei:
            runner.run_dispatched(task_id)

        assert str(ei.value) == "unsupported_execution_kind:python"

        events = store.list_events(task_id)
        assert not any(e.get("type") == "RUN_STARTED" for e in events)
