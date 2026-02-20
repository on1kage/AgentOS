from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from agentos.adapter_role_contract_checker import contract_sha256
from agentos.canonical import canonical_json, sha256_hex
from agentos.evidence import EvidenceBundle
from agentos.pipeline import verify_task
from agentos.store_fs import FSStore
from agentos.task import Task, TaskState


def _latest_task_evaluated_event(store: FSStore, task_id: str) -> Dict[str, Any]:
    events = list(store.list_events(task_id))
    for e in reversed(events):
        if str(e.get("type")) == "TASK_EVALUATED":
            return dict(e)
    raise RuntimeError("no_task_evaluated_event")


def _load_created_event(store: FSStore, task_id: str) -> Dict[str, Any]:
    events = list(store.list_events(task_id))
    for e in events:
        if str(e.get("type")) == "TASK_CREATED":
            return dict(e)
    raise RuntimeError("missing_task_created_event")


def _load_verified_event(store: FSStore, task_id: str) -> Dict[str, Any]:
    events = list(store.list_events(task_id))
    for e in reversed(events):
        if str(e.get("type")) == "TASK_VERIFIED":
            return dict(e)
    raise RuntimeError("missing_task_verified_event")


def _latest_run_succeeded_event(store: FSStore, task_id: str) -> Dict[str, Any]:
    events = list(store.list_events(task_id))
    for e in reversed(events):
        if str(e.get("type")) == "RUN_SUCCEEDED":
            return dict(e)
    raise RuntimeError("no_run_succeeded_event")


def _load_run_summary(evidence_root: str, task_id: str, exec_id: str) -> Dict[str, Any]:
    p = Path(evidence_root) / task_id / exec_id / "run_summary.json"
    if not p.exists():
        raise FileNotFoundError(str(p))
    return json.loads(p.read_text(encoding="utf-8"))


def create_refinement_task_from_parent(
    *, store: FSStore, evidence_root: str, parent_task_id: str
) -> Dict[str, str]:
    ev = _latest_task_evaluated_event(store, parent_task_id)
    body = dict(ev.get("body") or {})
    decision = body.get("decision")
    if decision != "refine":
        raise RuntimeError("parent_not_refine")

    note = body.get("note")
    if not isinstance(note, str) or not note.strip():
        raise RuntimeError("refinement_requires_non_empty_note")

    refinement_task_id = body.get("refinement_task_id")
    if not isinstance(refinement_task_id, str) or not refinement_task_id:
        raise RuntimeError("missing_refinement_task_id")

    run_spec_sha256 = body.get("run_spec_sha256")
    if not isinstance(run_spec_sha256, str) or not run_spec_sha256:
        raise RuntimeError("missing_parent_run_spec_sha256")

    expected = f"refine::{parent_task_id}::{run_spec_sha256}"

    # Prevent duplicate refinement with identical note hash
    note_hash = sha256_hex(note.strip().encode("utf-8"))
    prefix = f"refine::{parent_task_id}::"
    for entry in store.root.joinpath("events").glob(f"{prefix}*"):
        rid = entry.name
        events = store.list_events(rid)
        for ev2 in events:
            if str(ev2.get("type")) == "TASK_CREATED":
                body2 = dict(ev2.get("body") or {})
                payload2 = body2.get("payload") or {}
                if payload2.get("lineage_refinement_note_sha256") == note_hash:
                    raise RuntimeError("duplicate_refinement_note")
    if refinement_task_id != expected:
        raise RuntimeError("refinement_task_id_mismatch")

    created_ev = _load_created_event(store, parent_task_id)
    created_body = dict(created_ev.get("body") or {})
    role = created_body.get("role")
    action = created_body.get("action")
    payload = created_body.get("payload")

    if not isinstance(role, str) or not role:
        raise RuntimeError("parent_created_missing_role")
    if not isinstance(action, str) or not action:
        raise RuntimeError("parent_created_missing_action")
    if not isinstance(payload, dict):
        raise RuntimeError("parent_created_missing_payload")

    verified_ev = _load_verified_event(store, parent_task_id)
    verified_body = dict(verified_ev.get("body") or {})
    ims = verified_body.get("inputs_manifest_sha256")
    if not isinstance(ims, str) or not ims:
        raise RuntimeError("parent_verified_missing_inputs_manifest_sha256")

    run_ev = _latest_run_succeeded_event(store, parent_task_id)
    run_body = dict(run_ev.get("body") or {})
    exec_id = run_body.get("exec_id")
    parent_run_spec_sha256 = run_body.get("spec_sha256")
    if not isinstance(exec_id, str) or not exec_id:
        raise RuntimeError("parent_run_missing_exec_id")
    if not isinstance(parent_run_spec_sha256, str) or not parent_run_spec_sha256:
        raise RuntimeError("parent_run_missing_spec_sha256")

    rs = _load_run_summary(evidence_root, parent_task_id, exec_id)
    parent_run_manifest_sha256 = rs.get("manifest_sha256")
    if not isinstance(parent_run_manifest_sha256, str) or not parent_run_manifest_sha256:
        raise RuntimeError("parent_run_summary_missing_manifest_sha256")

    eval_spec_sha256 = body.get("evaluation_spec_sha256")
    if not isinstance(eval_spec_sha256, str) or not eval_spec_sha256:
        raise RuntimeError("missing_parent_evaluation_spec_sha256")

    new_payload = dict(payload)
    new_payload["inputs_manifest_sha256"] = ims
    new_payload["lineage_parent_task_id"] = parent_task_id
    new_payload["lineage_parent_exec_id"] = exec_id
    new_payload["lineage_parent_run_spec_sha256"] = parent_run_spec_sha256
    new_payload["lineage_parent_run_manifest_sha256"] = parent_run_manifest_sha256
    new_payload["lineage_parent_evaluation_spec_sha256"] = eval_spec_sha256
    new_payload["lineage_refinement_task_id"] = refinement_task_id
    new_payload["lineage_refinement_note"] = note
    new_payload["lineage_refinement_note_sha256"] = sha256_hex(note.strip().encode("utf-8"))
    new_payload["lineage_adapter_role_contract_sha256"] = contract_sha256()

    spec_obj = {
        "refinement_task_id": refinement_task_id,
        "parent_task_id": parent_task_id,
        "parent_exec_id": exec_id,
        "parent_run_spec_sha256": parent_run_spec_sha256,
        "parent_run_manifest_sha256": parent_run_manifest_sha256,
        "parent_evaluation_spec_sha256": eval_spec_sha256,
        "refinement_note_sha256": sha256_hex(note.strip().encode("utf-8")),
        "adapter_role_contract_sha256": contract_sha256(),
        "role": role,
        "action": action,
        "inputs_manifest_sha256": ims,
    }
    spec_sha256 = sha256_hex(canonical_json(spec_obj).encode("utf-8"))
    bundle = EvidenceBundle(root=evidence_root).write_verification_bundle(
        spec_sha256=spec_sha256,
        decisions=spec_obj,
        reason="refinement_task_created",
        idempotency_key=refinement_task_id,
    )

    task = Task(
        task_id=refinement_task_id,
        state=TaskState.CREATED,
        role=role,
        action=action,
        payload=new_payload,
        attempt=0,
    )
    verify_res = verify_task(store, task)
    if not verify_res.ok:
        raise RuntimeError(f"refinement_task_verify_failed:{verify_res.reason}")

    return {
        "refinement_task_id": refinement_task_id,
        "refinement_create_spec_sha256": spec_sha256,
        "refinement_create_manifest_sha256": str(bundle.get("manifest_sha256") or ""),
    }
