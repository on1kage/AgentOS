import pytest

from agentos.fsm import EventType, FSMViolationError, TaskFSM
from agentos.task import TaskState


def e(task_id, typ, **kw):
    d = {"task_id": task_id, "type": typ}
    d.update(kw)
    return d


def test_happy_path_verified_to_completed():
    fsm = TaskFSM("t1", initial_state=TaskState.CREATED)
    fsm.replay(
        [
            e("t1", EventType.TASK_CREATED.value),
            e("t1", EventType.TASK_VERIFIED.value),
            e("t1", EventType.TASK_DISPATCHED.value),
            e("t1", EventType.RUN_STARTED.value),
            e("t1", EventType.RUN_SUCCEEDED.value),
        ]
    )
    assert fsm.state == TaskState.COMPLETED


def test_illegal_transition_fail_closed():
    fsm = TaskFSM("t2", initial_state=TaskState.CREATED)
    with pytest.raises(FSMViolationError):
        fsm.replay(
            [
                e("t2", EventType.RUN_STARTED.value),
            ]
        )


def test_post_terminal_event_rejected():
    fsm = TaskFSM("t3", initial_state=TaskState.CREATED)
    with pytest.raises(FSMViolationError):
        fsm.replay(
            [
                e("t3", EventType.TASK_CREATED.value),
                e("t3", EventType.TASK_VERIFIED.value),
                e("t3", EventType.TASK_DISPATCHED.value),
                e("t3", EventType.RUN_STARTED.value),
                e("t3", EventType.RUN_SUCCEEDED.value),
                e("t3", EventType.TASK_VERIFIED.value),
            ]
        )
