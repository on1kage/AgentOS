from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from agentos.canonical import canonical_json, sha256_hex
from agentos.evidence import EvidenceBundle
from agentos.policy import KNOWN_ACTIONS
from agentos.store_fs import FSStore


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _norm_text(s: str) -> str:
    return " ".join(s.strip().lower().split())


def _score_contains(text: str, needles: List[str]) -> float:
    if not needles:
        return 0.0
    hits = 0
    for n in needles:
        if n in text:
            hits += 1
    return float(hits) / float(len(needles))


@dataclass(frozen=True)
class IntentCandidate:
    role: str
    action: str
    confidence: float
    evidence: List[str]

    def to_obj(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "action": self.action,
            "confidence": float(self.confidence),
            "evidence": list(self.evidence),
        }


@dataclass(frozen=True)
class IntentNormalizedReceipt:
    intent_sha256: str
    verification_spec_sha256: str
    bundle_dir: str
    manifest_sha256: str


class IntentNormalizer:
    """
    Deterministic, non-authoritative intent normalization.

    Produces a verification bundle under store.root/evidence/verify/<spec_sha256>.

    This stage:
    - does NOT execute
    - does NOT decide policy
    - does NOT route
    - only emits structured candidates + explicit unresolved ambiguities
    """

    def __init__(self, store: FSStore, *, evidence_root: Optional[str] = None) -> None:
        self.store = store
        er = evidence_root
        if not isinstance(er, str) or not er:
            er = str(store.root / "evidence")
        self._eb = EvidenceBundle(root=Path('store') / 'weekly_proof' / intent_name / run_id / 'evidence')

    def normalize(
        self,
        intent_text: str,
        *,
        intent_sha256: Optional[str] = None,
        normalized_at_utc: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> IntentNormalizedReceipt:
        if not isinstance(intent_text, str) or not intent_text:
            raise TypeError("intent_text must be a non-empty string")

        norm = _norm_text(intent_text)
        ish = intent_sha256 if isinstance(intent_sha256, str) and intent_sha256 else sha256_hex(canonical_json({"intent_text": intent_text}).encode("utf-8"))

        ts = normalized_at_utc if isinstance(normalized_at_utc, str) and normalized_at_utc else f"deterministic:{ish}"
        if not isinstance(ts, str) or not ts:
            raise TypeError("normalized_at_utc must be a non-empty string")

        candidates: List[IntentCandidate] = []
        unresolved: List[str] = []

        exec_needles = ["run ", "execute ", "cmd", "command", "shell", "ls", "cat ", "pytest", "git ", "grep "]
        exec_score = _score_contains(norm, exec_needles)
        if exec_score > 0.0:
            candidates.append(
                IntentCandidate(
                    role="envoy",
                    action="deterministic_local_execution",
                    confidence=min(1.0, 0.5 + exec_score * 0.5),
                    evidence=[f"contains:{n.strip()}" for n in exec_needles if n in norm],
                )
            )

        research_needles = ["research", "find sources", "look up", "search the web", "papers", "citations"]
        research_score = _score_contains(norm, research_needles)
        if research_score > 0.0:
            candidates.append(
                IntentCandidate(
                    role="scout",
                    action="external_research",
                    confidence=min(1.0, 0.5 + research_score * 0.5),
                    evidence=[f"contains:{n}" for n in research_needles if n in norm],
                )
            )

        arch_needles = ["design", "architecture", "spec", "protocol", "define", "decision matrix"]
        arch_score = _score_contains(norm, arch_needles)
        if arch_score > 0.0:
            candidates.append(
                IntentCandidate(
                    role="morpheus",
                    action="architecture",
                    confidence=min(1.0, 0.5 + arch_score * 0.5),
                    evidence=[f"contains:{n}" for n in arch_needles if n in norm],
                )
            )

        verify_needles = ["verify", "validate", "check", "audit", "prove", "tests"]
        verify_score = _score_contains(norm, verify_needles)
        if verify_score > 0.0:
            candidates.append(
                IntentCandidate(
                    role="morpheus",
                    action="verification",
                    confidence=min(1.0, 0.5 + verify_score * 0.5),
                    evidence=[f"contains:{n}" for n in verify_needles if n in norm],
                )
            )

        if not candidates:
            unresolved.append("no_candidate_matches_v1_ruleset")

        for c in candidates:
            if c.action not in KNOWN_ACTIONS:
                raise RuntimeError(f"normalizer_produced_unknown_action:{c.action}")

        verify_spec = sha256_hex(canonical_json({"stage":"intent_normalized","intent_sha256": ish,"normalized_at_utc": ts,"ruleset_version": 1}).encode("utf-8"))


        payload: Dict[str, Any] = {
            "intent_sha256": ish,
            "normalized_at_utc": ts,
            "candidates": [c.to_obj() for c in candidates],
            "unresolved": list(unresolved),
            "stage": "intent_normalized",
            "ruleset_version": 1,
        }

        bundle = self._eb.write_verification_bundle(
            spec_sha256=verify_spec,
            decisions=payload,
            reason="intent_normalized",
            idempotency_key=idempotency_key,
        )

        return IntentNormalizedReceipt(
              intent_sha256=ish,
              verification_spec_sha256=verify_spec,
            bundle_dir=str(bundle["bundle_dir"]),
            manifest_sha256=str(bundle["manifest_sha256"]),
        )
