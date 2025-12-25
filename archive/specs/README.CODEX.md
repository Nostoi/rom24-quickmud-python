# README.CODEX.md — Using Codex with the QuickMUD Port

This document explains **how to run Codex** against this repository using our two agents:

- **Auditor** (`AGENT.md`) — scans code & docs, updates the plan (`PYTHON_PORT_PLAN.md`) and rules (`port.instructions.md`), and may propose tiny safe fixes.
- **Executor** (`AGENT.EXECUTOR.md`) — implements tasks from the plan, updates tests & code, validates, and marks tasks complete.

You can run them **together** in a loop or run **Executor-only** when you just want to implement already-queued tasks.

---

## 0) Prerequisites

- **Git** repo with a clean working tree (`git status` should show no unstaged changes).
- **Python** v3.10+ with your venv active if you plan to run tests locally.
- **Codex CLI** installed:
  ```bash
  # macOS (Homebrew)
  brew tap openai/codex
  brew install codex

  # Or: curl installer (fictional example if brew is unavailable)
  # curl -fsSL https://codex.install.sh | bash
  ```
- Optional but recommended: `ripgrep`, `ruff`, `mypy`, `pytest` available in your environment.

> The Codex CLI can run **without API keys** for local sandboxed workflows. If your setup prompts for login, follow `codex login` once.

---

## 1) Key Files & Folders

- `AGENT.md` — **Auditor** prompt (parity analysis; writes tasks/rules; tiny fixes).
- `AGENT.EXECUTOR.md` — **Executor** prompt (implements plan tasks).
- `PYTHON_PORT_PLAN.md` — plan of record (coverage matrix + **Parity Gaps & Corrections**).
- `port.instructions.md` — rules added by the Auditor between `<!-- RULES-START/END -->`.
- `agent/constants.yaml` — knobs (catalog, risk labels, batch limits) the prompts reference.
- `.agent_logs/` — logs written by our runner scripts.
- `scripts/agent_loop.sh` — **Auditor → Executor** loop runner (pairs both).
- `scripts/executor_only.sh` — **Executor-only** loop runner.

---

## 2) Quick Start: Auditor → Executor loop

This drives **both agents** round-robin until the Auditor reports **No-Op** (i.e., parity achieved or nothing more to add).

```bash
chmod +x scripts/agent_loop.sh
scripts/agent_loop.sh
```

What it does:
- Runs `AGENT.md` via `codex exec` with safe defaults.
- Parses the Auditor’s `<!-- OUTPUT-JSON ... OUTPUT-JSON -->` block.
- If **No-Op** → stops. Otherwise runs `AGENT.EXECUTOR.md`.
- Repeats up to `MAX_ROUNDS` (default 20).

### Tuning (Environment Variables)

- `MAX_ROUNDS` — maximum Auditor/Executor cycles (default `20`).
- `LOG_DIR` — directory for logs (default `.agent_logs`).
- `WORKDIR` — repo root used by Codex (default `.`).
- `RUN_FLAGS` — advanced Codex flags (default `--json --full-auto -s workspace-write -C ${WORKDIR}`).

Example with a different workdir:
```bash
WORKDIR=$(pwd) LOG_DIR=.agent_logs scripts/agent_loop.sh
```

Logs to check:
- `.agent_logs/auditor_<N>.jsonl` — JSONL event stream from Codex.
- `.agent_logs/auditor_<N>.last.txt` — final pretty panel from the Auditor.
- Ditto `executor_<N>.*` for the Executor.

---

## 3) Executor-Only loop

When the plan already has tasks and you just want to **implement** them:

```bash
chmod +x scripts/executor_only.sh
scripts/executor_only.sh
```

Stop conditions:
- Executor returns `mode: "Execute — No-Op"` in OUTPUT-JSON, **or**
- No `- [P0]` / `- [P1]` / `- [P2]` lines remain inside `PYTHON_PORT_PLAN.md`.

Environment knobs (same as above) plus:

- `PLAN_FILE` — path to the plan (default `PYTHON_PORT_PLAN.md`).

---

## 4) One-shot runs (no loops)

Sometimes you just want a **single pass**:

### Auditor once
```bash
codex exec --json --full-auto -s workspace-write -C . < AGENT.md \
  | tee .agent_logs/auditor_single.jsonl >/dev/stderr
```

### Executor once
```bash
codex exec --json --full-auto -s workspace-write -C . < AGENT.EXECUTOR.md \
  | tee .agent_logs/executor_single.jsonl >/dev/stderr
```

> The prompts are self-contained: they will read and update the plan/rules and produce a concise output log. The loop scripts simply automate multiple passes and extract the `OUTPUT-JSON` blocks for you.

---

## 5) Interpreting the Output

Both prompts print a machine-readable block at the end:

```text
<!-- OUTPUT-JSON
{
  "mode": "Discovery | Parity Audit | Execute | No-Op | Error",
  "status": "short summary",
  "files_updated": ["PYTHON_PORT_PLAN.md", "port.instructions.md", "mud/... (if tiny fix)"],
  "next_actions": ["<P0 or P1 summary items>"],
  "commit": "branch + message OR 'none'",
  "notes": "diagnostics (e.g., 'pip install jsonschema')"
}
OUTPUT-JSON -->
```

Your loop scripts extract that block and echo it. If you’re running one-shot, scroll to the end of the last message to read it.

---

## 6) Typical Workflow

1. **Run the Auditor → Executor loop**:
   ```bash
   scripts/agent_loop.sh
   ```
   The Auditor updates the plan & rules; the Executor implements some tasks.

2. **Check diffs**:
   ```bash
   git status
   git diff
   ```
   If you’re happy, let Codex commit (the prompts will do small commits as they go). Otherwise, make manual edits and re-run.

3. **Executor-only to finish queued work**:
   ```bash
   scripts/executor_only.sh
   ```

4. **Manual coding** is always allowed. Keep the plan up to date; the Auditor will reconcile on the next pass.

---

## 7) Troubleshooting

- **“codex: command not found”**  
  Install the CLI (see prerequisites) and ensure it’s on your `PATH`.

- **No output / empty OUTPUT-JSON**  
  Check `.agent_logs/*last.txt` for the pretty transcript; errors often show there. The loop scripts already try both sources.

- **Sandbox limits**  
  The scripts default to `-s workspace-write` and `--full-auto`. If you need broader access (e.g., network), remove or adjust flags **carefully**.

- **Test failures due to missing deps**  
  The OUTPUT-JSON’s `notes` frequently lists `pip install` suggestions. Install them in your venv, re-run.

- **Git not clean**  
  Commit or stash your changes first. Codex expects a clean working tree for safe diffs/commits.

---

## 8) Safety & Scope

- The Auditor **does not** modify plan Sections **8** and **10**.
- The Auditor **forbids** suggestions around “plugin(s)” and unrelated refactors.
- Both agents cap changed files/lines per run; they’ll split work into small diffs.
- The Executor only implements tasks already in the plan.

---

## 9) Advanced: Custom Flags

You can override the runner flags via `RUN_FLAGS`. Examples:

- **Read-only dry run**:
  ```bash
  RUN_FLAGS="--json -s read-only -C ." scripts/agent_loop.sh
  ```

- **Colorized human output (no JSON)**:
  ```bash
  RUN_FLAGS="--full-auto -s workspace-write -C . --color always" scripts/executor_only.sh
  ```

---

## 10) Expected End State

When parity is achieved and no tasks remain, the Auditor appends a **Completion Note** to `PYTHON_PORT_PLAN.md` and returns `mode: "No-Op"`. The loop stops. Executor-only also stops when no `[P0|P1|P2]` tasks exist.

Happy porting — let the bots grind while you keep the compass true.
