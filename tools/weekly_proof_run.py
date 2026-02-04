import argparse
import json
import os
import time
import shutil
from pathlib import Path
from typing import Dict, Any, Tuple, List
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

def _required_env_present(env_allowlist: list[str]) -> Tuple[bool, list[str]]:
    missing = []
    for k in env_allowlist:
        if k not in os.environ or os.environ.get(k, "") == "":
            missing.append(k)
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
    if not isinstance(adapter, dict):
        raise RuntimeError(f"unknown_role:{role}")

    cmd = adapter.get("cmd")
    env_allowlist = adapter.get("env_allowlist")
    if not isinstance(cmd, list) or not all(isinstance(x, str) and x for x in cmd):
        raise RuntimeError(f"invalid_cmd_for_role:{role}")
    if not isinstance(env_allowlist, list) or not all(isinstance(x, str) and x for x in env_allowlist):
        raise RuntimeError(f"invalid_env_allowlist_for_role:{role}")

    ok_env, missing = _required_env_present(env_allowlist)
    if not ok_env and (not require_env):
        return {
            "ok": False,
            "skipped": True,
            "reason": "missing_required_env",
            "missing_env": missing,
        }
    if not ok_env and require_env:
        raise RuntimeError(f"missing_required_env_for_role:{role}:{','.join(missing)}")

    task_id = f"weekly_{role}"
    exec_id = run_id
    spec = _make_spec(
        role=role,
        task_id=task_id,
        exec_id=exec_id,
        cmd_argv=cmd,
        env_allowlist=env_allowlist,
        cwd=cwd,
        paths_allowlist=paths_allowlist,
        intent_name=intent_name,
    )

    evidence_root = store_root / "evidence" / task_id
    bundle = EvidenceBundle(root=str(evidence_root))
    ex = LocalExecutor()
    r = ex.run(spec)

    outcome = ExecutionOutcome.SUCCEEDED if r.exit_code == 0 else ExecutionOutcome.FAILED
    reason = "exit_code_0" if r.exit_code == 0 else f"exit_code_{r.exit_code}"
    outputs: Dict[str, bytes] = {}
    try:
        parsed = json.loads(r.stdout.decode("utf-8", errors="replace"))
        outputs["parsed.json"] = canonical_json(parsed).encode("utf-8")
    except Exception:
        pass

    bundle_info = bundle.write_bundle(
        spec=spec,
        stdout=r.stdout,
        stderr=r.stderr,
        outputs=outputs,
        outcome=outcome,
        reason=reason,
        idempotency_key=None,
    )

    return {
        "ok": r.exit_code == 0,
        "skipped": False,
        "exit_code": r.exit_code,
        "bundle_dir": bundle_info.get("bundle_dir"),
        "spec_sha256": bundle_info.get("spec_sha256"),
        "manifest_sha256": bundle_info.get("manifest_sha256"),
    }

def _parse_roles(s: str) -> List[str]:
    items = []
    for part in (s or "").split(","):
        v = part.strip()
        if v:
            items.append(v)
    if not items:
        raise ValueError("roles_empty")
    return items

def main(*, intent_name: str, roles_csv: str, require_scout: bool) -> int:
    run_id = _now_run_id()
    store_root = _store_root(intent_name, run_id)

    if store_root.exists():
        shutil.rmtree(store_root)
    store_root.mkdir(parents=True, exist_ok=True)

    cwd = str(Path.cwd())
    paths_allowlist = [str(store_root.resolve()), cwd]

    roles = _parse_roles(roles_csv)
    results: Dict[str, Any] = {}
    exit_code = 0

    for role in roles:
        require_env = True
        if role == "scout" and (not require_scout):
            require_env = False
        res = _run_role(
            intent_name=intent_name,
            run_id=run_id,
            role=role,
            store_root=store_root,
            cwd=cwd,
            paths_allowlist=paths_allowlist,
            require_env=require_env,
        )
        results[role] = res
        if role == "envoy" and not res.get("ok", False):
            exit_code = 2
        if role == "scout":
            if res.get("skipped", False):
                pass
            elif not res.get("ok", False):
                exit_code = 3

    payload = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "store_root": str(store_root),
        "intent": intent_name,
        "roles": roles,
        "results": results,
    }
    print(canonical_json(payload))
    return int(exit_code)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Weekly proof runner with parameterized intent and adapter selection")
    parser.add_argument("--intent", type=str, default="utc_date")
    parser.add_argument("--roles", type=str, default="envoy,scout")
    parser.add_argument("--require-scout", action="store_true")
    args = parser.parse_args()
    raise SystemExit(main(intent_name=args.intent, roles_csv=args.roles, require_scout=bool(args.require_scout)))
