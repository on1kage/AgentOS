from __future__ import annotations
from typing import Dict, Any
from dataclasses import dataclass

@dataclass(frozen=True)
class CapabilitySpec:
    role: str
    action: str
    payload_schema: Dict[str, type]
    allowed_paths: list[str]
    allowed_env: list[str]

def registry() -> Dict[str, CapabilitySpec]:
    return {
        "envoy:deterministic_local_execution": CapabilitySpec(
            role="envoy",
            action="deterministic_local_execution",
            payload_schema={
                "exec_id": str,
                "kind": str,
                "cmd_argv": list,
                "cwd": str,
                "env_allowlist": list,
                "timeout_s": int,
                "inputs_manifest_sha256": str,
                "paths_allowlist": list,
                "note": (str, type(None)),
            },
            allowed_paths=[],
            allowed_env=[],
        ),
    }
