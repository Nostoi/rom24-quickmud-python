# Session Summary — 2026-06-10 — char_update condition decay diff-harness scenario

## Scope

Continuation from v2.13.70 (EFFECTS-003/004/005 affect stubs closed). The previous
session completed the EFFECTS_C_AUDIT and identified the `char_update` condition-decay
diff-harness scenario as the natural next step — a C-oracle test exercising the
negative-delta `gain_condition` path (hunger/thirst/drunk drain) via `__char_update`
meta-command across multiple ticks.

## Outcomes

### `char_update_condition_decay` scenario — ✅ ADDED

- **Python**: `tools/diff_harness/pyreplay.py` — `__cond_drunk` meta-cmd, `__char_update` dispatch
- **ROM C**: `src/update.c:755-759` — `gain_condition(DRUNK,-1)`, `gain_condition(FULL,-4/-2)`,
  `gain_condition(THIRST,-1)`, `gain_condition(HUNGER,-2/-1)` sequence
- **Scenario**: `tools/diff_harness/scenarios/char_update_condition_decay.json` — sets
  COND_HUNGER=2, COND_THIRST=2, COND_DRUNK=2, runs two `__char_update` pulses.
  First tick drains each from 2 → 1 (silent); second tick drains each from 1 → 0,
  triggering "You are sober.", "You are thirsty.", "You are hungry." in ROM's
  DRUNK → FULL → THIRST → HUNGER dispatch order.
- **Golden**: `tests/data/golden/diff/char_update_condition_decay.golden.json` (5 steps, C sha 6ce46887)
- **Tests**: diff-harness smoke test auto-picked up the new scenario; 45 diff-harness
  tests pass (was 44).

### `__cond_drunk=N` meta-command — ✅ ADDED

- **C shim**: `src/diff_shim/diffmain.c` — block after `__cond_hunger=` handler,
  sets `ch->pcdata->condition[COND_DRUNK]` (index 0) to the given value.
- **Python replay**: `tools/diff_harness/pyreplay.py` — symmetric `__cond_drunk=` handler
  sets `char.pcdata.condition[int(Condition.DRUNK)]` (also index 0).
- Mirrors the existing `__cond_hunger`, `__cond_thirst`, `__cond_full` trio.
- C binary rebuilt after the change: `make -f Makefile.diffshim diffshim` clean.

## Files Modified

- `src/diff_shim/diffmain.c` — `__cond_drunk=N` meta-cmd block added (9 lines)
- `tools/diff_harness/pyreplay.py` — symmetric `__cond_drunk=` handler added (5 lines)
- `tools/diff_harness/scenarios/char_update_condition_decay.json` — new scenario (14 lines)
- `tests/data/golden/diff/char_update_condition_decay.golden.json` — new C golden (234 lines)
- `CHANGELOG.md` — added [2.13.71] Added entries
- `pyproject.toml` — 2.13.70 → 2.13.71

## Test Status

- `pytest tests/test_differential_smoke.py tests/test_diff_harness_unit.py` — **45/45 passing**
  (was 44, +1 new scenario)
- Full suite: **5523 passed, 4 skipped** (unchanged from before)

## Next Steps

Cross-file invariants remains the active pass. Concrete candidates:

1. **MATH-002/003/004** — ⚠️ OPEN hygiene items in `docs/parity/audits/MATH_AND_RNG.md`
   (LOW severity, no observable gap). Held for a future PARITY008 lint rule; can
   be picked up now as a contained fix.

2. **Next cross-INV candidate** — probe affect-tick contracts or position-transition
   edges for divergences not yet covered by an INV row. Method: pick a candidate area
   (affect-tick timing, position-transition sequencing, or group/follower chain), run
   the 5-minute probe (read ROM C contract → read Python equivalent → write one failing
   test), then either close as a gap-closer commit or file as the next free INV-NNN
   in `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`.

3. **Additional diff-harness coverage** — `affect_expiry_lifecycle` already covers
   spell-affect drain; a `char_update_regen` scenario could exercise the
   HP/mana/move regeneration path (hit_gain/mana_gain/move_gain) with conditions
   controlling the regen multiplier.
