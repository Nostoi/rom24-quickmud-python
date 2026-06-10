# Session Status — 2026-06-10 — diff-harness affect_expiry_lifecycle scenario (2.13.62)

## Current State

- **Active mode**: cross-file invariants pass
- **Last completed**:
  - **`affect_expiry_lifecycle` diff-harness scenario** — new scenario covering spell
    affect bitvector set/clear lifecycle: `cast sanctuary` + `cast haste` (AFF_SANCTUARY
    + AFF_HASTE set), then `__set_affect_duration=0` + `__char_update` (both cleared).
    First harness coverage of affect expiry. Skips until C golden is captured.
  - **`__mana=N` meta-command** added to pyreplay.py and diffmain.c — enables
    multi-spell scenarios beyond the 100-mana harness default.
  - Unit test `test_drive_python_replay_mana_meta_sets_mana_and_max_mana` added.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-10_DIFF_HARNESS_AFFECT_EXPIRY_SCENARIO.md](SESSION_SUMMARY_2026-06-10_DIFF_HARNESS_AFFECT_EXPIRY_SCENARIO.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.62 |
| Tests | 5501 passed, 6 skipped (full suite) |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-INV rows | 26 enforced |
| Diff-harness scenarios | 25 scenarios, 39 passing (2 skipped — affect_expiry_lifecycle no golden, shop_sell_keeper_broke) |
| FINDINGS.md highest ID | FINDING-032 |

## Next Intended Task

Cross-file invariants remains the active pass. The `affect_expiry_lifecycle` scenario
is authored but ungolden — the next concrete step is either:

1. **Capture the golden** for `affect_expiry_lifecycle` using the instrumented C binary:
   `cd src && make -f Makefile.diffshim diffshim`, then
   `python3 -m tools.diff_harness.capture --scenario affect_expiry_lifecycle`.
   Once captured the scenario becomes a live C-oracle guard for affect expiry.

2. **Author a second scenario** on an untested surface — `drink`/`eat`/`food`
   consumption (condition decay, THIRST/FULL/HUNGER) or charm/follower wear-off
   lifecycle. `__mana=N` is now available for any multi-spell scenario.

3. **MATH-002/003/004** — documented ⚠️ OPEN hygiene items (LOW severity) in
   `docs/parity/audits/MATH_AND_RNG.md`. No observable behavioral gap; held for a
   future PARITY008 lint rule.
