from __future__ import annotations

import shutil

from agentos.canonical import canonical_json
from agentos.router import ExecutionRouter
from agentos.store_fs import FSStore
from agentos.task import Task, TaskState


def main() -> None:
    shutil.rmtree("store", ignore_errors=True)
    store = FSStore(root="store")
    router = ExecutionRouter(store)

    t_ok = Task(task_id="t_ok", state=TaskState.VERIFIED, role="morpheus", action="architecture", payload={})
    t_bad = Task(task_id="t_bad", state=TaskState.VERIFIED, role="morpheus", action="network_calls", payload={})
    t_state = Task(task_id="t_state", state=TaskState.CREATED, role="morpheus", action="architecture", payload={})

    r1 = router.route(t_ok)
    r2 = router.route(t_bad)
    r3 = router.route(t_state)

    payload = {
        "r1": r1.__dict__,
        "r2": r2.__dict__,
        "r3": r3.__dict__,
        "events_t_ok": store.list_events("t_ok"),
        "events_t_bad": store.list_events("t_bad"),
        "events_t_state": store.list_events("t_state"),
        "chain_ok_t_ok": store.verify_chain("t_ok"),
        "chain_ok_t_bad": store.verify_chain("t_bad"),
        "chain_ok_t_state": store.verify_chain("t_state"),
    }

    print(canonical_json(payload))


if __name__ == "__main__":
    main()
