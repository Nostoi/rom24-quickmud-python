# Session Status — 2026-04-29 — `const.c` ✅ Audited (CONST-006 closed; file flip complete)

## Current State

- **Active audit**: none — `const.c` just flipped to ✅ Audited 95%. Pick the next file from `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`.
- **Last completed**: `CONST-006` (`advance_level` practice gain now `wis_app[get_curr_stat(STAT_WIS)].practice` mirroring `src/update.c:87`; new `WIS_APP[26]` table + `wis_practice_bonus(ch)` accessor in `mud/math/stat_apps.py`). File flip: `const.c` ⚠️ Partial 80% → ✅ Audited 95%. Commits `2ca5247` (gap), pending handoff commit (this) for version bump + summary.
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-04-29_CONST_006_WIS_PRACTICE.md](SESSION_SUMMARY_2026-04-29_CONST_006_WIS_PRACTICE.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.6.52 |
| Tests | 1455 passed / 10 skipped (full integration suite). |
| ROM C files audited | 19 / 43 (44%) ✅ Audited; `const.c` ✅ Audited 95% (CONST-001 + CONST-007 deferred-by-design). |
| Active focus | none — pick next file from the tracker. |

## `const.c` close-out

5 of 7 `const.c` gaps closed this session arc:

- ✅ `CONST-002` — `GET_HITROLL` augments with `str_app[STR].tohit`.
- ✅ `CONST-003` — `GET_DAMROLL` augments with `str_app[STR].todam`.
- ✅ `CONST-004` — `GET_AC` augments with `dex_app[DEX].defensive` (IS_AWAKE-gated).
- ✅ `CONST-005` — `advance_level` HP rolls `number_range(class.hp_min, class.hp_max) + con_app[CON].hitp`, ×9/10, UMAX(2).
- ✅ `CONST-006` — `advance_level` practice gain = `wis_app[WIS].practice`.

Deferred-by-design (intentionally not in `const.c` scope):

- 🔄 `CONST-001` `title_table` (480 entries) → NANNY-009 dedicated session.
- 🔄 `CONST-007` `weapon_table` (8 entries) → OLC audit.

## Next Intended Task

Pick the next file from `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`. Likely candidates:

1. **`recycle.c`** (P3) — currently ⚠️ Partial. Buffer / object / mob / character pool plumbing. Worth a Phase-1 inventory pass to confirm whether the Python implementation actually relies on pool-reuse semantics or has bypassed them.
2. The next ⚠️ Partial row in **P0/P1**: scan once `recycle.c` clears, or jump straight there if the user prefers behavioral over plumbing-style audits.

**Repo Hygiene flag**: `README.md` still says "13 of 43 files at 100%" (lines 172, 335). Actual is **19 / 43** as of this session. Per Repo Hygiene §2, the next commit that touches README must coordinate-refresh AGENTS.md tracker pointers + this `SESSION_STATUS.md` so the three surfaces don't disagree. Treat that as a documentation-shaped task in its own commit, not piggybacked on a parity-gap closure.

Run `/rom-parity-audit <file>.c` to start a new file audit, or `/rom-gap-closer <ID>` if jumping to an existing OPEN gap.
