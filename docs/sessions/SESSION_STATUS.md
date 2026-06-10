# Session Status — 2026-06-10 — char_update_regen_fast_healing scenario + __char_class meta-cmd (2.13.74)

## Current State

- **Active mode**: cross-file invariants pass
- **Last completed**:
  - **`__char_class=<n>` meta-command** — new harness primitive for both pyreplay.py
    and diffmain.c; sets PC class index (0=mage … 3=warrior) mid-scenario without
    side effects. Required to exercise warrior-specific `hit_gain` in the fast_healing
    scenario.
  - **`char_update_regen_fast_healing` scenario** — warrior (class 3, level 6),
    `fast healing` at 100%, HP=5/max=20, three `__char_update` pulses with `__seed=12345`.
    C oracle confirms HP progression 5→10→18→20 (rolls 24/97/90 from seed 12345).
    31 scenarios, 49 C-oracle tests passing.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-10_CHAR_UPDATE_REGEN_FAST_HEALING_SCENARIO.md](SESSION_SUMMARY_2026-06-10_CHAR_UPDATE_REGEN_FAST_HEALING_SCENARIO.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.74 |
| Tests | 5528 passed, 4 skipped (full suite) |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-INV rows | 26 enforced |
| Diff-harness scenarios | 31 scenarios, 49 C-oracle tests passing, 0 skipped, 0 xfailed |
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

3. **More diff-harness skill scenarios** — the fast_healing + meditation pair validates
   the bonus-roll branch of `hit_gain`/`mana_gain`. Remaining candidates: sleeping/resting
   position variant (exercises the position switch arms), or a `move_gain` scenario.
