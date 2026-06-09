# Session Status — 2026-06-09 — Diff-harness movement trigger scenario (2.13.53)

## Current State

- **Active mode**: divergence Class 11 / dynamic differential widening
  (per-file audit tracker has no ⚠️ Partial / ❌ Not Audited rows).
- **Last completed**:
  - **Diff-harness C-oracle scenario for TRIG_EXIT + TRIG_GRALL.**
    `mob_movement_triggers.json` + golden exercise `mp_exit_trigger` (direction-0,
    movement-blocking) and `mp_greet_trigger` GRALL path (percent-based, arrival-firing).
    Both Python and C agree: `test_python_matches_c_golden[mob_movement_triggers]` passes.
    Version 2.13.53; 5,479 tests pass.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-09_DIFF_HARNESS_MOVEMENT_TRIGGER_SCENARIO.md](SESSION_SUMMARY_2026-06-09_DIFF_HARNESS_MOVEMENT_TRIGGER_SCENARIO.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.53 |
| Tests | 5,479 passed, 5 skipped (last full run) |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-INV rows | 25 enforced |
| Diff-harness scenarios | 10 static + 19 generated-oracle tests; all findings resolved |
| Class 11 dynamic widening | All deterministic MEdit triggers covered; TRIG_EXIT + TRIG_GRALL have C-oracle diff-harness ground truth |

## Next Intended Task

Class 11 remaining work (in priority order):

1. **TRIG_GREET ground truth** — confirm the `default_pos` + `can_see` gate differs from
   GRALL by adding a diff-harness step or scenario where the mob is not standing (so
   GREET skips, GRALL fires). Completes greet-path coverage.
2. **TRIG_EXALL ground truth** — add a movement step in a non-0 direction to confirm EXALL
   fires without the position/visibility gate that EXIT requires.
3. **RNG-locked paths** (`TRIG_RANDOM`, `TRIG_DELAY`) — defer until seed alignment has
   a grounded probe.
4. **Next divergence class** — consult `docs/parity/DIVERGENCE_CLASS_ROSTER.md` for the
   next unverified surface outside Class 11.
