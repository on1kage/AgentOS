import sys, os, json
from pathlib import Path

# === ARGUMENT PARSING ===
intent = sys.argv[1] if len(sys.argv) > 1 else 'utc_date'
run_id = sys.argv[2] if len(sys.argv) > 2 else 'local'
store_root = os.environ.get('STORE_ROOT', os.getcwd())
evidence_dir = Path(store_root)/'evidence'
evidence_dir.mkdir(parents=True, exist_ok=True)

# === PROBE EXECUTION ===
exit_code = 0
outputs = {}

try:
    outputs['utc_date'] = __import__('datetime').datetime.utcnow().strftime('%Y-%m-%d')
except Exception as e:
    outputs['error'] = str(e)
    exit_code = 1

# === WRITE EVIDENCE ===
evidence_file = evidence_dir/f'envoy_{intent}_{run_id}.json'
with open(evidence_file, 'w') as f:
    json.dump({'intent': intent, 'run_id': run_id, 'outputs': outputs, 'exit_code': exit_code}, f, indent=2)

sys.exit(exit_code)
