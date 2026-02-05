import argparse
import json
import os
import time
import shutil
from pathlib import Path
from typing import Dict, Any
from agentos.canonical import canonical_json, sha256_hex
from agentos.adapter_registry import ADAPTERS
from agentos.execution import ExecutionSpec, canonical_inputs_manifest
from agentos.executor import LocalExecutor
from agentos.evidence import EvidenceBundle
from agentos.outcome import ExecutionOutcome

SCHEMA_VERSION = "agentos-weekly-proof/v1"

def _now_run_id() -> str:
    return str(int(time.time()))

def _store_root(intent_name: str, run_id: str) -> Path:
    return Path("store") / "weekly_proof" / intent_name / run_id

def _required_env_present(env_allowlist: list[str]):
    missing = [k for k in env_allowlist if not os.environ.get(k)]
    return (len(missing) == 0, missing)

def _make_spec(*, role: str, task_id: str, exec_id: str, cmd_argv: list[str], env_allowlist: list[str], cwd: str, paths_allowlist: list[str], intent_name: str) -> ExecutionSpec:
    inputs_manifest = canonical_inputs_manifest({"intent": sha256_hex(intent_name.encode("utf-8"))})
    return ExecutionSpec(
        exec_id=exec_id,
        task_id=task_id,
        role=role,
        action="weekly_proof",
        kind="shell",
        cmd_argv=list(cmd_argv),
        cwd=cwd,
        env_allowlist=list(env_allowlist),
        timeout_s=60,
        inputs_manifest_sha256=inputs_manifest,
        paths_allowlist=list(paths_allowlist),
        note=f"weekly_proof intent={intent_name} role={role}",
    )

def _run_role(*, intent_name: str, run_id: str, role: str, store_root: Path, cwd: str, paths_allowlist: list[str], require_env: bool) -> Dict[str, Any]:
    adapter = ADAPTERS.get(role)
    cmd = list(adapter["cmd"]) + [intent_name]
    env_allowlist = adapter["env_allowlist"]
    ok_env, missing = _required_env_present(env_allowlist)
    if not ok_env:
        if require_env:
            raise RuntimeError(f"missing_required_env_for_role:{role}:{','.join(missing)}")
        else:
            return {"ok": False, "skipped": True, "reason": "missing_required_env", "missing_env": missing}

    task_id = f"weekly_{role}"
    exec_id = run_id
    spec = _make_spec(role=role, task_id=task_id, exec_id=exec_id, cmd_argv=cmd, env_allowlist=env_allowlist, cwd=cwd, paths_allowlist=paths_allowlist, intent_name=intent_name)
    executor = LocalExecutor()
    r = executor.run(spec)
    evidence = EvidenceBundle().write_bundle(spec=spec, stdout=r.stdout, stderr=r.stderr, outputs={}, outcome=ExecutionOutcome.SUCCEEDED if r.exit_code == 0 else ExecutionOutcome.FAILED, reason="weekly_proof")
    return {
        "ok": r.exit_code == 0,
        "skipped": False,
        "exit_code": r.exit_code,
        "bundle_dir": evidence.get("bundle_dir"),
        "spec_sha256": evidence.get("spec_sha256"),
        "manifest_sha256": evidence.get("manifest_sha256"),
    }

def _parse_roles(s: str):
    return [v.strip() for v in (s or "").split(",") if v.strip()]

def main(*, intent_name: str, roles_csv: str, require_scout: bool) -> int:
    run_id = _now_run_id()
    intents = [i.strip() for i in intent_name.split(",") if i.strip()]
    roles = _parse_roles(roles_csv)
    exit_code = 0

    for intent in intents:
        store_root = _store_root(intent, run_id)
        if store_root.exists():
            shutil.rmtree(store_root)
        store_root.mkdir(parents=True, exist_ok=True)
        cwd = str(Path.cwd())
        paths_allowlist = [str(store_root.resolve()), cwd]
        results: Dict[str, Any] = {}

        for role in roles:
            require_env = True
            if role == "scout" and not require_scout:
                require_env = False
            res = _run_role(intent_name=intent, run_id=run_id, role=role, store_root=store_root, cwd=cwd, paths_allowlist=paths_allowlist, require_env=require_env)
            results[role] = res
            if role == "envoy" and not res.get("ok", False):
                exit_code = 2
            if role == "scout":
                if not res.get("skipped", False) and not res.get("ok", False):
                    exit_code = 3

        payload = {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "store_root": str(store_root),
            "intent": intent,
            "roles": roles,
            "results": results,
        }
        print(canonical_json(payload))

    return exit_code

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Weekly proof runner with parameterized intent and adapter selection")
    parser.add_argument("--intent", type=str, default="utc_date")
    parser.add_argument("--roles", type=str, default="envoy,scout")
    parser.add_argument("--require-scout", action="store_true")
    args = parser.parse_args()
    raise SystemExit(main(intent_name=args.intent, roles_csv=args.roles, require_scout=bool(args.require_scout)))
