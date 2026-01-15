"""
AgentOS capabilities package.

This package may apply capability-scoped side effects (e.g., runtime patches) in a
deterministic, import-time manner so production behavior does not depend on tests.
"""

# Side-effect import: monkey-patches TaskRunner.run_dispatched for idempotency.
import agentos.capabilities.patches.runner_idempotency_patch  # noqa: F401
