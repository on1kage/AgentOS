
import tempfile
from agentos.pipeline import verify_task
from agentos.store_fs import FSStore
from agentos.task import Task, TaskState

def test_verify_task_fails_closed_on_intent_compilation_manifest_mismatch():
    with tempfile.TemporaryDirectory() as tmp:
        store = FSStore(root=tmp)

        task = Task(
            task_id="t_icm_mismatch",
            state=TaskState.CREATED,
            role="morpheus",
            action="architecture",
            payload={
                "inputs_manifest_sha256":"a"*64,
                "intent_compilation_manifest_sha256":"b"*64
            },
            attempt=0
        )

        vr = verify_task(store,task)
        assert vr.ok is False
        assert vr.reason == "intent_compilation_manifest_sha256_mismatch"

        events = store.list_events(task.task_id)
        assert any(e.get("type")=="TASK_REJECTED" for e in events)
