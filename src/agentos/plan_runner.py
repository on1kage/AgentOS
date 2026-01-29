from __future__ import annotations
import re
HEX64 = re.compile(r'^[0-9a-f]{64}$')
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from agentos.evidence_plan import PlanEvidenceBundle
from agentos.pipeline import Step as PolicyStep
from agentos.pipeline import verify_plan, verify_task
from agentos.router import ExecutionRouter, RouteResult
from agentos.runner import RunSummary, TaskRunner
from agentos.store_fs import FSStore
from agentos.task import Task, TaskState
from agentos.plan import Plan, require_payload_map
def _require_intent_compilation_manifest(payload: dict) -> str:
    v = payload.get('intent_compilation_manifest_sha256')
    if not isinstance(v, str) or not HEX64.fullmatch(v):
        raise ValueError('missing_or_invalid_intent_compilation_manifest_sha256')
    return v
@dataclass(frozen=True)
class PlanStepResult:
    step_id: str
    task_id: str
    role: str
    action: str
    verified_ok: bool
    verified_reason: str
    routed_ok: Optional[bool]
    routed_reason: Optional[str]
    run_ok: Optional[bool]
    run_exit_code: Optional[int]
    run_exec_id: Optional[str]
    run_evidence_manifest_sha256: Optional[str]
    def to_obj(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "role": self.role,
            "routed_ok": self.routed_ok,
            "routed_reason": self.routed_reason,
            "run_evidence_manifest_sha256": self.run_evidence_manifest_sha256,
            "run_exec_id": self.run_exec_id,
            "run_exit_code": self.run_exit_code,
            "run_ok": self.run_ok,
            "step_id": self.step_id,
            "task_id": self.task_id,
            "verified_ok": self.verified_ok,
            "verified_reason": self.verified_reason,
        }
@dataclass(frozen=True)
class PlanRunResult:
    ok: bool
    plan_id: str
    plan_spec_sha256: str
    plan_verification_ok: bool
    plan_verification_bundle_dir: str
    plan_verification_manifest_sha256: str
    steps: List[PlanStepResult]
    plan_bundle_dir: str
    plan_manifest_sha256: str
    def to_obj(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "plan_id": self.plan_id,
            "plan_spec_sha256": self.plan_spec_sha256,
            "plan_verification_ok": self.plan_verification_ok,
            "plan_verification_bundle_dir": self.plan_verification_bundle_dir,
            "plan_verification_manifest_sha256": self.plan_verification_manifest_sha256,
            "steps": [s.to_obj() for s in self.steps],
            "plan_bundle_dir": self.plan_bundle_dir,
            "plan_manifest_sha256": self.plan_manifest_sha256,
        }
class PlanRunner:
    def __init__(self, store: FSStore, *, evidence_root: str = "evidence") -> None:
        self.store = store
        self.router = ExecutionRouter(store)
        self.runner = TaskRunner(store, evidence_root=evidence_root)
        self.plan_evidence = PlanEvidenceBundle(evidence_root)
    def run(self, plan: Plan, *, payloads_by_task_id: Dict[str, Any]) -> PlanRunResult:
        payloads = require_payload_map(payloads_by_task_id)
        for st in plan.steps:
            p = payloads.get(st.task_id)
            if p is None:
                continue
            _require_intent_compilation_manifest(p)
        policy_steps = [PolicyStep(role=s.role, action=s.action) for s in plan.steps]
        pvr = verify_plan(policy_steps, evidence_root=str(self.store.root / "evidence"))
        plan_spec_sha = plan.spec_sha256()
        step_results: List[PlanStepResult] = []
        if not pvr.ok:
            payload: Dict[str, Any] = {
                "plan_id": plan.plan_id,
                "plan_spec_sha256": plan_spec_sha,
                "plan_verification_ok": bool(pvr.ok),
                "plan_verification_bundle_dir": pvr.verification_bundle_dir,
                "plan_verification_manifest_sha256": pvr.verification_manifest_sha256,
                "steps": [],
                "ok": False,
            }
            pe = self.plan_evidence.write_plan_bundle(plan_spec_sha256=plan_spec_sha, payload=payload)
            return PlanRunResult(
                ok=False,
                plan_id=plan.plan_id,
                plan_spec_sha256=plan_spec_sha,
                plan_verification_ok=bool(pvr.ok),
                plan_verification_bundle_dir=str(pvr.verification_bundle_dir),
                plan_verification_manifest_sha256=str(pvr.verification_manifest_sha256),
                steps=[],
                plan_bundle_dir=str(pe["bundle_dir"]),
                plan_manifest_sha256=str(pe["manifest_sha256"]),
            )
        overall_ok = True
        for s in plan.steps:
            payload = payloads.get(s.task_id)
            if payload is None:
                sr = PlanStepResult(
                    step_id=s.step_id,
                    task_id=s.task_id,
                    role=s.role,
                    action=s.action,
                    verified_ok=False,
                    verified_reason="missing_payload_for_task_id",
                    routed_ok=None,
                    routed_reason=None,
                    run_ok=None,
                    run_exit_code=None,
                    run_exec_id=None,
                    run_evidence_manifest_sha256=None,
                )
                step_results.append(sr)
                overall_ok = False
                break
            task = Task(
                task_id=s.task_id,
                state=TaskState.CREATED,
                role=s.role,
                action=s.action,
                payload=dict(payload),
                attempt=0,
            )
            vres = verify_task(self.store, task)
            if not vres.ok:
                sr = PlanStepResult(
                    step_id=s.step_id,
                    task_id=s.task_id,
                    role=s.role,
                    action=s.action,
                    verified_ok=False,
                    verified_reason=vres.reason,
                    routed_ok=None,
                    routed_reason=None,
                    run_ok=None,
                    run_exit_code=None,
                    run_exec_id=None,
                    run_evidence_manifest_sha256=vres.verification_manifest_sha256,
                )
                step_results.append(sr)
                overall_ok = False
                break
            routed: RouteResult = self.router.route(task)
            if not routed.ok:
                sr = PlanStepResult(
                    step_id=s.step_id,
                    task_id=s.task_id,
                    role=s.role,
                    action=s.action,
                    verified_ok=True,
                    verified_reason=vres.reason,
                    routed_ok=False,
                    routed_reason=routed.reason,
                    run_ok=None,
                    run_exit_code=None,
                    run_exec_id=None,
                    run_evidence_manifest_sha256=vres.verification_manifest_sha256,
                )
                step_results.append(sr)
                overall_ok = False
                break
            run_summary: RunSummary = self.runner.run_dispatched(task.task_id)
            sr = PlanStepResult(
                step_id=s.step_id,
                task_id=s.task_id,
                role=s.role,
                action=s.action,
                verified_ok=True,
                verified_reason=vres.reason,
                routed_ok=True,
                routed_reason=routed.reason,
                run_ok=run_summary.ok,
                run_exit_code=run_summary.exit_code,
                run_exec_id=run_summary.exec_id,
                run_evidence_manifest_sha256=run_summary.evidence_manifest_sha256,
            )
            step_results.append(sr)
            if not run_summary.ok:
                overall_ok = False
                break
        payload: Dict[str, Any] = {
            "plan_id": plan.plan_id,
            "plan_spec_sha256": plan_spec_sha,
            "plan_verification_ok": bool(pvr.ok),
            "plan_verification_bundle_dir": pvr.verification_bundle_dir,
            "plan_verification_manifest_sha256": pvr.verification_manifest_sha256,
            "steps": [sr.to_obj() for sr in step_results],
            "ok": bool(overall_ok),
        }
        pe = self.plan_evidence.write_plan_bundle(plan_spec_sha256=plan_spec_sha, payload=payload)
        return PlanRunResult(
            ok=bool(overall_ok),
            plan_id=plan.plan_id,
            plan_spec_sha256=plan_spec_sha,
            plan_verification_ok=bool(pvr.ok),
            plan_verification_bundle_dir=str(pvr.verification_bundle_dir),
            plan_verification_manifest_sha256=str(pvr.verification_manifest_sha256),
            steps=step_results,
            plan_bundle_dir=str(pe["bundle_dir"]),
            plan_manifest_sha256=str(pe["manifest_sha256"]),
        )
