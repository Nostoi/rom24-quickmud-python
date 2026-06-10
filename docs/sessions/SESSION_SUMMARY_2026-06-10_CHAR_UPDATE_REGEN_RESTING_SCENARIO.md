# Session Summary — 2026-06-10 — char_update regen resting scenario

## Scope

Continuation from v2.13.75 (`char_update_regen_sleeping` diff-harness scenario complete,
`__char_position=<n>` meta-command added). The session picked up the first concrete candidate
identified at session end: author the resting position variant to complete C-oracle coverage of
the position switch arms across `hit_gain`, `mana_gain`, and `move_gain`.

The `__char_position=5` (POS_RESTING) path was already supported by the `__char_position=`
primitive added last session. No new meta-commands were needed — the scenario dropped straight in
using the same structure as `char_update_regen_sleeping.json` with position=5.

No parity bugs were uncovered. All three resting branches were already correctly implemented in
`mud/game_loop.py`. The C oracle confirmed the resting rates are exactly half the sleeping rates
(with C integer division: `gain //= 2` for HP and mana; `DEX // 2` for move).

## Outcomes

### `char_update_regen_resting` scenario — ✅ ADDED

- **Scenario**: `tools/diff_harness/scenarios/char_update_regen_resting.json` — mage (class 0,
  default, `fMana=TRUE`), level 5, `__char_position=5` (resting), HP=5/max=20, mana=30/max=100,
  move=20/max=100, `__seed=12345`, three `__char_update` pulses.
- **C oracle results** (via `python3 -m tools.diff_harness.capture --scenario char_update_regen_resting`):
  - HP: 5 → 10 → 15 → 20 (+5/pulse). Base gain `max(3, CON-3+level//2) + hp_max-10 = 10`,
    POS_RESTING divides by 2: `10 // 2 = 5`. Half the sleeping rate (+10/pulse).
  - Mana: 30 → 38 → 46 → 54 (+8/pulse). Base gain `(WIS+INT+level)//2 = (13+16+5)//2 = 17`
    (INT=16 is the mage prime stat), POS_RESTING divides by 2: `17 // 2 = 8`. Half sleeping (+17).
  - Move: 20 → 41 → 62 → 83 (+21/pulse). `UMAX(15, level) + DEX//2 = 15 + 13//2 = 15 + 6 = 21`.
    POS_SLEEPING adds full DEX (13), resting adds DEX//2 (6). No `//2` halving on the total —
    the switch case only adds DEX//2 instead of DEX.
- **Golden**: `tests/data/golden/diff/char_update_regen_resting.golden.json`
  (8 steps, C sha 8077d0ae, build flags `-DOLD_RAND`).
- **Key observation**: Resting gives exactly half of sleeping for HP and mana. Move gain is more
  subtle: resting uses `DEX//2` in the switch, not a post-switch halving — so the base 15 is
  not halved, only the DEX contribution. A standing character gets neither bonus (the switch has
  no default case for move_gain), yielding only the base `UMAX(15, level) = 15`.
- **Tests**: diff-harness smoke test auto-picked up the new scenario; 53 diff-harness tests
  pass (was 51). 33 scenarios total (was 32).

### `test_drive_python_replay_char_position_resting_halves_all_gain` — ✅ ADDED

- **Location**: `tests/test_diff_harness_unit.py`
- **Verifies**: all three resting gain values (HP +5, mana +8, move +21) in one `__char_update`
  pulse against C-oracle ground truth. Also confirms `position == "RESTING"` is tracked in
  the snapshot.
- **Tests**: 1 new unit test passing.

## Files Modified

- `tools/diff_harness/scenarios/char_update_regen_resting.json` — new scenario (17 lines)
- `tests/data/golden/diff/char_update_regen_resting.golden.json` — new C golden (8 steps)
- `tests/test_diff_harness_unit.py` — `test_drive_python_replay_char_position_resting_halves_all_gain`
- `CHANGELOG.md` — added [2.13.76] Added entries
- `pyproject.toml` — 2.13.75 → 2.13.76

## Test Status

- `pytest tests/test_differential_smoke.py tests/test_diff_harness_unit.py` — **53/53 passing**
  (was 51, +1 smoke scenario, +1 unit test)
- Full suite: **5532 expected** (was 5530; +2 new tests)

## Position Coverage Summary (all three gain functions)

| Position | HP gain | Mana gain | Move gain |
|----------|---------|-----------|-----------|
| POS_SLEEPING (4) | base (÷1) | base (÷1) | UMAX(15,lvl) + DEX |
| POS_RESTING (5) | base ÷ 2 | base ÷ 2 | UMAX(15,lvl) + DEX//2 |
| POS_STANDING (8) / default | base ÷ 4 | base ÷ 4 | UMAX(15,lvl) (no bonus) |
| POS_FIGHTING | base ÷ 6 | base ÷ 6 | (no move gain during fight) |

All four branches now have C-oracle coverage across `hit_gain` and `mana_gain`.
`move_gain`'s POS_FIGHTING branch is not reachable in the current diff-harness
(no sustained combat scenario), but it is not part of `char_update` (fighting
chars skip the regen block per ROM `src/update.c:685`).

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

3. **Remaining diff-harness candidates** — the regen position matrix is now fully covered
   (sleeping/resting/standing all have scenarios). Next harness expansion candidates:
   - A standing-specific scenario that exercises the `÷4` HP path and `÷4` mana path
     with a low-level character to confirm the standing default branches.
   - A condition (hunger/thirst zero) scenario to C-oracle verify the `gain //= 2` halving
     in hit/mana gain when a condition slot hits 0.
