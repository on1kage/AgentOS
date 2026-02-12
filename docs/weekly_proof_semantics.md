# Weekly Proof Semantics

## Purpose
Define the deterministic, fail-closed contract for a valid weekly proof run in AgentOS.

Weekly proof is not a smoke test. It is a cryptographic integrity assertion over execution + evaluation.

---

## Definition of a Weekly Proof

A weekly proof is a single execution that:

1. Executes at least one Envoy role and one Scout role.
2. Produces canonical execution evidence bundles for each role.
3. Produces verification bundles proving evaluation decisions.
4. Passes cryptographic hash validation under CI.

---

## Execution Evidence Contract

For each role (Envoy / Scout), an execution bundle MUST exist under:

store/weekly_proof/<intent>/<run_id>/evidence/<task_id>/<exec_id>/

The bundle MUST contain:

- exec_spec.json
- stdout.txt
- stderr.txt
- manifest.sha256.json
- run_summary.json
- outputs/ (directory, may be empty)

### Hash Invariants (Non-Negotiable)

The following MUST hold:

1. sha256(exec_spec.json bytes) == run_summary.spec_sha256
2. sha256(manifest.sha256.json bytes) == run_summary.manifest_sha256
3. For every file listed in manifest.sha256.json:
   sha256(file bytes) == manifest entry
4. manifest.sha256.json MUST be canonical JSON
5. Evidence directory MUST NOT pre-exist before write

Violation of any invariant invalidates the weekly proof.

---

## Verification Bundle Contract

Verification bundles MUST exist under:

store/weekly_proof/<intent>/<run_id>/evidence/verify/<spec_sha256>/

Each verification bundle MUST:

- Contain manifest.sha256.json
- Be canonical JSON
- Match directory name == spec_sha256
- Be byte-identical on recomputation

---

## CI Enforcement

The GitHub Actions workflow:

.github/workflows/weekly_proof.yml

Performs:

1. Execution of weekly_proof_run.py
2. Deterministic validation via tools/validate_evidence.py
3. Fail-closed exit on ANY mismatch

CI does NOT trust runtime logs.
CI validates bytes on disk.

If hash mismatch occurs, build fails.

---

## Fail-Closed Conditions

Weekly proof FAILS if:

- Any required file missing
- Any manifest mismatch
- run_summary hash mismatch
- Evidence directory collision
- Verification bundle mismatch
- Scout required but skipped
- Envoy execution fails
- Policy rejection occurs without verification artifact

---

## Adapter & Evidence Immutability Guarantees

The following are frozen:

- ExecutionSpec canonical serialization format
- spec_sha256 definition (sha256 over canonical JSON)
- manifest.sha256.json structure: {"files": {path: sha256}}
- EvidenceBundle directory layout
- Verification bundle canonical payload structure

Breaking these requires:

- Contract version increment
- Explicit CI update
- Migration note in release notes

---

## Output Contract (Runner JSON)

weekly_proof_run.py MUST emit canonical JSON containing:

- schema_version: agentos-weekly-proof/v1
- run_id
- store_root
- intent
- roles
- results per role:
  - ok
  - exit_code
  - spec_sha256
  - manifest_sha256
  - bundle_dir

Output is informational.
Integrity is enforced via evidence validation.

---

## Principle

If evidence hashes validate → execution is cryptographically proven.
If evidence hashes do not validate → execution did not happen.

No simulation.
No silent fallback.
No unverifiable claims.
