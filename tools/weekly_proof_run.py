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
        action="deterministic_local_execution",
        kind="shell",
        cmd_argv=list(cmd_argv),
        cwd=cwd,
        env_allowlist=list(env_allowlist),
        timeout_s=60,
        inputs_manifest_sha256=inputs_manifest,
        paths_allowlist=[cwd],
        note=f"weekly_proof intent={intent_name} role={role}",
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
            return {"ok": False, "skipped": True, "reason": "missing_required_env", "missing_env": missing}

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

    evidence = EvidenceBundle(root=str(evidence_root)).write_bundle(
        spec=spec,
        stdout=r.stdout,
        stderr=r.stderr,
        outputs={},
        outcome=ExecutionOutcome.SUCCEEDED if r.exit_code == 0 else ExecutionOutcome.FAILED,
        reason="weekly_proof",
    )

    # Deterministic accept/refine placeholder: record results, allow for later evaluation
    review_bundle = EvidenceBundle(root=Path(store_root) / "review")
    review_bundle.write_verification_bundle(
        spec_sha256=evidence["spec_sha256"],
        decisions={"accept": True},
        reason="weekly_proof_evaluation",
    )

    return {
        "ok": r.exit_code == 0,
        "skipped": False,
        "exit_code": r.exit_code,
        "bundle_dir": evidence.get("bundle_dir"),
        "spec_sha256": evidence.get("spec_sha256"),
        "manifest_sha256": evidence.get("manifest_sha256"),
        "adapter_version": adapter["adapter_version"],
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

        payload = {
            "schema_version": SCHEMA_VERSION,
            "intent": intent,
            "roles": roles,
            "results": results,
        }

        print(canonical_json(payload))
        artifact_path = Path('store/weekly_proof/artifacts') / f'{intent}_{run_id}.json'
        artifact_path.write_text(canonical_json(payload), encoding='utf-8')
    return exit_code

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--intent", type=str, default="utc_date")
    parser.add_argument("--roles", type=str, default="envoy,scout")
    parser.add_argument("--require-scout", action="store_true")
    args = parser.parse_args()
    raise SystemExit(main(intent_name=args.intent, roles_csv=args.roles, require_scout=bool(args.require_scout)))
