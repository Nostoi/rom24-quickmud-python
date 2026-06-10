# Session Status — 2026-06-10 — GL-038 PLAGUE Fix + Regen Scenarios (PLAGUE/SLOW/Room Rates) (2.13.80)

## Current State

- **Active mode**: cross-file invariants pass
- **Last completed**:
  - **GL-038 fix** — `_char_update_tick_effects` plague tick gate changed from bitmask
    (`has_affect(AffectFlag.PLAGUE)`) to spell-affect list scan, matching ROM's
    `is_affected(ch, gsn_plague)`. Removed orphan-bit clearing. Mobs with innate
    AFF_PLAGUE (no spell entry) now correctly keep the bitmask and regen at ÷8
    every pulse without triggering the tick loop.
  - **`char_update_regen_plague` scenario** — C oracle confirms orphan PLAGUE bit
    persists across all pulses; ÷8 divisor applies every pulse.
    HP: 1→2→3→4 (+1), mana: 5→7→9→11 (+2), move: 5→8→11→14 (+3).
  - **`char_update_regen_slow` scenario** — AFF_SLOW ÷2 divisor (same branch as HASTE);
    HP+5/mana+8/move+14 per pulse.
  - **`__set_heal_rate=N` and `__set_mana_rate=N` meta-commands** — added to both
    `diffmain.c` and `pyreplay.py`; allow direct room-rate manipulation in scenarios.
  - **`char_update_regen_room_rates` scenario** — confirms `heal_rate` scales HP+move,
    `mana_rate` scales only mana (independent multipliers). Python already correct.
  - **3 unit tests** added to `tests/test_diff_harness_unit.py` (plague/slow/room_rates).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-10_GL038_PLAGUE_FIX_AND_REGEN_SCENARIOS.md](SESSION_SUMMARY_2026-06-10_GL038_PLAGUE_FIX_AND_REGEN_SCENARIOS.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.80 |
| Tests | 5544 passed, 4 skipped (full suite) |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-INV rows | 26 enforced |
| Diff-harness scenarios | 39 scenarios, 65 C-oracle tests passing, 0 skipped, 0 xfailed |
| FINDINGS.md highest ID | FINDING-033 (✅ RESOLVED — all findings resolved) |
| GL-038 | ✅ FIXED (plague tick gate bitmask vs spell-list) |

## Next Intended Task

Cross-file invariants remains the active pass. Concrete candidates:

1. **MATH-002/003/004** — ⚠️ OPEN hygiene items in `docs/parity/audits/MATH_AND_RNG.md`
   (LOW severity, no observable gap). Held for a future PARITY008 lint rule.

2. **Furniture bonus scenario**: SLEEPING PC on furniture with nonzero `value[3]`/`value[4]`
   — no existing furniture objects with non-100 values in game data; requires a `__oload` +
   `__set_on=` meta-command to set `char.on` to a furniture object. Design `__set_on` for
   both pyreplay.py and diffmain.c.

3. **Next cross-INV candidate** — probe affect-tick contracts or position-transition edges for
   divergences not yet covered by an INV row. Candidates: affect-tick timing, position-transition
   sequencing, group/follower chain. Method: pick a candidate, run 5-minute probe (ROM C
   contract → Python equivalent → one failing test), then either gap-closer commit or file
   as the next free INV-NNN in `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`.
