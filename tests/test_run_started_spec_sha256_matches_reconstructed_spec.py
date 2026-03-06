import tempfile

from agentos.store_fs import FSStore
from agentos.runner import TaskRunner


def test_run_started_spec_sha256_matches_reconstructed_spec():
    with tempfile.TemporaryDirectory() as tmp:
        store = FSStore(root=tmp)
        task_id = "t_run_started_spec_match_1"
        verified_ims = "b" * 64

        store.append_event(
            task_id,
            "TASK_CREATED",
            {
                "role": "envoy",
                "action": "deterministic_local_execution",
                "payload": {
                    "exec_id": "exec-1",
                    "kind": "shell",
                    "cmd_argv": ["python3", "-c", "print('ok')"],
                    "cwd": tmp,
                    "env_allowlist": [],
                    "timeout_s": 5,
                    "inputs_manifest_sha256": "a" * 64,
                    "paths_allowlist": [tmp],
                    "note": None,
                },
                "attempt": 0,
            },
        )
        store.append_event(
            task_id,
            "TASK_VERIFIED",
            {
                "role": "envoy",
                "action": "deterministic_local_execution",
                "reason": "ok",
                "inputs_manifest_sha256": verified_ims,
                "attempt": 0,
            },
        )
        store.append_event(
            task_id,
            "TASK_DISPATCHED",
            {
                "role": "envoy",
                "action": "deterministic_local_execution",
                "attempt": 0,
                "inputs_manifest_sha256": verified_ims,
            },
        )

        runner = TaskRunner(store, evidence_root="evidence")
        res = runner.run_dispatched(task_id)
        assert res.ok is True

        payload = runner._load_created_payload(task_id)
        role, action = runner._load_created_role_action(task_id)
        payload = dict(payload)
        payload["inputs_manifest_sha256"] = verified_ims
        spec = runner._build_spec(task_id=task_id, role=role, action=action, payload=payload)

        events = store.list_events(task_id)
        rs = [e for e in events if e.get("type") == "RUN_STARTED"]
        assert len(rs) == 1
        body = rs[0].get("body") or {}
        assert body.get("spec_sha256") == spec.spec_sha256()
    