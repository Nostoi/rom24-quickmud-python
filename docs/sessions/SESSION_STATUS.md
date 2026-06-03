# Session Status — 2026-06-03 — cancellation dispel roll + infravision actor + idle autoquit (2.12.96)

## Current State

This session closed the last open engine bug and the three gaps it surfaced,
all pushed to `master` (5 commits, `d3f2bf2a..889118f5`):

1. **MAGIC-009** (✅ FIXED, 2.12.92) — `cancellation` now rolls a per-effect
   `saves_dispel` via `check_dispel` instead of stripping every effect
   unconditionally. The "victim gets NO save" comment refers only to the absent
   upfront wholesale save, not the per-effect rolls.
2. **MAGIC-015** (✅ FIXED, 2.12.93) — infravision room line uses the **caster**
   as the `$n` actor (ROM `ch`), not the target; resolved a duplicate-`MAGIC-009`
   ID collision (the infravision gap → `MAGIC-015`).
3. **GL-035** (✅ FIXED, 2.12.94) — connected idle players now auto-quit: the
   sync tick schedules an async `conn.close()`, the parked `readline` returns
   `None`, and the playing-loop `finally` runs the full `do_quit`-equivalent
   teardown. Wake-chain **proven** with a real `TelnetStream`/`socketpair` test.
4. **GL-034** (✅ FIXED, 2.12.95; ordering corrected 2.12.96) — at most one idle
   autoquit per tick; ROM prepends to `char_list`, so the **oldest** idler quits
   first (first-wins over the append-ordered registry).

- **Pointer to this session's summary**:
  [SESSION_SUMMARY_2026-06-03_CANCELLATION_INFRAVISION_IDLE_AUTOQUIT.md](SESSION_SUMMARY_2026-06-03_CANCELLATION_INFRAVISION_IDLE_AUTOQUIT.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.12.96 |
| Tests | Full suite `pytest` → 5379 passed, 4 skipped |
| Lint | `ruff check .` + `ruff format --check .` clean repo-wide; 5 pre-commit hooks pass |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-file invariants | 31 active rows |
| Open engine bugs | **None** known. Lower-priority divergences: GL-037 (autoquit messaging), and the historical low-impact items below. |

## Next Intended Task

No open engine bug remains. Per-file audit tracker has no ⚠️/❌ rows, so
cross-file invariants + the divergence-class roster (`/rom-divergence-sweep`)
are the active passes. Concrete candidates:

1. **GL-037** (`UPDATE_C_AUDIT.md`, OPEN) — emit ROM `do_quit`'s "Alas, all good
   things must come to an end." / "$n has left the game." on the idle-autoquit
   path specifically. Small `/rom-gap-closer`.
2. `diff_harness` Hypothesis widening — the only enumeration-independent path to
   *unknown* divergences.
3. New cross-INV probe (affect-tick / group-follower / position-transition edge).
4. Housekeeping: INV tracker consolidation (31 rows, past the ~20 soft cap).

## Other open / deferred items

- **GL-037** (`UPDATE_C_AUDIT.md`) — idle-autoquit farewell/room messaging not replicated by the clean-disconnect path. Low impact.
- **test-fixtures-lint** — manual-staged style lint; re-enable once legacy tests migrate or it's reworked to changed-files-only.
