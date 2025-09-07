#!/usr/bin/env bash
set -euo pipefail

# --- config knobs ---
AUDITOR_CMD=${AUDITOR_CMD:-"codex exec --approval-mode auto-edit --quiet --json --prompt-file AGENTS.md"}
EXECUTOR_CMD=${EXECUTOR_CMD:-"codex exec --approval-mode auto-edit --quiet --json --prompt-file AGENTS.EXECUTOR.md"}
MAX_ROUNDS=${MAX_ROUNDS:-20}
LOG_DIR=${LOG_DIR:-.agent_logs}
mkdir -p "$LOG_DIR"

round=0
while (( round < MAX_ROUNDS )); do
  round=$((round+1))
  echo "== Round $round: Auditor =="
  
  # Run Auditor and log output
  "$AUDITOR_CMD" 2>&1 | tee "$LOG_DIR/auditor_$round.log"
  # Display the agent's OUTPUT LOG
  echo "---- Auditor OUTPUT LOG ----"
  grep -A1000 '"MODE":' "$LOG_DIR/auditor_$round.log" || echo "(no OUTPUT LOG found)"
  echo "----------------------------"
  
  # Stop if Auditor signals completion
  if grep -qi '"MODE":\s*"No-Op"' "$LOG_DIR/auditor_$round.log"; then
    echo "Auditor reports No-Op. Done."
    exit 0
  fi
  
  echo "== Round $round: Executor =="
  
  "$EXECUTOR_CMD" 2>&1 | tee "$LOG_DIR/executor_$round.log"
  echo "---- Executor OUTPUT LOG ----"
  grep -A1000 '"MODE":' "$LOG_DIR/executor_$round.log" || echo "(no OUTPUT LOG found)"
  echo "-----------------------------"
  
  # Optional: Executor had no tasks
  if grep -qi '"MODE":\s*"Execute — No-Op"' "$LOG_DIR/executor_$round.log"; then
    echo "Executor had no work this round."
  fi
done

echo "Hit MAX_ROUNDS=$MAX_ROUNDS without No-Op. Check $LOG_DIR/ for details."
exit 1

