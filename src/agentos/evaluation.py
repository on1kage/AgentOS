from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from agentos.canonical import canonical_json, sha256_hex
from agentos.adapter_role_contract_checker import contract_sha256
from agentos.fsm import rebuild_task_state
from agentos.task import TaskState
from agentos.evidence import EvidenceBundle
from agentos.store_fs import FSStore

def _latest_run_succeeded_event(store: FSStore, task_id: str) -> Dict[str, Any]:
    events = list(store.list_events(task_id))
    for e in reversed(events):
        if str(e.get('type')) == 'RUN_SUCCEEDED':
            return dict(e)
    raise RuntimeError('no_run_succeeded_event')

def _load_run_summary(evidence_root: str, task_id: str, exec_id: str) -> Dict[str, Any]:
    p = Path(evidence_root) / task_id / exec_id / 'run_summary.json'
    if not p.exists():
        raise FileNotFoundError(str(p))
    return json.loads(p.read_text(encoding='utf-8'))

def evaluate_task(
    *, store: FSStore, evidence_root: str, task_id: str, decision: str, note: Optional[str] = None
) -> Dict[str, str]:
    if decision not in ('accept', 'refine'):
        raise ValueError('decision must be accept or refine')
    snap = rebuild_task_state(store, task_id)
    derived_state = TaskState(str(snap['state']))
    if derived_state is not TaskState.COMPLETED:
        raise RuntimeError(f'invalid_state_for_evaluation:{derived_state.value}')

    run_ev = _latest_run_succeeded_event(store, task_id)
    body = dict(run_ev.get('body') or {})
    exec_id = str(body.get('exec_id') or '')
    run_spec_sha256 = str(body.get('spec_sha256') or '')
    if not exec_id or not run_spec_sha256:
        raise RuntimeError('run_event_missing_fields')

    rs = _load_run_summary(evidence_root, task_id, exec_id)
    run_manifest_sha256 = str(rs.get('manifest_sha256') or '')
    if not run_manifest_sha256:
        raise RuntimeError('run_summary_missing_manifest_sha256')

    eval_spec_obj = {
        'task_id': task_id,
        'exec_id': exec_id,
        'run_spec_sha256': run_spec_sha256,
        'run_manifest_sha256': run_manifest_sha256,
        'adapter_role_contract_sha256': contract_sha256(),
        'decision': decision,
        'note': note,
    }
    eval_spec_sha256 = sha256_hex(canonical_json(eval_spec_obj).encode('utf-8'))

    bundle = EvidenceBundle(root=evidence_root).write_verification_bundle(
        spec_sha256=eval_spec_sha256,
        decisions=eval_spec_obj,
        reason='task_evaluation',
        idempotency_key=None,
    )

    store.append_event(
        task_id,
        'TASK_EVALUATED',
        {
            'decision': decision,
            'note': note,
            'exec_id': exec_id,
            'run_spec_sha256': run_spec_sha256,
            'run_manifest_sha256': run_manifest_sha256,
            'evaluation_spec_sha256': eval_spec_sha256,
            'evaluation_manifest_sha256': bundle['manifest_sha256'],
        },
    )

    return {
        'evaluation_spec_sha256': eval_spec_sha256,
        'evaluation_manifest_sha256': bundle['manifest_sha256'],
    }
