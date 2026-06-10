# Session Status — 2026-06-10 — char_update_regen_sleeping scenario + __char_position meta-cmd (2.13.75)

## Current State

- **Active mode**: cross-file invariants pass
- **Last completed**:
  - **`__char_position=<n>` meta-command** — new harness primitive for both pyreplay.py
    and diffmain.c; sets PC position (4=sleeping, 5=resting, 8=standing) mid-scenario.
    Mirrors the existing `__mob_position=` for NPCs. Required to exercise position-specific
    branches in `hit_gain`/`mana_gain`/`move_gain`.
  - **`char_update_regen_sleeping` scenario** — mage (class 0, level 5), sleeping
    (position=4), HP=5/mana=30/move=20, three `__char_update` pulses with `__seed=12345`.
    C oracle confirms sleeping regen: HP 5→15→20→20 (+10/pulse), mana 30→47→64→81
    (+17/pulse), move 20→48→76→100 (+28/pulse). First scenario to exercise all three
    position branches (sleeping arm) across hit_gain/mana_gain/move_gain simultaneously.
  - **1 unit test** for `__char_position=` (`test_drive_python_replay_char_position_meta_affects_hit_gain`).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-10_CHAR_UPDATE_REGEN_SLEEPING_SCENARIO.md](SESSION_SUMMARY_2026-06-10_CHAR_UPDATE_REGEN_SLEEPING_SCENARIO.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.75 |
| Tests | 5530 passed, 4 skipped (full suite) |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-INV rows | 26 enforced |
| Diff-harness scenarios | 32 scenarios, 51 C-oracle tests passing, 0 skipped, 0 xfailed |
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

3. **More diff-harness regen scenarios** — remaining position variants: `char_update_regen_resting`
   (exercises the gain//2 resting arms across hit/mana/move_gain), or a `move_gain`
   scenario that explicitly exercises the DEX stat contribution in isolation.
