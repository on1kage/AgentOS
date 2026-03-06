from agentos.runner import TaskRunner
from agentos.adapter_registry import ADAPTERS


_orig_build_spec = TaskRunner._build_spec


def _build_spec_with_adapter_binding(self, *, task_id: str, role: str, action: str, payload):
    spec = _orig_build_spec(self, task_id=task_id, role=role, action=action, payload=payload)

    if role in ("morpheus", "scout"):
        adapter = ADAPTERS.get(role)
        if not isinstance(adapter, dict):
            raise RuntimeError(f"adapter_binding_required:{role}:{action}")

        expected_cmd = list(adapter.get("cmd") or [])
        expected_env = list(adapter.get("env_allowlist") or [])

        if list(spec.cmd_argv) != expected_cmd:
            raise RuntimeError(f"adapter_binding_required:{role}:{action}")

        if sorted(list(spec.env_allowlist)) != sorted(expected_env):
            raise RuntimeError(f"adapter_binding_required:{role}:{action}")

    return spec


TaskRunner._build_spec = _build_spec_with_adapter_binding
