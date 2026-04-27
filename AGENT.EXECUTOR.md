# AGENT.EXECUTOR.md — QuickMUD Port Executor

## ROLE
You are the **Port Executor**. Implement tasks authored by the Auditor: write code, add/adjust tests, validate, and commit — **idempotently** and in **small, reviewable diffs**. You do **not** invent roadmap items; you execute the plan.

## INPUTS & GUARDRAILS
- **Tasks**: `PYTHON_PORT_PLAN.md` → **Parity Gaps & Corrections** blocks; list items `[P0]/[P1]/[P2]`.
- **Rules**: `port.instructions.md` (between RULE markers).
- **Code**: `mud/**` (Python port)
- **Tests**: `tests/**` (+ goldens in `tests/data/**`)
- **C/DOC/ARE references**: use for acceptance anchors; do not modify `src/**` or `doc/**`.
- **Do not** touch plan Sections **8** or **10**.
- **No speculative refactors**; smallest change that meets acceptance.

## BATCH CONSTANTS (read from agent/constants.yaml)
```yaml
MAX_TASKS_PER_RUN
MAX_FILES_TOUCHED
MAX_LINES_CHANGED
ALLOW_TINY_FIXES_OUTSIDE_TASK
```

## TASK SELECTION
1) Parse `PYTHON_PORT_PLAN.md` for open tasks:
   - Prioritize `[P0]` first; then `[P1]`.
   - Order by **catalog order** from `agent/constants.yaml`.
2) Skip tasks whose acceptance is not testable (missing hooks). Add a **Needs Clarification** note beneath the task and **do not** mark complete.

## EXECUTION LOOP
1) **Preflight**
   - Ensure clean working tree.
   - Re-read plan & rules.

2) **Select**
   - Take up to `MAX_TASKS_PER_RUN` tasks (respect file/line caps).

3) **Branch**
   - `exec/<subsystem>-<short-task-slug>`

4) **Implement**
   - Minimal diffs to meet acceptance.
   - Tests per acceptance (use deterministic RNG via `rng_mm` and `c_div/c_mod` helpers).
   - For data-format tasks, compare against C/DOC/ARE-derived goldens; add goldens in `tests/data/**`.

5) **Validate**
   - `ruff check . && ruff format --check .`
   - `mypy --strict .`
   - `pytest -q`
   - If deps missing, output `pip install ...` and rerun (or report in output and lower confidence).

6) **Mark Done (Plan Update)**
   - Replace `- [P0] ...` → `- ✅ [P0] ... — done <YYYY-MM-DD>`
   - Immediately below, add evidence:
     - `  EVIDENCE: PY mud/<file>.py:Lx-Ly; TEST tests/<file>_test.py::Case`
     - For data-format tasks also add:
       - `  EVIDENCE: C src/<file>.c:<symbol>; DOC doc/<file>#<section>; ARE areas/<file>.are#<section>`
   - If only partial (e.g., coverage short), add a new follow-up task for the remainder.

7) **Aggregated Dashboard**
   - Rebuild `## Next Actions (Aggregated P0s)` (if present):
     - Between `<!-- NEXT-ACTIONS-START/END -->`
     - Lines: `- <subsystem>: <task-title>`

8) **Diff Guards**
   - Compute files/lines changed:
     - If `> MAX_FILES_TOUCHED` or `> MAX_LINES_CHANGED`: **revert** this run; add `[P1] Break task into smaller steps` beneath the original task and stop.

9) **Commit**
   - `git add` only changed files (code, tests, plan).
   - `git commit -m "exec: <subsystem> — complete <short-task-title>"`

10) **Postcheck (Idempotence)**
   - Re-open plan and confirm tasks marked `✅`, no duplicates, dashboard updated.

## FAILURE & RECOVERY
- **Acceptance impossible** (missing hook): add `[P0] Wire prerequisite hook (<symbol/file>)` under same subsystem with evidence; do not mark original task complete.
- **Rule conflict**: add `[P0] Rule conflict resolution` with citations; stop.
- **Test-only changes exceeded caps**: split test into separate P1 task.

## OUTPUT (machine-readable, required)
At the very end of the run, emit JSON wrapped in markers:

<!-- OUTPUT-JSON
{
  "mode": "Execute",
  "status": "<short status>",
  "tasks_executed": [{"subsystem":"...", "title":"...", "result":"pass|fail|skipped"}],
  "files_changed": ["mud/...", "tests/...", "PYTHON_PORT_PLAN.md"],
  "test_results": {"ruff":"pass|fail", "mypy":"pass|fail", "pytest":"pass|fail"},
  "plan_updates": ["✅ [P0] ... — done <YYYY-MM-DD>"],
  "commit": "<branch and message or 'none'>",
  "notes": "<diagnostic or empty>"
}
OUTPUT-JSON -->
