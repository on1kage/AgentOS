import tempfile

from agentos.plan import Plan, PlanStep
from agentos.plan_runner import PlanRunner
from agentos.store_fs import FSStore


def test_plan_runner_happy_path_two_steps():
    with tempfile.TemporaryDirectory() as tmp:
        store = FSStore(root=tmp)

        plan = Plan(
            plan_id="p1",
            steps=[
                PlanStep(step_id="s1", role="morpheus", action="architecture", task_id="t_plan_1"),
                PlanStep(step_id="s2", role="envoy", action="deterministic_local_execution", task_id="t_plan_2"),
            ],
        )

        ims = "c" * 64

        payloads = {
            "t_plan_1": {
                "exec_id": "exec_plan_1",
                "kind": "shell",
                "cmd_argv": ["python3", "-c", "print('ok1')"],
                "cwd": tmp,
                "env_allowlist": [],
                "timeout_s": 5,
                "inputs_manifest_sha256": ims,
                "paths_allowlist": [tmp],
                "note": "plan step 1",
            },
            "t_plan_2": {
                "exec_id": "exec_plan_2",
                "kind": "shell",
                "cmd_argv": ["python3", "-c", "print('ok2')"],
                "cwd": tmp,
                "env_allowlist": [],
                "timeout_s": 5,
                "inputs_manifest_sha256": ims,
                "paths_allowlist": [tmp],
                "note": "plan step 2",
            },
        }

        pr = PlanRunner(store, evidence_root="evidence")

        res = pr.run(plan, payloads_by_task_id=payloads)
        assert res.ok is True
        assert res.plan_verification_ok is True
        assert len(res.steps) == 2
        assert all(s.run_ok for s in res.steps)
        assert res.plan_manifest_sha256 is not None and len(res.plan_manifest_sha256) == 64
