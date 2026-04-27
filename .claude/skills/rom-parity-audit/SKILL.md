---
name: rom-parity-audit
description: Run a full ROM 2.4b6 → Python parity audit on a single ROM C source file (e.g. act_obj.c, scan.c, special.c). Use when starting a new file-level audit, when the user says "audit X.c", or when ROM_C_SUBSYSTEM_AUDIT_TRACKER.md shows a P0/P1 file as Partial/Not Audited. Encodes the 5-phase methodology: (1) read ROM C and Python entry point, (2) write per-file audit doc with gap table, (3) ID gaps with stable IDs (FILE-001 etc.), (4) close gaps via integration tests + implementation (defer to rom-gap-closer per gap), (5) flip tracker rows and write a session summary. Not for single-gap closures — use rom-gap-closer for those.
---

# ROM Parity Audit (per-file)

You are auditing one ROM 2.4b6 C source file against its QuickMUD Python equivalent. Source of truth is the ROM C — when behavior diverges, the Python is wrong unless explicitly documented otherwise.

## Inputs you need

- The ROM C file under `src/<file>.c` (read-only reference).
- The QuickMUD Python module(s) listed for that file in `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`.
- The per-file audit doc (create at `docs/parity/<FILE>_C_AUDIT.md` if it doesn't exist; follow the format used by `ACT_OBJ_C_AUDIT.md`, `ACT_ENTER_C_AUDIT.md`, `HANDLER_C_AUDIT.md`).

## Mandatory reading before you start

- `docs/ROM_PARITY_VERIFICATION_GUIDE.md` — non-negotiable. Read sections "Three Levels of Verification" and "Common Parity Pitfalls" before writing the audit doc.
- `AGENTS.md` ROM Parity Rules section — RNG, integer math, flag enums, `char.equipment[WearLocation.X]`, `room.people`, no deferring P2/optional.

## The 5 phases

### Phase 1 — Inventory

1. List every public ROM function in `src/<file>.c` (function definitions, not statics).
2. For each, locate the Python counterpart. Use `gitnexus_query({query: "<concept>"})` first; fall back to `grep -rn "def do_<name>" mud/`.
3. Record the mapping in the audit doc's "Phase 2 Function Map" table — one row per ROM function with: ROM line range, Python file:line, status (✅ AUDITED / 🔄 IN PROGRESS / ❌ MISSING / ⚠️ PARTIAL / N/A).

### Phase 2 — Line-by-line verification (P0/P1 functions only)

For each P0/P1 function:

1. Read the ROM C function top-to-bottom alongside the Python.
2. Check for these recurring gap categories (see `docs/ROM_PARITY_VERIFICATION_GUIDE.md` "Common Parity Pitfalls"):
   - **Missing TO_ROOM `act()` broadcasts** — ROM emits two messages (TO_CHAR + TO_ROOM); Python often only has TO_CHAR.
   - **RNG drift** — `random.*` in Python where ROM uses `number_*`. Must use `mud.math.rng_mm`.
   - **Integer math drift** — `//` / `%` in Python where ROM uses C signed division. Must use `c_div`/`c_mod`.
   - **Flag value drift** — hardcoded hex constants. Must use IntEnum (`PlayerFlag.X`, `WearFlag.X`).
   - **Wrong attribute names** — `char.carrying` (wrong) vs `char.inventory` (right); `room.characters` (wrong) vs `room.people` (right); `char.equipped["held"]` (wrong) vs `char.equipment[WearLocation.HOLD]` (right).
   - **Immortal bypass missing** — many ROM commands skip type checks / fullness / encumbrance for `is_immortal()`.
   - **Pre-checks skipped** — drunk/full/thirst pre-checks before the main op.
   - **Affect calculations** — duration, level, modifier, location must match ROM exactly.
3. Citing line ranges (`src/<file>.c:NNN-MMM`) is mandatory.

### Phase 3 — Gap identification

For each divergence, add a row to the audit doc's "Gaps" table with:

- **Gap ID**: `<FILE_PREFIX>-NNN` where prefix is the command/feature (e.g. `DROP-001`, `ENTER-002`, `HANDLER-014`). IDs are stable forever — never renumber.
- **Severity**: CRITICAL (visible behavior diverges, e.g. wrong damage / wrong message / wrong save) / IMPORTANT (broadcast or wording wrong) / MINOR (cosmetic).
- **ROM C reference**: file:line.
- **Python reference**: file:line.
- **Description**: one sentence on what's wrong.
- **Status**: 🔄 OPEN initially.

### Phase 4 — Gap closure

Per gap, hand off to **rom-gap-closer** (one gap = one TDD cycle). Do not batch. Each gap closure must:

1. Have an integration test in `tests/integration/test_<area>.py` that fails before the fix.
2. Reference ROM C source in a code comment (`# mirroring ROM src/<file>.c:NNN`).
3. Update the audit doc row to ✅ FIXED.
4. Land in a single commit with `feat(parity)` or `fix(parity)` prefix.

Critical gaps with HIGH/CRITICAL `gitnexus_impact` results MUST be reported to the user before editing.

### Phase 5 — Closure

When all P0/P1 gaps are closed:

1. Flip the tracker row in `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` to ✅ AUDITED with the new percentage.
2. Update the file's status block at the top of the tracker (e.g. "act_obj.c Status: ✅ 100% COMPLETE").
3. Update CHANGELOG.md under `[Unreleased]` with `Added` / `Fixed` lines per gap closed.
4. Hand off to **rom-session-handoff** to write `docs/sessions/SESSION_SUMMARY_<date>_<file>.md` and refresh `SESSION_STATUS.md`.
5. Bump `pyproject.toml` patch version (per AGENTS.md Repo Hygiene).

## Audit doc skeleton

When creating a new `<FILE>_C_AUDIT.md`, mirror the structure of `docs/parity/ACT_OBJ_C_AUDIT.md`. Required sections:

- Status header (date, % complete, current phase)
- Phase 1: function inventory table
- Phase 2: function-by-function verification (one subsection per P0/P1 function)
- Phase 3: gap table (all gaps with stable IDs)
- Phase 4: gap closures (one subsection per closed gap with the test name + commit reference)
- Phase 5: completion summary

## What "done" means

- All P0/P1 functions verified line-by-line against ROM C.
- All CRITICAL and IMPORTANT gaps closed with integration tests.
- MINOR/cosmetic gaps may be deferred (document in the audit doc).
- `pytest tests/integration/test_<area>.py` green.
- Tracker row flipped, CHANGELOG updated, session summary written.

## Anti-patterns

- ❌ Marking gaps "P2 — optional" to skip them. Per AGENTS.md, parity gaps are always P0.
- ❌ Updating the tracker before closing the gaps.
- ❌ "More iterations until something happens" tests without seeding `rng_mm.seed_mm(<seed>)`.
- ❌ A test asserting Python behavior over ROM behavior. ROM is the source of truth — fix the test, not the implementation.
- ❌ Fixing multiple gaps in one commit. One gap, one commit, one test.
