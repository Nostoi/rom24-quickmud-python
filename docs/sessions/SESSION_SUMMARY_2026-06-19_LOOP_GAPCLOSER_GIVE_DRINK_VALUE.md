# Session Summary — 2026-06-19 — /loop gap-closer: changer/give/drink/value + group PERS (5/5)

## Scope

`/loop` dynamic-mode gap-closer session, target 5 gaps then handoff. Picked up
from the prior loop's GROUP-005 OPEN pointer (`SESSION_STATUS.md`). Gap 1 was the
documented GROUP-005. The per-file audit tracker had no other actionable
non-deferred rows (all MOB_CMDS "⚠️ DIVERGENT" Phase-1 labels are stale — the
Phase-3 gap list MOBCMD-001..021 is fully ✅ FIXED), so gaps 2–5 came from the
**probe-then-scope** mode: parallel Explore-agent C-vs-Python probes of fresh
surfaces (`do_give`, weather/time, `do_drink`/`do_eat`, shop `do_buy/sell/value`),
each candidate **re-verified against ROM C source by hand** before being treated
as a gap. Several probe candidates were correctly rejected as non-divergences
(weather `\n\r` vs `\r\n` — the delivery layer normalizes; `do_split` keyword
parsing — intentional legacy compat; changer `IS_NPC`/`can_see` guards —
non-observable).

## Outcomes

### `GROUP-005` — ✅ FIXED (2.14.149)

- **Python**: `mud/commands/group_commands.py:do_group`
- **ROM C**: `src/act_comm.c:1784, :1796, :1841-1854`
- **Gap**: do_group's display header, member line, and add/remove broadcasts baked
  `short_descr`/`name` instead of ROM's `PERS(x, ch)` / `act()` masking.
- **Fix**: header → `_pers_gated(leader, char)` (lowercase "someone's group:");
  member → `capitalize_act_line(_pers_gated(gch, char))` ("Someone"); broadcasts →
  `act_format` (per-recipient `$n`/`$N` PERS + `$s` possessive, not a baked name);
  delivery still `_send_to_char_sync` (GROUP-001 preserved). Removed dead
  `_display_name` helper.
- **Tests**: `tests/integration/test_group_005_pers_masking.py` (3) — pass.

### `GIVE-004` — ✅ FIXED (2.14.150)

- **Python**: `mud/commands/give.py:_handle_changer_exchange`
- **ROM C**: `src/act_obj.c:741`
- **Gap**: money-changer gold-exchange formula had a spurious extra `/100`. ROM
  `change = silver ? 95*amount/100/100 : 95*amount` — the gold branch has no
  division (10 gold → 950 silver). Python's `95*amount//100` returned 9 silver and
  tripped "not enough to change" on any gold gift ≤ 1.
- **Fix**: gold branch → `95 * amount`. Contradicted a stale Phase-1 "changer
  verified ✅" note (corrected in place).
- **Tests**: `test_give_command.py::test_give_gold_to_changer_returns_silver_minus_fee` — pass.

### `GIVE-005` — ✅ FIXED (2.14.151)

- **Python**: `mud/commands/give.py:do_give` (shop branch)
- **ROM C**: `src/act_obj.c:801`
- **Gap**: give-to-shopkeeper refusal didn't set `ch->reply = victim` (a live
  mechanic — `do_reply` reads `char.reply`).
- **Fix**: set `char.reply = victim` before the refusal return.
- **Tests**: `test_give_command.py::test_give_item_to_shopkeeper_sets_reply_target` — pass.

### `DRINK-011` — ✅ FIXED (2.14.152)

- **Python**: `mud/commands/consumption.py:do_drink`
- **ROM C**: `src/act_obj.c:1243-1250` (+ `src/const.c` liq_table)
- **Gap**: the four `gain_condition` deltas used bare `//`, but `liq_affect`
  columns can be negative (slime mold juice thirst −8, blood −1, salt water −2).
  `2 * -8 // 10 == -2` (floor) vs ROM `-16 / 10 == -1` (truncate) — player got
  thirsty 2× as fast for negative-affect liquids. A signed-math (`c_div`) violation;
  DRINK-005's "affect calculations ✅" never exercised the sign case.
- **Fix**: all four deltas → `c_div(...)`.
- **Tests**: `test_consumables.py::test_drink_negative_thirst_affect_truncates_toward_zero` — pass.

### `VAL-005` — ✅ FIXED (2.14.153)

- **Python**: `mud/commands/shop.py:do_value`
- **ROM C**: `src/act_obj.c:2994, :3007`
- **Gap**: the can't-see and "uninterested" branches hardcoded "The shopkeeper …"
  instead of ROM's `act("$n …"/"$n looks uninterested in $p.", keeper, obj, ch,
  TO_VICT)` — a named keeper showed "The shopkeeper" and the uninterested line
  dropped the item name. The sibling `do_sell` already rendered these via
  `_act_to_char` (SELL-002/003); `do_value` was the outlier.
- **Fix**: both branches → `_act_to_char`. Also updated the stale
  `tests/test_shops.py::test_value_respects_drop_and_visibility_gates` assertion
  that pinned the pre-fix buggy string (caught by the full suite, not the per-gap
  `-k` run).
- **Tests**: `test_shop_error_paths.py::test_value_uninterested_uses_keeper_name_and_item` (new) + `test_shops.py` (assertion updated) — pass.

## Files Modified

- `mud/commands/group_commands.py` — GROUP-005 PERS-masking + dead helper removal
- `mud/commands/give.py` — GIVE-004 changer gold formula + GIVE-005 reply
- `mud/commands/consumption.py` — DRINK-011 c_div (import + 4 deltas)
- `mud/commands/shop.py` — VAL-005 do_value keeper-voiced messages
- `tests/integration/test_group_005_pers_masking.py` — new (3 tests)
- `tests/integration/test_give_command.py` — GIVE-004 + GIVE-005 tests
- `tests/integration/test_consumables.py` — DRINK-011 test
- `tests/integration/test_shop_error_paths.py` — VAL-005 test
- `tests/test_shops.py` — stale VAL-005 assertion updated
- `docs/parity/ACT_COMM_C_AUDIT.md` — GROUP-005 → ✅
- `docs/parity/ACT_OBJ_C_AUDIT.md` — GIVE-004/005, DRINK-011, VAL-005 → ✅ (+ stale-✅ corrections)
- `CHANGELOG.md` — 5 Fixed entries
- `pyproject.toml` — 2.14.148 → 2.14.153

## Test Status

- Area suites (per gap, `-n0`): group/follow/act_comm (121), give (19),
  consumables (59), shop_error_paths + test_shops (39) — all green.
- Full suite: **5867 passed, 4 skipped** (the lone failure — a stale `test_shops.py`
  assertion pinning the pre-VAL-005 buggy string — was fixed and folded into the
  VAL-005 commit; re-confirmed green).

## Next Steps

Per-file audit tracker remains exhausted of actionable rows → continue the
probe-then-scope / divergence-class sweep. Unmined probe candidates surfaced but
**not** closed this session (verify before treating as gaps): shop `do_buy`/`do_list`
buyer/keeper `can_see_obj` filters (ROM `get_obj_keeper` `src/act_obj.c:2459-2460`);
`get_cost` using `proto.cost` vs runtime `obj->cost` after a haggle; `do_sell`
95% cap skipped when `buy_price == 0`. Also re-check whether the MOB_CMDS Phase-1
"⚠️ DIVERGENT" inventory labels should be flipped to ✅ (they're stale — gaps all
closed). **Durable lesson reinforced:** the per-gap `-k` suite is NOT sufficient —
run the full suite before pushing; VAL-005 broke a sibling assertion in a file the
`-k` filter never touched (the exact failure mode the advisor flagged).
