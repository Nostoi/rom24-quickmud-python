# Session Status — 2026-06-10 — char_update regen affect-penalty scenarios (2.13.78)

## Current State

- **Active mode**: cross-file invariants pass
- **Last completed**:
  - **`__add_affect=<bit>` meta-command** — new diff-harness primitive in both
    `src/diff_shim/diffmain.c` and `tools/diff_harness/pyreplay.py`. ORs an AFF_*
    bitmask into `ch->affected_by` without a spell AFFECT_DATA entry, letting scenarios
    exercise IS_AFFECTED regen divisor branches independently of tick-handler logic.
  - **`char_update_regen_poison` scenario** — mage (class 0, level 5), sleeping
    (position=4), HP=1/mana=5/move=5, `__add_affect=4096` (AFF_POISON). Three
    `__char_update` pulses. C oracle confirms POISON ÷4 divisor:
    HP 1→3→5→7 (+2/pulse), mana 5→9→13→17 (+4/pulse), move 5→12→19→26 (+7/pulse).
  - **`char_update_regen_haste` scenario** — same setup, `__add_affect=2097152`
    (AFF_HASTE). C oracle confirms HASTE ÷2 divisor:
    HP 1→6→11→16 (+5/pulse), mana 5→13→21→29 (+8/pulse), move 5→19→33→47 (+14/pulse).
  - **2 unit tests** (`test_drive_python_replay_poison_affect_halves_regen_by_four`,
    `test_drive_python_replay_haste_affect_halves_regen_by_two`) — verify gains after
    one pulse against C-oracle ground truth.
  - **AFF_PLAGUE deferred**: Python `_char_update_tick_effects` clears orphan PLAGUE bit
    (no spell-affect entry); C does not. Fix Python first, then author scenario.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-10_CHAR_UPDATE_REGEN_AFFECT_PENALTY_SCENARIOS.md](SESSION_SUMMARY_2026-06-10_CHAR_UPDATE_REGEN_AFFECT_PENALTY_SCENARIOS.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.78 |
| Tests | 5538 passed, 4 skipped (full suite) |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-INV rows | 26 enforced |
| Diff-harness scenarios | 36 scenarios, 59 C-oracle tests passing, 0 skipped, 0 xfailed |
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

3. **Remaining diff-harness candidates** — affect-penalty (POISON, HASTE) now covered.
   Next expansions:
   - **AFF_PLAGUE fix + scenario**: fix Python orphan-bit clearing in
     `_char_update_tick_effects`, then author C-oracle scenario.
   - **AFF_SLOW scenario**: check orphan-bit status, then author scenario (÷2 like HASTE).
   - **Furniture bonus scenario**: SLEEPING PC on furniture with nonzero `value[3]`/
     `value[4]` — C-oracle verifying `gain * value[3] / 100` and `gain * value[4] / 100`
     multipliers in `hit_gain`/`mana_gain`/`move_gain`.
   - **`heal_rate` / `mana_rate` room multiplier scenario** (rooms with non-100 rates).
