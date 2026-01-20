import pytest

from agentos.evidence import EvidenceBundle
from agentos.execution import ExecutionSpec
from agentos.outcome import ExecutionOutcome


def test_evidence_bundle_single_shot_dir(tmp_path):
    ev = EvidenceBundle(str(tmp_path / "evidence"))

    spec = ExecutionSpec(
        exec_id="exec_immutable_0001",
        task_id="task_immutable",
        role="envoy",
        action="deterministic_local_execution",
        kind="shell",
        cmd_argv=["/bin/echo", "ok"],
        cwd=str(tmp_path),
        env_allowlist=[],
        timeout_s=1,
        inputs_manifest_sha256="00" * 32,
        paths_allowlist=[str(tmp_path), "/bin/echo"],
        note="immutability test",
    )

    # First write succeeds
    ev.write_bundle(
        spec=spec,
        stdout=b"ok\n",
        stderr=b"",
        outputs={},
        outcome=ExecutionOutcome.SUCCEEDED,
        reason="exit_code:0",
        idempotency_key="k",
    )

    # Second write must fail closed (dir exists)
    with pytest.raises(FileExistsError):
        ev.write_bundle(
            spec=spec,
            stdout=b"ok\n",
            stderr=b"",
            outputs={},
            outcome=ExecutionOutcome.SUCCEEDED,
            reason="exit_code:0",
            idempotency_key="k",
        )


def test_rejection_bundle_single_shot_dir(tmp_path):
    ev = EvidenceBundle(str(tmp_path / "evidence"))
    task_id = "task_rej_immutable"

    # First rejection write succeeds
    ev.write_rejection(
        task_id,
        reason="some_reject_reason",
        idempotency_key="k",
        context={"x": "y"},
    )

    # Same reason => same rej_id => same directory => must fail closed
    with pytest.raises(FileExistsError):
        ev.write_rejection(
            task_id,
            reason="some_reject_reason",
            idempotency_key="k",
            context={"x": "y"},
        )
