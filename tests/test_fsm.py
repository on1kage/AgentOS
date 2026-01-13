import pytest
from agentos.fsm import (
    TaskFSM,
    TaskState,
    EventType,
    FSMViolationError,
)

def e(task_id, typ, **kw):
    d = {"task_id": task_id, "type": typ}
    d.update(kw)
    return d

def test_happy_path():
    fsm = TaskFSM("t1")
    fsm.replay([
        e("t1", EventType.TASK_CREATED.value),
        e("t1", EventType.TASK_READY.value),
        e("t1", EventType.TASK_DISPATCHED.value),
        e("t1", EventType.RUN_STARTED.value),
        e("t1", EventType.RUN_SUCCEEDED.value),
    ])
    assert fsm.state == TaskState.SUCCEEDED

def test_illegal_transition():
    fsm = TaskFSM("t2")
    with pytest.raises(FSMViolationError):
        fsm.replay([
            e("t2", EventType.RUN_STARTED.value),
        ])

def test_post_terminal_event_rejected():
    fsm = TaskFSM("t3")
    with pytest.raises(FSMViolationError):
        fsm.replay([
            e("t3", EventType.TASK_CREATED.value),
            e("t3", EventType.TASK_READY.value),
            e("t3", EventType.TASK_DISPATCHED.value),
            e("t3", EventType.RUN_STARTED.value),
            e("t3", EventType.RUN_SUCCEEDED.value),
            e("t3", EventType.TASK_READY.value),
        ])
