"""
AgentOS Subsystem (minimal scaffold)

Contract goals:
- Importable without side effects.
- Deterministic static metadata via describe().
- Fail-closed dependency declaration (no silent capability claims).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class AgentOSSubsystem:
    """
    Minimal subsystem contract.

    NOTE:
    - No execution entrypoint is wired yet.
    - describe() must remain deterministic and side-effect free.
    """
    name: str = "AgentOS"
    version: str = "0.1"
    capabilities: List[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        # dataclasses + frozen: use object.__setattr__
        if self.capabilities is None:
            object.__setattr__(self, "capabilities", ["orchestration", "fsm_contract"])

    def execute(self, context=None):
        """Kernel entrypoint placeholder.

        Must exist for Kernel Contract v1 compliance.
        No execution is wired in AgentOS yet.
        """
        raise NotImplementedError("AgentOSSubsystem.execute is not wired yet")

    def describe(self) -> Dict[str, object]:
        """
        Return static metadata for kernel contract compliance.
        Must be deterministic and side-effect free.
        """
        return {
            "name": self.name,
            "version": self.version,
            "capabilities": list(self.capabilities),
            "requires": {
                # Declared dependencies (not imported here).
                "chatgptprotocol": Optional[str].__name__,
                "onemind_fsm_kernel": Optional[str].__name__,
            },
        }
