def test_agentos_fsm_smoke():
    from agentos.fsm import TaskFSM, EventType
    from agentos.task import TaskState

    fsm = TaskFSM(task_id="t1")
    assert fsm.state == TaskState.CREATED

    fsm.apply({"task_id": "t1", "type": EventType.TASK_CREATED.value})
    assert fsm.state == TaskState.CREATED

    fsm.apply({"task_id": "t1", "type": EventType.TASK_VERIFIED.value})
    assert fsm.state == TaskState.VERIFIED

    fsm.apply({"task_id": "t1", "type": EventType.TASK_DISPATCHED.value})
    assert fsm.state == TaskState.DISPATCHED

    fsm.apply({"task_id": "t1", "type": EventType.RUN_STARTED.value})
    assert fsm.state == TaskState.RUNNING

    fsm.apply({"task_id": "t1", "type": EventType.RUN_SUCCEEDED.value})
    assert fsm.state == TaskState.COMPLETED
