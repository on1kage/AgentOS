from __future__ import annotations

import os
import subprocess
from typing import Dict

from agentos.execution import ExecutionSpec


class ExecutionResult:
    def __init__(self, *, exit_code: int, stdout: bytes, stderr: bytes) -> None:
        self.exit_code = int(exit_code)
        self.stdout = stdout
        self.stderr = stderr


def _real_abs(path: str) -> str:
    return os.path.realpath(os.path.abspath(path))


def _allowed_path(child: str, allow_entry: str) -> bool:
    """
    Allowlist semantics:
    - If allow_entry resolves to a file: allow exact match only.
    - If allow_entry resolves to a directory (or non-existent path treated as directory prefix): allow descendants.
    """
    if child == allow_entry:
        return True

    # If allow_entry exists and is a file, only exact match is allowed (already handled above).
    if os.path.exists(allow_entry) and os.path.isfile(allow_entry):
        return False

    # Directory (or non-existent prefix treated as directory): allow descendants.
    parent = allow_entry
    if not parent.endswith(os.sep):
        parent = parent + os.sep
    return child.startswith(parent)


class LocalExecutor:
    """
    Deterministic local executor.

    Guarantees:
    - argv-only execution (no shell)
    - explicit cwd
    - env filtered by allowlist
    - timeout enforced
    - byte-for-byte stdout/stderr capture
    - fail-closed side-effect boundary via paths_allowlist
    """

    def _preflight_paths(self, spec: ExecutionSpec) -> None:
        cwd_real = _real_abs(spec.cwd)

        allow = [_real_abs(x) for x in spec.paths_allowlist]
        allow.sort()

        # cwd must be within allowlist
        if not any(_allowed_path(cwd_real, a) for a in allow):
            raise PermissionError(f"cwd_not_allowlisted:{cwd_real}")

        # Conservative argv path checks
        for arg in spec.cmd_argv:
            if not isinstance(arg, str) or arg == "":
                raise TypeError("cmd_argv entries must be non-empty strings")

            # Absolute path: must be allowlisted regardless of existence
            if os.path.isabs(arg):
                ap = _real_abs(arg)
                if not any(_allowed_path(ap, a) for a in allow):
                    raise PermissionError(f"arg_path_not_allowlisted:{ap}")
                continue

            # Relative path-like arg: only enforce if it exists on disk
            if os.sep in arg:
                ap = _real_abs(os.path.join(cwd_real, arg))
                if os.path.exists(ap) and (not any(_allowed_path(ap, a) for a in allow)):
                    raise PermissionError(f"arg_path_not_allowlisted:{ap}")

    def run(self, spec: ExecutionSpec) -> ExecutionResult:
        if spec.kind != "shell":
            raise ValueError(f"unsupported_execution_kind:{spec.kind}")

        # Fail-closed: enforce side-effect boundaries before running anything.
        self._preflight_paths(spec)

        # Build environment from allowlist only
        env: Dict[str, str] = {}
        for k in spec.env_allowlist:
            if k in os.environ:
                env[k] = os.environ[k]

        try:
            completed = subprocess.run(
                spec.cmd_argv,
                cwd=spec.cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=spec.timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired as e:
            # Deterministic timeout failure
            stdout = e.stdout if e.stdout is not None else b""
            stderr = e.stderr if e.stderr is not None else b""
            return ExecutionResult(exit_code=124, stdout=stdout, stderr=stderr)

        return ExecutionResult(
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )