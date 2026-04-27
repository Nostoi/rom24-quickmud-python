---
name: rom-session-handoff
description: Write the end-of-session deliverables for QuickMUD ROM-parity work — generate docs/sessions/SESSION_SUMMARY_<date>_<topic>.md and refresh docs/sessions/SESSION_STATUS.md from the session's git diff and trackers touched. Use when the user says "wrap up", "write the session summary", "session handoff", at end of a parity audit, or after rom-gap-closer batches. Follows the AGENTS.md "Session Notes" conventions exactly.
---

# ROM Session Handoff

You are producing the end-of-session deliverables for a QuickMUD ROM-parity work session. Two files always change; CHANGELOG and version may change too.

## Always-required deliverables

1. **`docs/sessions/SESSION_SUMMARY_YYYY-MM-DD_<short-topic>.md`** — new file. Append-only log; never overwrite previous summaries.
2. **`docs/sessions/SESSION_STATUS.md`** — overwrite with current state. Single canonical "current" pointer.

## Conditional deliverables

- **`CHANGELOG.md`** — if any user-visible/dev-visible behavior changed (almost always for parity work).
- **`pyproject.toml`** version bump — if anything is being pushed to a branch / PR / master (per AGENTS.md Repo Hygiene §3).
- **`docs/parity/<FILE>_C_AUDIT.md`** rows already flipped — verify, don't re-do.
- **`docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`** — flip the file's row if a whole file just hit 100%.

## Inputs to gather (mandatory, in this order)

```bash
git status
git diff --stat HEAD~5..HEAD       # broaden if session was longer
git log --oneline HEAD~10..HEAD    # spot the parity commits
ls -t docs/sessions/ | head -5     # last few summaries — match style
```

Then read:

- The most recent `SESSION_SUMMARY_*.md` to copy formatting and tone.
- Each `<FILE>_C_AUDIT.md` touched this session (to confirm gap-row status).

## SESSION_SUMMARY_*.md format

Mirror the structure of the most recent existing summary. The de-facto template:

```markdown
# Session Summary — YYYY-MM-DD — <short title (file or feature)>

## Scope

<One paragraph: what was attempted, where the session picked up from.>

## Outcomes

### `<gap-id-or-symbol>` — ✅ <AUDITED | FIXED | CLOSED>

- **Python**: `mud/.../<file>.py:NNN`
- **ROM C**: `src/<file>.c:NNN-MMM`
- **Gap (if applicable)**: <ID> — <one-line description>
- **Fix**: <what changed>
- **Tests**: <count + filename + result>

<Repeat per gap closed.>

## Files Modified

- `mud/...` — <one-line>
- `tests/integration/...` — <one-line>
- `docs/parity/<FILE>_C_AUDIT.md` — flipped rows: <IDs>
- `CHANGELOG.md` — added <Added/Fixed> entries
- `pyproject.toml` — X.Y.Z → X.Y.Z+1 (if bumped)

## Test Status

- `pytest tests/integration/test_<area>.py` — N/N passing
- Full suite: <run-or-skipped, with numbers>

## Next Steps

<One paragraph or bullet list. Concrete next gap ID(s) or audit phase.>
```

### Naming rules (from AGENTS.md)

- **Filename pattern**: `SESSION_SUMMARY_YYYY-MM-DD_<UPPER_SNAKE_TOPIC>.md`. Multi-session days get distinct topics (`..._ACT_OBJ_DROP.md`, `..._ACT_OBJ_RECITE.md`).
- **Handoff variant**: if the session ended mid-stream and another agent is picking up, use `HANDOFF_YYYY-MM-DD_<topic>.md` instead. Same directory.
- **Topic** is the audit area or gap cluster — short and specific. Bad: `..._WORK.md`. Good: `..._DO_DROP_GAPS_001-005.md`.

## SESSION_STATUS.md format

Overwrite the entire file. The canonical state pointer. Required sections:

```markdown
# Session Status — YYYY-MM-DD — <short title>

## Current State

- **Active audit**: `<file>.c` (Phase N — <description>)
- **Last completed**: <gap IDs or audit milestone>
- **Pointer to latest summary**: [SESSION_SUMMARY_YYYY-MM-DD_<topic>.md](SESSION_SUMMARY_YYYY-MM-DD_<topic>.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | <pyproject.toml> |
| Tests | <X / Y passing> |
| ROM C files audited | <N / 43> |
| Active focus | <file>.c (<%>) |

## Next Intended Task

<One paragraph: what the next session should pick up. Specific gap IDs or audit phase.>
```

Pull the version and test numbers from `pyproject.toml` and the latest pytest run respectively. If pytest hasn't been run this session, run it (the project documents the suite as ~8 minutes wall-clock).

## CHANGELOG.md update

Per AGENTS.md Repo Hygiene §1, add entries under `## [Unreleased]` (or a new version section if the version is being bumped this session).

- Use Keep a Changelog headings: `Added` / `Changed` / `Fixed` / `Removed`.
- One line per gap closed, citing the gap ID and ROM C reference:
  ```
  ### Fixed
  - `DROP-001` — TO_ROOM "$n drops $p." broadcast on do_drop (ROM src/act_obj.c:768).
  ```

## Version bump (when applicable)

Per AGENTS.md Repo Hygiene §3, bump `pyproject.toml` `version` if pushing/PRing:

- **patch** — parity gap closures, fixes, docs.
- **minor** — new commands, new gameplay features, new test infrastructure.
- **major** — breaking save-format / protocol / data-model changes.

Almost all parity work is patch.

## Pre-handoff verification

Before declaring the handoff complete:

```bash
ruff check .                                      # clean
pytest tests/integration/<area> -v                # area suite green
# gitnexus_detect_changes()  ← run via MCP
```

Confirm:

- All `<FILE>_C_AUDIT.md` rows you closed this session are ✅.
- `SESSION_STATUS.md` "Last completed" matches the new summary.
- `CHANGELOG.md` `[Unreleased]` lists every gap closed.
- `pyproject.toml` version matches what's about to be pushed (if anything is).

## What goes WHERE (do not duplicate)

| Information | Lives in |
|-------------|----------|
| Per-file audit detail (gaps, ROM C refs, test names) | `docs/parity/<FILE>_C_AUDIT.md` |
| Cross-file audit progress (43-file tracker) | `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` |
| Per-session narrative | `docs/sessions/SESSION_SUMMARY_*.md` |
| "What's the current state?" pointer | `docs/sessions/SESSION_STATUS.md` |
| User/dev-visible changes | `CHANGELOG.md` |
| Setup, parity badges, top-level metrics | `README.md` |
| Workflow rules / invariants | `AGENTS.md` |

If the session bumps top-level metrics (e.g. a whole ROM C file just hit 100%), AGENTS.md Repo Hygiene now requires a coordinated update of README + AGENTS tracker pointers + SESSION_STATUS in the same commit. Do all three.

## Anti-patterns

- ❌ Updating `SESSION_STATUS.md` without also writing the dated `SESSION_SUMMARY_*.md`. The summary is the durable history; the status pointer rots.
- ❌ Putting session narrative into `AGENTS.md` or `README.md`. They are stable surfaces.
- ❌ Skipping `CHANGELOG.md` because the change is "internal". Parity gap closures are user-visible by definition (they change game behavior).
- ❌ Editing the tracker doc to claim 100% before all gaps are actually closed. Source of truth — never optimistic.
- ❌ Vague topics in the filename (`SESSION_SUMMARY_..._WORK.md`). Future-you will not be able to find anything.
