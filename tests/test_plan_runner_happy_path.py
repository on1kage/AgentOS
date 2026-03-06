import hashlib
import tempfile
import uuid
from pathlib import Path

from agentos.adapter_registry import ADAPTERS
from agentos.plan import Plan, PlanStep
from agentos.plan_runner import PlanRunner
from agentos.store_fs import FSStore


def _sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def test_plan_runner_happy_path_two_steps():
    with tempfile.TemporaryDirectory() as tmp:
        store = FSStore(root=tmp)

        plan_id = f"p_{uuid.uuid4().hex}"
        step_id_1 = f"s_{uuid.uuid4().hex}"
        step_id_2 = f"s_{uuid.uuid4().hex}"
        task_id_1 = f"t_{uuid.uuid4().hex}"
        task_id_2 = f"t_{uuid.uuid4().hex}"

        plan = Plan(
            plan_id=plan_id,
            steps=[
                PlanStep(step_id=step_id_1, role="morpheus", action="architecture", task_id=task_id_1),
                PlanStep(
                    step_id=step_id_2,
                    role="envoy",
                    action="deterministic_local_execution",
                    task_id=task_id_2,
                ),
            ],
        )

        ims = _sha256_hex(uuid.uuid4().bytes)
        cwd = str(Path.cwd())

        payloads = {
            task_id_1: {
                "exec_id": f"exec_{task_id_1}",
                "kind": "shell",
                "cmd_argv": list(ADAPTERS["morpheus"]["cmd"]) + ["onemind_stack_descriptions"],
                "cwd": cwd,
                "env_allowlist": list(ADAPTERS["morpheus"]["env_allowlist"]),
                "timeout_s": 60,
                "inputs_manifest_sha256": ims,
                "intent_compilation_manifest_sha256": ims,
                "paths_allowlist": [cwd],
                "note": "plan step 1 morpheus",
            },
            task_id_2: {
                "exec_id": f"exec_{task_id_2}",
                "kind": "shell",
                "cmd_argv": list(ADAPTERS["envoy"]["cmd"]) + ["system_status"],
                "cwd": cwd,
                "env_allowlist": list(ADAPTERS["envoy"]["env_allowlist"]),
                "timeout_s": 60,
                "inputs_manifest_sha256": ims,
                "intent_compilation_manifest_sha256": ims,
                "paths_allowlist": [cwd],
                "note": "plan step 2 envoy",
            },
        }

        evidence_root = str(Path(tmp) / "evidence")
        pr = PlanRunner(store, evidence_root=evidence_root)

        res = pr.run(plan, payloads_by_task_id=payloads)
        assert res.ok is True
        assert res.plan_verification_ok is True
        assert len(res.steps) == 2
        assert all(s.run_ok for s in res.steps)
        assert res.steps[0].role == "morpheus"
        assert res.steps[1].role == "envoy"
        assert res.plan_manifest_sha256 is not None and len(res.plan_manifest_sha256) == 64
