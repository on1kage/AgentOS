# Weekly Proof Semantics

## Purpose
Define the rules for a valid weekly proof run in AgentOS.

## Definition of a Weekly Proof
A weekly proof is a single execution that:
- Runs at least one Scout task and one Envoy task.
- Produces complete evidence bundles for each task.
- Produces verification bundles with explicit evaluation decisions.

## Required Artifacts
For each task (Scout / Envoy):
- Execution evidence bundle under `store/weekly_proof/<run_id>/evidence/weekly_<role>/`
- Files must include:
  - `exec_spec.json`
  - `stdout.txt`
  - `stderr.txt`
  - `outputs/parsed.json` (if execution succeeded)
- A `manifest.sha256.json` must exist and verify.

## Evaluation Semantics
- Each task must be evaluated by Morpheus.
- Decision must be one of:
  - `ACCEPT`: Output is correct, complete, and policy-compliant.
  - `REFINE`: Output is incomplete, incorrect, or violates policy.
- Evaluation is stored in a verification bundle under:
  `store/weekly_proof/<run_id>/evidence/verify/<spec_sha>/manifest.sha256.json`

## Fail-Closed Rules
A weekly proof FAILS if any of the following occur:
- Evidence bundle missing or incomplete.
- Manifest hash mismatch.
- Parsed output missing or empty.
- Evaluation missing.
- Envoy violates authoritative source policy.

## Output Contract
The weekly proof runner must emit canonical JSON with:
- `schema_version: agentos-weekly-proof/v1`
- `run_id`
- `store_root`
- Scout result + evaluation
- Envoy result + evaluation
