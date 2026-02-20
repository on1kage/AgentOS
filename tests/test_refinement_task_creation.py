import json
from pathlib import Path

from agentos.evaluation import evaluate_task
from agentos.refinement import create_refinement_task_from_parent
from agentos.fsm import rebuild_task_state
from agentos.store_fs import FSStore
from agentos.task import TaskState


def _emit_completed_with_run_summary(tmp_path: Path, store: FSStore, task_id: str):
    store.append_event(task_id, "TASK_CREATED", {"role": "envoy", "action": "deterministic_local_execution", "payload": {"exec_id": "e1", "kind": "shell", "cmd_argv": ["true"], "cwd": ".", "env_allowlist": [], "timeout_s": 1, "inputs_manifest_sha256": "x", "paths_allowlist": []}, "attempt": 0})
    store.append_event(task_id, "TASK_VERIFIED", {"role": "envoy", "action": "deterministic_local_execution", "inputs_manifest_sha256": "a" * 64, "attempt": 0})
    store.append_event(task_id, "TASK_DISPATCHED", {"role": "envoy", "action": "deterministic_local_execution", "attempt": 0, "inputs_manifest_sha256": "a" * 64})
    store.append_event(task_id, "RUN_STARTED", {"exec_id": "e1", "spec_sha256": "b" * 64, "inputs_manifest_sha256": "a" * 64, "kind": "shell"})
    store.append_event(task_id, "RUN_SUCCEEDED", {"exec_id": "e1", "spec_sha256": "b" * 64, "exit_code": 0, "stdout_sha256": "c" * 64, "stderr_sha256": "d" * 64, "outputs_manifest_sha256": "e" * 64})

    evidence_root = str(tmp_path / "evidence")
    p = Path(evidence_root) / task_id / "e1"
    p.mkdir(parents=True, exist_ok=True)
    (p / "run_summary.json").write_text(json.dumps({"manifest_sha256": "f" * 64}), encoding="utf-8")
    return evidence_root


def test_refinement_creates_new_task_and_verifies(tmp_path: Path):
    store = FSStore(str(tmp_path / "events"))
    parent_task_id = "t_parent_1"
    evidence_root = _emit_completed_with_run_summary(tmp_path, store, parent_task_id)

    snap0 = rebuild_task_state(store, parent_task_id)
    assert TaskState(str(snap0["state"])) is TaskState.COMPLETED

    ev = evaluate_task(store=store, evidence_root=evidence_root, task_id=parent_task_id, decision="refine", note="x")
    rid = ev["refinement_task_id"]
    assert isinstance(rid, str) and rid

    out = create_refinement_task_from_parent(store=store, evidence_root=evidence_root, parent_task_id=parent_task_id)
    assert out["refinement_task_id"] == rid
    assert out["refinement_create_spec_sha256"]
    assert out["refinement_create_manifest_sha256"]

    snap_new = rebuild_task_state(store, rid)
    assert TaskState(str(snap_new["state"])) is TaskState.VERIFIED
