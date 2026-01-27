from pathlib import Path
import json
from hashlib import sha256
from datetime import datetime

store_root = Path("store") / "intent"
store_root.mkdir(parents=True, exist_ok=True)

def ingest_intent(intent_text: str) -> dict:
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    intent_hash = sha256(intent_text.encode("utf-8")).hexdigest()
    path = store_root / f"{ts}_{intent_hash}.json"
    payload = {"intent_text": intent_text, "intent_sha256": intent_hash, "timestamp_utc": ts}
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload
