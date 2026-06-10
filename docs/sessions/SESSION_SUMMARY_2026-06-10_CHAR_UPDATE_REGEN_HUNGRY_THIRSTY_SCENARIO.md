# Session Summary — 2026-06-10 — char_update regen hungry/thirsty condition scenario

## Scope

Continuation from v2.13.76 (`char_update_regen_resting` diff-harness scenario complete, all
three position branches covered). The session picked up the last concrete diff-harness candidate
identified at session end: author a C-oracle scenario exercising the `COND_HUNGER == 0` and
`COND_THIRST == 0` halving branches in `hit_gain`, `mana_gain`, and `move_gain`
(ROM `src/update.c:207-211`, `289-293`, `341-345`).

The required meta-commands (`__cond_hunger=`, `__cond_thirst=`) were already implemented in both
`diffmain.c` and `pyreplay.py` from an earlier session. No new primitives were needed.

A key design decision — surfaced by advisor review before authoring — was the choice of position.
STANDING (the default branch) gives `base ÷ 4` before conditions are applied; with both
conditions zeroed that becomes `base ÷ 16`, which floors to 0 for the small gains in our test
character. A zero-per-pulse gain passes the smoke test even if the halving logic is broken,
making the test non-discriminating. SLEEPING (no HP position penalty) was chosen instead: the
same dual-halving yields `base ÷ 4` overall but from a larger base, keeping gains at +2 HP,
+4 mana, +7 move per pulse — clearly nonzero and distinct from the un-halved sleeping baseline
of +10/+17/+28 per pulse.

No parity bugs were uncovered. Python already implements the hunger/thirst halving in
`hit_gain`, `mana_gain`, and `move_gain` (`mud/game_loop.py:206-209`, `275-278`, `321-324`).
The C oracle confirmed the Python implementation is correct.

## Outcomes

### `char_update_regen_hungry_thirsty` scenario — ✅ ADDED

- **Scenario**: `tools/diff_harness/scenarios/char_update_regen_hungry_thirsty.json` — mage
  (class 0, `fMana=TRUE`), level 5, `__char_position=4` (sleeping), HP=1/max=20,
  mana=5/max=100, move=5/max=100, `__cond_hunger=0`, `__cond_thirst=0`, three
  `__char_update` pulses.
- **C oracle results** (via `python3 -m tools.diff_harness.capture --scenario char_update_regen_hungry_thirsty`):
  - HP: 1 → 3 → 5 → 7 (+2/pulse). Base gain for sleeping mage = 10; `10 //2 (hunger) //2
    (thirst) = 2`. Two sequential C integer divisions, not `// 4` directly.
  - Mana: 5 → 9 → 13 → 17 (+4/pulse). Base sleeping mana gain = 17; `17 //2 = 8`, `8 //2 = 4`.
  - Move: 5 → 12 → 19 → 26 (+7/pulse). Base = `UMAX(15,5) + DEX = 15 + 13 = 28`; `28 //2 = 14`,
    `14 //2 = 7`.
- **Golden**: `tests/data/golden/diff/char_update_regen_hungry_thirsty.golden.json`
  (9 steps, C sha 21137cc9, build flags `-DOLD_RAND`).
- **Key observation**: ROM applies the two halvings sequentially with integer truncation after
  each step: `gain //= 2` then `gain //= 2`. This is not the same as `gain //= 4` when
  the intermediate result is odd (e.g. `17 // 2 = 8`, `8 // 2 = 4` vs `17 // 4 = 4` — same
  result here, but `15 // 2 = 7`, `7 // 2 = 3` vs `15 // 4 = 3` — also same; however
  `move: 28 // 2 = 14`, `14 // 2 = 7` vs `28 // 4 = 7` — all agree for these values but the
  two-step path matters conceptually for verifying the Python implementation mirrors ROM C).
- **Tests**: diff-harness smoke test auto-picked up the new scenario; 55 diff-harness tests pass
  (was 53). 34 scenarios total (was 33).

### `test_drive_python_replay_hunger_thirst_zero_halves_regen_twice` — ✅ ADDED

- **Location**: `tests/test_diff_harness_unit.py`
- **Verifies**: all three gain values (HP +2, mana +4, move +7) after one `__char_update` pulse
  with hunger=0 and thirst=0 against C-oracle ground truth. Also confirms `position == "SLEEPING"`
  is preserved through the snapshot.
- **Tests**: 1 new unit test passing.

## Files Modified

- `tools/diff_harness/scenarios/char_update_regen_hungry_thirsty.json` — new scenario (18 lines)
- `tests/data/golden/diff/char_update_regen_hungry_thirsty.golden.json` — new C golden (9 steps)
- `tests/test_diff_harness_unit.py` — `test_drive_python_replay_hunger_thirst_zero_halves_regen_twice`
- `CHANGELOG.md` — added [2.13.77] Added entries
- `pyproject.toml` — 2.13.76 → 2.13.77

## Test Status

- `pytest tests/test_differential_smoke.py tests/test_diff_harness_unit.py` — **55/55 passing**
  (was 53, +1 smoke scenario, +1 unit test)
- Full suite: **5534 passed, 4 skipped** (was 5532; +2 new tests)

## Condition Halving Coverage Summary

| Condition | `hit_gain` halved | `mana_gain` halved | `move_gain` halved |
|-----------|-------------------|--------------------|--------------------|
| COND_HUNGER == 0 | ✅ `game_loop.py:206` | ✅ `game_loop.py:275` | ✅ `game_loop.py:321` |
| COND_THIRST == 0 | ✅ `game_loop.py:208` | ✅ `game_loop.py:277` | ✅ `game_loop.py:323` |

Both branches now have C-oracle lock via the `char_update_regen_hungry_thirsty` scenario.

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

3. **Remaining diff-harness candidates** — the regen position matrix and condition-halving
   branches are now fully covered. Next harness expansion candidates:
   - Furniture bonus scenario: a SLEEPING PC sitting on furniture with nonzero value[3] (heal) /
     value[4] (mana) — C-oracle verifying `gain * value[3] / 100` and `gain * value[4] / 100`
     multipliers in `hit_gain`/`mana_gain`/`move_gain`.
   - `AFFECT_POISON` / `AFFECT_PLAGUE` / `AFFECT_HASTE` regen penalty scenarios (each apply
     their own divisor to `hit_gain`/`mana_gain`/`move_gain`).
   - `heal_rate` / `mana_rate` room multiplier scenario (rooms with non-100 rates).
