# Session Summary — 2026-06-10 — char_update regen scenario + RNG gating fix

## Scope

Continuation from v2.13.71 (`char_update_condition_decay` scenario complete, cross-file
invariants the active pass). The session picked up from the `char_update_regen` diff-harness
scenario candidate identified at session end. Before authoring the scenario, a code-read of
`_apply_regeneration` (`mud/game_loop.py:536-547`) revealed a parity bug: Python called
`hit_gain`/`mana_gain` unconditionally every tick, consuming `number_percent()` RNG rolls
even when `hit == max_hit` / `mana == max_mana`. ROM C `src/update.c:698-712` gates both
calls inside `if (ch->hit < ch->max_hit)` etc. The fix was done first (TDD: failing test →
fix → green), then the meta-commands and scenario followed.

## Outcomes

### `_apply_regeneration` RNG gating — ✅ FIXED

- **Python**: `mud/game_loop.py:536-547` (`_apply_regeneration`)
- **ROM C**: `src/update.c:698-712` — `if (ch->hit < ch->max_hit) ch->hit += hit_gain(ch); else ch->hit = ch->max_hit;` pattern (×3 for hit/mana/move)
- **Bug**: `hit_gain` and `mana_gain` each call `rng_mm.number_percent()` once unconditionally for PC characters. At full HP/mana the gain is clamped to 0 by the deficit floor, so no stat changed — but the RNG state advanced. With fast_healing/meditation skills active, this would produce divergent roll sequences vs ROM C across multi-tick scenarios.
- **Fix**: Gate each call on `resource < max`, and add `else: resource = max` clamp branch, exactly mirroring ROM C. `move_gain` has no RNG call so it's safe either way, but gating it is also correct.
- **Tests**: `TestApplyRegenerationRNGGating::test_rng_not_consumed_when_hit_at_max` — seeds RNG, runs `_apply_regeneration` on a character at max HP/mana/move, asserts the first subsequent `number_percent()` returns the same seed-derived value (proving no phantom rolls were consumed). 1 new test; was failing before fix, passes after.

### `__hp=N` and `__move=N` meta-commands — ✅ ADDED

- **C shim**: `src/diff_shim/diffmain.c` — `__hp=` handler after the `__mana=` block (sets `ch->hit` and `ch->max_hit` if lower); `__move=` handler mirrors it for `ch->move` / `ch->max_move`. C binary rebuilt clean.
- **Python replay**: `tools/diff_harness/pyreplay.py` — symmetric `__hp=` and `__move=` handlers set `char.hit`/`char.max_hit` and `char.move`/`char.max_move`.
- Completes the resource-setter trio alongside `__mana=`.

### `char_update_regen` scenario — ✅ ADDED

- **Scenario**: `tools/diff_harness/scenarios/char_update_regen.json` — level-5 mage, seed 12345, room 3001. Steps: `__hp=5`, `__mana=30`, `__move=20`, then three `__char_update` pulses.
- **Expected output**: three ticks of steady regen at standing position, full conditions (hunger/thirst=48). Confirmed values at seed 12345: hit+2/tick, mana+4/tick, move+15/tick.
- **Golden**: `tests/data/golden/diff/char_update_regen.golden.json` (6 steps, C sha 5de3cdd6)
- **Tests**: diff-harness smoke test auto-picked up the new scenario; 46 diff-harness tests pass (was 45). 29 scenarios total (was 28).

## Files Modified

- `mud/game_loop.py` — `_apply_regeneration` gated on `resource < max` (24 lines, was 12)
- `tests/test_char_update_rom_parity.py` — added `_apply_regeneration` import; added `TestApplyRegenerationRNGGating` class with 1 test
- `src/diff_shim/diffmain.c` — `__hp=N` and `__move=N` handler blocks added (26 lines); C binary rebuilt
- `tools/diff_harness/pyreplay.py` — `__hp=` and `__move=` handlers added (8 lines)
- `tools/diff_harness/scenarios/char_update_regen.json` — new scenario (12 lines)
- `tests/data/golden/diff/char_update_regen.golden.json` — new C golden (captured from rebuilt binary)
- `CHANGELOG.md` — added [2.13.72] Fixed + Added entries
- `pyproject.toml` — 2.13.71 → 2.13.72

## Test Status

- `pytest tests/test_char_update_rom_parity.py` — **31/31 passing** (was 30, +1 RNG gating test)
- `pytest tests/test_differential_smoke.py tests/test_diff_harness_unit.py` — **46/46 passing** (was 45, +1 new scenario)
- Full suite: **5525 passed, 4 skipped** (was 5523, +2 new tests)

## Next Steps

Cross-file invariants remains the active pass. Concrete candidates:

1. **MATH-002/003/004** — ⚠️ OPEN hygiene items in `docs/parity/audits/MATH_AND_RNG.md`
   (LOW severity, no observable gap). Held for a future PARITY008 lint rule.

2. **Next cross-INV candidate** — probe affect-tick contracts or position-transition
   edges for divergences not yet covered by an INV row. Method: pick a candidate area
   (affect-tick timing, position-transition sequencing, group/follower chain), run
   the 5-minute probe (read ROM C contract → read Python equivalent → write one failing
   test), then either close as a gap-closer commit or file as the next free INV-NNN
   in `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`.

3. **`char_update_regen` skill variant** — a follow-on scenario with `__learn=meditation`
   + below-max mana would directly exercise the roll-dependent mana gain path and confirm
   the RNG gating fix holds under skill activation. Useful as a regression guard but not
   strictly required now that the unit test pins the contract.
