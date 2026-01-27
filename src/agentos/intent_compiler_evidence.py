from pathlib import Path
import json
from .intent_compiler import compile_intent

store_root = Path("store") / "intent" / "evidence"
store_root.mkdir(parents=True, exist_ok=True)

def write_compilation_evidence(intent_text: str):
    result = compile_intent(intent_text)
    evidence_id = result.intent_sha256 if hasattr(result, "intent_sha256") else "unknown"
    path = store_root / f"{evidence_id}.json"
    payload = {
        "intent": intent_text,
        "type": type(result).__name__,
        "data": result.__dict__,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path, result
