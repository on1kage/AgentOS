from dataclasses import dataclass
from typing import List

@dataclass(frozen=True)
class SupportedIntentClass:
    name: str
    allowed_agents: List[str]
    allowed_actions: List[str]
    allowed_constraints: List[str]
    ambiguity_rules: List[str]

basic_intent = SupportedIntentClass(
    name="simple_query",
    allowed_agents=["scout", "envoy"],
    allowed_actions=["search", "report_status"],
    allowed_constraints=["no_network", "read_only"],
    ambiguity_rules=["any other wording triggers refusal"]
)
