# Session Status — 2026-06-10 — char_update condition decay diff-harness scenario (2.13.71)

## Current State

- **Active mode**: cross-file invariants pass
- **Last completed**:
  - **`char_update_condition_decay` scenario** — new C-oracle diff-harness scenario
    exercising tick-based hunger/thirst/drunk drain via `__char_update`. Sets each
    condition to 2 and runs two `char_update` pulses; second tick drains all three
    to 0, producing "You are sober." / "You are thirsty." / "You are hungry." in
    ROM's DRUNK→FULL→THIRST→HUNGER order (`src/update.c:755-759`). 28 scenarios,
    47 C-oracle tests passing.
  - **`__cond_drunk=N` meta-command** — added to both `diffmain.c` and `pyreplay.py`
    (symmetric with `__cond_hunger`/`__cond_thirst`/`__cond_full`). C binary rebuilt.
  - 5523 tests pass, 4 skipped.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-10_CHAR_UPDATE_CONDITION_DECAY_SCENARIO.md](SESSION_SUMMARY_2026-06-10_CHAR_UPDATE_CONDITION_DECAY_SCENARIO.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.71 |
| Tests | 5523 passed, 4 skipped (full suite) |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-INV rows | 26 enforced |
| Diff-harness scenarios | 28 scenarios, 47 C-oracle tests passing, 0 skipped, 0 xfailed |
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

3. **`char_update_regen` diff-harness scenario** — HP/mana/move regeneration path
   (hit_gain/mana_gain/move_gain) with damaged character recovering across multiple
   `__char_update` pulses. Natural follow-on to `char_update_condition_decay`.
