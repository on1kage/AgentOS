from __future__ import annotations

import os
from pathlib import Path
from pathlib import Path
from pathlib import Path

from typing import Any, Dict, List, Tuple

from agentos.canonical import canonical_json, sha256_hex
from agentos.intent_evidence import IntentEvidence
from agentos.intent_normalizer import IntentNormalizer
from agentos.pipeline import Step, PipelineResult, verify_plan
from agentos.evidence import EvidenceBundle
from agentos.store_fs import FSStore


def _deterministic_submitted_at_utc(intent_text: str) -> str:
    base = {"intent_text": intent_text}
    return "deterministic:" + sha256_hex(canonical_json(base).encode("utf-8"))


def _deterministic_intent_sha256(intent_text: str, submitted_at_utc: str) -> str:
    base = {
        "intent_text": intent_text,
        "submitted_at_utc": submitted_at_utc,
        "submitter_id": None,
    }
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

    ie = IntentEvidence(store, evidence_root=evidence_root)
    ie.write_intent_ingest(
        intent_text,
        submitted_at_utc=submitted_at_utc,
        submitter_id=None,
        idempotency_key=intent_sha256,
    )

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
            decisions={"stage": "intent_compilation_refusal", "intent_sha256": intent_sha256, "refusal_reason": refusal_reason, "intent_compilation_manifest_sha256": nrec.manifest_sha256},
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
    return verify_plan(steps, evidence_root=evidence_root)
