import hashlib
import tempfile
import uuid
from pathlib import Path

from agentos.plan import Plan, PlanStep
from agentos.plan_runner import PlanRunner
from agentos.store_fs import FSStore


def _sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def test_plan_runner_fails_closed_when_missing_intent_compilation_manifest():
    with tempfile.TemporaryDirectory() as tmp:
        store = FSStore(root=tmp)

        plan_id = f"p_{uuid.uuid4().hex}"
        step_id = f"s_{uuid.uuid4().hex}"
        task_id = f"t_{uuid.uuid4().hex}"
        exec_id = f"exec_{uuid.uuid4().hex}"

        plan = Plan(
            plan_id=plan_id,
            steps=[PlanStep(step_id=step_id, role="morpheus", action="architecture", task_id=task_id)],
        )

        ims = _sha256_hex(uuid.uuid4().bytes)

        payloads = {
            task_id: {
                "exec_id": exec_id,
                "kind": "shell",
                "cmd_argv": ["python3", "-c", "print('ok')"],
                "cwd": tmp,
                "env_allowlist": [],
                "timeout_s": 5,
                "inputs_manifest_sha256": ims,
                "paths_allowlist": [tmp],
                "note": "missing compilation manifest",
            }
        }

        evidence_root = str(Path(tmp) / "evidence")
        pr = PlanRunner(store, evidence_root=evidence_root)
        try:
            pr.run(plan, payloads_by_task_id=payloads)
        except ValueError as e:
            assert str(e) == "missing_or_invalid_intent_compilation_manifest_sha256"
            return
        raise AssertionError("expected ValueError")
