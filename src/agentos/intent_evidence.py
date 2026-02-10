from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from agentos.canonical import canonical_json, sha256_hex
from agentos.evidence import EvidenceBundle
from agentos.store_fs import FSStore


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _intent_sha256(intent_text: str, submitted_at_utc: str, submitter_id: Optional[str]) -> str:
    base: Dict[str, Any] = {
        "intent_text": intent_text,
        "submitted_at_utc": submitted_at_utc,
        "submitter_id": submitter_id,
    }
    b = canonical_json(base).encode("utf-8")
    return sha256_hex(b)


@dataclass(frozen=True)
class IntentIngestReceipt:
    intent_sha256: str
    bundle_dir: str
    manifest_sha256: str


class IntentEvidence:
    def __init__(self, store: FSStore, *, evidence_root: Optional[str] = None) -> None:
        er = evidence_root
        if not isinstance(er, str) or not er:
            er = str(store.root / "evidence")
        self._eb = EvidenceBundle(root=str(er))

    def write_intent_ingest(
        self,
        intent_text: str,
        *,
        submitted_at_utc: Optional[str] = None,
        submitter_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> IntentIngestReceipt:
        if not isinstance(intent_text, str) or not intent_text:
            raise TypeError("intent_text must be a non-empty string")

        ts = submitted_at_utc if isinstance(submitted_at_utc, str) and submitted_at_utc else _utc_now_iso()
        if not isinstance(ts, str) or not ts:
            raise TypeError("submitted_at_utc must be a non-empty string")

        sid = submitter_id if isinstance(submitter_id, str) and submitter_id else None

        ish = _intent_sha256(intent_text, ts, sid)

        payload: Dict[str, Any] = {
            "intent_sha256": ish,
            "intent_text": intent_text,
            "submitted_at_utc": ts,
            "submitter_id": sid,
            "stage": "intent_ingest",
        }

        bundle = self._eb.write_verification_bundle(
            spec_sha256=ish,
            decisions=payload,
            reason="intent_ingest",
            idempotency_key=idempotency_key,
        )

        return IntentIngestReceipt(
            intent_sha256=ish,
            bundle_dir=str(bundle["bundle_dir"]),
            manifest_sha256=str(bundle["manifest_sha256"]),
        )
