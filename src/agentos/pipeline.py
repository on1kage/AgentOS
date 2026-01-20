from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from agentos.evidence import EvidenceBundle
from agentos.canonical import sha256_hex, canonical_json
from agentos.policy import decide
from agentos.store_fs import FSStore, EventRef
from agentos.task import Task

@dataclass(frozen=True)
class Step:
    role: str
    action: str

@dataclass(frozen=True)
class PipelineResult:
    ok: bool
    decisions: List[dict]
    verification_bundle_dir: str | None = None
    verification_manifest_sha256: str | None = None

    def to_canonical_json(self) -> str:
        payload = {
            "ok": self.ok,
            "decisions": self.decisions,
            "verification_bundle_dir": self.verification_bundle_dir,
            "verification_manifest_sha256": self.verification_manifest_sha256,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

@dataclass(frozen=True)
class TaskVerifyResult:
    ok: bool
    reason: str
    task_id: str
    created_event: Optional[EventRef]
    decision_event: Optional[EventRef]
    verification_bundle_dir: str | None = None
    verification_manifest_sha256: str | None = None

    def to_canonical_json(self) -> str:
        payload: Dict[str, Any] = {
            "ok": self.ok,
            "reason": self.reason,
            "task_id": self.task_id,
            "created_event": None if self.created_event is None else self.created_event.__dict__,
            "decision_event": None if self.decision_event is None else self.decision_event.__dict__,
            "verification_bundle_dir": self.verification_bundle_dir,
            "verification_manifest_sha256": self.verification_manifest_sha256,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

def verify_plan(steps: List[Step]) -> PipelineResult:
    decisions: List[dict] = []
    ok = True
    for i, s in enumerate(steps):
        d = decide(s.role, s.action)
        decisions.append({
            "i": i,
            "role": s.role,
            "action": s.action,
            "allow": d.allow,
            "reason": d.reason,
        })
        if not d.allow:
            ok = False

    per_step: Dict[str, Any] = {str(row['i']): row for row in decisions}
    plan_bytes = canonical_json([{'role': s.role, 'action': s.action} for s in steps]).encode('utf-8')
    plan_spec_sha256 = sha256_hex(plan_bytes)
    bundle = EvidenceBundle().write_verification_bundle(
        spec_sha256=plan_spec_sha256,
        decisions=per_step,
        reason='plan_verification',
        idempotency_key=None,
    )
    return PipelineResult(
        ok=ok,
        decisions=decisions,
        verification_bundle_dir=bundle["bundle_dir"],
        verification_manifest_sha256=bundle["manifest_sha256"]
    )

def verify_task(store: FSStore, task: Task) -> TaskVerifyResult:
    created_ref: Optional[EventRef] = None
    decision_ref: Optional[EventRef] = None

    prior = store.list_events(task.task_id)
    if len(prior) == 0:
        created_ref = store.append_event(
            task.task_id,
            'TASK_CREATED',
            {
                'role': task.role,
                'action': task.action,
                'payload': task.payload,
                'attempt': task.attempt,
            },
        )

    d = decide(task.role, task.action)

    ims = task.payload.get('inputs_manifest_sha256')
    if not isinstance(ims, str) or not re.fullmatch(r'[0-9a-f]{64}', ims):
        bad_reason = 'missing_or_invalid_inputs_manifest_sha256'
        fail_spec = sha256_hex(canonical_json({'task_id': task.task_id, 'attempt': task.attempt}).encode('utf-8'))
        bundle = EvidenceBundle().write_verification_bundle(
            spec_sha256=fail_spec,
            decisions={'role': task.role, 'action': task.action, 'allow': False, 'reason': bad_reason},
            reason='task_verification',
            idempotency_key=None,
        )
        decision_ref = store.append_event(
            task.task_id,
            'TASK_REJECTED',
            {
                'role': task.role,
                'action': task.action,
                'reason': bad_reason,
                'attempt': task.attempt,
            },
        )
        return TaskVerifyResult(
            ok=False,
            reason=bad_reason,
            task_id=task.task_id,
            created_event=created_ref,
            decision_event=decision_ref,
            verification_bundle_dir=bundle['bundle_dir'],
            verification_manifest_sha256=bundle['manifest_sha256'],
        )

    bundle = EvidenceBundle().write_verification_bundle(
        spec_sha256=ims,
        decisions={'role': task.role, 'action': task.action, 'allow': d.allow, 'reason': d.reason},
        reason='task_verification',
        idempotency_key=None,
    )

    if d.allow:
        decision_ref = store.append_event(
            task.task_id,
            'TASK_VERIFIED',
            {
                'role': task.role,
                'action': task.action,
                'reason': d.reason,
                'attempt': task.attempt,
            },
        )
        return TaskVerifyResult(
            ok=True,
            reason=d.reason,
            task_id=task.task_id,
            created_event=created_ref,
            decision_event=decision_ref,
            verification_bundle_dir=bundle['bundle_dir'],
            verification_manifest_sha256=bundle['manifest_sha256'],
        )

    decision_ref = store.append_event(
        task.task_id,
        'TASK_REJECTED',
        {
            'role': task.role,
            'action': task.action,
            'reason': d.reason,
            'attempt': task.attempt,
        },
    )
    return TaskVerifyResult(
        ok=False,
        reason=d.reason,
        task_id=task.task_id,
        created_event=created_ref,
        decision_event=decision_ref,
        verification_bundle_dir=bundle['bundle_dir'],
        verification_manifest_sha256=bundle['manifest_sha256'],
    )
