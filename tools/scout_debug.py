import sys
import json

adapter_role = "scout"
adapter_version = "1.0.0"
action_class = "weekly_proof"

intent = sys.argv[1] if len(sys.argv) > 1 else "utc_date"

result = {}
sources = []
errors = []

if intent == "utc_date":
    result = {"info": "scout_probe_ok"}
else:
    result = {}
    errors.append("unsupported_intent")

payload = {
    "adapter_role": adapter_role,
    "adapter_version": adapter_version,
    "action_class": action_class,
    "ok": len(errors) == 0,
    "result": result,
    "sources": sources,
    "errors": errors,
}

print(json.dumps(payload, sort_keys=True))
