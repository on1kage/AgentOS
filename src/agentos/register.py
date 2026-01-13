"""
Explicit registration adapter for AgentOS.

Rules:
- No implicit side effects at import time.
- Registration is explicit via register_into(kernel).
- Fail-closed if a kernel object does not meet the expected minimal interface.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from agentos.subsystem import AgentOSSubsystem


@runtime_checkable
class KernelLike(Protocol):
    subsystems: Any

    def register_subsystem(self, name: str, subsystem: Any, overwrite: bool = False) -> None: ...


def register_into(kernel: Any, *, overwrite: bool = False) -> None:
    """
    Register AgentOSSubsystem into a Kernel-like object.

    This function does not import onemind kernel modules. Caller supplies the kernel instance.
    """
    if kernel is None:
        raise TypeError("kernel is None (expected Kernel-like object)")

    if not isinstance(kernel, KernelLike):
        raise TypeError(
            "kernel does not satisfy KernelLike protocol "
            "(expected .subsystems and .register_subsystem(name, subsystem, overwrite=...))"
        )

    subsystem = AgentOSSubsystem()
    kernel.register_subsystem("agentos", subsystem, overwrite=overwrite)
