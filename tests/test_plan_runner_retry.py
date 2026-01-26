import hashlib
import tempfile
import uuid
from pathlib import Path

from agentos.plan import Plan, PlanStep
from agentos.plan_runner_retry_patch import PlanRunnerRetry
from agentos.store_fs import FSStore


def _sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def test_plan_runner_retry_failure_is_stable():
    with tempfile.TemporaryDirectory() as tmp:
        store_root = str(Path(tmp) / "store")
        store = FSStore(root=store_root)

        plan_id = f"p_{uuid.uuid4().hex}"
        step_id = f"s_{uuid.uuid4().hex}"
        task_id = f"t_{uuid.uuid4().hex}"
        exec_id = f"exec_{uuid.uuid4().hex}"

        plan = Plan(
            plan_id=plan_id,
            steps=[
                PlanStep(
                    step_id=step_id,
                    role="envoy",
                    action="deterministic_local_execution",
                    task_id=task_id,
                )
            ],
        )

        ims = _sha256_hex(uuid.uuid4().bytes)

        payloads = {
            task_id: {
                "exec_id": exec_id,
                "kind": "shell",
                "cmd_argv": ["python3", "-c", "import sys; sys.exit(1)"],
                "cwd": tmp,
                "env_allowlist": [],
                "timeout_s": 1,
                "inputs_manifest_sha256": ims,
                "paths_allowlist": [tmp],
                "note": "retry test",
            }
        }

        evidence_root = str(Path(tmp) / "evidence")
        pr = PlanRunnerRetry(store, evidence_root=evidence_root)

        res = pr.run(plan, payloads_by_task_id=payloads, retry_attempts=3, partial_continue=True)
        assert res.ok is False
        assert len(res.steps) >= 1
        assert all(s.run_ok is False for s in res.steps)
