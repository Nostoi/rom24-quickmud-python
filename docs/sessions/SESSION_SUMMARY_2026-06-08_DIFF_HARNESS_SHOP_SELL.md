# Session Summary — 2026-06-08 — Diff-Harness: shop sell + do_sell/do_buy wealth parity (2.13.21)

## Scope

Picked up from SESSION_STATUS "Next Intended Task — shop interactions (`do_buy`/`do_sell`)
via the diff harness." Added a deterministic shop-sell scenario to the harness, surfacing four
independent parity bugs in `do_sell` and `do_buy`'s wealth-accounting paths. Also fixed a
harness-internal ordering bug in `normalize_step` that produced "no field localized" false
failures when multiple watch-chars appear in different insertion orders.

## Outcomes

### `do_sell` player credit — incremental gold/silver (FINDING-028) — ✅ FIXED

- **Python**: `mud/commands/shop.py:do_sell` (around line 1007–1010)
- **ROM C**: `src/act_obj.c:2938-2939`
- **Gap**: Python called `_set_character_total_wealth(char, total + price)`, which rebalances
  the player's entire wealth into `gold = total//100, silver = total%100`. With the test char
  holding gold=10 and silver=200, a sell for 100 silver produced gold=13, silver=0 instead of
  ROM's gold=11, silver=200 (each bucket incremented independently).
- **Fix**: `char.gold += price // 100; char.silver += price % 100`, matching ROM's two-line
  independent increment.
- **Tests**: `test_generated_shop_sell_matches_live_c` (Tester silver/gold assertions pass)

### `do_sell` unconditional `number_percent()` RNG draw (FINDING-028) — ✅ FIXED

- **Python**: `mud/commands/shop.py:do_sell` haggle block
- **ROM C**: `src/act_obj.c:2925`
- **Gap**: Python gated `roll = rng_mm.number_percent()` behind `if haggle_skill > 0:`.
  ROM always draws from the RNG stream even when the player has no haggle skill — the call
  fires unconditionally; only the bonus application is conditional.
- **Fix**: Hoisted `roll = rng_mm.number_percent()` outside the guard (same class as
  FIGHT-021/022 — ROM C draws RNG even when the result is discarded).
- **Note**: The trailing `__seed=5678` bracket in the sell test scenario resets the stream
  after `sell sword`, so the harness does not directly verify this fix — confirmed by source
  reading only.

### `do_sell` keeper deduction via `deduct_cost` (FINDING-029) — ✅ FIXED

- **Python**: `mud/commands/shop.py:do_sell` (around line 1011)
- **ROM C**: `src/act_obj.c:2940` → `src/handler.c:2397-2422 deduct_cost`
- **Gap**: Python called `_set_keeper_total_wealth(keeper, total_wealth - price)`, which
  rebalances the keeper's full wealth total into gold/silver. Since the weaponsmith holds
  substantial silver from area-reset stock (measured: silver≈11100 at spawn from seed 4321),
  the rebalance folded that silver into gold — C=246 gold vs Python=356 gold after the sell.
  ROM's `deduct_cost` subtracts from silver first, leaving gold unchanged unless silver is
  exhausted.
- **Fix**: `deduct_cost(keeper, price)` — already imported from `mud.handler`, already
  duck-type compatible with `MobInstance` (uses `getattr`/direct attr write).
- **Tests**: `test_generated_shop_sell_matches_live_c` with weaponsmith in `watch_chars`;
  Hypothesis state machine exercises co-loaded drunk + weaponsmith paths.

### `do_buy` keeper credit — incremental gold/silver (FINDING-029) — ✅ FIXED

- **Python**: `mud/commands/shop.py:do_buy` (around line 829)
- **ROM C**: `src/act_obj.c:2747-2748`
- **Gap**: Same class as the sell-side fix — `_set_keeper_total_wealth(keeper, total + cost)`
  rebalanced when it should have incremented. ROM does `keeper->gold += cost/100;
  keeper->silver += cost - (cost/100)*100`.
- **Fix**: Direct incremental credit matching ROM. Not yet covered by a diff-harness oracle
  scenario (buy scenario is the next task), confirmed by source reading.

### `normalize_step` list-ordering fix — ✅ FIXED

- **Python**: `tools/diff_harness/compare.py:normalize_step`
- **Gap**: `normalize_step` passed the `chars` and `rooms` lists through without sorting the
  lists themselves (only sorted fields *within* each element). The `diff_traces` equality
  check (`c_step == py_step`) is order-sensitive on Python lists, so when C emits chars as
  `[Tester, drunk, weaponsmith]` and Python emits `[Tester, weaponsmith, drunk]`, the equality
  fails but `_render_step_diff`'s dict-keyed per-field loops both pass — producing the
  misleading "no field localized" fallback. Triggered immediately when `load_weaponsmith` and
  `load_drunk` were combined in the Hypothesis machine.
- **Fix**: `chars` sorted by `key`, `rooms` sorted by `vnum` inside `normalize_step`.

## Files Modified

- `mud/commands/shop.py` — `do_sell`: incremental player credit + unconditional
  `number_percent()` + `deduct_cost(keeper, price)`; `do_buy`: incremental keeper credit
- `tools/diff_harness/generated.py` — `load_weaponsmith` rule (with corrected `__hour` comment
  explaining negative boot-time `time_info.hour`); `sell_sword_to_weaponsmith` rule; weaponsmith
  added to `teardown()` watch_chars; `__hour` comment updated from "platform-dependent" to
  explain the actual mechanism (current_time unset → lhour negative in C)
- `tools/diff_harness/compare.py` — `normalize_step` sorts chars by key and rooms by vnum
- `tests/test_diff_harness_generated.py` — `test_generated_shop_sell_matches_live_c` added;
  watches `["Tester", "weaponsmith"]`
- `tools/diff_harness/FINDINGS.md` — FINDING-028 and FINDING-029 filed
- `CHANGELOG.md` — 2.13.21 section: four Fixed entries + three Added entries
- `pyproject.toml` — 2.13.20 → 2.13.21

## Test Status

- **Diff harness**: 28/28 passing (`tests/test_diff_harness_generated.py` 15 +
  `tests/test_diff_harness_unit.py` 13)
- **Shop tests**: 49/49 passing (`tests/test_shops.py`)
- **Full suite**: 5434+ passed, 0 failed (background run exit code 0 after commit)
- `ruff check .` clean; `gitnexus_detect_changes()` LOW risk, 0 affected processes

## Next Steps

1. **`do_buy` diff-harness scenario** — add `__mob_carry=<vnum>` meta-command (C shim +
   Python replay) to equip a keeper with specific stock, then a `buy_sword_from_keeper` rule
   and static `test_generated_shop_buy_matches_live_c` scenario. Verify both player deduction
   (`deduct_cost`) and keeper credit (just fixed) against the live C oracle.
2. **Mob scripts** (`mob_prog.c`) — `mprog_act_trigger`/`mprog_entry_trigger`; entry-level
   probes, no RNG alignment needed.
3. **Additional spells** beyond armor — `detect_evil`, `fly`, `bless`; seed alignment for
   the skill check.
4. Cross-INV candidates: affect-tick ordering contracts (call order in `char_update` vs ROM),
   shop transaction atomicity.
