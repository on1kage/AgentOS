import tempfile

from agentos.plan import Plan, PlanStep
from agentos.plan_runner import PlanRunner
from agentos.store_fs import FSStore


def test_plan_runner_fails_closed_when_plan_verification_denies():
    with tempfile.TemporaryDirectory() as tmp:
        store = FSStore(root=tmp)

        plan = Plan(
            plan_id="p_deny",
            steps=[
                PlanStep(step_id="s1", role="morpheus", action="architecture", task_id="t_deny_1"),
                PlanStep(step_id="s2", role="morpheus", action="network_calls", task_id="t_deny_2"),
            ],
        )

        ims = "d" * 64

        payloads = {
            "t_deny_1": {
                "exec_id": "exec_deny_1",
                "kind": "shell",
                "cmd_argv": ["python3", "-c", "print('ok')"],
                "cwd": tmp,
                "env_allowlist": [],
                "timeout_s": 5,
                "inputs_manifest_sha256": ims,
                "paths_allowlist": [tmp],
                "note": "deny step 1",
            },
            "t_deny_2": {
                "exec_id": "exec_deny_2",
                "kind": "shell",
                "cmd_argv": ["python3", "-c", "print('no')"],
                "cwd": tmp,
                "env_allowlist": [],
                "timeout_s": 5,
                "inputs_manifest_sha256": ims,
                "paths_allowlist": [tmp],
                "note": "deny step 2",
            },
        }

        pr = PlanRunner(store, evidence_root="evidence")
        res = pr.run(plan, payloads_by_task_id=payloads)

        assert res.ok is False
        assert res.plan_verification_ok is False
        assert res.steps == []
        assert res.plan_manifest_sha256 is not None and len(res.plan_manifest_sha256) == 64
