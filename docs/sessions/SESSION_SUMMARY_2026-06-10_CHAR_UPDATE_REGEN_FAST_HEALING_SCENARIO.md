# Session Summary — 2026-06-10 — char_update regen fast_healing scenario + __char_class meta-cmd

## Scope

Continuation from v2.13.73 (`char_update_regen_meditation` diff-harness scenario complete,
`_get_skill_percent` level gating fixed). The session picked up the concrete candidate
identified at session end: author `char_update_regen_fast_healing`, the symmetric follow-on
to the meditation scenario using `fast healing` on the HP side.

The scenario required a new harness primitive: `__char_class=<n>` to set the PC's class index
mid-scenario. Without it there was no way to exercise warrior-specific `hit_gain` (class 3,
`hp_max=15`, `fast healing` unlocks at level 6) since the default test character is always
mage (class 0, `fast healing` requires level 15 — not reachable without a multi-step level
escalation that would consume extra RNG rolls).

No parity bugs were uncovered; the fast_healing path was already correct after the
`_get_skill_percent` level-gating fix landed in the prior session.

## Outcomes

### `__char_class=<n>` meta-command — ✅ ADDED

- **Python**: `tools/diff_harness/pyreplay.py` (`_run_python_command`)
- **C shim**: `src/diff_shim/diffmain.c` (`main` dispatch block, after `__level=`)
- **Effect**: Sets `char.ch_class` (Python) / `ch->class` (C) to the given integer
  (0=mage, 1=cleric, 2=thief, 3=warrior). No side effects — does not wipe skills or
  reset stats, mirrors `__level=` in scope.
- **Tests**: `test_drive_python_replay_char_class_meta_affects_hit_gain` — verifies via
  HP delta after `__char_update`: warrior (class 3) yields `hit_gain` of 4 (17//4),
  mage (class 0) yields 2 (10//4), distinguishing the two class table entries.

### `char_update_regen_fast_healing` scenario — ✅ ADDED

- **Scenario**: `tools/diff_harness/scenarios/char_update_regen_fast_healing.json` —
  warrior (class 3), level 6, `fast healing` at 100%, HP=5/max=20, mana=100 (at max,
  no mana roll), move=100 (at max, no move roll), `__seed=12345`, three `__char_update`
  pulses.
- **Expected output (HP)**: 5 → 10 (+5, roll=24) → 18 (+8, roll=97) → 20 (+2, roll=90,
  capped at max_hit=20). Bonus formula: `(gain + roll*gain//100) // 4` where
  `gain = max(3, CON-3+level//2) + hp_max-10 = 12+5 = 17`.
- **Golden**: `tests/data/golden/diff/char_update_regen_fast_healing.golden.json`
  (8 steps, C sha 0688d79c, build flags `-DOLD_RAND`).
- **Tests**: diff-harness smoke test auto-picked up the new scenario; 49 diff-harness
  tests pass (was 48). 31 scenarios total (was 30).

## Files Modified

- `tools/diff_harness/pyreplay.py` — `_run_python_command`: added `__char_class=` branch
  after `__level=`
- `src/diff_shim/diffmain.c` — dispatch block: added `__char_class=` handler after
  `__level=`; rebuilt `src/diffshim` binary
- `tools/diff_harness/scenarios/char_update_regen_fast_healing.json` — new scenario (17 lines)
- `tests/data/golden/diff/char_update_regen_fast_healing.golden.json` — new C golden (8 steps)
- `tests/test_diff_harness_unit.py` — `test_drive_python_replay_char_class_meta_affects_hit_gain`
- `CHANGELOG.md` — added [2.13.74] Added entries
- `pyproject.toml` — 2.13.73 → 2.13.74

## Test Status

- `pytest tests/test_differential_smoke.py tests/test_diff_harness_unit.py` — **49/49 passing**
  (was 48, +1 from new scenario + new unit test)
- Full suite: **5528 passed, 4 skipped** (was 5526, +2)

## Next Steps

Cross-file invariants remains the active pass. Concrete candidates:

1. **MATH-002/003/004** — ⚠️ OPEN hygiene items in `docs/parity/audits/MATH_AND_RNG.md`
   (LOW severity, no observable gap). Held for a future PARITY008 lint rule.

2. **Next cross-INV candidate** — probe affect-tick contracts or position-transition edges for
   divergences not yet covered by an INV row. Method: pick a candidate area not yet covered
   (affect-tick timing, position-transition sequencing, group/follower chain), run the
   5-minute probe (read ROM C contract → read Python equivalent → write one failing test),
   then either close as a gap-closer commit or file as the next free INV-NNN in
   `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`.

3. **More diff-harness skill scenarios** — the fast_healing + meditation pair validates the
   bonus-roll branch of `hit_gain`/`mana_gain`. The no-skill baseline (plain regen without
   bonus) is already covered by `char_update_regen`. Remaining candidate: `move_gain` bonus
   path (no skill gating, pure RNG-independent formula) or a sleeping/resting position
   variant to exercise the position switch arms.
