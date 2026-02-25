import argparse
import json
import os
import shutil
from pathlib import Path
from typing import Dict, Any
from agentos.canonical import canonical_json, sha256_hex
from agentos.adapter_registry import ADAPTERS
from agentos.intents import intent_spec
from agentos.execution import ExecutionSpec, canonical_inputs_manifest
from agentos.executor import LocalExecutor
from agentos.evidence import EvidenceBundle
from agentos.outcome import ExecutionOutcome
from agentos.store_fs import FSStore
from agentos.evaluation import evaluate_task
from agentos.fsm import rebuild_task_state
from agentos.policy import decide, KNOWN_ACTIONS
from agentos.adapter_role_contract_checker import contract_sha256

SCHEMA_VERSION = "agentos-weekly-proof/v1"

def _store_root(intent_name: str) -> Path:
    return Path("store") / "weekly_proof" / intent_name / "deterministic"

def _required_env_present(env_allowlist: list[str]):
    missing = [k for k in env_allowlist if not os.environ.get(k)]
    return (len(missing) == 0, missing)

def _make_spec(*, role: str, task_id: str, cmd_argv: list[str], env_allowlist: list[str], cwd: str, intent_name: str, intent_spec_obj: dict) -> ExecutionSpec:
    intent_name_sha = sha256_hex(intent_name.encode("utf-8"))
    intent_spec_sha = sha256_hex(canonical_json(intent_spec_obj).encode("utf-8"))
    inputs_manifest = canonical_inputs_manifest({
        "intent/name": intent_name_sha,
        "intent/spec": intent_spec_sha,
    })
    return ExecutionSpec(
        exec_id="weekly_proof",
        task_id=task_id,
        role=role,
        action=("external_research" if role == "scout" else "deterministic_local_execution"),
        kind="shell",
        cmd_argv=list(cmd_argv),
        cwd=cwd,
        env_allowlist=list(env_allowlist),
        timeout_s=60,
        inputs_manifest_sha256=inputs_manifest,
        paths_allowlist=[cwd],
        note=f"weekly_proof intent={intent_name} role={role}",
    )

def _write_run_summary(evidence_root: Path, task_id: str, exec_id: str, manifest_sha256: str) -> None:
    d = evidence_root / task_id / exec_id
    d.mkdir(parents=True, exist_ok=True)
    p = d / "run_summary.json"
    p.write_text(canonical_json({"manifest_sha256": manifest_sha256}), encoding="utf-8")

def _emit_minimal_task_events(store: FSStore, spec: ExecutionSpec, ok: bool, exit_code: int, manifest_sha256: str) -> None:
    task_id = spec.task_id
    created_payload = {
        "exec_id": spec.exec_id,
        "kind": spec.kind,
        "cmd_argv": list(spec.cmd_argv),
        "cwd": spec.cwd,
        "env_allowlist": list(spec.env_allowlist),
        "timeout_s": int(spec.timeout_s),
        "inputs_manifest_sha256": spec.inputs_manifest_sha256,
        "paths_allowlist": list(spec.paths_allowlist),
        "note": spec.note,
    }
    store.append_event(
        task_id,
        "TASK_CREATED",
        {
            "role": spec.role,
            "action": spec.action,
            "payload": created_payload,
            "attempt": 0,
        },
    )
    d = decide(spec.role, spec.action)
    store.append_event(
        task_id,
        "TASK_VERIFIED",
        {
            "role": spec.role,
            "action": spec.action,
            "reason": d.reason,
            "inputs_manifest_sha256": spec.inputs_manifest_sha256,
            "adapter_role_contract_sha256": contract_sha256(),
            "attempt": 0,
        },
    )
    store.append_event(
        task_id,
        "TASK_DISPATCHED",
        {
            "role": spec.role,
            "action": spec.action,
            "attempt": 0,
            "inputs_manifest_sha256": spec.inputs_manifest_sha256,
        },
    )
    store.append_event(
        task_id,
        "RUN_STARTED",
        {
            "role": spec.role,
            "action": spec.action,
            "exec_id": spec.exec_id,
            "spec_sha256": sha256_hex(spec.to_canonical_json().encode("utf-8")),
        },
    )
    if ok:
        store.append_event(
            task_id,
            "RUN_SUCCEEDED",
            {
                "role": spec.role,
                "action": spec.action,
                "exec_id": spec.exec_id,
                "spec_sha256": sha256_hex(spec.to_canonical_json().encode("utf-8")),
                "exit_code": int(exit_code),
                "manifest_sha256": manifest_sha256,
            },
        )
    else:
        store.append_event(
            task_id,
            "RUN_FAILED",
            {
                "role": spec.role,
                "action": spec.action,
                "exec_id": spec.exec_id,
                "spec_sha256": sha256_hex(spec.to_canonical_json().encode("utf-8")),
                "exit_code": int(exit_code),
                "manifest_sha256": manifest_sha256,
            },
        )

def _run_role(*, intent_name: str, intent_spec_obj: dict, role: str, store_root: Path, cwd: str, require_env: bool) -> Dict[str, Any]:
    adapter = ADAPTERS.get(role)
    if adapter is None:
        raise SystemExit(f"unknown_role:{role}")

    cmd = list(adapter["cmd"]) + [intent_name]
    env_allowlist = adapter["env_allowlist"]

    ok_env, missing = _required_env_present(env_allowlist)
    if not ok_env:
        if require_env:
            raise RuntimeError(f"missing_required_env_for_role:{role}:{','.join(missing)}")
        else:
            task_id = f"weekly_{role}"
            store_root = _store_root(intent_name)
            store_root.mkdir(parents=True, exist_ok=True)
            ev_store = FSStore(str(store_root / "events"))
            spec = _make_spec(
                role=role,
                task_id=task_id,
                cmd_argv=cmd,
                env_allowlist=env_allowlist,
                cwd=cwd,
                intent_name=intent_name,
                intent_spec_obj=intent_spec_obj,
            )
            _emit_minimal_task_events(ev_store, spec, True, 0, "0"*64)
            evidence_root = store_root / "evidence"
            evidence_root.mkdir(parents=True, exist_ok=True)
            _write_run_summary(evidence_root, task_id, spec.exec_id, "0"*64)
            ev = evaluate_task(store=ev_store, evidence_root=str(evidence_root), task_id=task_id, decision="accept", note="weekly_proof_evaluation_skipped_env")
            snap = rebuild_task_state(ev_store, task_id)
            if str(snap.get("state")) != "EVALUATED":
                raise RuntimeError(f"weekly_proof_fsm_not_evaluated:{snap.get('state')}")
            evs = list(ev_store.list_events(task_id))
            te = [e for e in evs if str(e.get("type")) == "TASK_EVALUATED"]
            if not te:
                raise RuntimeError("weekly_proof_missing_TASK_EVALUATED")
            body = dict(te[-1].get('body') or {})
            if str(body.get('evaluation_manifest_sha256')) != str(ev.get('evaluation_manifest_sha256')):
                raise RuntimeError("weekly_proof_evaluation_manifest_mismatch")
            return {
                "ok": True,
                "skipped": True,
                "exit_code": 0,
                "bundle_dir": "",
                "spec_sha256": "0"*64,
                "manifest_sha256": "0"*64,
                "adapter_version": adapter["adapter_version"],
                "adapter_role": role,
                "action_class": spec.action,
                "evaluation_decision": "accept",
                "evaluation_spec_sha256": ev.get("evaluation_spec_sha256"),
                "evaluation_manifest_sha256": ev.get("evaluation_manifest_sha256"),
                "refinement_task_id": None,
            }

    task_id = f"weekly_{role}"

    spec = _make_spec(
        role=role,
        task_id=task_id,
        cmd_argv=cmd,
        env_allowlist=env_allowlist,
        cwd=cwd,
        intent_name=intent_name,
        intent_spec_obj=intent_spec_obj,
    )

    executor = LocalExecutor()
    r = executor.run(spec)

    evidence_root = store_root / "evidence"
    evidence_root.mkdir(parents=True, exist_ok=True)

    outcome = ExecutionOutcome.SUCCEEDED if r.exit_code == 0 else ExecutionOutcome.FAILED
    evidence = EvidenceBundle(root=str(evidence_root)).write_bundle(
        spec=spec,
        stdout=r.stdout,
        stderr=r.stderr,
        outputs={},
        outcome=outcome,
        reason="weekly_proof",
    )

    _write_run_summary(evidence_root, task_id, spec.exec_id, str(evidence.get("manifest_sha256")))
    ev_store = FSStore(str(store_root / "events"))
    _emit_minimal_task_events(ev_store, spec, bool(r.exit_code == 0), int(r.exit_code), str(evidence.get("manifest_sha256")))

    decision = "accept" if r.exit_code == 0 else "refine"
    ev = evaluate_task(store=ev_store, evidence_root=str(evidence_root), task_id=task_id, decision=decision, note="weekly_proof_evaluation")

    # Fail-closed: weekly_proof must prove deterministic FSM replay reaches EVALUATED.
    snap = rebuild_task_state(ev_store, task_id)
    if str(snap.get("state")) != "EVALUATED":
        raise RuntimeError(f"weekly_proof_fsm_not_evaluated:{snap.get('state')}")

    # Fail-closed: evaluation manifest must match what was recorded in TASK_EVALUATED.
    evs = list(ev_store.list_events(task_id))
    te = [e for e in evs if str(e.get("type")) == "TASK_EVALUATED"]
    if not te:
        raise RuntimeError("weekly_proof_missing_TASK_EVALUATED")
    body = dict(te[-1].get('body') or {})
    if str(body.get('evaluation_manifest_sha256')) != str(ev.get('evaluation_manifest_sha256')):
        raise RuntimeError("weekly_proof_evaluation_manifest_mismatch")


    return {
        "ok": r.exit_code == 0,
        "skipped": False,
        "exit_code": r.exit_code,
        "bundle_dir": evidence.get("bundle_dir"),
        "spec_sha256": evidence.get("spec_sha256"),
        "manifest_sha256": evidence.get("manifest_sha256"),
        "adapter_version": adapter["adapter_version"],
        "adapter_role": role,
        "action_class": spec.action,
        "evaluation_decision": decision,
        "evaluation_spec_sha256": ev.get("evaluation_spec_sha256"),
        "evaluation_manifest_sha256": ev.get("evaluation_manifest_sha256"),
        "refinement_task_id": ev.get("refinement_task_id"),
    }

def _parse_roles(s: str):
    return [v.strip() for v in (s or "").split(",") if v.strip()]

def main(*, intent_name: str, roles_csv: str, require_scout: bool) -> int:
    run_id = "weekly_proof"
    intents = [i.strip() for i in intent_name.split(",") if i.strip()]
    roles = _parse_roles(roles_csv)
    exit_code = 0

    for intent in intents:
        spec = intent_spec(intent)
        store_root = _store_root(intent)
        if store_root.exists():
            shutil.rmtree(store_root)
        store_root.mkdir(parents=True, exist_ok=True)

        cwd = str(Path.cwd())
        results: Dict[str, Any] = {}

        for role in roles:
            require_env = True
            if role == "scout" and not require_scout:
                require_env = False

            res = _run_role(
                intent_name=intent,
                intent_spec_obj=spec,
                role=role,
                store_root=store_root,
                cwd=cwd,
                require_env=require_env,
            )

            results[role] = res

            if role == "envoy" and not res.get("ok", False):
                exit_code = 2
            if role == "scout" and not res.get("ok", False) and not res.get("skipped", False):
                exit_code = 3

        actions_universe = {"known_actions": sorted(list(KNOWN_ACTIONS))}
        actions_universe_sha256 = sha256_hex(canonical_json(actions_universe).encode("utf-8"))

        payload = {
            "schema_version": SCHEMA_VERSION,
            "actions_universe_sha256": actions_universe_sha256,
            "intent": intent,
            "roles": roles,
            "results": results,
        }

        print(canonical_json(payload))
        artifact_path = Path("store/weekly_proof/artifacts") / f"{intent}_{run_id}.json"
        artifact_path.write_text(canonical_json(payload), encoding="utf-8")
    return exit_code

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--intent", type=str, default="utc_date")
    parser.add_argument("--roles", type=str, default="envoy,scout")
    parser.add_argument("--require-scout", action="store_true")
    args = parser.parse_args()
    raise SystemExit(main(intent_name=args.intent, roles_csv=args.roles, require_scout=bool(args.require_scout)))
