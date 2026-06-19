# Session Summary — 2026-06-19 — /loop gap-closer: get_cost runtime-state parity (5/5)

## Scope

A `/loop` gap-closer session targeting 5 ROM parity gaps. Picked up from the
prior shop-visibility/cost `/loop` (v2.14.158) with the per-file audit tracker
exhausted of actionable rows — so the active mode was the **probe-then-scope
cross-file / divergence-class sweep**. Started with the one documented `🔄 OPEN`
row (SELL-006), then mined `src/act_obj.c:get_cost` against `mud/commands/shop.py`
function-by-function for the remaining four, filing each gap ID before closing it
TDD (failing test first → fix → commit). Theme: ROM prices from **runtime object
state** (`obj->cost`, `obj->value`, the live `keeper->carrying` list), where the
Python port repeatedly read the **prototype** instead — the same proto→runtime
divergence class as GETCOST-001/BUY-009.

## Outcomes

### `SELL-006` — ✅ FIXED (v2.14.159)

- **Python**: `mud/commands/shop.py:953`
- **ROM C**: `src/act_obj.c:2930`
- **Gap**: sell-haggle bonus `cost += obj->cost / 2 * roll / 100` read `proto.cost`; ROM uses runtime `obj->cost`.
- **Fix**: `base_cost` now reads `selected_obj.cost`.
- **Tests**: `tests/test_shops.py::test_sell_haggle_bonus_uses_runtime_cost` (profit_buy raised to 300 so the 95% cap at :2931 doesn't bind and mask the base).

### `GETCOST-003` — ✅ FIXED (v2.14.160)

- **Python**: `mud/commands/shop.py:477-481`
- **ROM C**: `src/act_obj.c:2504`
- **Gap**: ROM guards the keeper duplicate-stock discount loop with `if (!IS_OBJ_STAT(obj, ITEM_SELL_EXTRACT))`; Python applied the discount unconditionally.
- **Fix**: discount loop short-circuits when the sold object (or proto) has `ITEM_SELL_EXTRACT`.
- **Tests**: `tests/test_shops.py::test_get_cost_sell_extract_skips_dupe_discount` (self-validating: derives base, proves a plain object discounts, then asserts SELL_EXTRACT skips it).

### `GETCOST-002` — ✅ FIXED (v2.14.161)

- **Python**: `mud/commands/shop.py:486-491`
- **ROM C**: `src/act_obj.c:2505-2515`
- **Gap**: ROM's same-item discount loop has **no `break`** — it discounts once per matching copy, so non-inventory dupes compound (`cost*3/4` each). `obj_to_keeper` keeps non-inventory dupes as separate nodes (:2436-2437); the `ITEM_INVENTORY` branch can't compound (its dedup destroys the dupe at :2421). Python broke after the first match.
- **Fix**: removed the `break`.
- **Tests**: `tests/test_shops.py::test_get_cost_dupe_discount_compounds_per_copy`.
- **Collateral**: corrected a latent test bug in `test_wand_staff_price_scales_with_charges_and_inventory_discount` — it hardcoded `1<<18` (≠ `ITEM_INVENTORY`=8192, bit 13), so it never exercised the `/2` inventory path and its expected value encoded the old single-discount behavior. Now uses the real enum on the object (not the shared prototype) + the ROM-compounded value (2).

### `GETCOST-004` — ✅ FIXED (v2.14.162)

- **Python**: `mud/commands/shop.py:486-490`
- **ROM C**: `src/act_obj.c:2507-2508`
- **Gap**: ROM matches a keeper duplicate on `pIndexData == AND !str_cmp(short_descr)` — both. Python's predicate `op is proto OR (vnum AND descr)` short-circuited on prototype identity, discounting a same-prototype copy with a different runtime `short_descr`.
- **Fix**: descr check now always applied (`same_proto and other_descr == obj_descr`).
- **Tests**: `tests/test_shops.py::test_get_cost_dupe_discount_requires_matching_short_descr`.

### `GETCOST-005` — ✅ FIXED (v2.14.163)

- **Python**: `mud/commands/shop.py:503-507`
- **ROM C**: `src/act_obj.c:2520-2523`
- **Gap**: wand/staff charge scaling `cost = cost * obj->value[2] / obj->value[1]` reads runtime `obj->value` (remaining/max charges deplete with use); Python read `proto.value`, overpricing a partially-used wand/staff at its original full-charge ratio.
- **Fix**: charge scaling now reads `obj.value` (proto fallback).
- **Tests**: `tests/test_shops.py::test_get_cost_wand_charge_scaling_uses_runtime_value`. Also synced `obj.value` in the existing wand-scaling test (spawn invariant, mirroring GETCOST-001).

## Files Modified

- `mud/commands/shop.py` — `_get_cost` (SELL_EXTRACT guard, no-break compounding, descr-match, runtime value) and `do_sell` (runtime cost base).
- `tests/test_shops.py` — 5 new tests + `_clean_keeper_for_lantern` helper + corrected wand-scaling test; `c_div` import added.
- `docs/parity/ACT_OBJ_C_AUDIT.md` — flipped/added rows: SELL-006, GETCOST-002, GETCOST-003, GETCOST-004, GETCOST-005.
- `CHANGELOG.md` — 5 `Fixed` entries.
- `pyproject.toml` — 2.14.158 → 2.14.163.

## Test Status

- `tests/test_shops.py` — 45/45 passing.
- Full suite: **5877 passed, 4 skipped** (was 5872; +5 new gap tests). Confirmed clean after the GETCOST-002 no-break change (which altered sell pricing wherever a keeper carries matching stock — the durable "full suite, not the curated subset" lesson held: it broke exactly one sibling, the latent-bug wand test).
- `ruff check` clean.

## Outstanding

None filed this session — all five probed gaps were closed in-flight. The
`get_cost` surface is now fully reconciled against ROM `src/act_obj.c:2477-2527`
for the runtime-state divergence class (cost, value, dupe-list, SELL_EXTRACT,
descr-match). One adjacent observation noted but **not** a divergence: ROM's
`get_cost` buy-type loop and wand/staff gate use `obj->item_type` while Python
reads `proto.item_type` (`shop.py:471,502`) — these agree in practice because
runtime item_type is not mutated post-spawn; left as-is (no behavioral gap).

## Next Steps

Per-file tracker remains exhausted; continue the cross-file / divergence-class
sweep. Candidate next probes in `act_obj.c`: `do_value` (does it mirror every
`get_cost`/visibility gate now in `do_sell`?), and the `get_obj_keeper` /
`obj_from_keeper` cost-inheritance path on **buy** (does a bought item's runtime
cost get clamped and re-stocked exactly as ROM's `do_buy` :2765-2766?). Otherwise
pick a fresh divergence-class area (affect ticks, position transitions) via
`/rom-divergence-sweep`.
