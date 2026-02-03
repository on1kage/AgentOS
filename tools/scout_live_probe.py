import json
import sys
from agentos.canonical import canonical_json
from onemind.scout.perplexity import ask_perplexity

def main() -> int:
    question = "What is today's UTC date? Respond with a single ISO date string."
    r = ask_perplexity(question=question, context="Return a single ISO date string only.", timeout=30.0)
    payload = {
        "schema_version": r.schema_version,
        "question": r.question,
        "answer": r.answer,
        "citations": list(r.citations),
        "model": r.model,
        "usage": r.usage,
    }
    sys.stdout.write(canonical_json(payload))
    sys.stdout.write("\n")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
