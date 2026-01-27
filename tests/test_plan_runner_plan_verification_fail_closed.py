import hashlib
import tempfile
import uuid
from pathlib import Path

from agentos.plan import Plan, PlanStep
from agentos.plan_runner import PlanRunner
from agentos.store_fs import FSStore


def _sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def test_plan_runner_fails_closed_when_plan_verification_denies():
    with tempfile.TemporaryDirectory() as tmp:
        store = FSStore(root=tmp)

        plan_id = f"p_{uuid.uuid4().hex}"
        step_id_1 = f"s_{uuid.uuid4().hex}"
        step_id_2 = f"s_{uuid.uuid4().hex}"
        task_id_1 = f"t_{uuid.uuid4().hex}"
        task_id_2 = f"t_{uuid.uuid4().hex}"
        exec_id_1 = f"exec_{uuid.uuid4().hex}"
        exec_id_2 = f"exec_{uuid.uuid4().hex}"

        plan = Plan(
            plan_id=plan_id,
            steps=[
                PlanStep(step_id=step_id_1, role="morpheus", action="architecture", task_id=task_id_1),
                PlanStep(step_id=step_id_2, role="morpheus", action="network_calls", task_id=task_id_2),
            ],
        )

        ims = _sha256_hex(uuid.uuid4().bytes)

        payloads = {
            task_id_1: {
                "exec_id": exec_id_1,
                "kind": "shell",
                "cmd_argv": ["python3", "-c", "print('ok')"],
                "cwd": tmp,
                "env_allowlist": [],
                "timeout_s": 5,
                "inputs_manifest_sha256": ims,
                  "intent_compilation_manifest_sha256": ims,
                "paths_allowlist": [tmp],
                "note": "deny step 1",
            },
            task_id_2: {
                "exec_id": exec_id_2,
                "kind": "shell",
                "cmd_argv": ["python3", "-c", "print('no')"],
                "cwd": tmp,
                "env_allowlist": [],
                "timeout_s": 5,
                "inputs_manifest_sha256": ims,
                  "intent_compilation_manifest_sha256": ims,
                "paths_allowlist": [tmp],
                "note": "deny step 2",
            },
        }

        evidence_root = str(Path(tmp) / "evidence")
        pr = PlanRunner(store, evidence_root=evidence_root)
        res = pr.run(plan, payloads_by_task_id=payloads)

        assert res.ok is False
        assert res.plan_verification_ok is False
        assert res.steps == []
        assert res.plan_manifest_sha256 is not None and len(res.plan_manifest_sha256) == 64
