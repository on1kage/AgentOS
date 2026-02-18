#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Tuple

from agentos.adapter_role_contract_checker import verify_adapter_output, load_contract, verify_registry_versions
from agentos.adapter_registry import ADAPTERS


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
    except Exception:
        return False, "registry_contract_check_exception"

    intent = str(d.get("intent") or "")
    if not intent:
        return False, "artifact_missing_intent"

    results = d.get("results")
    if not isinstance(results, dict):
        return False, "artifact_missing_results"

    for role in ("envoy", "scout"):
        if role not in results or not isinstance(results[role], dict):
            return False, f"artifact_missing_role_result:{role}"

        r = dict(results[role])

        # 1) Verify contract + output schema + adapter_version + adapter_role + action_class invariants
        try:
            ok = verify_adapter_output(role, r)
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
