from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone

from agentos.canonical import canonical_json
from agentos.store_fs import FSStore


def main() -> None:
    # Clean test store for deterministic behavior
    shutil.rmtree("store", ignore_errors=True)

    store = FSStore(root="store")
    task_id = "selftest-task"

    store.append_event(task_id, "TASK_CREATED", {"ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")})
    store.append_event(task_id, "TASK_VERIFIED", {"ok": True, "policy": "fail_closed"})
    store.append_event(task_id, "TASK_DISPATCHED", {"executor": "noop", "attempt": 1})
    store.append_event(task_id, "TASK_COMPLETED", {"ok": True})

    ok = store.verify_chain(task_id)
    events = store.list_events(task_id)

    payload = {
        "ok": ok,
        "task_id": task_id,
        "event_count": len(events),
        "head_seq": events[-1]["seq"] if events else None,
        "events": events,
    }

    print(canonical_json(payload))


if __name__ == "__main__":
    main()
