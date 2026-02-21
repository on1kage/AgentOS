import json
from pathlib import Path
import pytest
from typing import Dict

from agentos.evaluation import evaluate_task
from agentos.refinement import create_refinement_task_from_parent
from agentos.fsm import rebuild_task_state
from agentos.store_fs import FSStore
from agentos.task import Task, TaskState
from agentos.router import ExecutionRouter, RouteResult


def _emit_completed_with_run_summary(tmp_path: Path, store: FSStore, task_id: str) -> str:
    """Creates a fresh task that reaches EVALUATED (bootstrap only)."""
    evidence_root = str(tmp_path / "evidence")
    
    store.append_event(task_id, "TASK_CREATED", {
        "role": "envoy",
        "action": "deterministic_local_execution",
        "payload": {
            "exec_id": "e1",
            "kind": "shell",
            "cmd_argv": ["true"],
            "cwd": ".",
            "env_allowlist": [],
            "timeout_s": 1,
            "inputs_manifest_sha256": "x",
            "paths_allowlist": []
        },
        "attempt": 0
    })
    store.append_event(task_id, "TASK_VERIFIED", {
        "role": "envoy",
        "action": "deterministic_local_execution",
        "inputs_manifest_sha256": "a"*64,
        "attempt": 0
    })
    store.append_event(task_id, "TASK_DISPATCHED", {
        "role": "envoy",
        "action": "deterministic_local_execution",
        "attempt": 0,
        "inputs_manifest_sha256": "a"*64
    })
    store.append_event(task_id, "RUN_STARTED", {
        "exec_id": "e1",
        "spec_sha256": "b"*64,
        "inputs_manifest_sha256": "a"*64,
        "kind": "shell"
    })
    store.append_event(task_id, "RUN_SUCCEEDED", {
        "exec_id": "e1",
        "spec_sha256": "b"*64,
        "exit_code": 0,
        "stdout_sha256": "c"*64,
        "stderr_sha256": "d"*64,
        "outputs_manifest_sha256": "e"*64
    })
    
    p = Path(evidence_root) / task_id / "e1"
    p.mkdir(parents=True, exist_ok=True)
    (p / "run_summary.json").write_text(json.dumps({"manifest_sha256": "f"*64}), encoding="utf-8")
    
    evaluate_task(store=store, evidence_root=evidence_root, task_id=task_id, decision="refine", note="parent evaluation note")
    return evidence_root


def _advance_to_evaluated(tmp_path: Path, store: FSStore, task_id: str, evidence_root: str) -> None:
    """Safely advances any task to EVALUATED from current state."""
    snap = rebuild_task_state(store, task_id)
    current_state = TaskState(str(snap["state"]))
    
    if current_state == TaskState.EVALUATED:
        return
    
    if current_state in (TaskState.CREATED, TaskState.VERIFIED):
        store.append_event(task_id, "TASK_DISPATCHED", {
            "role": "envoy", "action": "deterministic_local_execution", "attempt": 0, "inputs_manifest_sha256": "a"*64
        })
        store.append_event(task_id, "RUN_STARTED", {
            "exec_id": "e1", "spec_sha256": "b"*64, "inputs_manifest_sha256": "a"*64, "kind": "shell"
        })
        store.append_event(task_id, "RUN_SUCCEEDED", {
            "exec_id": "e1", "spec_sha256": "b"*64, "exit_code": 0,
            "stdout_sha256": "c"*64, "stderr_sha256": "d"*64, "outputs_manifest_sha256": "e"*64
        })
        
        p = Path(evidence_root) / task_id / "e1"
        p.mkdir(parents=True, exist_ok=True)
        (p / "run_summary.json").write_text(json.dumps({"manifest_sha256": "f"*64}), encoding="utf-8")
        
        evaluate_task(store=store, evidence_root=evidence_root, task_id=task_id, decision="refine", note=f"eval {task_id}")


def test_refinement_creates_new_task_and_verifies(tmp_path: Path):
    store = FSStore(str(tmp_path / "events"))
    evidence_root = str(tmp_path / "evidence")
    parent_task_id = "t_parent_1"

    _emit_completed_with_run_summary(tmp_path, store, parent_task_id)
    snap0 = rebuild_task_state(store, parent_task_id)
    assert TaskState(str(snap0["state"])) is TaskState.EVALUATED

    out = create_refinement_task_from_parent(store=store, evidence_root=evidence_root, parent_task_id=parent_task_id)
    assert isinstance(out["refinement_task_id"], str) and out["refinement_task_id"]
    assert out["refinement_create_spec_sha256"]
    assert out["refinement_create_manifest_sha256"]

    snap_child = rebuild_task_state(store, out["refinement_task_id"])
    assert TaskState(str(snap_child["state"])) is TaskState.VERIFIED


def test_refinement_depth_limit_exceeded(tmp_path: Path):
    store = FSStore(str(tmp_path / "events"))
    evidence_root = str(tmp_path / "evidence")
    parent_task_id = "refine::refine::refine::t_base_1::" + "b"*64

    _emit_completed_with_run_summary(tmp_path, store, parent_task_id)
    snap0 = rebuild_task_state(store, parent_task_id)
    assert TaskState(str(snap0["state"])) is TaskState.EVALUATED

    with pytest.raises(RuntimeError) as ei:
        create_refinement_task_from_parent(store=store, evidence_root=evidence_root, parent_task_id=parent_task_id)
    assert str(ei.value) == "refinement_depth_exceeded"


def test_router_refinement_duplicate_note(tmp_path: Path):
    store = FSStore(str(tmp_path / "events"))
    evidence_root = str(tmp_path / "evidence")
    parent_task_id = "t_parent_dup_note"

    _emit_completed_with_run_summary(tmp_path, store, parent_task_id)
    snap_parent = rebuild_task_state(store, parent_task_id)
    assert TaskState(str(snap_parent["state"])) is TaskState.EVALUATED

    router = ExecutionRouter(store)
    out1 = create_refinement_task_from_parent(store=store, evidence_root=evidence_root, parent_task_id=parent_task_id)
    child1_id = out1["refinement_task_id"]
    
    task1 = Task(task_id=child1_id, state=None, role="envoy", action="deterministic_local_execution", payload={}, attempt=0)
    res1 = router.route(task1)
    assert isinstance(res1, RouteResult)

    with pytest.raises(RuntimeError) as ei:
        create_refinement_task_from_parent(store=store, evidence_root=evidence_root, parent_task_id=parent_task_id)
    assert str(ei.value) == "duplicate_refinement_note"

def test_router_refinement_depth_limit(tmp_path: Path):
    store = FSStore(str(tmp_path / "events"))
    parent_task_id = "base1"
    max_depth = 3

    evidence_root = _emit_completed_with_run_summary(tmp_path, store, parent_task_id)
    snap_parent = rebuild_task_state(store, parent_task_id)
    assert TaskState(str(snap_parent["state"])) is TaskState.EVALUATED

    previous_id = parent_task_id
    for i in range(max_depth):
        # Create child refinement
        out = create_refinement_task_from_parent(
            store=store,
            evidence_root=evidence_root,
            parent_task_id=previous_id
        )
        # Advance the new child to EVALUATED
        _advance_to_evaluated(tmp_path, store, out["refinement_task_id"], evidence_root)
        previous_id = out["refinement_task_id"]

    # Attempt one more refinement beyond max depth → should raise
    with pytest.raises(RuntimeError) as ei:
        create_refinement_task_from_parent(store=store, evidence_root=evidence_root, parent_task_id=previous_id)
    assert str(ei.value) == "refinement_depth_exceeded"

