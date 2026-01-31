from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal, Optional, Tuple


Mode = Literal["research", "local_exec"]


@dataclass(frozen=True)
class ResearchOrLocalIntentV1:
    """
    First supported intent class (v1).

    Exactly one of two modes:
      - research    -> Scout / external_research
      - local_exec  -> Envoy / deterministic_local_execution

    Closed-world constraints only. Anything else must be refused by the compiler.
    """
    mode: Mode
    query: str
    max_results: Optional[int] = None
    no_network: Optional[bool] = None
    read_only: Optional[bool] = None


# Deterministic trigger vocabulary (closed set)
RESEARCH_TRIGGERS: Final[Tuple[str, ...]] = (
    "search",
    "look up",
    "find sources",
    "papers",
    "citations",
    "research",
)

LOCAL_EXEC_TRIGGERS: Final[Tuple[str, ...]] = (
    "run",
    "execute",
    "command",
    "shell",
    "pytest",
    "git",
    "grep",
    "cat",
    "ls",
)

# Closed constraint vocabulary
MAX_RESULTS_MIN: Final[int] = 1
MAX_RESULTS_MAX: Final[int] = 50
DEFAULT_MAX_RESULTS: Final[int] = 10

DEFAULT_NO_NETWORK: Final[bool] = True
DEFAULT_READ_ONLY: Final[bool] = True

# Canonical role/action mapping for this intent class
ROLE_FOR_MODE: Final[dict[str, str]] = {
    "research": "scout",
    "local_exec": "envoy",
}
ACTION_FOR_MODE: Final[dict[str, str]] = {
    "research": "external_research",
    "local_exec": "deterministic_local_execution",
}

# Closed refusal reasons (compiler must emit exactly these shapes)
REFUSAL_NO_MODE_MATCH: Final[str] = "refusal:no_mode_match"
REFUSAL_AMBIGUOUS_MODE: Final[str] = "refusal:ambiguous_mode"
REFUSAL_MISSING_QUERY: Final[str] = "refusal:missing_query"
REFUSAL_UNSUPPORTED_CONSTRAINT_PREFIX: Final[str] = "refusal:unsupported_constraint:"
REFUSAL_OUT_OF_BOUNDS_MAX_RESULTS: Final[str] = "refusal:out_of_bounds:max_results"
REFUSAL_FORBIDDEN_NO_NETWORK_FALSE: Final[str] = "refusal:forbidden:no_network_false"
REFUSAL_FORBIDDEN_READ_ONLY_FALSE: Final[str] = "refusal:forbidden:read_only_false"


# --- legacy compatibility: basic_intent (do not remove) ---
# Legacy compiler path imports `basic_intent.allowed_agents`. Keep this stable until the old
# intent_compiler / evidence stages are fully retired.
from dataclasses import dataclass as _dataclass
from typing import Final as _Final, Tuple as _Tuple

@_dataclass(frozen=True)
class _LegacyBasicIntent:
    allowed_agents: _Tuple[str, ...]

basic_intent: _Final[_LegacyBasicIntent] = _LegacyBasicIntent(
    allowed_agents=("scout", "envoy"),
)
