# Envoy Time Truth Policy

## Purpose
Define the authoritative source of time for Envoy executions.

## Policy
- Envoy uses the **system UTC clock** as the sole authoritative source for time.
- Local or remote language models are **not** authoritative for real-time truth.
- Any model output related to time is considered non-authoritative unless explicitly derived from the system clock.

## Rationale
- Local models have static or stale knowledge.
- Deterministic correctness is required for evidence-backed execution.
- System UTC clock is auditable, deterministic, and verifiable.

## Enforcement
- Envoy probes must derive time from `datetime.now(timezone.utc)`.
- Evidence bundles must record the derived value.
- Evaluation must REFINE if time is sourced from a non-authoritative origin.
