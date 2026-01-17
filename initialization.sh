#!/usr/bin/env zsh
set -euo pipefail

cd ~/ChatGPTProtocol || exit 1

export PYTHONPATH=""
for sub in Macrobrain onemind-FSM-Kernel AgentOS TRadar RiskCore storm Chain-Lightning Credit-Pulse DataForge TRawler Arktic; do
    export PYTHONPATH="$HOME/$sub/src:$PYTHONPATH"
done

echo "[INIT] Enforced rule: no comment lines allowed in any shell scripts"
files=$(find . -type f -name "*.sh")
for f in $files; do
    if grep -q '^\s*#' "$f"; then
        echo "[ENFORCEMENT] ERROR: Comment lines detected in $f"
        exit 1
    fi
done

echo "[INIT] Verifying OneMind FSM before any work..."
bin/init_fsm_first.sh
echo "[INIT] FSM verification passed."

echo "[INIT] Starting ChatGPTProtocol FSM..."
./init_chatgpt.sh
echo "[INIT] ChatGPTProtocol FSM initialized successfully."
