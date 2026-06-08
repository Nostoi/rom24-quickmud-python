# Session Status — 2026-06-07 — Diff-Harness sit + char_update (2.13.20)

## Current State

- **Active mode**: cross-file invariants / divergence-class sweep (per-file audit
  tracker has no ⚠️ Partial / ❌ Not Audited rows).
- **Last completed**:
  - **Diff-harness widening (2.13.19–2.13.20).** Two commits landed:
    1. `sit` position transition added to `DeterministicNoRngDiffMachine`; `rest`/`sleep`/`stand`
       preconditions corrected to match the full ROM transition graph (`src/act_move.c`).
    2. `__char_update` + `__set_affect_duration=N` meta-commands (C shim + Python replay);
       `learn_and_cast_armor` + `char_update_tick` Hypothesis rules exercise the real
       `char_update()` affect-duration tick loop including `number_range(0,4)` level-decay RNG.
       C shim rebuilt. 5434 passed, 0 failed, 4 skipped.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-07_DIFF_HARNESS_SIT_CHAR_UPDATE.md](SESSION_SUMMARY_2026-06-07_DIFF_HARNESS_SIT_CHAR_UPDATE.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.20 |
| Tests | 5434 passed, 0 failed, 4 skipped |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Diff-harness scenarios | 8 static + 14 generated-oracle tests |
| Diff-harness position rules | sit/rest/sleep/stand/wake — full ROM graph |
| Diff-harness affect rules | learn_and_cast_armor + char_update_tick (up to 8/run) |

## Next Intended Task

1. Continue cross-INV probe-then-scope. Remaining diff-harness surface areas:
   - **Shop interactions** (`do_buy`/`do_sell`) — no RNG; clean Hypothesis rules for
     gold/silver transaction verification
   - **Mob scripts** — `mprog_act_trigger`/`mprog_entry_trigger` entry-level probes
   - **Additional spells** — `detect_evil`, `fly`, `bless`; seed alignment for skill check
2. Cross-INV candidates: affect-tick ordering contracts (call order in `char_update` vs ROM),
   shop transaction atomicity (gold deducted before item transfer?).
