# Session Status — 2026-06-10 — char_update regen scenario + RNG gating fix (2.13.72)

## Current State

- **Active mode**: cross-file invariants pass
- **Last completed**:
  - **`_apply_regeneration` RNG gating fix** — `hit_gain`/`mana_gain` were called
    unconditionally, consuming phantom `number_percent()` rolls at max HP/mana.
    Fixed to gate on `resource < max`, mirroring ROM C `src/update.c:698-712`.
    Enforcement test added: `TestApplyRegenerationRNGGating::test_rng_not_consumed_when_hit_at_max`.
  - **`__hp=N` and `__move=N` meta-commands** — added to both `diffmain.c` and
    `pyreplay.py` (symmetric with `__mana=N`). C binary rebuilt.
  - **`char_update_regen` scenario** — level-5 mage, HP=5/mana=30/move=20, three
    `__char_update` pulses. 29 scenarios, 46 C-oracle tests passing.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-10_CHAR_UPDATE_REGEN_SCENARIO.md](SESSION_SUMMARY_2026-06-10_CHAR_UPDATE_REGEN_SCENARIO.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.72 |
| Tests | 5525 passed, 4 skipped (full suite) |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-INV rows | 26 enforced |
| Diff-harness scenarios | 29 scenarios, 46 C-oracle tests passing, 0 skipped, 0 xfailed |
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

3. **`char_update_regen` skill variant** — follow-on scenario with `__learn=meditation`
   + below-max mana to exercise the roll-dependent mana gain path as a regression guard
   for the RNG gating fix under skill activation.
