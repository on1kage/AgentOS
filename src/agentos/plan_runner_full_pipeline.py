from __future__ import annotations
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple, Set

from agentos.canonical import canonical_json, sha256_hex
from agentos.intent_evidence import IntentEvidence
from agentos.pipeline import Step, PipelineResult, verify_plan
from agentos.evidence import EvidenceBundle
from agentos.store_fs import FSStore
from agentos.roles import roles as role_registry



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

def _legacy_path_block(*, stage: str, evidence_root: str, intent_sha256: str, intent_text: str, legacy_id: str) -> PipelineResult:
    reason = f"legacy_path_blocked:{legacy_id}"
    spec_sha = sha256_hex(canonical_json({
        "stage": stage,
        "intent_sha256": intent_sha256,
        "legacy_id": legacy_id,
        "reason": reason,
    }).encode("utf-8"))
    rb = EvidenceBundle(root=evidence_root).write_verification_bundle(
        spec_sha256=spec_sha,
        decisions={
            "stage": stage,
            "intent_sha256": intent_sha256,
            "intent_text": intent_text,
            "legacy_id": legacy_id,
            "refusal_reason": reason,
        },
        reason="legacy_path_blocked",
        idempotency_key=intent_sha256,
    )
    return PipelineResult(
        ok=False,
        decisions=[{"stage": stage, "reason": reason, "legacy_id": legacy_id}],
        verification_bundle_dir=rb["bundle_dir"],
        verification_manifest_sha256=rb["manifest_sha256"],
    )

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

    entry_allowed: Set[str] = {"intent_text", "plan_spec"}
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

    intent_source = os.environ.get("AGENTOS_INTENT_SOURCE")
    if intent_source is None:
        return _legacy_path_block(
            stage="intent_source_gate",
            evidence_root=evidence_root,
            intent_sha256=intent_sha256,
            intent_text=intent_text,
            legacy_id="intent_source_unset",
        )
    if intent_source != "planspec_v1":
        return _legacy_path_block(
            stage="intent_source_gate",
            evidence_root=evidence_root,
            intent_sha256=intent_sha256,
            intent_text=intent_text,
            legacy_id="intent_source_not_planspec_v1",
        )
    ps = payload.get("plan_spec")
    payload.pop("plan_spec", None)
    allowed_ps = {"role", "action", "metadata"}
    if not isinstance(ps, dict):
        refusal_reason = "planspec_invalid:not_a_dict"
        refusal_spec = sha256_hex(canonical_json({"stage": "planspec_refusal", "intent_sha256": intent_sha256, "reason": refusal_reason}).encode("utf-8"))
        rb = EvidenceBundle(root=evidence_root).write_verification_bundle(
            spec_sha256=refusal_spec,
            decisions={"stage": "planspec_refusal", "intent_sha256": intent_sha256, "refusal_reason": refusal_reason},
            reason="planspec_refusal",
            idempotency_key=intent_sha256,
        )
        return PipelineResult(
            ok=False,
            decisions=[{"stage": "planspec_refusal", "reason": refusal_reason}],
            verification_bundle_dir=rb["bundle_dir"],
            verification_manifest_sha256=rb["manifest_sha256"],
        )
    unknown_ps = _payload_unknown_keys(ps, allowed_ps)
    if unknown_ps:
        refusal_reason = "planspec_invalid:unknown_keys"
        refusal_spec = sha256_hex(canonical_json({"stage": "planspec_refusal", "intent_sha256": intent_sha256, "reason": refusal_reason, "unknown_keys": unknown_ps}).encode("utf-8"))
        rb = EvidenceBundle(root=evidence_root).write_verification_bundle(
            spec_sha256=refusal_spec,
            decisions={"stage": "planspec_refusal", "intent_sha256": intent_sha256, "refusal_reason": refusal_reason, "unknown_keys": unknown_ps},
            reason="planspec_refusal",
            idempotency_key=intent_sha256,
        )
        return PipelineResult(
            ok=False,
            decisions=[{"stage": "planspec_refusal", "reason": refusal_reason, "unknown_keys": unknown_ps}],
            verification_bundle_dir=rb["bundle_dir"],
            verification_manifest_sha256=rb["manifest_sha256"],
        )
    role = ps.get("role")
    action = ps.get("action")
    metadata = ps.get("metadata", {})
    if not isinstance(role, str) or not role:
        refusal_reason = "planspec_invalid:missing_or_invalid_role"
        refusal_spec = sha256_hex(canonical_json({"stage": "planspec_refusal", "intent_sha256": intent_sha256, "reason": refusal_reason}).encode("utf-8"))
        rb = EvidenceBundle(root=evidence_root).write_verification_bundle(
            spec_sha256=refusal_spec,
            decisions={"stage": "planspec_refusal", "intent_sha256": intent_sha256, "refusal_reason": refusal_reason},
            reason="planspec_refusal",
            idempotency_key=intent_sha256,
        )
        return PipelineResult(
            ok=False,
            decisions=[{"stage": "planspec_refusal", "reason": refusal_reason}],
            verification_bundle_dir=rb["bundle_dir"],
            verification_manifest_sha256=rb["manifest_sha256"],
        )
    if not isinstance(action, str) or not action:
        refusal_reason = "planspec_invalid:missing_or_invalid_action"
        refusal_spec = sha256_hex(canonical_json({"stage": "planspec_refusal", "intent_sha256": intent_sha256, "reason": refusal_reason}).encode("utf-8"))
        rb = EvidenceBundle(root=evidence_root).write_verification_bundle(
            spec_sha256=refusal_spec,
            decisions={"stage": "planspec_refusal", "intent_sha256": intent_sha256, "refusal_reason": refusal_reason},
            reason="planspec_refusal",
            idempotency_key=intent_sha256,
        )
        return PipelineResult(
            ok=False,
            decisions=[{"stage": "planspec_refusal", "reason": refusal_reason}],
            verification_bundle_dir=rb["bundle_dir"],
            verification_manifest_sha256=rb["manifest_sha256"],
        )
    if not isinstance(metadata, dict):
        refusal_reason = "planspec_invalid:metadata_not_dict"
        refusal_spec = sha256_hex(canonical_json({"stage": "planspec_refusal", "intent_sha256": intent_sha256, "reason": refusal_reason}).encode("utf-8"))
        rb = EvidenceBundle(root=evidence_root).write_verification_bundle(
            spec_sha256=refusal_spec,
            decisions={"stage": "planspec_refusal", "intent_sha256": intent_sha256, "refusal_reason": refusal_reason},
            reason="planspec_refusal",
            idempotency_key=intent_sha256,
        )
        return PipelineResult(
            ok=False,
            decisions=[{"stage": "planspec_refusal", "reason": refusal_reason}],
            verification_bundle_dir=rb["bundle_dir"],
            verification_manifest_sha256=rb["manifest_sha256"],
        )
    rm = role_registry()
    if role not in rm:
        refusal_reason = "planspec_invalid:unknown_role"
        refusal_spec = sha256_hex(canonical_json({"stage": "planspec_refusal", "intent_sha256": intent_sha256, "reason": refusal_reason, "role": role}).encode("utf-8"))
        rb = EvidenceBundle(root=evidence_root).write_verification_bundle(
            spec_sha256=refusal_spec,
            decisions={"stage": "planspec_refusal", "intent_sha256": intent_sha256, "refusal_reason": refusal_reason, "role": role},
            reason="planspec_refusal",
            idempotency_key=intent_sha256,
        )
        return PipelineResult(
            ok=False,
            decisions=[{"stage": "planspec_refusal", "reason": refusal_reason, "role": role}],
            verification_bundle_dir=rb["bundle_dir"],
            verification_manifest_sha256=rb["manifest_sha256"],
        )
    allowed_actions = list(rm[role].authority)
    if action not in allowed_actions:
        refusal_reason = "planspec_invalid:unknown_action_for_role"
        refusal_spec = sha256_hex(canonical_json({"stage": "planspec_refusal", "intent_sha256": intent_sha256, "reason": refusal_reason, "role": role, "action": action, "allowed_actions": allowed_actions}).encode("utf-8"))
        rb = EvidenceBundle(root=evidence_root).write_verification_bundle(
            spec_sha256=refusal_spec,
            decisions={"stage": "planspec_refusal", "intent_sha256": intent_sha256, "refusal_reason": refusal_reason, "role": role, "action": action, "allowed_actions": allowed_actions},
            reason="planspec_refusal",
            idempotency_key=intent_sha256,
        )
        return PipelineResult(
            ok=False,
            decisions=[{"stage": "planspec_refusal", "reason": refusal_reason, "role": role, "action": action, "allowed_actions": allowed_actions}],
            verification_bundle_dir=rb["bundle_dir"],
            verification_manifest_sha256=rb["manifest_sha256"],
        )
    norm_ps = {"role": role, "action": action, "metadata": metadata}
    spec_sha = sha256_hex(canonical_json(norm_ps).encode("utf-8"))
    rb = EvidenceBundle(root=evidence_root).write_verification_bundle(
        spec_sha256=spec_sha,
        decisions={"intent_text": intent_text, "intent_sha256": intent_sha256, "plan_spec": norm_ps},
        reason="planspec_evidence",
        idempotency_key=intent_sha256,
    )
    steps: List[Step] = [Step(role=role, action=action)]
    exit_allowed: Set[str] = {"intent_text", "intent_sha256", "intent_compilation_manifest_sha256", "compiled_intent"}
    payload["compiled_intent"] = {
        "intent_sha256": intent_sha256,
        "selected": {"role": role, "action": action},
        "intent_compilation_manifest_sha256": rb["manifest_sha256"],
        "plan_spec": norm_ps,
    }
    payload["intent_sha256"] = intent_sha256
    payload["intent_compilation_manifest_sha256"] = rb["manifest_sha256"]
    payload.pop("plan_spec", None)
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

