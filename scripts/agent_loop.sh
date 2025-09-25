#!/usr/bin/env bash
set -euo pipefail

# knobs
MAX_ROUNDS=${MAX_ROUNDS:-20}
LOG_DIR=${LOG_DIR:-.agent_logs}
MODE_NOOP_REGEX='MODE:[[:space:]]*(No-Op|Execute — No-Op)'
mkdir -p "$LOG_DIR"

round=0
while (( round < MAX_ROUNDS )); do
  round=$((round+1))
  echo "== Round $round: Auditor =="

  AUD_LOG="$LOG_DIR/auditor_$round.log"
  codex --auto-edit <<'EOF' | tee "$AUD_LOG"
$(cat AGENT.md)
EOF

  # Show the agent’s declared output block if present
  awk '/^OUTPUT LOG/{flag=1;print;next} /^COMMIT:/{print;flag=0} flag' "$AUD_LOG" || true

  # Stop if the Auditor says there’s nothing left
  if grep -qi "$MODE_NOOP_REGEX" "$AUD_LOG"; then
    echo "Auditor reports No-Op. Done."
    exit 0
  fi

  echo "== Round $round: Executor =="
  EXE_LOG="$LOG_DIR/executor_$round.log"
  codex --auto-edit <<'EOF' | tee "$EXE_LOG"
$(cat AGENT.EXECUTOR.md)
EOF

  # Echo executor’s summary too
  awk '/^MODE: Execute/{print;flag=1;next} /^COMMIT:/{print;flag=0} flag' "$EXE_LOG" || true

  # If executor has no work, keep looping; the next audit may create tasks
  if grep -qi 'MODE:[[:space:]]*Execute — No-Op' "$EXE_LOG"; then
    echo "Executor had no work this round."
  fi
done

echo "Hit MAX_ROUNDS=$MAX_ROUNDS without No-Op. Check $LOG_DIR/ for full transcripts."
exit 1
