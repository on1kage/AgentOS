import tempfile

from agentos.evidence import EvidenceBundle
from agentos.execution import ExecutionSpec
from agentos.outcome import ExecutionOutcome


def _spec() -> ExecutionSpec:
    return ExecutionSpec(
        exec_id="exec-1",
        task_id="task-1",
        role="envoy",
        action="deterministic_local_execution",
        kind="shell",
        cmd_argv=["python3", "-c", "print('ok')"],
        cwd="/deterministic/cwd",
        env_allowlist=[],
        timeout_s=5,
        inputs_manifest_sha256="a" * 64,
        paths_allowlist=["/deterministic/cwd"],
        note="repro-test",
    )


def test_write_bundle_is_reproducible_for_identical_inputs():
    with tempfile.TemporaryDirectory() as tmp1, tempfile.TemporaryDirectory() as tmp2:
        spec1 = _spec()
        spec2 = _spec()

        b1 = EvidenceBundle(root=tmp1).write_bundle(
            spec=spec1,
            stdout=b'{"result":{"status":"ok"}}\n',
            stderr=b"",
            outputs={},
            outcome=ExecutionOutcome.SUCCEEDED,
            reason="exit_code:0",
            idempotency_key=None,
        )

        b2 = EvidenceBundle(root=tmp2).write_bundle(
            spec=spec2,
            stdout=b'{"result":{"status":"ok"}}\n',
            stderr=b"",
            outputs={},
            outcome=ExecutionOutcome.SUCCEEDED,
            reason="exit_code:0",
            idempotency_key=None,
        )

        assert b1["spec_sha256"] == b2["spec_sha256"]
        assert b1["manifest_sha256"] == b2["manifest_sha256"]
