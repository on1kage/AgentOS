import json
from pathlib import Path

from agentos.store_fs import FSStore
from agentos.evaluation import evaluate_task
from agentos.task import TaskState
from agentos.fsm import rebuild_task_state

def test_evaluate_task_appends_event_and_writes_bundle(tmp_path):
    store_root = tmp_path / 'store'
    ev_root = tmp_path / 'evidence'
    store = FSStore(str(store_root))
    task_id = 't_eval_1'
    exec_id = 'e1'

    store.append_event(task_id, 'TASK_CREATED', {'role':'envoy','action':'weekly_proof','attempt':0})
    store.append_event(task_id, 'TASK_VERIFIED', {'role':'envoy','action':'weekly_proof','inputs_manifest_sha256':'x','attempt':0})
    store.append_event(task_id, 'TASK_DISPATCHED', {'role':'envoy','action':'weekly_proof','attempt':0,'inputs_manifest_sha256':'x'})
    store.append_event(task_id, 'RUN_STARTED', {'exec_id':exec_id,'spec_sha256':'a'*64,'inputs_manifest_sha256':'x','kind':'shell'})
    store.append_event(task_id, 'RUN_SUCCEEDED', {'exec_id':exec_id,'spec_sha256':'a'*64,'exit_code':0,'stdout_sha256':'b'*64,'stderr_sha256':'c'*64,'outputs_manifest_sha256':'d'*64})

    bundle_dir = ev_root / task_id / exec_id
    bundle_dir.mkdir(parents=True, exist_ok=True)
    run_summary = {'schema_version':'agentos-run-summary/v1','task_id':task_id,'exec_id':exec_id,'outcome':'SUCCEEDED','reason':'ok','idempotency_key':None,'spec_sha256':'a'*64,'inputs_manifest_sha256':'x','manifest_sha256':'e'*64}
    (bundle_dir / 'run_summary.json').write_text(json.dumps(run_summary), encoding='utf-8')

    snap0 = rebuild_task_state(store, task_id)
    assert TaskState(str(snap0['state'])) is TaskState.COMPLETED

    res = evaluate_task(store=store, evidence_root=str(ev_root), task_id=task_id, decision='accept', note='ok')
    assert 'evaluation_spec_sha256' in res
    assert 'evaluation_manifest_sha256' in res

    snap1 = rebuild_task_state(store, task_id)
    assert TaskState(str(snap1['state'])) is TaskState.EVALUATED

    vpath = ev_root / 'verify' / res['evaluation_spec_sha256'] / 'manifest.sha256.json'
    assert vpath.exists()
