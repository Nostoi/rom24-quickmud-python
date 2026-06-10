# Session Status — 2026-06-10 — char_update_regen_hungry_thirsty scenario (2.13.77)

## Current State

- **Active mode**: cross-file invariants pass
- **Last completed**:
  - **`char_update_regen_hungry_thirsty` scenario** — mage (class 0, level 5), sleeping
    (position=4), HP=1/mana=5/move=5, with `COND_HUNGER=0` and `COND_THIRST=0`, three
    `__char_update` pulses with seed 12345.
    C oracle confirms dual condition halving: HP 1→3→5→7 (+2/pulse), mana 5→9→13→17 (+4/pulse),
    move 5→12→19→26 (+7/pulse). Two sequential `//2` halvings: sleeping base +10/+17/+28 reduced
    to +2/+4/+7 per pulse. SLEEPING position chosen to keep gains nonzero (STANDING floors to 0).
  - **1 unit test** (`test_drive_python_replay_hunger_thirst_zero_halves_regen_twice`) —
    verifies all three condition-halved gain values in one pulse against C-oracle ground truth.
  - **Condition halving coverage complete**: both COND_HUNGER==0 and COND_THIRST==0 branches
    now have C-oracle scenarios in all three gain functions.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-10_CHAR_UPDATE_REGEN_HUNGRY_THIRSTY_SCENARIO.md](SESSION_SUMMARY_2026-06-10_CHAR_UPDATE_REGEN_HUNGRY_THIRSTY_SCENARIO.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.77 |
| Tests | 5534 passed, 4 skipped (full suite) |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-INV rows | 26 enforced |
| Diff-harness scenarios | 34 scenarios, 55 C-oracle tests passing, 0 skipped, 0 xfailed |
| FINDINGS.md highest ID | FINDING-033 (✅ RESOLVED — all findings resolved) |
| Effects integration tests | 37 / 37 passing |

## Next Intended Task

Cross-file invariants remains the active pass. Concrete candidates:

1. **MATH-002/003/004** — ⚠️ OPEN hygiene items in `docs/parity/audits/MATH_AND_RNG.md`
   (LOW severity, no observable gap). Held for a future PARITY008 lint rule.

2. **Next cross-INV candidate** — probe affect-tick contracts or position-transition
   edges for divergences not yet covered by an INV row. Pick a candidate area not
   yet covered (affect-tick timing, position-transition sequencing, group/follower
   chain), run the 5-minute probe (read ROM C contract → read Python equivalent →
   write one failing test), then either close as a gap-closer commit or file as the
   next free INV-NNN in `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`.

3. **Remaining diff-harness candidates** — regen position matrix and condition-halving
   are fully covered. Next expansions:
   - Furniture bonus scenario: SLEEPING PC on furniture with nonzero `value[3]`/`value[4]`
     — C-oracle verifying `gain * value[3] / 100` and `gain * value[4] / 100` multipliers.
   - Affect penalty scenarios: `AFFECT_POISON` (÷4), `AFFECT_PLAGUE` (÷8), `AFFECT_HASTE`/
     `AFFECT_SLOW` (÷2) regen divisors in `hit_gain`/`mana_gain`/`move_gain`.
   - `heal_rate` / `mana_rate` room multiplier scenario (rooms with non-100 rates).
