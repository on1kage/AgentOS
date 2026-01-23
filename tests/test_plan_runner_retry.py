from agentos.plan import Plan, PlanStep
from agentos.plan_runner import PlanRunner
from agentos.store_fs import FSStore
def test_plan_runner_retry_success():
    store = FSStore(root="store")
    pr = PlanRunner(store, evidence_root="evidence")
    plan = Plan(plan_id="p_retry", steps=[
        PlanStep(step_id="s1", role="envoy", action="deterministic_local_execution", task_id="t_retry_1")
    ])
    payloads = {
        "t_retry_1":{"exec_id":"exec_retry_1","kind":"shell","cmd_argv":["python3","-c","import sys; sys.exit(1)"],"cwd":".","env_allowlist":[],"timeout_s":1,"inputs_manifest_sha256":"f"*64,"paths_allowlist":["."],"note":"retry test"}
    }
    res = pr.run(plan, payloads_by_task_id=payloads, retry_attempts=3, partial_continue=True)
    assert res.steps[0].run_ok is False
    assert res.ok is False
