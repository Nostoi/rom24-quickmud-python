# Session Status — 2026-06-10 — Diff-harness C-oracle for TRIG_RANDOM and TRIG_DELAY (2.13.59)

## Current State

- **Active mode**: divergence Class 11 / dynamic differential widening — **COMPLETE**
  (per-file audit tracker has no ⚠️ Partial / ❌ Not Audited rows; all 15 Class 11
  mobprog dispatch paths now have C-oracle diff-harness ground truth).
- **Last completed**:
  - **`__mobile_update` meta-command** added to C shim (`diffmain.c`) and Python replay
    (`pyreplay.py`). Calls `mobile_update()` to tick TRIG_RANDOM and TRIG_DELAY paths.
  - **`__mob_delay=N` meta-command** added to prime `mprog_delay` before a `mobile_update`
    tick, enabling deterministic TRIG_DELAY testing.
  - **TRIG_RANDOM C-oracle ground truth.** `mob_random_trigger.json` — fires unconditionally
    each `mobile_update` when `position == default_pos` and `trig_phrase=101`. Python and
    C agree on first try.
  - **TRIG_DELAY C-oracle ground truth.** `mob_delay_trigger.json` — fires when
    `mprog_delay` reaches 0 on a `mobile_update` tick. Python and C agree on first try.
  - Stale golden `mob_death_test.golden.json` removed (leftover from pre-commit c49ccff1).
  - Version 2.13.59.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-10_DIFF_HARNESS_RANDOM_DELAY_ORACLES.md](SESSION_SUMMARY_2026-06-10_DIFF_HARNESS_RANDOM_DELAY_ORACLES.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.59 |
| Tests | ~5,493 passed, 5 skipped (last full run at 2.13.58; +2 new diff-harness tests at 2.13.59) |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-INV rows | 25 enforced |
| Diff-harness scenarios | 22 scenarios (added RANDOM + DELAY this session) |
| Class 11 dynamic widening | **COMPLETE** — all 15 mobprog dispatch paths have C-oracle ground truth |

## Next Intended Task

Class 11 is complete. Next divergence class candidates (from `docs/parity/DIVERGENCE_CLASS_ROSTER.md`):

1. **Next divergence class** — consult `docs/parity/DIVERGENCE_CLASS_ROSTER.md` for the
   next unverified surface outside Class 11. Candidates: async message delivery ordering,
   affect-tick edge contracts, position-transition invariants.
2. **Latent parity gap: wizard shop status** — Python's `_has_shop` returns False for mob
   3000 (wizard) because the midgaard JSON area file has no `shops` section. C's
   midgaard.are defines wizard as a shopkeeper. Should be reviewed against shop scenario
   coverage before claiming shop parity complete.
