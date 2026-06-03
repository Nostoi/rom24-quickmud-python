# Session Summary — 2026-06-03 — FINDING-026 diff light/shop widening (2.13.9)

## Scope

Picked up from `SESSION_SUMMARY_2026-06-03_FINDING_025_MOB_EQUIP_DISARM.md`.
The active mode remains the cross-file invariants / divergence-class sweep. This
session continued Phase C deterministic diff-harness widening for light/hold and
money/shop paths.

## Outcomes

### `light_hold` — ✅ ADDED

- **Harness**: `tools/diff_harness/scenarios/light_hold.json`
- **ROM C**: captured via `src/diffshim` against stock Midgaard object `3030`
  (torch).
- **Coverage**: `__oload=3030`, `get torch`, `hold torch`, `remove torch`, and
  `drop torch`; the snapshot observes LIGHT-slot equipment and inventory state.
- **Result**: Python replay matches the committed C golden.

### FINDING-026 — shop sell/value duplicate-stock pricing + wording — ✅ RESOLVED

- **Python**: `mud/commands/shop.py:_get_cost`, `do_value`, `do_sell`
- **ROM C**: `src/act_obj.c:get_cost`, `do_value`, `do_sell`
- **Gap**: `shop_sell_weapon` surfaced a C/Python mismatch on `value staff`:
  ROM quoted 116 coins while Python quoted 174 coins, and Python's keeper/sell
  wording differed from ROM `act()` capitalization and punctuation.
- **Fix**: `_get_cost` now checks duplicate-stock `ITEM_INVENTORY` on the
  keeper's carried object flags; `do_value` formats the ROM `act()` quote with
  first-letter capitalization; `do_sell` always emits ROM's silver+gold wording
  with the ROM suffix rule.
- **Tests**: `shop_sell_weapon` C golden plus `tests/test_shops.py` lock the
  pricing and wording behavior.

### Diff-harness `__hour=<n>` — ✅ ADDED

- **Python**: `tools/diff_harness/pyreplay.py`
- **ROM C shim**: `src/diff_shim/diffmain.c`
- **Purpose**: deterministic shop scenarios need an open shop hour. The new
  meta-command sets `time_info.hour` on both replay sides without reseeding RNG.

## Files Modified

- `mud/commands/shop.py` — fixed duplicate-stock sell discount and ROM
  sell/value wording.
- `src/diff_shim/diffmain.c` — added `__hour=<n>` meta-command.
- `tools/diff_harness/pyreplay.py` — added matching `__hour=<n>` replay support.
- `tools/diff_harness/scenarios/light_hold.json` — new deterministic light/hold
  scenario.
- `tools/diff_harness/scenarios/shop_sell_weapon.json` — new deterministic
  shop/money scenario.
- `tests/data/golden/diff/light_hold.golden.json` — C golden.
- `tests/data/golden/diff/shop_sell_weapon.golden.json` — C golden.
- `tests/test_shops.py` — corrected stale expectations to ROM sell/value wording.
- `tools/diff_harness/FINDINGS.md` — filed FINDING-026 as resolved.
- `CHANGELOG.md` — added 2.13.9 unreleased entries.
- `pyproject.toml` — 2.13.8 → 2.13.9.

## Test Status

- `python3 -m pytest -n0 tests/test_differential_smoke.py tests/test_diff_harness_unit.py -q`
  → 19 passed
- `python3 -m pytest -n0 tests/test_shops.py -q` → 35 passed
- Final lint / broader verification: see `SESSION_STATUS.md` and commit notes.

## Next Steps

Continue deterministic diff-harness widening on adjacent no-RNG money paths
(`drop <amount> gold/silver`, `get coins`, `give coins`) before adding
RNG-locked combat scenarios. Add RNG combat only after seed alignment is proven.
