import argparse
parser = argparse.ArgumentParser(description='Weekly proof runner with parameterized intent')
parser.add_argument('--intent', type=str, default='utc_date', help='Intent name for the run')
args, unknown = parser.parse_known_args()
intent_name = args.intent

from typing import Tuple, Dict, Any, List
from pathlib import Path
import json
import time
import shutil

from agentos.store_fs import FSStore
from agentos.canonical import canonical_json
from agentos.execution import ExecutionSpec, canonical_inputs_manifest
from agentos.executor import LocalExecutor
from agentos.evidence import EvidenceBundle
from agentos.outcome import ExecutionOutcome

scout_cmd = ['python3','-c',f'import sys,runpy; sys.path[:0]=['src','src/onemind-FSM-Kernel/src']; runpy.run_path(f'tools/scout_live_probe.py', run_name='__main__')']
envoy_cmd = ['python3','-c',f'import sys,runpy; sys.path[:0]=['src','src/onemind-FSM-Kernel/src']; runpy.run_path(f'tools/envoy_live_probe.py', run_name='__main__')']
