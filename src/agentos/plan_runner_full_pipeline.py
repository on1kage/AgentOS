from __future__ import annotations
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple, Set

from agentos.canonical import canonical_json, sha256_hex
from agentos.intent_evidence import IntentEvidence
from agentos.intent_normalizer import IntentNormalizer
from agentos.pipeline import Step, PipelineResult, verify_plan
from agentos.evidence import EvidenceBundle
from agentos.store_fs import FSStore
from agentos.research_or_local_intent_compiler import ResearchOrLocalIntentCompiler
from agentos.intent_compiler_evidence import write_compilation_evidence

def _payload_unknown_keys(payload: dict, allowed: Set[str]) -> List[str]:
    if not isinstance(payload, dict):
        return ["__payload_not_dict__"]
    ks: List[str] = []
    for k in payload.keys():
        if not isinstance(k, str):
            ks.append("__non_string_key__")
            continue
        if k not in allowed:
            ks.append(k)
    return sorted(set(ks))

def _fail_closed_payload_contract(*, stage: str, payload: dict, allowed_keys: Set[str], evidence_root: str, intent_sha256: str) -> PipelineResult:
    unknown = _payload_unknown_keys(payload, allowed_keys)
    if not unknown:
        return PipelineResult(ok=True, decisions=[], verification_bundle_dir=None, verification_manifest_sha256=None)
    reason = f"payload_contract_violation:{stage}"
    refusal_spec = sha256_hex(canonical_json({
        "stage": stage,
        "intent_sha256": intent_sha256,
        "reason": reason,
        "allowed_keys": sorted(allowed_keys),
        "unknown_keys": unknown,
    }).encode("utf-8"))
    rb = EvidenceBundle(root=evidence_root).write_verification_bundle(
        spec_sha256=refusal_spec,
        decisions={
            "stage": stage,
            "intent_sha256": intent_sha256,
            "refusal_reason": reason,
            "allowed_keys": sorted(allowed_keys),
            "unknown_keys": unknown,
        },
        reason="payload_contract_violation",
        idempotency_key=intent_sha256,
    )
    return PipelineResult(
        ok=False,
        decisions=[{"stage": stage, "reason": reason, "unknown_keys": unknown}],
        verification_bundle_dir=rb["bundle_dir"],
        verification_manifest_sha256=rb["manifest_sha256"],
    )

def _deterministic_submitted_at_utc(intent_text: str) -> str:
    base = {"intent_text": intent_text}
    return "deterministic:" + sha256_hex(canonical_json(base).encode("utf-8"))

def _deterministic_intent_sha256(intent_text: str, submitted_at_utc: str) -> str:
    base = {"intent_text": intent_text, "submitted_at_utc": submitted_at_utc, "submitter_id": None}
    return sha256_hex(canonical_json(base).encode("utf-8"))

def _select_candidate(decisions: Dict[str, Any]) -> Tuple[str, str]:
    cands = decisions.get("candidates")
    unresolved = decisions.get("unresolved")
    if isinstance(unresolved, list) and len(unresolved) > 0:
        raise ValueError("intent_compilation_refused:unresolved_intent")
    if not isinstance(cands, list) or len(cands) == 0:
        raise ValueError("intent_compilation_refused:no_candidates")
    best = None
    best_score = None
    tie = False
    for c in cands:
        if not isinstance(c, dict):
            continue
        role = c.get("role")
        action = c.get("action")
        conf = c.get("confidence")
        if not isinstance(role, str) or not role:
            continue
        if not isinstance(action, str) or not action:
            continue
        if not isinstance(conf, (int, float)):
            continue
        score = float(conf)
        if best is None or score > float(best_score):
            best = (role, action)
            best_score = score
            tie = False
        elif score == float(best_score):
            if best != (role, action):
                tie = True
    if best is None:
        raise ValueError("intent_compilation_refused:no_valid_candidates")
    if tie:
        raise ValueError("intent_compilation_refused:ambiguous_top_candidate")
    return best

def run_full_pipeline(payload: dict) -> PipelineResult:
    intent_text = payload.get("intent_text")
    if not isinstance(intent_text, str) or not intent_text:
        raise ValueError("missing_intent_text")
    store_root = os.environ.get("AGENTOS_STORE_ROOT", "store")
    store = FSStore(root=store_root)
    evidence_root = str(store.root / "evidence")
    submitted_at_utc = _deterministic_submitted_at_utc(intent_text)
    intent_sha256 = _deterministic_intent_sha256(intent_text, submitted_at_utc)
    entry_allowed: Set[str] = {"intent_text"}
    entry_chk = _fail_closed_payload_contract(
        stage="payload_contract_entry",
        payload=payload,
        allowed_keys=entry_allowed,
        evidence_root=evidence_root,
        intent_sha256=intent_sha256,
    )
    if entry_chk.ok is False:
        return entry_chk
    ie = IntentEvidence(store, evidence_root=evidence_root)
    ie.write_intent_ingest(intent_text, submitted_at_utc=submitted_at_utc, submitter_id=None)
    use_new_compiler = os.environ.get("AGENTOS_INTENT_COMPILER") == "research_or_local_v1"
    if use_new_compiler:
        compiler = ResearchOrLocalIntentCompiler()
        result = compiler.compile(intent_text, intent_sha256=intent_sha256)
        write_compilation_evidence(intent_text, result)
        if isinstance(result, CompilationRefusal):
            return PipelineResult(
                ok=False,
                decisions=[{"stage": "intent_compilation_refusal", "reason": result.refusal_reason}],
                verification_bundle_dir=None,
                verification_manifest_sha256=None,
            )
        role = result.plan_spec["delegate"]["role"]
        action = result.plan_spec["delegate"]["action"]
        steps: List[Step] = [Step(role=role, action=action)]
        exit_allowed: Set[str] = {"intent_text", "intent_sha256", "intent_compilation_manifest_sha256", "compiled_intent"}
        payload["compiled_intent"] = {
            "intent_sha256": intent_sha256,
            "selected": {"role": role, "action": action},
            "intent_compilation_manifest_sha256": None,
        }
        exit_chk = _fail_closed_payload_contract(
            stage="payload_contract_exit",
            payload=payload,
            allowed_keys=exit_allowed,
            evidence_root=evidence_root,
            intent_sha256=intent_sha256,
        )
        if exit_chk.ok is False:
            return exit_chk
        return verify_plan(steps, evidence_root=evidence_root)
    normalizer = IntentNormalizer(store, evidence_root=evidence_root)
    nrec = normalizer.normalize(
        intent_text,
        intent_sha256=intent_sha256,
        normalized_at_utc="deterministic:" + intent_sha256,
        idempotency_key=intent_sha256,
    )
    payload["intent_sha256"] = intent_sha256
    payload["intent_compilation_manifest_sha256"] = nrec.manifest_sha256
    manifest_path = Path(nrec.bundle_dir) / "manifest.sha256.json"
    if not manifest_path.exists():
        raise RuntimeError("intent_compilation_evidence_missing")
    import json as _json
    decisions = _json.loads(manifest_path.read_text(encoding="utf-8")).get("decisions", {})
    try:
        role, action = _select_candidate(decisions)
    except ValueError as e:
        refusal_reason = str(e)
        refusal_spec = sha256_hex(canonical_json({"stage": "intent_compilation_refusal", "intent_sha256": intent_sha256, "reason": refusal_reason}).encode("utf-8"))
        rb = EvidenceBundle(root=evidence_root).write_verification_bundle(
            spec_sha256=refusal_spec,
            decisions={
                "stage": "intent_compilation_refusal",
                "intent_sha256": intent_sha256,
                "refusal_reason": refusal_reason,
                "intent_compilation_manifest_sha256": nrec.manifest_sha256,
            },
            reason="intent_compilation_refusal",
            idempotency_key=intent_sha256,
        )
        return PipelineResult(
            ok=False,
            decisions=[{"stage": "intent_compilation_refusal", "reason": refusal_reason}],
            verification_bundle_dir=rb["bundle_dir"],
            verification_manifest_sha256=rb["manifest_sha256"],
        )
    payload["compiled_intent"] = {
        "intent_sha256": intent_sha256,
        "selected": {"role": role, "action": action},
        "intent_compilation_manifest_sha256": nrec.manifest_sha256,
    }
    steps: List[Step] = [Step(role=role, action=action)]
    exit_allowed: Set[str] = {
        "intent_text",
        "intent_sha256",
        "intent_compilation_manifest_sha256",
        "compiled_intent",
    }
    exit_chk = _fail_closed_payload_contract(
        stage="payload_contract_exit",
        payload=payload,
        allowed_keys=exit_allowed,
        evidence_root=evidence_root,
        intent_sha256=intent_sha256,
    )
    if exit_chk.ok is False:
        return exit_chk
    return verify_plan(steps, evidence_root=evidence_root)
