Adapter Role Contract Freeze (Lock)

Lock date: 2026-02-12
Scope: AgentOS adapters (Scout, Envoy) and their role-preserving update safety constraints.

1. Purpose
This document freezes the role semantics that must remain invariant across:
- model upgrades (Perplexity/Scout, ChatGPT/Morpheus, Ollama/Recon or local workers)
- adapter implementation refactors
- prompt/template changes
- runtime environment changes

Any change that violates this contract MUST fail CI (weekly proof) and MUST be treated as a breaking change.

2. Definitions
Adapter: A deterministic boundary that executes an action class under a role with canonical inputs/outputs.
Role: A fixed capability partition (Scout or Envoy) that constrains allowed action classes and output schemas.
ExecutionSpec: Canonical serialized spec that defines what may be executed; hashed via spec_sha256.
Evidence Bundle: Canonical output + artifacts for an execution; hashed via manifest_sha256 and validated in CI.

3. Roles and Allowed Action Classes
3.1 Scout (Research / Retrieval Role)
Allowed action classes:
- web_search
- doc_retrieval
- data_lookup
- summarize_sources
- extract_entities
- transform_text

Forbidden:
- any action that mutates local/remote state
- any network action beyond explicit retrieval/search APIs exposed by Scout adapter
- any filesystem write outside AgentOS evidence paths
- any credentialed authority escalation

3.2 Envoy (Execution Role)
Allowed action classes:
- shell_exec (only when explicitly authorized by plan + local policy gates)
- repo_ops (read/write within scoped workspace only)
- test_exec
- build_exec
- file_write (within scoped workspace only)
- artifact_pack

Forbidden:
- arbitrary network access unless explicitly authorized by plan + policy (and logged as such)
- any action not declared in ExecutionSpec.action_class
- any attempt to modify AgentOS policy or role maps at runtime

4. Invariants (Hard Requirements)
4.1 Role → Action Mapping Is Immutable
- The mapping from role to allowed action classes is a frozen set.
- Any attempt to run an action class not allowed for the active role MUST fail closed before execution.

4.2 Output Schema Per Role Is Frozen
Scout output MUST be JSON with:
- adapter_role: "scout"
- adapter_version: semver string
- action_class: string (one of allowed)
- ok: boolean
- result: object
- sources: array (may be empty)
- errors: array (may be empty)
No additional top-level keys are permitted unless explicitly added via contract update process.

Envoy output MUST be JSON with:
- adapter_role: "envoy"
- adapter_version: semver string
- action_class: string (one of allowed)
- ok: boolean
- exit_code: integer (required when action_class implies execution)
- stdout: string
- stderr: string
- artifacts: array (may be empty)
- errors: array (may be empty)
No additional top-level keys are permitted unless explicitly added via contract update process.

4.3 ExecutionSpec and Evidence Semantics Must Not Drift
- ExecutionSpec canonical structure is frozen (see evidence_contract_lock.md and weekly_proof_semantics.md).
- Evidence store layout is frozen.
- spec_sha256 and manifest_sha256 definitions are frozen.
- Weekly proof must verify these invariants.

4.4 Fail-Closed Rules
- If any required key is missing: ok=false, fail closed, evidence still written.
- If any forbidden key is present: ok=false, fail closed, evidence still written.
- If adapter_role mismatches expected role: ok=false, fail closed, evidence still written.
- If action_class is not in the role allowlist: ok=false, fail closed, evidence still written.

5. Deterministic Normalization Requirements (Pre-Seal)
Before evidence sealing:
- Remove nondeterministic fields (timestamps, request ids, ephemeral model metadata, latency, token counts).
- Ensure stable JSON ordering (canonical serialization).
- Ensure sources list ordering is deterministic (sorted by stable keys when applicable).

6. Versioning and Update Safety
6.1 Adapter Version
- Each adapter exposes adapter_version (semver).
- Weekly proof records adapter_version per run in evidence.
- Any adapter_version change requires weekly proof to pass (structural + hash checks).

6.2 Contract Update Process (Breaking Change Control)
A contract update MUST include:
- a version bump to this document (append “Contract revision” section)
- updated schema validation logic in code
- updated tests and golden fixtures
- CI weekly proof passing
Without all four, changes are rejected.

7. Lock Statement
This contract is locked. Model upgrades are permitted only if:
- they do not change output schema,
- they do not expand role capabilities,
- they pass weekly proof including schema validation and determinism checks.

