from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional

from agentos.canonical import sha256_hex, canonical_json


ExecutionKind = Literal["shell", "python", "http"]


@dataclass(frozen=True)
class ExecutionSpec:
    """
    Canonical execution contract.

    Design constraints:
    - Deterministic serialization (canonical JSON)
    - Hash-addressable (spec_sha256)
    - Explicit side-effect boundaries (paths_allowlist)
    - Explicit environment boundaries (env_allowlist)
    - No implicit defaults that change across machines
    """

    exec_id: str
    task_id: str
    role: str
    action: str

    kind: ExecutionKind

    # Shell execution uses argv (no shell string).
    cmd_argv: List[str]

    # Execution context
    cwd: str

    # Environment control (names only; values supplied by executor at runtime)
    env_allowlist: List[str]

    # Safety
    timeout_s: int

    # Integrity hooks (hashes of inputs and expected artifacts)
    inputs_manifest_sha256: str

    # Side effects must be explicitly allowed paths (directories or files)
    paths_allowlist: List[str]

    # Optional, human-readable intent (non-authoritative)
    note: Optional[str] = None

    def to_canonical_obj(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "cmd_argv": list(self.cmd_argv),
            "cwd": self.cwd,
            "env_allowlist": list(self.env_allowlist),
            "exec_id": self.exec_id,
            "inputs_manifest_sha256": self.inputs_manifest_sha256,
            "kind": self.kind,
            "note": self.note,
            "paths_allowlist": list(self.paths_allowlist),
            "role": self.role,
            "task_id": self.task_id,
            "timeout_s": int(self.timeout_s),
        }

    def to_canonical_json(self) -> str:
        return canonical_json(self.to_canonical_obj())

    def spec_sha256(self) -> str:
        return sha256_hex(self.to_canonical_json().encode("utf-8"))


def canonical_inputs_manifest(files: Dict[str, str]) -> str:
    """
    Canonicalize an inputs manifest (path -> sha256 hex) and return its sha256.
    """
    payload = {"files": dict(files)}
    s = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256_hex(s.encode("utf-8"))
