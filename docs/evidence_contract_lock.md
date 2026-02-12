# Evidence & Adapter Contract Lock

This document freezes the structural guarantees relied upon by CI, verification logic, and cryptographic integrity checks.

This is NOT explanatory documentation.
This is a contract boundary.

---

## 1. ExecutionSpec Contract

ExecutionSpec canonical object fields (sorted JSON):

- action
- cmd_argv
- cwd
- env_allowlist
- exec_id
- inputs_manifest_sha256
- kind
- note
- paths_allowlist
- role
- task_id
- timeout_s

spec_sha256 is defined as:

sha256( canonical_json(ExecutionSpec) )

This definition MUST NOT change without:

- Version bump
- CI validator update
- Backward compatibility note

---

## 2. Adapter Registry Contract

Each adapter entry MUST define:

- cmd: deterministic argv array
- env_allowlist: explicit list of allowed environment variables

Adapters MUST NOT:

- Implicitly inherit environment
- Execute via shell string
- Modify cwd outside ExecutionSpec

Any adapter contract change requires:

- Weekly proof pass
- Evidence hash validation
- Test suite pass

---

## 3. EvidenceBundle Execution Contract

Execution bundle layout:

evidence/<task_id>/<exec_id>/

Required files:

- exec_spec.json
- stdout.txt
- stderr.txt
- manifest.sha256.json
- run_summary.json
- outputs/

manifest.sha256.json format:

{
  "files": {
    "relative/path": "sha256_hex"
  }
}

run_summary.json MUST contain:

- spec_sha256
- manifest_sha256
- schema_version
- task_id
- exec_id
- outcome
- reason
- inputs_manifest_sha256

No additional required fields may be silently introduced.

---

## 4. Verification Bundle Contract

verify/<spec_sha256>/

manifest.sha256.json MUST:

- Be canonical JSON
- Match directory name
- Be byte-identical on recomputation

Collision rule:

Same spec_sha256 MUST produce identical manifest bytes.

---

## 5. CI Enforcement

tools/validate_evidence.py is the canonical enforcement mechanism.

CI relies on:

- ci/evidence_contract.v1.json
- Deterministic directory layout
- Canonical JSON serialization
- sha256_hex implementation

If these change, CI must be updated in the same commit.

---

## 6. Reproducibility Guarantee

Given identical:

- intent_text
- environment variables
- adapter command definitions
- canonical serialization

AgentOS MUST produce:

- Identical spec_sha256
- Identical manifest_sha256
- Identical verification bundle bytes

If not reproducible → integrity is broken.

---

## Principle

Evidence defines reality.

If the evidence hash validates, the action happened.
If it does not validate, it did not happen.

This boundary is frozen.
