#!/usr/bin/env bash
# scripts/executor_only.sh
set -euo pipefail

# --- knobs you can tweak ---
MAX_ROUNDS=${MAX_ROUNDS:-20}
LOG_DIR=${LOG_DIR:-.agent_logs}
WORKDIR=${WORKDIR:-.}  # repo root
RUN_FLAGS=${RUN_FLAGS:-"--json --full-auto -s workspace-write -C ${WORKDIR}"}  # safe, auto, workspace write
PLAN_FILE=${PLAN_FILE:-"PYTHON_PORT_PLAN.md"}

mkdir -p "$LOG_DIR"

# Extract the JSON payload inside <!-- OUTPUT-JSON ... --> from a text file
extract_output_json () {
  awk '/<!-- OUTPUT-JSON/{flag=1; next} /OUTPUT-JSON -->/{flag=0} flag' "$1" | sed '/^\s*$/d' || true
}

# Quick check: are there any open tasks left in the plan? (P0/P1/P2 not marked with ✅)
has_open_tasks () {
  # Limit search to the Parity Gaps block if present; else search whole file
  if awk '/<!-- PARITY-GAPS-START -->/{p=1;next} /<!-- PARITY-GAPS-END -->/{p=0} p' "$PLAN_FILE" >/dev/null 2>&1; then
    awk '/<!-- PARITY-GAPS-START -->/{p=1;next} /<!-- PARITY-GAPS-END -->/{p=0} p' "$PLAN_FILE" \
      | grep -E '^- \[P[0-2]\]' >/dev/null 2>&1
  else
    grep -E '^- \[P[0-2]\]' "$PLAN_FILE" >/dev/null 2>&1
  fi
}

run_executor_once () {
  local RAW_LOG="$1"
  local LAST_MSG="$2"

  # Run Codex Exec with prompt from file; JSONL to RAW_LOG, final assistant panel to LAST_MSG
  codex exec $RUN_FLAGS --output-last-message "$LAST_MSG" < AGENT.EXECUTOR.md 2>&1 | tee "$RAW_LOG" >/dev/stderr || true

  # Prefer OUTPUT-JSON from LAST_MSG; fall back to RAW_LOG if needed
  local OUT_JSON
  OUT_JSON="$(extract_output_json "$LAST_MSG")"
  if [[ -z "$OUT_JSON" ]]; then
    OUT_JSON="$(extract_output_json "$RAW_LOG")"
  fi

  if [[ -n "$OUT_JSON" ]]; then
    echo "$OUT_JSON"
  else
    echo "{}"
  fi
}

round=0
while (( round < MAX_ROUNDS )); do
  round=$((round+1))
  echo "== Executor-only run: Round $round =="

  EXE_RAW="$LOG_DIR/executor_only_${round}.jsonl"
  EXE_LAST="$LOG_DIR/executor_only_${round}.last.txt"
  EXE_JSON="$(run_executor_once "$EXE_RAW" "$EXE_LAST")"

  echo "EXECUTOR OUTPUT-JSON:"
  echo "$EXE_JSON"

  # Stop conditions:
  # 1) Executor reports No-Op mode explicitly in OUTPUT-JSON or last message
  if grep -qi '"mode"\s*:\s*"Execute — No-Op"' <<<"$EXE_JSON" || grep -qi 'Execute — No-Op' "$EXE_LAST"; then
    echo "Executor reports No-Op. Done."
    exit 0
  fi

  # 2) Plan has no open tasks (no - [P0]/[P1]/[P2] lines)
  if ! has_open_tasks; then
    echo "No open tasks remain in ${PLAN_FILE}. Done."
    exit 0
  fi

  # Otherwise, loop again (the executor may complete tasks incrementally)
done

echo "Hit MAX_ROUNDS=${MAX_ROUNDS} without reaching No-Op and tasks still remain."
echo "Check logs in ${LOG_DIR}/ for details."
exit 1
