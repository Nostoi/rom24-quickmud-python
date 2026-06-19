# Session Summary — 2026-06-19 — /loop gap-closer: shop visibility + runtime-cost parity (5/5)

## Scope

`/loop` gap-closer session, target 5 gaps then handoff. Picked up from the
prior `/loop` session (GIVE/DRINK/VALUE + GROUP, v2.14.153) whose
`SESSION_STATUS.md` "Next Intended Task" listed unmined shop probe candidates:
`do_buy`/`do_list` `can_see_obj` filters, `get_cost` proto-vs-runtime cost, and
the `do_sell` 95%-cap-when-`buy_price==0` edge. All five gaps below were
verified against ROM C `src/act_obj.c` before treating as gaps; each closed
failing-test-first, one test = one commit. Two of the five were stale-✅ audit
claims (BUY-007 / get_obj_keeper "visibility filter applied").

## Outcomes

### `BUY-007` — ✅ FIXED (`ee7a325d`, v2.14.154)

- **Python**: `mud/commands/shop.py:do_buy`
- **ROM C**: `src/act_obj.c:2459-2460, 2659` (`get_obj_keeper`)
- **Gap**: `do_buy` candidate loop lacked `can_see_obj(keeper, obj) && can_see_obj(ch, obj)`; a blind buyer (or `ITEM_INVIS` w/o detect-invis) could buy. Audit row for `get_obj_keeper` falsely claimed "visibility filter applied" (stale ✅).
- **Fix**: both visibility checks gated inside the candidate loop (so the `N.name` index only counts visible items).
- **Tests**: `tests/test_shops.py::test_buy_blind_buyer_cannot_see_item` (1).

### `LIST-004` — ✅ FIXED (`47f3e4cb`, v2.14.155)

- **Python**: `mud/commands/shop.py:do_list`
- **ROM C**: `src/act_obj.c:2831`
- **Gap**: listing loop lacked the `can_see_obj(ch, obj)` buyer filter. Note: `do_list` checks **only** the buyer's visibility, NOT the keeper's (asymmetric with `get_obj_keeper`).
- **Fix**: `can_see_object(char, obj)` gate added in the listing loop.
- **Tests**: `tests/test_shops.py::test_list_hides_items_blind_buyer_cannot_see` (1).

### `GETCOST-001` — ✅ FIXED (`6470150a`, v2.14.156)

- **Python**: `mud/commands/shop.py:_get_cost`
- **ROM C**: `src/act_obj.c:2487, 2499`
- **Gap**: `_get_cost` read the PROTOTYPE cost for both buy/sell; ROM uses the RUNTIME `obj->cost`. `do_buy` already clamps a purchased item's `obj.cost` to the haggled price (`shop.py:880-881`), but resale priced from `proto.cost` — a haggle-buy-cheap/resell-dear exploit.
- **Fix**: `_get_cost` reads `obj.cost` (proto fallback) for both directions. Bonus: room-reset objects (ROM `reset_room` 'O' zeroes `obj->cost`, `src/db.c:1783`, mirrored at `reset_handler.py:537`) now correctly resell for 0.
- **Tests**: `tests/test_shops.py::test_sell_uses_runtime_cost_not_prototype` (1). Plus 5 fixture repairs (3 files) that spawned vnum 3031/3050 then mutated the shared prototype — now sync each live object's runtime cost to the proto cost (the ROM spawn invariant). Full suite caught these 5 regressions, not the `-k` filter.

### `BUY-009` — ✅ FIXED (`0e31d009`, v2.14.157)

- **Python**: `mud/commands/shop.py:do_buy`
- **ROM C**: `src/act_obj.c:2727`
- **Gap**: buy-haggle discount base read `proto.cost`; ROM computes `cost -= obj->cost / 2 * roll / 100` using runtime `obj->cost`. Diverges once an item's runtime cost has been haggle-clamped.
- **Fix**: discount base reads `obj.cost` (proto fallback).
- **Tests**: `tests/test_shops.py::test_buy_haggle_discount_uses_runtime_cost` (1).

### `SELL-005` — ✅ FIXED (`fdaddbe2`, v2.14.158)

- **Python**: `mud/commands/shop.py:do_sell`
- **ROM C**: `src/act_obj.c:2931`
- **Gap**: the sell-haggle cap `cost = UMIN(cost, 95 * get_cost(keeper, obj, TRUE) / 100)` is UNCONDITIONAL in ROM; a zero buy price (`profit_buy == 0`) clamps the sale to 0. Python guarded it behind `if buy_price > 0`, paying the full haggled price.
- **Fix**: cap applied unconditionally.
- **Tests**: `tests/test_shops.py::test_sell_haggle_cap_applies_when_buy_price_zero` (1).

## Files Modified

- `mud/commands/shop.py` — `do_buy` (visibility filter + haggle base), `do_list` (visibility filter), `_get_cost` (runtime cost), `do_sell` (unconditional cap).
- `tests/test_shops.py` — 5 new tests; 5 fixture cost-syncs.
- `tests/integration/test_arith_111_haggle_no_floor.py`, `test_arith_115_keeper_wealth_no_floor.py` — fixture cost-syncs (GETCOST-001 fallout).
- `docs/parity/ACT_OBJ_C_AUDIT.md` — flipped/added rows: BUY-007, LIST-004, GETCOST-001, BUY-009, SELL-005 ✅; SELL-006 🔄 OPEN; corrected stale `get_obj_keeper` note (line 170).
- `CHANGELOG.md` — 5 `Fixed` entries.
- `pyproject.toml` — 2.14.153 → 2.14.158.

## Test Status

- Shop + arith suites: 49/49 passing.
- Full suite: **5872 passed, 4 skipped** (parallel, `PYTEST_EXIT=0`, captured directly). Re-run after each cost-touching gap per the VAL-005 lesson.
- `ruff check` clean on all touched files.

## Outstanding (filed durably this session)

- **SELL-006** (`docs/parity/ACT_OBJ_C_AUDIT.md`, 🔄 OPEN) — `do_sell` sell-haggle
  bonus base reads `proto.cost` (`shop.py:954`); ROM uses runtime `obj->cost`
  (`src/act_obj.c:2930`). Sell-side mirror of BUY-009/GETCOST-001. Close with a
  failing test first; pick `profit_buy` high enough that the 95% cap (:2931)
  doesn't bind and mask the difference.

## Next Steps

Close **SELL-006** (next free gap, ready to go). Then continue mining shop /
`act_obj.c` probe candidates from the prior session that remain unverified:
`do_buy`/`do_list` keeper `can_see_obj` symmetry already done here; remaining —
`get_cost` haggle interactions on ITEM_INVENTORY dupes, and the MOB_CMDS Phase-1
"⚠️ DIVERGENT" inventory labels still need flipping to ✅ (doc-only hygiene,
MOBCMD-001..021 all closed). Per-file tracker remains exhausted → cross-file /
divergence-class sweep (Layer C) stays the active pass.
