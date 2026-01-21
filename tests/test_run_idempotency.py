import tempfile

from agentos.pipeline import verify_task
from agentos.router import ExecutionRouter
from agentos.runner import TaskRunner
from agentos.store_fs import FSStore
from agentos.task import Task, TaskState


def test_duplicate_execution_produces_rejection_with_prior_linkage():
    with tempfile.TemporaryDirectory() as tmp:
        store = FSStore(root=tmp)

        ims = "b" * 64

        payload = {
            "exec_id": "exec_1",
            "kind": "shell",
            "cmd_argv": ["python3", "-c", "print('ok')"],
            "cwd": tmp,
            "env_allowlist": [],
            "timeout_s": 5,
            "inputs_manifest_sha256": ims,
            "paths_allowlist": [tmp],
            "note": "idempotency test",
        }

        task = Task(
            task_id="t_run_idem_1",
            state=TaskState.CREATED,
            role="morpheus",
            action="architecture",
            payload=payload,
            attempt=0,
        )

        assert verify_task(store, task).ok
        assert ExecutionRouter(store).route(task).ok

        runner = TaskRunner(store)

        # First run should succeed (and produce evidence under exec_id)
        r1 = runner.run_dispatched(task.task_id)
        assert r1.ok is True

        # Second run must be blocked by idempotency wrapper with an auditable rejection bundle
        try:
            runner.run_dispatched(task.task_id)
        except Exception:
            pass

        # Verify only one RUN_STARTED and one RUN_SUCCEEDED exist
        events = store.list_events(task.task_id)
        assert len([e for e in events if e.get("type") == "RUN_STARTED"]) == 1
        assert len([e for e in events if e.get("type") == "RUN_SUCCEEDED"]) == 1

        # Verify rejection bundle exists with duplicate_execution reason and prior exec linkage
        import json
        from pathlib import Path as P

        rej_root = P("evidence") / task.task_id / "rejections"
        assert rej_root.is_dir()

        rejs = list(rej_root.glob("*/rejection.json"))
        assert len(rejs) >= 1

        objs = [json.loads(p.read_text(encoding="utf-8")) for p in rejs]
        dup = [o for o in objs if o.get("reason") == "duplicate_execution"]
        assert len(dup) >= 1

        # prior_exec_id must point at the first run's exec_id
        assert any(o.get("prior_exec_id") == r1.exec_id for o in dup)
