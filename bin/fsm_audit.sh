#!/usr/bin/env bash
set -euo pipefail

echo "[FSM-AUDIT] Starting OneMind FSM audit"

# Locate kernel
KERNEL_DIR="${ONEMIND_KERNEL_DIR:-$HOME/onemind-FSM-Kernel}"
if [[ ! -d "$KERNEL_DIR" ]]; then
  echo "[FSM-AUDIT][FAIL] Kernel not found at $KERNEL_DIR"
  exit 1
fi

export PYTHONPATH="$KERNEL_DIR/src${PYTHONPATH:+:$PYTHONPATH}"

echo "[FSM-AUDIT] Using kernel at $KERNEL_DIR"
echo "[FSM-AUDIT] Running persistent bootstrap (timeout)"

set +e
OUTPUT=$(timeout 6s python3 -u "$KERNEL_DIR/bin/oneMind_persistent_bootstrap.py" 2>&1)
RC=$?
set -e

echo "$OUTPUT"

if [[ $RC -ne 0 && $RC -ne 124 ]]; then
  echo "[FSM-AUDIT][FAIL] Kernel bootstrap failed (rc=$RC)"
  exit 1
fi

# Basic compliance check: must see audit header
if ! echo "$OUTPUT" | grep -q "OneMind Kernel Full Subsystem Audit"; then
  echo "[FSM-AUDIT][FAIL] Audit header not found"
  exit 1
fi

echo "[FSM-AUDIT][OK] Kernel audit completed"
