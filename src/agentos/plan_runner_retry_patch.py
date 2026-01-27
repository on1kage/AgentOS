from __future__ import annotations

import re

HEX64 = re.compile(r'^[0-9a-f]{64}$')

from dataclasses import replace
from typing import Any, Dict, List, Optional

from agentos.pipeline import Step as PolicyStep
from agentos.pipeline import verify_plan, verify_task
from agentos.plan import Plan, require_payload_map

def _require_intent_compilation_manifest(payload: dict) -> str:
    v = payload.get('intent_compilation_manifest_sha256')
    if not isinstance(v, str) or not HEX64.fullmatch(v):
        raise ValueError('missing_or_invalid_intent_compilation_manifest_sha256')
    return v
from agentos.plan_runner import PlanRunner, PlanRunResult, PlanStepResult
from agentos.task import Task, TaskState


def _derive_retry_id(base: str, attempt: int) -> str:
    return f"{base}__a{attempt}"


class PlanRunnerRetry(PlanRunner):
    def run(
        self,
        plan: Plan,
        payloads_by_task_id: Dict[str, Any],
        retry_attempts: int = 3,
        partial_continue: bool = True,
    ) -> PlanRunResult:
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
            base_payload = payloads.get(s.task_id)
            if base_payload is None:
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
                if not partial_continue:
                    break
                continue

            attempt_ok = False
            last_sr: Optional[PlanStepResult] = None

            for attempt in range(int(retry_attempts)):
                retry_task_id = _derive_retry_id(s.task_id, attempt)
                retry_exec_id = _derive_retry_id(str(base_payload.get("exec_id", "exec")), attempt)

                payload = dict(base_payload)
                payload["exec_id"] = retry_exec_id

                task = Task(
                    task_id=retry_task_id,
                    state=TaskState.CREATED,
                    role=s.role,
                    action=s.action,
                    payload=dict(payload),
                    attempt=int(attempt),
                )

                vres = verify_task(self.store, task)
                if not vres.ok:
                    last_sr = PlanStepResult(
                        step_id=s.step_id,
                        task_id=retry_task_id,
                        role=s.role,
                        action=s.action,
                        verified_ok=False,
                        verified_reason=vres.reason,
                        routed_ok=None,
                        routed_reason=None,
                        run_ok=False,
                        run_exit_code=None,
                        run_exec_id=retry_exec_id,
                        run_evidence_manifest_sha256=vres.verification_manifest_sha256,
                    )
                    step_results.append(last_sr)
                    continue

                routed = self.router.route(task)
                if not routed.ok:
                    last_sr = PlanStepResult(
                        step_id=s.step_id,
                        task_id=retry_task_id,
                        role=s.role,
                        action=s.action,
                        verified_ok=True,
                        verified_reason=vres.reason,
                        routed_ok=False,
                        routed_reason=routed.reason,
                        run_ok=False,
                        run_exit_code=None,
                        run_exec_id=retry_exec_id,
                        run_evidence_manifest_sha256=vres.verification_manifest_sha256,
                    )
                    step_results.append(last_sr)
                    continue

                run_summary = self.runner.run_dispatched(task.task_id)

                last_sr = PlanStepResult(
                    step_id=s.step_id,
                    task_id=retry_task_id,
                    role=s.role,
                    action=s.action,
                    verified_ok=True,
                    verified_reason=vres.reason,
                    routed_ok=True,
                    routed_reason=routed.reason,
                    run_ok=bool(run_summary.ok),
                    run_exit_code=run_summary.exit_code,
                    run_exec_id=run_summary.exec_id,
                    run_evidence_manifest_sha256=run_summary.evidence_manifest_sha256,
                )
                step_results.append(last_sr)

                if run_summary.ok:
                    attempt_ok = True
                    break

            if not attempt_ok:
                overall_ok = False
                if not partial_continue:
                    break

        payload_out: Dict[str, Any] = {
            "plan_id": plan.plan_id,
            "plan_spec_sha256": plan_spec_sha,
            "plan_verification_ok": bool(pvr.ok),
            "plan_verification_bundle_dir": pvr.verification_bundle_dir,
            "plan_verification_manifest_sha256": pvr.verification_manifest_sha256,
            "steps": [sr.to_obj() for sr in step_results],
            "ok": bool(overall_ok),
        }

        pe = self.plan_evidence.write_plan_bundle(plan_spec_sha256=plan_spec_sha, payload=payload_out)

        res = PlanRunResult(
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
        return replace(res, steps=step_results, ok=bool(overall_ok))
