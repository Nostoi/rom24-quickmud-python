#!/usr/bin/env bash
# scripts/agent_loop.sh
set -euo pipefail

# Resolve repo root
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# --- knobs you can tweak ---
MAX_ROUNDS=${MAX_ROUNDS:-20}
LOG_DIR=${LOG_DIR:-"$REPO_ROOT/.agent_logs"}
WORKDIR=${WORKDIR:-"$REPO_ROOT"}   # Codex working directory

# Sensible default flags: JSONL events, sandboxed workspace write, auto-run in sandbox, set working dir
RUN_FLAGS=${RUN_FLAGS:-"--json --full-auto -s workspace-write --cd ${WORKDIR}"}

# Prompt files (override with env if you keep them elsewhere)
AUD_PROMPT_FILE=${AUD_PROMPT_FILE:-"$REPO_ROOT/AGENT.md"}
EXE_PROMPT_FILE=${EXE_PROMPT_FILE:-"$REPO_ROOT/AGENT.EXECUTOR.md"}

mkdir -p "$LOG_DIR"

# Helper: extract the JSON payload inside <!-- OUTPUT-JSON ... -->
extract_output_json () {
  local file="$1"
  awk '/<!-- OUTPUT-JSON/{flag=1; next} /OUTPUT-JSON -->/{flag=0} flag' "$file" | sed '/^\s*$/d' || true
}

# Run Codex once with a given prompt file; prints extracted OUTPUT-JSON to stdout (or empty)
run_codex () {
  local PROMPT_FILE="$1"
  local RAW_LOG="$2"
  local LAST_MSG="$3"

  # Ensure last msg file exists (Codex will overwrite it)
  : > "$LAST_MSG"

  # Feed prompt via stdin; tee JSONL stream to RAW_LOG
  # NOTE: no --prompt-file flag; stdin is the prompt
  codex exec $RUN_FLAGS --output-last-message "$LAST_MSG" < "$PROMPT_FILE" 2>&1 | tee "$RAW_LOG" >/dev/stderr || true

  # Prefer extracting OUTPUT-JSON from the final message; fall back to the JSONL log
  local OUT_JSON
  OUT_JSON="$(extract_output_json "$LAST_MSG")"
  if [[ -z "$OUT_JSON" ]]; then
    OUT_JSON="$(extract_output_json "$RAW_LOG")"
  fi
  echo "${OUT_JSON:-}"
}

# Friendly check for required files
missing=0
for f in "$AUD_PROMPT_FILE" "$EXE_PROMPT_FILE"; do
  if [[ ! -f "$f" ]]; then
    echo "ERROR: Missing prompt file: $f" >&2
    missing=1
  fi
done
if (( missing )); then
  echo "Tip: place AGENT.md and AGENT.EXECUTOR.md at $REPO_ROOT/, or set AUD_PROMPT_FILE/EXE_PROMPT_FILE env vars." >&2
  exit 1
fi

round=0
while (( round < MAX_ROUNDS )); do
  round=$((round+1))
  echo "== Round $round: Auditor =="

  AUD_JSONL="$LOG_DIR/auditor_${round}.jsonl"
  AUD_LAST="$LOG_DIR/auditor_${round}.last.txt"
  AUD_JSON="$(run_codex "$AUD_PROMPT_FILE" "$AUD_JSONL" "$AUD_LAST")"

  echo "---- Auditor OUTPUT-JSON ----"
  if [[ -n "$AUD_JSON" ]]; then
    echo "$AUD_JSON"
  else
    echo "(no OUTPUT-JSON block found)"
  fi
  echo "-----------------------------"

  # Stop if Auditor says No-Op
  if grep -qi '"mode"\s*:\s*"No-Op"' <<<"${AUD_JSON:-}"; then
    echo "Auditor reports No-Op. Done."
    exit 0
  fi

  echo "== Round $round: Executor =="
  EXE_JSONL="$LOG_DIR/executor_${round}.jsonl"
  EXE_LAST="$LOG_DIR/executor_${round}.last.txt"
  EXE_JSON="$(run_codex "$EXE_PROMPT_FILE" "$EXE_JSONL" "$EXE_LAST")"

  echo "---- Executor OUTPUT-JSON ----"
  if [[ -n "$EXE_JSON" ]]; then
    echo "$EXE_JSON"
  else
    echo "(no OUTPUT-JSON block found)"
  fi
  echo "------------------------------"

  # Optional: note if executor had nothing to do
  if grep -qi '"mode"\s*:\s*"Execute — No-Op"' <<<"${EXE_JSON:-}"; then
    echo "Executor had no work this round."
  fi
done

echo "Hit MAX_ROUNDS=$MAX_ROUNDS without No-Op. See $LOG_DIR/ for details."
exit 1
