import sys
import os
import json
from pathlib import Path
from datetime import datetime

adapter_role = "envoy"
adapter_version = "1.0.0"
action_class = "deterministic_local_execution"

intent = sys.argv[1] if len(sys.argv) > 1 else "utc_date"
run_id = sys.argv[2] if len(sys.argv) > 2 else "local"

store_root = os.environ.get("STORE_ROOT", os.getcwd())
evidence_dir = Path(store_root) / "evidence"
evidence_dir.mkdir(parents=True, exist_ok=True)

exit_code = 0
stdout = ""
stderr = ""
artifacts = []
errors = []

try:
    if intent == "utc_date":
        stdout = datetime.utcnow().strftime("%Y-%m-%d")
    else:
        stdout = "unsupported_intent"
        exit_code = 1
        errors.append("unsupported_intent")
except Exception as e:
    exit_code = 1
    stderr = str(e)
    errors.append(str(e))

payload = {
    "adapter_role": adapter_role,
    "adapter_version": adapter_version,
    "action_class": action_class,
    "ok": exit_code == 0,
    "exit_code": exit_code,
    "stdout": stdout,
    "stderr": stderr,
    "artifacts": artifacts,
    "errors": errors,
}

evidence_file = evidence_dir / f"envoy_{intent}_{run_id}.json"
with open(evidence_file, "w") as f:
    json.dump(payload, f, sort_keys=True)

sys.exit(exit_code)
