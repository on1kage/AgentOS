#!/usr/bin/env python3
import subprocess
import sys

adapters = ["scout", "envoy"]

all_ok = True
for adapter in adapters:
    outputs_file = f"/tmp/{adapter}_outputs.json"
    r = subprocess.run(
        ["python3", "src/agentos/adapter_role_contract_checker.py", adapter, outputs_file],
        capture_output=True,
        text=True
    )
    print(r.stdout.strip())
    if "False" in r.stdout:
        all_ok = False

sys.exit(0 if all_ok else 1)
