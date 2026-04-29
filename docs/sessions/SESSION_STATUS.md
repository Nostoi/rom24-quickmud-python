# Session Status — 2026-04-28 — `tables.c` audit Phase 1+2 complete (⚠️ Partial)

## Current State

- **Active audit**: `tables.c` — Phase 1 inventory + Phase 2 spot-checks complete; 3 gaps documented and **deferred**. Critical finding: `AffectFlag` bit positions diverge from ROM `merc.h` (TABLES-001), reproducer landed as `xfail` strict.
- **Last completed**: `tables.c` audit doc + reproducer test suite; tracker row refreshed; CHANGELOG updated; version 2.6.31.
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-04-28_TABLES_C_AUDIT_PHASE_1_2.md](SESSION_SUMMARY_2026-04-28_TABLES_C_AUDIT_PHASE_1_2.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.6.31 |
| Tests | `tests/integration/test_tables_parity.py` 4 passed + 1 xfail (TABLES-001 reproducer); lookup/flag parity suites green |
| ROM C files audited | 27 / 43 (`tables.c` stays ⚠️ Partial 75%) |
| Active focus | TABLES-001 (CRITICAL, AffectFlag bit-pos divergence) — deferred until persistence migration plan |

## Next Intended Task

**TABLES-001** is the highest-impact next move but is risk-bearing — it needs a persistence migration design before code change. Recommended ordering:

1. **TABLES-002** — add ROM-name aliases on diverging IntFlag members (`ActFlag`, `PlayerFlag`, `OffFlag` lowercase ROM-table names) so `do_flag` / OLC accept ROM-style abbreviations like `npc`, `healer`, `dirt_kick`, `can_loot`. No persistence risk; close per-IntFlag.
2. **TABLES-003** — iterate the remaining ~30 tables and finish Phase 2 letter→bit verification. Likely 1-2 sessions; may surface more value-divergences like TABLES-001.
3. **TABLES-001** — focused session with persistence-migration plan: bump pfile schema version, on-load translate old `affected_by` ints, renumber `AffectFlag` to match `merc.h:953-982`, flip xfail to xpass.

Other candidates outside `tables.c`:

- **`board.c`** (P2 35%) — boards subsystem; mid-scope.
- **Deferred NANNY trio** (NANNY-008/009/010) — each architectural-scope.
- **OLC cluster** — `olc.c`/`olc_act.c`/`olc_save.c`/`olc_mpcode.c`/`hedit.c`. Multi-session block; would unblock `bit.c` and `string.c`.

## Pre-existing test/lint failures (not caused by this session)

- `tests/test_commands.py` 4 failures (alias / scan-directional / typo guards) and `tests/test_building.py` 14 failures — from another in-flight session.
- `mud/models/races.py` 8 ruff errors (typing.Tuple → tuple, typing.Type → type, import sort) pre-dating this session.
