import json
from pathlib import Path

from agentos.store_fs import FSStore
from agentos.evaluation import evaluate_task
from agentos.fsm import rebuild_task_state

def _emit_minimal_completed(store: FSStore, task_id: str):
    store.append_event(task_id, "TASK_CREATED", {"task_id": task_id})
    store.append_event(task_id, "TASK_VERIFIED", {"task_id": task_id})
    store.append_event(task_id, "TASK_DISPATCHED", {"task_id": task_id})
    store.append_event(task_id, "RUN_STARTED", {"task_id": task_id})
    store.append_event(
        task_id,
        "RUN_SUCCEEDED",
        {
            "task_id": task_id,
            "exec_id": "weekly_proof",
            "spec_sha256": "specsha",
            "exit_code": 0,
            "manifest_sha256": "manisha",
        },
    )

def test_evaluate_refine_emits_refinement_task_id(tmp_path: Path):
    store = FSStore(str(tmp_path / "events"))
    task_id = "t1"
    _emit_minimal_completed(store, task_id)

    snap = rebuild_task_state(store, task_id)
    assert snap["state"] == "COMPLETED"

    evidence_root = str(tmp_path / "evidence")
    p = Path(evidence_root) / task_id / "weekly_proof"
    p.mkdir(parents=True, exist_ok=True)
    (p / "run_summary.json").write_text(json.dumps({"manifest_sha256": "manisha"}), encoding="utf-8")

    out = evaluate_task(store=store, evidence_root=evidence_root, task_id=task_id, decision="refine", note="x")
    assert out["evaluation_spec_sha256"]
    assert out["evaluation_manifest_sha256"]

    evs = list(store.list_events(task_id))
    te = [e for e in evs if str(e.get("type")) == "TASK_EVALUATED"]
    assert te
    body = dict(te[-1].get("body") or {})
    assert body.get("decision") == "refine"
    assert isinstance(body.get("refinement_task_id"), str)
    assert body["refinement_task_id"].startswith(f"refine::{task_id}::")
