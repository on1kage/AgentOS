from __future__ import annotations

from typing import Dict, Any

from agentos.store_fs import FSStore
from agentos.execution import ExecutionSpec


class RunEventWriter:
    """
    FSM-compliant RUN lifecycle event writer.

    This module:
    - Emits RUN_STARTED / RUN_SUCCEEDED / RUN_FAILED only
    - Does NOT execute code
    - Relies on FSM replay to enforce ordering (fail-closed)
    """

    def __init__(self, store: FSStore) -> None:
        self.store = store

    def emit_run_started(self, spec: ExecutionSpec) -> None:
        self.store.append_event(
            spec.task_id,
            "RUN_STARTED",
            {
                "exec_id": spec.exec_id,
                "spec_sha256": spec.spec_sha256(),
                "kind": spec.kind,
            },
        )

    def emit_run_succeeded(
        self,
        spec: ExecutionSpec,
        *,
        exit_code: int,
        stdout_sha256: str,
        stderr_sha256: str,
        outputs_manifest_sha256: str,
    ) -> None:
        self.store.append_event(
            spec.task_id,
            "RUN_SUCCEEDED",
            {
                "exec_id": spec.exec_id,
                "spec_sha256": spec.spec_sha256(),
                "exit_code": int(exit_code),
                "stdout_sha256": stdout_sha256,
                "stderr_sha256": stderr_sha256,
                "outputs_manifest_sha256": outputs_manifest_sha256,
            },
        )

    def emit_run_failed(
        self,
        spec: ExecutionSpec,
        *,
        error_class: str,
        error_sha256: str,
        exit_code: int | None = None,
    ) -> None:
        body: Dict[str, Any] = {
            "exec_id": spec.exec_id,
            "spec_sha256": spec.spec_sha256(),
            "error_class": error_class,
            "error_sha256": error_sha256,
        }
        if exit_code is not None:
            body["exit_code"] = int(exit_code)

        self.store.append_event(
            spec.task_id,
            "RUN_FAILED",
            body,
        )
