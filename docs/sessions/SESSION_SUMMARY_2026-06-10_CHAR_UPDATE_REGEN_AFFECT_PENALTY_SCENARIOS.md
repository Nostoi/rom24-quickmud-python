# Session Summary — 2026-06-10 — char_update regen affect-penalty scenarios (POISON + HASTE)

## Scope

Continuation from v2.13.77 (`char_update_regen_hungry_thirsty` diff-harness scenario complete,
condition-halving coverage fully locked). The session picked up the next concrete diff-harness
candidate: authoring C-oracle scenarios for the `IS_AFFECTED` regen divisor branches —
specifically `AFF_POISON` (÷4) and `AFF_HASTE` (÷2) — in `hit_gain`, `mana_gain`, and
`move_gain` (ROM `src/update.c:274-284`).

A `__add_affect=<bit>` meta-command was designed and implemented to set a single AFF_* bitmask
bit on the test character without adding a full spell `AFFECT_DATA` entry. This allows the regen
divisor branch to fire cleanly without triggering the tick-handler's spell-affect linked-list
logic, avoiding the "orphan-bit" problem (the Python PLAGUE tick-handler clears the PLAGUE bit
when no spell-affect entry is found; C does not). POISON and HASTE were chosen because neither
engine clears their bits when no spell-affect entry is present, making them stable across
multiple pulses with only the bitmask set.

A PLAGUE scenario was considered but deferred: the Python `_char_update_tick_effects` path
clears the orphan PLAGUE bit, while C skips the sores loop entirely — a genuine divergence
across pulse 2+ that would require a separate fix, not just a scenario.

No parity bugs were found in POISON or HASTE handling. Python already implements the ÷4 and ÷2
divisors correctly in `hit_gain`, `mana_gain`, and `move_gain` (`mud/game_loop.py:231-234`,
`302-305`, `348-351`). The C oracle confirmed the Python implementation is correct.

## Outcomes

### `__add_affect=<bit>` meta-command — ✅ ADDED

- **C shim**: `src/diff_shim/diffmain.c` — new block after `__mob_delay=`, before
  `__charm_mob=`. Uses `SET_BIT(ch->affected_by, (int)bit)` to OR the given bitmask
  into the character's `affected_by` field directly.
- **Python**: `tools/diff_harness/pyreplay.py` — new block after `__mob_delay=`.
  `char.affected_by = int(getattr(char, "affected_by", 0) or 0) | val`.
- **Rationale**: exercises `IS_AFFECTED` regen branches without spell-affect entry, avoiding
  tick-handler interference. Safe for POISON/HASTE; not safe for PLAGUE (orphan-bit divergence).

### `char_update_regen_poison` scenario — ✅ ADDED

- **Scenario**: `tools/diff_harness/scenarios/char_update_regen_poison.json` — mage (class 0),
  level 5, `__char_position=4` (sleeping), HP=1/mana=5/move=5, `__add_affect=4096`
  (AFF_POISON = 1<<12), three `__char_update` pulses.
- **C oracle results** (via `python3 -m tools.diff_harness.capture --scenario char_update_regen_poison`):
  - HP: 1 → 3 → 5 → 7 (+2/pulse). Base sleeping gain = 10; `10 // 4 = 2`.
  - Mana: 5 → 9 → 13 → 17 (+4/pulse). Base = 17; `17 // 4 = 4`.
  - Move: 5 → 12 → 19 → 26 (+7/pulse). Base = 28; `28 // 4 = 7`.
  - `affect_flags: ['poison']` confirmed present on all three post-pulse snapshots.
- **Golden**: `tests/data/golden/diff/char_update_regen_poison.golden.json` (8 steps,
  C sha bfb77ddb, build flags `-DOLD_RAND`).
- **Note**: These values coincide numerically with the `char_update_regen_hungry_thirsty`
  scenario (+2/+4/+7). The paths differ — hunger+thirst applies two sequential `//2`
  halvings; POISON applies a single `//4` division. Both yield the same result for these
  specific base values.

### `char_update_regen_haste` scenario — ✅ ADDED

- **Scenario**: `tools/diff_harness/scenarios/char_update_regen_haste.json` — mage (class 0),
  level 5, `__char_position=4` (sleeping), HP=1/mana=5/move=5, `__add_affect=2097152`
  (AFF_HASTE = 1<<21), three `__char_update` pulses.
- **C oracle results**:
  - HP: 1 → 6 → 11 → 16 (+5/pulse). Base = 10; `10 // 2 = 5`.
  - Mana: 5 → 13 → 21 → 29 (+8/pulse). Base = 17; `17 // 2 = 8`.
  - Move: 5 → 19 → 33 → 47 (+14/pulse). Base = 28; `28 // 2 = 14`.
  - `affect_flags: ['haste']` confirmed present on all three post-pulse snapshots.
- **Golden**: `tests/data/golden/diff/char_update_regen_haste.golden.json` (8 steps).
- **Note**: Distinct values (+5/+8/+14) clearly differentiated from all other regen scenarios.

### Unit tests — ✅ ADDED

- **`test_drive_python_replay_poison_affect_halves_regen_by_four`** —
  `tests/test_diff_harness_unit.py`. Verifies HP=3/mana=9/move=12 after one pulse with
  AFF_POISON set via `__add_affect=4096`. Position confirmed SLEEPING.
- **`test_drive_python_replay_haste_affect_halves_regen_by_two`** —
  `tests/test_diff_harness_unit.py`. Verifies HP=6/mana=13/move=19 after one pulse with
  AFF_HASTE set via `__add_affect=2097152`. Position confirmed SLEEPING.

## Files Modified

- `src/diff_shim/diffmain.c` — `__add_affect=<bit>` meta-command (13 lines inserted)
- `tools/diff_harness/pyreplay.py` — `__add_affect=<bit>` handler (8 lines)
- `tools/diff_harness/scenarios/char_update_regen_poison.json` — new scenario (12 lines)
- `tools/diff_harness/scenarios/char_update_regen_haste.json` — new scenario (12 lines)
- `tests/data/golden/diff/char_update_regen_poison.golden.json` — new C golden (8 steps)
- `tests/data/golden/diff/char_update_regen_haste.golden.json` — new C golden (8 steps)
- `tests/test_diff_harness_unit.py` — two new unit tests (60 lines)
- `CHANGELOG.md` — added [2.13.78] Added entries
- `pyproject.toml` — 2.13.77 → 2.13.78

## Test Status

- `pytest tests/test_differential_smoke.py tests/test_diff_harness_unit.py` — **59/59 passing**
  (was 55; +2 smoke scenarios, +2 unit tests)
- Full suite: **5538 passed, 4 skipped** (was 5534; +4 new tests)

## Affect Penalty Regen Coverage Summary

| AFF_* flag | Divisor | `hit_gain` branch | `mana_gain` branch | `move_gain` branch | C-oracle scenario |
|------------|---------|-------------------|--------------------|--------------------|------------------|
| AFF_POISON (4096) | ÷4 | ✅ `game_loop.py:231` | ✅ `game_loop.py:302` | ✅ `game_loop.py:348` | `char_update_regen_poison` |
| AFF_HASTE (2097152) | ÷2 | ✅ `game_loop.py:233` | ✅ `game_loop.py:304` | ✅ `game_loop.py:350` | `char_update_regen_haste` |
| AFF_PLAGUE (8388608) | ÷8 | ⬜ covered by Python impl | ⬜ covered by Python impl | ⬜ covered by Python impl | ❌ deferred (orphan-bit divergence) |
| AFF_SLOW | ÷2 | ⬜ covered by Python impl | ⬜ covered by Python impl | ⬜ covered by Python impl | ❌ not yet |

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

3. **Remaining diff-harness candidates** — POISON and HASTE affect-penalty branches are now
   C-oracle locked. Remaining expansion candidates:
   - **AFF_PLAGUE C-oracle scenario**: requires fixing the orphan-bit divergence in
     `_char_update_tick_effects` first (Python clears PLAGUE bit when no spell-affect entry;
     C does not). Fix Python, add scenario, lock with C oracle.
   - **AFF_SLOW C-oracle scenario**: similar to HASTE; check whether orphan-bit divergence
     applies, then author scenario.
   - **Furniture bonus scenario**: SLEEPING PC on furniture with nonzero `value[3]`/`value[4]`
     — C-oracle verifying `gain * value[3] / 100` and `gain * value[4] / 100` multipliers.
   - **`heal_rate` / `mana_rate` room multiplier scenario** (rooms with non-100 rates).
