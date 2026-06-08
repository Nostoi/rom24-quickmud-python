# Session Summary — 2026-06-08 — Diff-Harness: shop buy + __mob_carry meta-command (2.13.22)

## Scope

Picked up from the 2.13.21 handoff's "Next Steps — `do_buy` diff-harness scenario". Implemented
the `__mob_carry=<vnum>` meta-command in both the C shim and Python replay to stock a shopkeeper
with specific inventory, then built the complete buy-side oracle verification: static scenario
`shop_buy_weapon`, golden captured from the live C engine, static test
`test_generated_shop_buy_matches_live_c`, and two new Hypothesis rules
(`stock_keeper_sword` / `buy_sword_from_keeper`) added to `DeterministicNoRngDiffMachine`.

## Outcomes

### `__mob_carry=<vnum>` meta-command — ✅ ADDED

- **C shim**: `src/diff_shim/diffmain.c` (after `__mob_hold` handler)
- **Python replay**: `tools/diff_harness/pyreplay.py:_run_python_command`
- **Design**: `create_object(oi, 0)` → `obj_to_char(obj, first_npc_in_room)` only — no
  `equip_char` call (contrast with `__mob_hold` which also calls `equip_char(mob, obj, WEAR_HOLD)`).
  Mirrors how a shopkeeper's real carry list is populated: items are in inventory, not slotted.
- **Tests**: All 16 generated tests + 8 golden smoke tests pass against both C and Python.

### `shop_buy_weapon` static scenario — ✅ ADDED

- **Scenario**: `tools/diff_harness/scenarios/shop_buy_weapon.json`
- **ROM C**: `src/act_obj.c:2660–2780 do_buy`
- **Design**: `start_room=3001`, `__mload=3003` (fresh weaponsmith, no area-reset carry-order
  ambiguity), `__mob_carry=3021` (stocks small sword, vnum 3021, cost=250), buy price=300 silver
  (`c_div(250*120,100)=300`, profit_buy=120 per midgaard weaponsmith shop record).
  `__seed=5678` brackets isolate `do_buy`'s unconditional `number_percent()` call
  (ROM `src/act_obj.c:2724`) from the surrounding stream.
- **Oracle result verified**:
  - Player: silver 300→0, gains small sword in inventory ✓
  - Keeper: gold 246→249 (`+3` = 300//100 = 3 gold, 300%100 = 0 silver — incremental credit
    fix from 2.13.21 working correctly in C) ✓
- **Golden**: `tests/data/golden/diff/shop_buy_weapon.golden.json` (11 steps)
- **Test**: `test_generated_shop_buy_matches_live_c` in
  `tests/test_diff_harness_generated.py` — PASSED against live C oracle.

### `stock_keeper_sword` + `buy_sword_from_keeper` Hypothesis rules — ✅ ADDED

- **Python**: `tools/diff_harness/generated.py:DeterministicNoRngDiffMachine`
- **New state**: `self._keeper_has_sword: bool` + `self.bought_sword: _ObjectState(vnum=3021)`
  tracks keeper inventory distinct from the player's own `small_sword`.
- **`stock_keeper_sword`**: precondition = weaponsmith in room and `_keeper_has_sword` False;
  emits `__mob_carry=3021`; sets `_keeper_has_sword = True`.
- **`buy_sword_from_keeper`**: precondition = `_keeper_has_sword`, `player_silver >= 300`,
  weaponsmith in room, `bought_sword` not yet in inventory; emits `__seed=5678` + `buy sword` +
  `__seed=5678`; sets `_keeper_has_sword = False`, `player_silver -= 300`,
  `bought_sword.inventory = True`.
- **Tests**: All 15 `test_diff_harness_generated.py` tests pass (including existing sell rules
  exercising interleaved drunk + weaponsmith paths).

## Files Modified

- `src/diff_shim/diffmain.c` — `__mob_carry=<vnum>` C shim handler (after `__mob_hold` block)
- `tools/diff_harness/pyreplay.py` — `__mob_carry=<vnum>` Python meta-command handler
- `tools/diff_harness/generated.py` — `bought_sword` + `_keeper_has_sword` state;
  `stock_keeper_sword` + `buy_sword_from_keeper` rules
- `tools/diff_harness/scenarios/shop_buy_weapon.json` — new static scenario
- `tests/data/golden/diff/shop_buy_weapon.golden.json` — new golden (C oracle output)
- `tests/test_diff_harness_generated.py` — `test_generated_shop_buy_matches_live_c` added
- `CHANGELOG.md` — 2.13.22 section: four Added entries
- `pyproject.toml` — 2.13.21 → 2.13.22

## Test Status

- **Diff harness golden**: 8/8 passing (`tests/test_differential_smoke.py`)
- **Diff harness generated**: 15/15 passing (`tests/test_diff_harness_generated.py`, seed=0)
- **Diff harness unit**: 13/13 passing (`tests/test_diff_harness_unit.py`)
- **Full suite**: 5433 passed, 4 skipped, 0 failed
- `ruff check .` clean; `gitnexus_detect_changes()` HIGH risk (expected — `diffmain.c:main`
  touched; all affected processes trace to C shim, not game engine)

## Next Steps

1. **Mob scripts** (`mob_prog.c`) — `mprog_act_trigger`/`mprog_entry_trigger` entry-level probes.
   No RNG alignment needed for basic trigger tests. Add a diff-harness scenario with a mob
   that has a greeting/entry trigger and verify the trigger fires identically.
2. **Additional spells** — `detect_evil`, `fly`, `bless`; seed alignment for the skill check.
   Extend `learn_and_cast_armor` pattern to these spells in the Hypothesis machine.
3. **Shop transaction atomicity** (INV candidate) — verify gold is deducted from player before
   item transfer in both engines; probe the error-exit paths (insufficient funds, item not for
   sale) for atomicity divergences.
4. Cross-INV candidates: affect-tick ordering contracts (call order in `char_update` vs ROM),
   shop transaction atomicity as above.
