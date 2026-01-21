import tempfile

from agentos.pipeline import verify_task
from agentos.router import ExecutionRouter
from agentos.store_fs import FSStore
from agentos.task import Task, TaskState


def test_task_dispatched_includes_inputs_manifest_sha256_and_matches_verified():
    with tempfile.TemporaryDirectory() as tmp:
        store = FSStore(root=tmp)

        valid_ims = "a" * 64

        task = Task(
            task_id="t_dispatch_ims_1",
            state=TaskState.CREATED,
            role="morpheus",
            action="architecture",
            payload={"inputs_manifest_sha256": valid_ims},
            attempt=0,
        )

        vr = verify_task(store, task)
        assert vr.ok is True

        router = ExecutionRouter(store)
        rr = router.route(task)
        assert rr.ok is True

        events = store.list_events(task.task_id)

        verified = [e for e in events if e.get("type") == "TASK_VERIFIED"]
        assert len(verified) == 1
        verified_body = verified[0].get("body") or {}
        assert verified_body.get("inputs_manifest_sha256") == valid_ims

        dispatched = [e for e in events if e.get("type") == "TASK_DISPATCHED"]
        assert len(dispatched) == 1
        dispatched_body = dispatched[0].get("body") or {}
        assert dispatched_body.get("inputs_manifest_sha256") == valid_ims
