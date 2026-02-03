from typing import Tuple, Dict, Any, List
from pathlib import Path
import json
import time
import shutil

from agentos.store_fs import FSStore
from agentos.canonical import canonical_json
from agentos.execution import ExecutionSpec, canonical_inputs_manifest
from agentos.executor import LocalExecutor
from agentos.evidence import EvidenceBundle
from agentos.outcome import ExecutionOutcome


scout_cmd = ["python3", "-c", "import sys,runpy; sys.path[:0]=['src','src/onemind-FSM-Kernel/src']; runpy.run_path('tools/scout_live_probe.py', run_name='__main__')"]
envoy_cmd = ["python3", "-c", "import sys,runpy; sys.path[:0]=['src','src/onemind-FSM-Kernel/src']; runpy.run_path('tools/envoy_live_probe.py', run_name='__main__')"]


def _mk_run_id() -> str:
    return str(int(time.time()))


def _ensure_clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _parse_json_stdout(stdout: bytes) -> dict:
    s = stdout.decode("utf-8", errors="replace").strip()
    if not s:
        raise ValueError("empty_stdout")
    try:
        return json.loads(s)
    except json.JSONDecodeError as e:
        raise ValueError(f"stdout_not_json:{e}") from e


def _run_exec_and_evidence(
    *,
    task_id: str,
    role: str,
    action: str,
    cmd_argv: List[str],
    cwd: str,
    env_allowlist: List[str],
    timeout_s: int,
    evidence_root: str,
    paths_allowlist: List[str],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    inputs_manifest_sha256 = canonical_inputs_manifest({"cmd_argv": "na"})
    spec = ExecutionSpec(
        exec_id=f"{task_id}-exec",
        task_id=task_id,
        role=role,
        action=action,
        kind="shell",
        cmd_argv=list(cmd_argv),
        cwd=str(cwd),
        env_allowlist=list(env_allowlist),
        timeout_s=int(timeout_s),
        inputs_manifest_sha256=str(inputs_manifest_sha256),
        paths_allowlist=list(paths_allowlist),
        note=None,
    )

    ex = LocalExecutor()
    ev = EvidenceBundle(root=evidence_root)

    res = ex.run(spec)
    ok = int(res.exit_code) == 0
    outcome = ExecutionOutcome.SUCCEEDED if ok else ExecutionOutcome.FAILED
    reason = "ok" if ok else f"exit_code:{int(res.exit_code)}"

    outputs: Dict[str, bytes] = {}
    parsed: dict | None = None
    if ok:
        parsed = _parse_json_stdout(res.stdout)
        outputs["parsed.json"] = canonical_json(parsed).encode("utf-8")

    bundle = ev.write_bundle(
        spec=spec,
        stdout=res.stdout,
        stderr=res.stderr,
        outputs=outputs,
        outcome=outcome,
        reason=reason,
        idempotency_key=None,
    )

    ev.verify_bundle_dir(bundle_dir=bundle["bundle_dir"])

    run_payload = spec.to_canonical_obj()
    run_payload["spec_sha256"] = spec.spec_sha256()
    run_payload["evidence_bundle"] = bundle

    result = {
        "phase": "run",
        "ok": bool(ok),
        "task_id": task_id,
        "route": {"role": role, "action": action},
        "run": run_payload,
        "parsed": parsed,
    }
    return result, run_payload


def _write_eval_bundle(evidence_root: str, task_id: str, decision: str, summary: dict) -> dict:
    ev = EvidenceBundle(root=evidence_root)
    spec_sha = summary.get("run", {}).get("spec_sha256") if isinstance(summary, dict) else None
    if not isinstance(spec_sha, str) or not spec_sha:
        raise RuntimeError("missing_spec_sha256_for_eval")
    vb = ev.write_verification_bundle(
        spec_sha256=spec_sha,
        decisions={"decision": str(decision), "summary": summary},
        reason="weekly_proof_eval",
        idempotency_key=None,
    )
    return vb


def main() -> None:
    run_id = _mk_run_id()
    store_root = Path("store") / "weekly_proof" / run_id
    _ensure_clean_dir(store_root)

    store = FSStore(root=str(store_root))
    evidence_root = str(store.root / "evidence")

    cwd = str(Path.cwd())
    paths_allowlist = [str(Path(store.root).resolve()), str(Path(cwd).resolve())]

    scout_res, _ = _run_exec_and_evidence(
        task_id="weekly_scout",
        role="scout",
        action="external_research",
        cmd_argv=scout_cmd,
        cwd=cwd,
        env_allowlist=["PPLX_API_KEY", "PPLX_BASE_URL", "PPLX_MODEL"],
        timeout_s=120,
        evidence_root=evidence_root,
        paths_allowlist=paths_allowlist,
    )
    scout_eval = _write_eval_bundle(
        evidence_root=evidence_root,
        task_id="weekly_scout",
        decision="ACCEPT" if scout_res.get("ok") else "REFINE",
        summary=scout_res,
    )

    envoy_res, _ = _run_exec_and_evidence(
        task_id="weekly_envoy",
        role="envoy",
        action="deterministic_local_execution",
        cmd_argv=envoy_cmd,
        cwd=cwd,
        env_allowlist=["OLLAMA_HOST", "OLLAMA_MODEL"],
        timeout_s=60,
        evidence_root=evidence_root,
        paths_allowlist=paths_allowlist,
    )
    envoy_eval = _write_eval_bundle(
        evidence_root=evidence_root,
        task_id="weekly_envoy",
        decision="ACCEPT" if envoy_res.get("ok") else "REFINE",
        summary=envoy_res,
    )

    out = {
        "schema_version": "agentos-weekly-proof/v1",
        "run_id": run_id,
        "store_root": str(store_root),
        "scout": {"result": scout_res, "evaluation": scout_eval},
        "envoy": {"result": envoy_res, "evaluation": envoy_eval},
    }

    print(canonical_json(out))


if __name__ == "__main__":
    main()
