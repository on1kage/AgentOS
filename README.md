AgentOS

Deterministic, fail-closed task orchestration with cryptographically verifiable execution evidence.

Purpose

AgentOS exists to ensure that no task, capability, or outcome can be claimed unless a corresponding execution artifact exists and is verifiably linked to that claim.

All execution paths are explicit, deterministic, auditable, and fail-closed by default.

Core Guarantees

AgentOS enforces the following guarantees at runtime.

No task execution without an explicit Task declaration.
No success status without verified execution artifacts.
No repeated execution without idempotency validation.
No claim without evidence.

If any guarantee cannot be satisfied, execution is rejected.

Execution Model

A Task is submitted with an explicit role, action, and payload.
TaskRouter validates the request against policy and capability gates.
TaskRunner executes the task in a controlled environment.
All outputs including stdout, stderr, and declared files are captured.
An EvidenceBundle is written to immutable storage.
RouteResult is emitted containing execution status, evidence bundle SHA-256, and artifact manifest.
Only RouteResult may be returned to callers.

No other object may assert execution success.

Evidence Bundles

Every execution produces a sealed evidence bundle containing a canonical execution specification, captured stdout and stderr, declared outputs with content hashes, a deterministic manifest, and a cryptographic bundle hash.

Evidence bundles are append-only and replayable.

Idempotency

AgentOS enforces idempotency via explicit idempotency keys.

If a task with the same idempotency key has already executed, execution is skipped, the original RouteResult is returned, and no side effects are re-applied.

Failure Semantics

Failures are first-class and explicit.

Possible outcomes include accepted, rejected, executed, failed, and skipped due to idempotency.

There is no implicit success state.

Scope

AgentOS does not schedule background work, execute arbitrary code, perform discovery, or claim capabilities outside verified execution.

It is an execution and verification kernel only.

Relationship to Other Systems

AgentOS integrates with downstream systems such as TRadar and Storm exclusively through RouteResult objects and evidence bundle references.

No downstream system may infer success without verification.

Status

This repository is under active development.

All guarantees described above are enforced by code and covered by hermetic tests.
