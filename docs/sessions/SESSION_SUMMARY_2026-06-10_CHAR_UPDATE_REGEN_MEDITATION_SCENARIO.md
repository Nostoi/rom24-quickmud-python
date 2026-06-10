# Session Summary — 2026-06-10 — char_update regen meditation scenario + level-gating fix

## Scope

Continuation from v2.13.72 (`char_update_regen` diff-harness scenario complete, cross-file
invariants the active pass). The session picked up from the "char_update regen skill variant"
candidate identified at session end: author `char_update_regen_meditation`, a diff-harness
scenario that places a level-6 mage with `meditation` learned and mana below max, then fires
three `__char_update` pulses to exercise the roll-dependent mana-gain path.

Authoring the scenario surfaced two parity gaps before the golden could pass:

1. **`_get_skill_percent` level gating** — Python returned the raw skill value without
   checking ROM C's class-specific level requirement. Fixed first (TDD).
2. **Seed timing asymmetry** — Python's `initialize_world()` consumes more `number_percent()`
   calls during boot than the C shim does, so the RNG state differs when `char_update` runs.
   Fixed by inserting `__seed=12345` just before the first `__char_update`, mirroring the
   pattern used by all other roll-sensitive diff-harness scenarios.

## Outcomes

### `_get_skill_percent` level gating — ✅ FIXED

- **Python**: `mud/game_loop.py:134-159` (`_get_skill_percent`)
- **ROM C**: `src/handler.c get_skill()` — `if (ch->level < skill_table[sn].skill_level[ch->class]) return 0;`
- **Bug**: Python returned the raw skill percent without checking whether the character had
  reached the level at which the class unlocks the skill. A level-5 mage (below the level-6
  requirement for meditation) was therefore granted the meditation bonus, diverging from ROM C.
- **Fix**: After the raw-value lookup, retrieve the skill's `levels` tuple from
  `skill_registry` (populated from `ROM_SKILL_METADATA`) and return 0 if
  `ch->level < levels[ch_class]`.
- **Tests**: `TestMeditation::test_meditation_adds_bonus_on_success` and
  `test_meditation_no_bonus_on_failure` — corrected from `ch_class=2` (thief, req level 15)
  to `ch_class=1` (cleric, req level 6) so the level-10 test character satisfies the gate and
  the bonus is exercised. 3 meditation tests passing.

### `char_update_regen_meditation` scenario — ✅ ADDED

- **Scenario**: `tools/diff_harness/scenarios/char_update_regen_meditation.json` — level-6
  mage, seed 12345, room 3001. Steps: `__hp=100`, `__mana=20`, `__move=20`, `__level=6`,
  `__learn=meditation`, `__seed=12345` (RNG resync), then three `__char_update` pulses.
- **Expected output (mana)**: 20 → 25 (+5, roll=24) → 33 (+8, roll=97) → 41 (+8, roll=90).
  Bonus formula: `(base + roll * base // 100) // 4` where `base = mana_gain(ch)` and the
  meditation roll path adds `roll * base // 100` when `roll < meditation_skill`.
- **Golden**: `tests/data/golden/diff/char_update_regen_meditation.golden.json` (9 steps,
  C sha d3b3a0f3)
- **Tests**: diff-harness smoke test auto-picked up the new scenario; 48 diff-harness tests
  pass (was 46). 30 scenarios total (was 29).

## Files Modified

- `mud/game_loop.py` — `_get_skill_percent`: added level-requirement check via skill_registry
  metadata; `isinstance((list, tuple))` → `list | tuple` (ruff UP038 fix)
- `tests/test_passive_skills_rom_parity.py` — `TestMeditation` tests: `ch_class=2` → `ch_class=1`
- `tools/diff_harness/scenarios/char_update_regen_meditation.json` — new scenario (18 lines)
- `tests/data/golden/diff/char_update_regen_meditation.golden.json` — new C golden (9 steps)
- `CHANGELOG.md` — added [2.13.73] Fixed + Added entries
- `pyproject.toml` — 2.13.72 → 2.13.73

## Test Status

- `pytest tests/test_passive_skills_rom_parity.py` — **39/39 passing** (3 meditation tests
  corrected, all pass)
- `pytest tests/test_differential_smoke.py tests/test_diff_harness_unit.py` — **48/48 passing**
  (was 46, +2 from new scenario)
- Full suite: **5526 passed, 4 skipped** (was 5525, +1 from diff-harness scenario count test)

## Next Steps

Cross-file invariants remains the active pass. Concrete candidates:

1. **MATH-002/003/004** — ⚠️ OPEN hygiene items in `docs/parity/audits/MATH_AND_RNG.md`
   (LOW severity, no observable gap). Held for a future PARITY008 lint rule.

2. **Next cross-INV candidate** — probe affect-tick contracts or position-transition edges for
   divergences not yet covered by an INV row. Method: pick a candidate area (affect-tick timing,
   position-transition sequencing, group/follower chain), run the 5-minute probe (read ROM C
   contract → read Python equivalent → write one failing test), then either close as a
   gap-closer commit or file as the next free INV-NNN in
   `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`.

3. **`fast_healing` diff-harness scenario** — symmetric follow-on to the meditation scenario:
   use `__learn=fast_healing` with a warrior (class 3, req level 6) at below-max HP. Would
   exercise the HP-side roll-dependent bonus path and confirm `_get_skill_percent` level
   gating is correct for `hit_gain` as well.
