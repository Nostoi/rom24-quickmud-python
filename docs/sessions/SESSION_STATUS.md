# Session Status — 2026-06-08 — Diff-Harness mob SPEECH trigger + __mob_prog (2.13.23)

## Current State

- **Active mode**: cross-file invariants / divergence-class sweep (per-file audit
  tracker has no ⚠️ Partial / ❌ Not Audited rows).
- **Last completed**:
  - **Diff-harness mob SPEECH trigger (2.13.23).** `__mob_prog=<trig>:<phrase>:<code>`
    meta-command added to both the C shim (`diffmain.c`) and Python replay (`pyreplay.py`):
    injects a `MPROG_LIST` / `MobProgram` into the first NPC's program list at runtime
    (hermetic — no area-file edits). Static scenario `mob_speech_trigger` (room 3001,
    Midgaard wizard vnum 3000, SPEECH trigger "hello" → `say Hello adventurer!`), golden
    captured from C oracle, `test_python_matches_c_golden[mob_speech_trigger]` passes.
    Also fixed `affect_flags` case normalization in `compare.py` (C stores lowercase,
    Python emits uppercase enum names).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-08_DIFF_HARNESS_MOB_SPEECH_TRIGGER.md](SESSION_SUMMARY_2026-06-08_DIFF_HARNESS_MOB_SPEECH_TRIGGER.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.23 |
| Tests | 5434 passed, 0 failed, 4 skipped |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Diff-harness scenarios | 9 static + 15 generated-oracle tests |
| Diff-harness position rules | sit/rest/sleep/stand/wake — full ROM graph |
| Diff-harness affect rules | learn_and_cast_armor + char_update_tick (up to 8/run) |
| Diff-harness shop rules | load_weaponsmith + sell_sword + stock_keeper_sword + buy_sword |
| Diff-harness mobprog rules | mob_speech_trigger (SPEECH keyword match) |

## Next Intended Task

**Additional spells** (`detect_evil`, `fly`, `bless`) in the Hypothesis diff machine — start
with `detect_evil` (easiest: no duration RNG, just affect apply). Pattern: add `__learn=detect evil`
step, add `__seed` bracket around cast (the skill check calls `number_percent()`), write a
`learn_and_cast_detect_evil` rule in `DeterministicNoRngDiffMachine` in `generated.py` mirroring
the existing `learn_and_cast_armor` rule. Then extend to `fly` and `bless`. After spells:
shop transaction atomicity (probe error-exit paths in `do_buy`/`do_sell`) and cross-INV
affect-tick ordering.
