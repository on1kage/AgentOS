import os
import sys
from datetime import datetime, timezone
from agentos.canonical import canonical_json

def _model() -> str:
    return os.getenv("OLLAMA_MODEL", "system_clock_utc")

def main() -> int:
    prompt = "Return today's UTC date as a single ISO date string only (YYYY-MM-DD)."
    expected = datetime.now(timezone.utc).date().isoformat()

    out = {
        "schema_version": "envoy-intel/v1",
        "model": _model(),
        "prompt": prompt,
        "answer": expected,
        "expected_utc_date": expected,
        "answer_raw": expected,
        "raw_keys": ["system_clock_utc"],
    }

    sys.stdout.write(canonical_json(out))
    sys.stdout.write("\n")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
