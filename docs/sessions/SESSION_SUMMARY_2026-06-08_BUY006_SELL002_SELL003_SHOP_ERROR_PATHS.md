# Session Summary — 2026-06-08 — BUY-006/SELL-002/SELL-003: shop error-exit parity

## Scope

Picked up from the 2.13.25 FINDING-030 handoff. Active mode is cross-file
invariants / diff-harness expansion (all 43 per-file audits at 100%). The
session notes called for probing `do_buy` / `do_sell` error-exit paths as
a prelude to adding diff-harness error-path scenarios.

While reading ROM C `src/act_obj.c` to plan the scenarios, three divergences
were found by direct source comparison — not via harness replay.

## Outcomes

### BUY-006 — `do_buy` check ordering — ✅ FIXED

- **Python**: `mud/commands/shop.py:do_buy`
- **ROM C**: `src/act_obj.c:2688` (afford), `2702` (level)
- **Gap**: Python ran the level check (ROM line 2702) before the afford check
  (ROM line 2688). ROM C checks afford first. A player with 0 silver trying to
  buy a level-gated item received "can't use yet" instead of "can't afford".
- **Fix**: Moved `total_cost` computation and the afford guard above the level
  guard in `do_buy`. Two ROM C cite comments updated.
- **Tests**: `test_buy_afford_checked_before_level` — discriminating double-failure
  setup (level-5 char, 0 silver, long sword vnum 3022 at level 7/cost 610).

### SELL-002 — `do_sell` keeper-can't-see message — ✅ FIXED

- **Python**: `mud/commands/shop.py:do_sell` `_keeper_can_see_object` branch
- **ROM C**: `src/act_obj.c:2905-2908` — `act("$n doesn't see what you are offering.", keeper, NULL, ch, TO_VICT)`
- **Gap**: Python returned hardcoded `"The shopkeeper doesn't see what you are
  offering."` — no `$n` expansion.
- **Fix**: `_act_to_char(keeper, "$n doesn't see what you are offering.")`
- **Tests**: `test_sell_cant_see_uses_keeper_name` — invisible sword (ITEM_INVIS)
  so keeper can't see object but can still see customer (blind keeper would fail
  `find_keeper`'s customer-visibility check first).

### SELL-003 — `do_sell` "looks uninterested" message — ✅ FIXED

- **Python**: `mud/commands/shop.py:do_sell` `get_cost<=0` branch
- **ROM C**: `src/act_obj.c:2911-2914` — `act("$n looks uninterested in $p.", keeper, obj, ch, TO_VICT)`
- **Gap**: Python returned hardcoded `"The shopkeeper doesn't buy that."` — wrong
  message entirely, no `$n`/`$p` expansion.
- **Fix**: `_act_to_char(keeper, "$n looks uninterested in $p.", obj=selected_obj)`
- **Tests**: `test_sell_uninterested_uses_keeper_name` — sell torch (vnum 3030,
  item_type=light) to weaponsmith who only buys types 5/6/7.

### `_act_to_char` helper — ✅ ADDED

New private helper in `mud/commands/shop.py` (alongside `_keeper_says`) that
renders ROM `act(message, keeper, obj, ch, TO_VICT)` strings by expanding
`$n` → `keeper.short_descr` and `$p` → `obj.short_descr`. Used for the two
`do_sell` branches that are NOT "tells you" format.

## Files Modified

- `mud/commands/shop.py` — `_act_to_char` added; `do_buy` reordered (BUY-006);
  `do_sell` two message sites updated (SELL-002/003)
- `tests/integration/test_shop_error_paths.py` — new file, 3 tests
- `docs/parity/ACT_OBJ_C_AUDIT.md` — post-audit gap table added, all 3 rows ✅ FIXED
- `CHANGELOG.md` — v2.13.26 entries
- `pyproject.toml` — 2.13.25 → 2.13.26

## Test Status

- `tests/integration/test_shop_error_paths.py` — 3/3 passing
- `tests/integration/test_shop_room_broadcasts.py` — 3/3 passing
- `tests/integration/test_shop_haggle_delivery_channel.py` — 3/3 passing

## Next Steps

The original plan for this session was to add diff-harness error-path scenarios
for shop transactions. The three source divergences were fixed first (they would
have caused harness mismatches). Next:

1. **Diff-harness error-path scenarios** — now that message output is ROM-correct,
   a `shop_buy_insufficient_funds` JSON scenario is ready to author:
   - `__silver=0 __gold=0`, weaponsmith loaded, sword stocked → `buy sword`
   - Watch: Tester messages (expect "can't afford to buy a long sword")
   - No `__mob_gold`/`__mob_silver` meta-commands needed for buy path.

2. **`sell`-side keeper-broke scenario** may need a `__mob_gold=0`/`__mob_silver=0`
   meta-command (diffmain.c + pyreplay.py) to zero the spawned keeper's wealth,
   since weaponsmith `wealth=25000` generates ~125-375 gold from RNG. Alternatively
   find a low-wealth keeper mob in the area files.

3. **Cross-INV affect-tick ordering** — `char_update` affect list traversal order
   vs ROM C `src/update.c:char_update` — still the longer-term invariant target.
