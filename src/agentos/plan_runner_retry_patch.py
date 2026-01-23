from agentos.plan_runner import PlanRunner as OrigPlanRunner
Orig_run = OrigPlanRunner.run
def run_with_retry(self, plan, payloads_by_task_id, retry_attempts=1, partial_continue=False):
    step_results = []
    overall_ok = True
    for s in plan.steps:
        attempt = 0
        while attempt < retry_attempts:
            payload = {s.task_id: payloads_by_task_id[s.task_id]}
            res = Orig_run(self, plan, payloads_by_task_id=payload)
            sr = res.steps[0]
            step_results.append(sr)
            if sr.run_ok:
                break
            attempt += 1
            if attempt >= retry_attempts:
                overall_ok = False
                if not partial_continue:
                    return res
    res.steps = step_results
    res.ok = overall_ok
    return res
OrigPlanRunner.run = run_with_retry
