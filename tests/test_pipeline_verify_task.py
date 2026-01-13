import tempfile

from agentos.pipeline import verify_task
from agentos.store_fs import FSStore
from agentos.task import Task, TaskState


def test_verify_task_emits_created_and_verified():
    with tempfile.TemporaryDirectory() as tmp:
        store = FSStore(root=tmp)

        task = Task(
            task_id="t_verify_1",
            state=TaskState.CREATED,
            role="morpheus",
            action="architecture",
            payload={},
            attempt=0,
        )

        res = verify_task(store, task)

        assert res.ok is True
        assert res.created_event is not None
        assert res.decision_event is not None

        events = store.list_events(task.task_id)
        types = [e["type"] for e in events]
        assert types == ["TASK_CREATED", "TASK_VERIFIED"]


def test_verify_task_idempotent_created_event():
    with tempfile.TemporaryDirectory() as tmp:
        store = FSStore(root=tmp)

        task = Task(
            task_id="t_verify_2",
            state=TaskState.CREATED,
            role="morpheus",
            action="architecture",
            payload={},
            attempt=0,
        )

        r1 = verify_task(store, task)
        r2 = verify_task(store, task)

        assert r1.ok is True
        assert r2.ok is True

        events = store.list_events(task.task_id)
        types = [e["type"] for e in events]
        # created only once, verified twice (append-only)
        assert types == ["TASK_CREATED", "TASK_VERIFIED", "TASK_VERIFIED"]
