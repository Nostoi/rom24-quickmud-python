# Session Summary — 2026-06-08 — BUY-007/ACT-CAP: keeper message capitalisation + quote order

## Scope

Picked up from the 2.13.26 BUY-006/SELL-002/SELL-003 handoff. Active mode
is cross-file invariants / diff-harness expansion. The intended task was to
author the `shop_buy_insufficient_funds` diff-harness scenario (the previous
session fixed the messages so they'd be ROM-correct before capturing goldens).

While capturing the C golden (`python3 -m tools.diff_harness.capture --scenario
shop_buy_insufficient_funds`), the replay test immediately diverged:

```
step 10 (buy sword):
  C  = ["The weaponsmith tells you 'You can't afford to buy a long sword'."]
  py = ["the weaponsmith tells you 'You can't afford to buy a long sword.'"]
```

Two bugs were found in `_keeper_says` (and `_act_to_char`): missing first-char
capitalisation and wrong closing-quote / period placement.

## Outcomes

### BUY-007/ACT-CAP — `_keeper_says` capitalisation + quote order — ✅ FIXED

- **Python**: `mud/commands/shop.py:_keeper_says`, `mud/commands/shop.py:_act_to_char`
- **ROM C**: `src/comm.c:2376-2379` — `buf[0] = UPPER(buf[0])` after per-recipient
  formatting in `act_new`. ROM capitalises the first rendered character for every
  `act()` call.
- **Gap 1 — capitalisation**: Both `_keeper_says` and `_act_to_char` returned the
  raw `keeper.short_descr` (e.g. `"the weaponsmith"`) without capitalising. All
  keeper-voiced messages were lowercase.
- **Gap 2 — quote/period order**: `_keeper_says` wrapped every message in `'...'`
  unconditionally. ROM C's format strings are inconsistent — some close the quote
  before the period (`"$n tells you 'You can't afford to buy $p'."`) while others
  have no closing quote (`"$n tells you 'I don't have that many in stock."`). The
  wrapper produced `.'` everywhere; correct is `'.` or no closing quote depending
  on the message.
- **Fix**:
  - Both helpers now call `capitalize_act_line(...)` on their return value
    (`mud/utils/act.py:capitalize_act_line` mirrors ROM `src/comm.c:2376-2379`).
  - `_keeper_says` no longer wraps; it prepends the opening `'` and passes the
    message through verbatim. Callers now supply the ROM-exact suffix (including
    whether the closing `'` precedes the period).
  - Four call sites updated with ROM-exact punctuation:
    - `"You can't afford to buy $p."` → `"You can't afford to buy $p'."`
    - `"You can't use $p yet."` → `"You can't use $p yet'."`
    - `"You don't have that item."` → `"You don't have that item'."`
    - `"I don't sell that -- try 'list'."` → `"I don't sell that -- try 'list''."`
- **Tests**: 5 existing assertions in `tests/test_shops.py` updated to ROM-correct
  format using `capitalize_act_line`. One test (`test_sell_respects_drop_and_visibility_gates`)
  had a pre-existing bug hardcoding `"The shopkeeper"` instead of the actual
  keeper's `short_descr` (vnum 3002 = "the grocer"); fixed to use `capitalize_act_line`.

### Diff-harness `shop_buy_insufficient_funds` scenario — ✅ ADDED

- **Scenario**: `tools/diff_harness/scenarios/shop_buy_insufficient_funds.json`
  — `__silver=0`, `__gold=0`, weaponsmith (`__mload=3003`) stocked with long sword
  (`__mob_carry=3022`), `list`, then `buy sword`.
- **Golden**: `tests/data/golden/diff/shop_buy_insufficient_funds.golden.json`
  — 10 steps, C-captured. Key outputs:
  - `list` step: `[ 7   732  1 ] a long sword`
  - `buy sword` step: `The weaponsmith tells you 'You can't afford to buy a long sword'.`
- **Replay**: `test_python_matches_c_golden[shop_buy_insufficient_funds]` — PASS.
  Locks the BUY-003/BUY-006/BUY-007 error-exit path end-to-end against C ground truth.

## Files Modified

- `mud/commands/shop.py` — `_keeper_says` / `_act_to_char` capitalisation + format
  fix; 4 call sites updated (BUY-007/ACT-CAP)
- `tests/test_shops.py` — 5 assertions updated to ROM-correct format; import
  `capitalize_act_line` added
- `tools/diff_harness/scenarios/shop_buy_insufficient_funds.json` — new scenario
- `tests/data/golden/diff/shop_buy_insufficient_funds.golden.json` — new C golden
- `CHANGELOG.md` — v2.13.27 entries
- `pyproject.toml` — 2.13.26 → 2.13.27

## Test Status

- `tests/test_differential_smoke.py` — 10/10 passing (all scenarios)
- `tests/test_shops.py` — all passing
- `tests/integration/test_shop_error_paths.py` — 3/3 passing
- Full suite: **5445 passed, 4 skipped**

## Next Steps

1. **Cross-INV affect-tick ordering** — `char_update` affect list traversal order
   vs ROM C `src/update.c:char_update`. This is the longer-term invariant target
   that has been deferred since 2.13.19. Probe: read `src/update.c:char_update`
   affect expiry loop, compare to `mud/world/update.py:char_update`, write a
   single failing enforcement test.

2. **`shop_sell_keeper_broke` scenario** (optional) — keeper-broke sell path. Needs
   `__mob_gold=0`/`__mob_silver=0` meta-commands in `diffmain.c` + `pyreplay.py`
   to zero keeper wealth after `__mload`, since weaponsmith `wealth=25000` generates
   ~125-375 gold from RNG on spawn. Alternatively use a low-wealth keeper mob.
