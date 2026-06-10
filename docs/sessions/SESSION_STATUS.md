# Session Status — 2026-06-10 — char_update_regen_resting scenario (2.13.76)

## Current State

- **Active mode**: cross-file invariants pass
- **Last completed**:
  - **`char_update_regen_resting` scenario** — mage (class 0, level 5), resting
    (position=5), HP=5/mana=30/move=20, three `__char_update` pulses with `__seed=12345`.
    C oracle confirms resting regen: HP 5→10→15→20 (+5/pulse), mana 30→38→46→54 (+8/pulse),
    move 20→41→62→83 (+21/pulse). Resting rates are exactly half sleeping for HP/mana;
    move uses `DEX//2` instead of full DEX (not a post-switch halving).
  - **1 unit test** (`test_drive_python_replay_char_position_resting_halves_all_gain`) —
    verifies all three resting gain values in one pulse against C-oracle ground truth.
  - **Position coverage complete**: all three position branches (sleeping/resting/standing)
    now have C-oracle scenarios across `hit_gain`, `mana_gain`, and `move_gain`.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-10_CHAR_UPDATE_REGEN_RESTING_SCENARIO.md](SESSION_SUMMARY_2026-06-10_CHAR_UPDATE_REGEN_RESTING_SCENARIO.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.76 |
| Tests | 5532 passed, 4 skipped (full suite) |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-INV rows | 26 enforced |
| Diff-harness scenarios | 33 scenarios, 53 C-oracle tests passing, 0 skipped, 0 xfailed |
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

3. **Remaining diff-harness candidates** — regen position matrix is fully covered.
   Next expansions:
   - Standing scenario exercising the `÷4` HP/mana default branches.
   - Hunger/thirst=0 scenario C-oracle verifying the `gain //= 2` condition halving
     in `hit_gain`/`mana_gain`.
