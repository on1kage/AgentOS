#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Tuple

from agentos.adapter_role_contract_checker import verify_adapter_output, load_contract, verify_registry_versions, verify_role_registry_parity
from agentos.adapter_registry import ADAPTERS
from agentos.roles import roles
from agentos.policy import KNOWN_ACTIONS
from agentos.canonical import canonical_json, sha256_hex


def _load_json(p: Path) -> Dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))


def _fail(msg: str) -> int:
    print(f"FAIL:{msg}")
    return 2


def _event_dir_for_intent(intent: str, role: str) -> Path:
    # store/weekly_proof/<intent>/deterministic/events/events/weekly_<role>/
    return Path("store") / "weekly_proof" / intent / "deterministic" / "events" / "events" / f"weekly_{role}"


def _latest_task_evaluated_body(evdir: Path) -> Dict[str, Any]:
    if not evdir.exists():
        raise FileNotFoundError(str(evdir))
    files = sorted([p for p in evdir.glob("*.json") if p.name != "HEAD"])
    if not files:
        raise RuntimeError("no_events")
    # Find last TASK_EVALUATED in order; fail-closed if missing.
    last_te: Dict[str, Any] | None = None
    for p in files:
        e = _load_json(p)
        if str(e.get("type")) == "TASK_EVALUATED":
            last_te = dict(e.get("body") or {})
    if last_te is None:
        raise RuntimeError("missing_TASK_EVALUATED")
    return last_te


def verify_weekly_proof_artifact(artifact_path: Path) -> Tuple[bool, str]:
    d = _load_json(artifact_path)

    contract = load_contract()
    try:
        if verify_registry_versions(ADAPTERS, contract) is not True:
            return False, "registry_contract_version_mismatch"
        if verify_role_registry_parity(roles(), contract) is not True:
            return False, "role_contract_action_parity_mismatch"
    except Exception as e:
        return False, f"registry_contract_check_exception:{type(e).__name__}:{e}"

    expected_actions_universe_sha256 = sha256_hex(canonical_json({"known_actions": sorted(list(KNOWN_ACTIONS))}).encode("utf-8"))
    au = d.get("actions_universe_sha256")
    if not isinstance(au, str) or not au:
        return False, "artifact_missing_actions_universe_sha256"
    if au != expected_actions_universe_sha256:
        return False, "actions_universe_sha256_mismatch"

    role_assignments_obj = json.loads((Path("src/agentos/role_assignments.json")).read_text(encoding="utf-8"))
    expected_role_assignments_sha256 = sha256_hex(canonical_json(role_assignments_obj).encode("utf-8"))
    ra = d.get("role_assignments_sha256")
    if not isinstance(ra, str) or not ra:
        return False, "artifact_missing_role_assignments_sha256"
    if ra != expected_role_assignments_sha256:
        return False, "role_assignments_sha256_mismatch"

    intent = str(d.get("intent") or "")
    if not intent:
        return False, "artifact_missing_intent"

    results = d.get("results")
    if not isinstance(results, dict):
        return False, "artifact_missing_results"

    artifact_roles = d.get("roles")
    if not isinstance(artifact_roles, list) or not artifact_roles or any((not isinstance(x, str) or not x) for x in artifact_roles):
        return False, "artifact_missing_roles"

    for role in artifact_roles:
        if role not in results or not isinstance(results[role], dict):
            return False, f"artifact_missing_role_result:{role}"

        r = dict(results[role])

        # 1) Verify contract + output schema + adapter_version + adapter_role + action_class invariants
        try:
            expected = ("external_research" if role == "scout" else "deterministic_local_execution")
            ok = verify_adapter_output(role, r, expected_action=expected)
        except Exception as e:
            return False, f"contract_check_exception:{role}:{type(e).__name__}"
        if ok is not True:
            return False, f"contract_check_failed:{role}"

        for k in ("evaluation_decision", "evaluation_spec_sha256", "evaluation_manifest_sha256"):
            if not isinstance(r.get(k), str) or not r.get(k):
                return False, f"artifact_missing_eval_field:{role}:{k}"

        decision = r.get("evaluation_decision")
        refinement_task_id = r.get("refinement_task_id")
        if decision == "refine":
            if not isinstance(refinement_task_id, str) or not refinement_task_id:
                return False, f"missing_refinement_task_id:{role}"
        if decision == "accept":
            if refinement_task_id:
                return False, f"unexpected_refinement_task_id:{role}"

        # 3) Cross-check artifact evaluation hashes against authoritative TASK_EVALUATED event
        evdir = _event_dir_for_intent(intent, role)
        try:
            body = _latest_task_evaluated_body(evdir)
        except Exception as e:
            return False, f"event_stream_error:{role}:{type(e).__name__}:{e}"

        if str(body.get("decision")) != str(r.get("evaluation_decision")):
            return False, f"eval_decision_mismatch:{role}"
        if str(body.get("evaluation_spec_sha256")) != str(r.get("evaluation_spec_sha256")):
            return False, f"eval_spec_sha256_mismatch:{role}"
        if str(body.get("evaluation_manifest_sha256")) != str(r.get("evaluation_manifest_sha256")):
            return False, f"eval_manifest_sha256_mismatch:{role}"

        # 4) Cross-check refinement chain linkage (fail-closed)
        b_ref = body.get("refinement_task_id")
        a_ref = r.get("refinement_task_id")
        if str(body.get("decision")) == "refine":
            if not isinstance(b_ref, str) or not b_ref:
                return False, f"missing_refinement_task_id_in_event:{role}"
            if not isinstance(a_ref, str) or not a_ref:
                return False, f"missing_refinement_task_id_in_artifact:{role}"
            if str(b_ref) != str(a_ref):
                return False, f"refinement_task_id_mismatch:{role}"
        if str(body.get("decision")) == "accept":
            if b_ref or a_ref:
                return False, f"unexpected_refinement_task_id:{role}"

    return True, "ok"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--artifact",
        type=str,
        default="store/weekly_proof/artifacts/utc_date_weekly_proof.json",
        help="Path to weekly_proof artifact JSON",
    )
    args = ap.parse_args()

    ok, reason = verify_weekly_proof_artifact(Path(args.artifact))
    if ok:
        print("OK:weekly_proof_verified")
        return 0
    return _fail(reason)


if __name__ == "__main__":
    raise SystemExit(main())
