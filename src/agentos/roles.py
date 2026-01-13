"""
Deterministic role registry for AgentOS.

No execution. Only declared roles, authorities, and prohibited actions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class Role:
    name: str
    authority: List[str]
    prohibited: List[str]


def roles() -> Dict[str, Role]:
    """
    Return the canonical AgentOS role map.
    Deterministic and side-effect free.
    """
    return {
        "morpheus": Role(
            name="morpheus",
            authority=["architecture", "verification", "protocol_enforcement"],
            prohibited=["code_execution", "network_calls", "state_mutation"],
        ),
        "scout": Role(
            name="scout",
            authority=["external_research", "source_collection"],
            prohibited=["local_execution", "state_mutation", "unauthorized_actions"],
        ),
        "recon": Role(
            name="recon",
            authority=["deterministic_local_execution", "evidence_capture"],
            prohibited=["internet_access", "unauthorized_actions", "capability_claims_without_proof"],
        ),
    }
