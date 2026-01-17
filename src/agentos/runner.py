from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional

from agentos.canonical import sha256_hex
from agentos.evidence import EvidenceBundle
from agentos.execution import ExecutionSpec, canonical_inputs_manifest
from agentos.outcome import ExecutionOutcome
from agentos.executor import LocalExecutor
from agentos.fsm import rebuild_task_state
from agentos.run_events import RunEventWriter
from agentos.store_fs import FSStore
from agentos.task import TaskState



@dataclass(frozen=True)
class RunSummary:
    ok: bool
    task_id: str
    exec_id: str
    exit_code: int
    stdout_sha256: str
    stderr_sha256: str
    outputs_manifest_sha256: str

    def to_obj(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "task_id": self.task_id,
            "exec_id": self.exec_id,
            "exit_code": int(self.exit_code),
            "stdout_sha256": self.stdout_sha256,
            "stderr_sha256": self.stderr_sha256,
            "outputs_manifest_sha256": self.outputs_manifest_sha256,
        }


class TaskRunner:
    """
    Deterministic runner for DISPATCHED tasks.

    Authoritative inputs:
    - FSMderived task state (must be DISPATCHED)
    - TASD_CREATED event body.payload (execution intent)

    This module:
    - Does NOT decide policy
    - Does NOT dispatch
    - Only executes after dispatch has occurred
    """

    def __init__(self, store: FSStore, *, evidence_root: str = "evidence") -> None:
        self.store = store
        self.executor = LocalExecutor()
        self.events = RunEventWriter(store)
        self.evidence = EvidenceBundle(evidence_root)

    def _load_created_payload(self, task_id: str) -> Dict[str, Any]:
        evs = list(self.store.list_events(task_id))
        for ev in evs:
            if str(ev.get("type")) == "TASK_CREATED":
                body = ev.get("body")
                if not isinstance(body, dict):
                    raise TypeError("TASK_CREATED body must be an object")
                payload = body.get("payload")
                if not isinstance(payload, dict):
                    raise TypeError("TASK_CREATED body.payload must be an object")
                return dict(payload)
        raise RuntimeError("missing TASK_CREATED event")

    def _load_created_role_action(self, task_id: str) -> tuple[str, str]:
        evs = list(self.store.list_events(task_id))
        for ev in evs:
            if str(ev.get("type")) == "TASK_CREATED":
                body = ev.get("body")
                if not isinstance(body, dict):
                    raise TypeError("TASK_CREATED body must be an object")
                role = body.get("role")
                action = body.get("action")
                if not isinstance(role, str) or not role:
                    raise TypeError("TASK_CREATED body.role must be a non-empty string")
                if not isinstance(action, str) or not action:
                    raise TypeError("TASK_CREATED body.action must be a non-empty string")
                return role, action
        raise RuntimeError("missing TASK_CREATED event")

    def _require_str(self, obj: Mapping[str, Any], k: str) -> str:
        v = obj.get(k)
        if not isinstance(v, str) or not v:
            raise TypeError(f"payload.{k} must be a non-empty string")
        return v

    def _require_int(self, obj: Mapping[str, Any], k: str) -> int:
        v = obj.get(k)
        if not isinstance(v, int):
            raise TypeError(f"payload.{k} must be an int")
        return int(v)

    def _require_list_str(self, obj: Mapping[str, Any], k: str) -> list[str]:
        v = obj.get(k)
        if not isinstance(v, list) or any((not isinstance(x, str)) for x in v):
            raise TypeError(f"payload.{k} must be a list[str]")
        return list(v)

    def _build_spec(self, *, task_id: str, role: str, action: str, payload: Mapping[str, Any]) -> ExecutionSpec:
        exec_id = self._require_str(payload, "exec_id")
        kind = self._require_str(payload, "kind")
        cmd_argv = self._require_list_str(payload, "cmd_argv")
        cwd = self._require_str(payload, "cwd")
        env_allowlist = self._require_list_str(payload, "env_allowlist")
        timeout_s = self._require_int(payload, "timeout_s")
        inputs_manifest_sha256 = self._require_str(payload, "inputs_manifest_sha256")
        paths_allowlist = self._require_list_str(payload, "paths_allowlist")
        note = payload.get("note")
        if note is not None and not isinstance(note, str):
            raise TypeError("payload.note must be a string or null")

        return ExecutionSpec(
            exec_id=exec_id,
            task_id=task_id,
            role=role,
            action=action,
            kind=kind,  # validated at runtime by executor expectations
            cmd_argv=cmd_argv,
            cwd=cwd,
            env_allowlist=env_allowlist,
            timeout_s=timeout_s,
            inputs_manifest_sha256=inputs_manifest_sha256,
            paths_allowlist=paths_allowlist,
            note=note,
        )

    def run_dispatched(self, task_id: str) -> RunSummary:
        try:
            snap = rebuild_task_state(self.store, task_id)
            derived_state = TaskState(str(snap["state"]))
            if derived_state is not TaskState.DISPATCHED:
                self.evidence.write_rejection(task_id, reason=f"invalid_state:{derived_state.value}")
                raise RuntimeError(f"invalid_state:{derived_state.value}")

            created_payload = self._load_created_payload(task_id)
            role, action = self._load_created_role_action(task_id)

            spec = self._build_spec(task_id=task_id, role=role, action=action, payload=created_payload)
            idem_key = getattr(self, "_current_idempotency_key", None)


            # Fail-closed: unsupported execution kinds are REJECTED pre-run (auditable)

            if spec.kind != "shell":

                raise RuntimeError(f"reject:unsupported_execution_kind:{spec.kind}")
        except Exception as e:
            # Preflight rejects must be auditable (fail-closed)
            if isinstance(e, RuntimeError) and str(e).startswith("invalid_state:"):
                raise
            if isinstance(e, RuntimeError) and str(e).startswith("reject:"):
                reason = str(e)[len("reject:"):]
                self.evidence.write_rejection(task_id, reason=reason, idempotency_key=idem_key)
                raise RuntimeError(reason)
            self.evidence.write_rejection(task_id, reason=f"preflight_error:{e.__class__.__name__}:{e}", idempotency_key=idem_key)
            raise

        # Emit RUN_STARTED first (FSM enforces legality)
        self.events.emit_run_started(spec)

        try:

            res = self.executor.run(spec)

        except Exception as e:

            # Fail-closed: any executor exception must persist FAILED evidence and RUN_FAILED.

            reason = f"executor_exception:{e.__class__.__name__}:{e}"

            self.evidence.write_bundle(

                spec=spec,

                stdout=b"",

                stderr=b"",

                outputs={},

                outcome=ExecutionOutcome.FAILED,

                reason=reason,

                idempotency_key=idem_key,

            )

            err_sha = sha256_hex(reason.encode("utf-8"))

            self.events.emit_run_failed(

                spec,

                error_class="executor_exception",

                error_sha256=err_sha,

                exit_code=None,

            )

            return RunSummary(

                ok=False,

                task_id=task_id,

                exec_id=spec.exec_id,

                exit_code=125,

                stdout_sha256=sha256_hex(b""),

                stderr_sha256=sha256_hex(b""),

                outputs_manifest_sha256=canonical_inputs_manifest({}),

            )

        stdout_sha = sha256_hex(res.stdout)
        stderr_sha = sha256_hex(res.stderr)

        # Step 7+ will bind declared outputs. For now, empty manifest.
        outputs_manifest_sha = canonical_inputs_manifest({})

        if res.exit_code == 0:
            self.evidence.write_bundle(spec=spec, stdout=res.stdout, stderr=res.stderr, outputs={}, outcome=ExecutionOutcome.SUCCEEDED, reason="exit_code:0", idempotency_key=idem_key)
            self.events.emit_run_succeeded(
                spec,
                exit_code=res.exit_code,
                stdout_sha256=stdout_sha,
                stderr_sha256=stderr_sha,
                outputs_manifest_sha256=outputs_manifest_sha,
            )
            return RunSummary(
                ok=True,
                task_id=task_id,
                exec_id=spec.exec_id,
                exit_code=res.exit_code,
                stdout_sha256=stdout_sha,
                stderr_sha256=stderr_sha,
                outputs_manifest_sha256=outputs_manifest_sha,
            )

        self.evidence.write_bundle(spec=spec, stdout=res.stdout, stderr=res.stderr, outputs={}, outcome=ExecutionOutcome.FAILED, reason=f"exit_code:{res.exit_code}", idempotency_key=idem_key)
        err_sha = sha256_hex(f"exit_code:{res.exit_code}".encode("utf-8"))
        self.events.emit_run_failed(spec, error_class="nonzero_exit", error_sha256=err_sha, exit_code=res.exit_code)
        return RunSummary(
            ok=False,
            task_id=task_id,
            exec_id=spec.exec_id,
            exit_code=res.exit_code,
            stdout_sha256=stdout_sha,
            stderr_sha256=stderr_sha,
            outputs_manifest_sha256=outputs_manifest_sha,
        )

# Side-effect import: ensure capability patches are applied in production.
# This must occur after TaskRunner is defined to avoid circular import hazards.
import agentos.capabilities  # noqa: F401

