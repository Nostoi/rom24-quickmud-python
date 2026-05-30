# Session Summary — 2026-05-30 — INV-001 Shop Haggle Channel

## Scope

Continued the cross-file invariants pass from
`SESSION_SUMMARY_2026-05-30_INV001_PET_FOLLOW_CHANNEL.md`.

Targeted the carried-open INV-001 wrong-channel cousin in shop haggle success
paths: pet buy, item buy, and sell haggles appended TO_CHAR text to
`char.messages` instead of delivering immediately to connected players.

## Outcome

### `INV-001` shop haggle wrong-channel cousin — ✅ FIXED (2.11.49)

- **Python**: `mud/commands/shop.py:_handle_pet_shop_purchase`,
  `mud/commands/shop.py:do_buy`, `mud/commands/shop.py:do_sell`
- **ROM C**: `src/act_obj.c:2606-2607`, `src/act_obj.c:2728`,
  `src/act_obj.c:2929`
- **Fix**: All three successful haggle lines now route through
  `mud/utils/messaging.py:push_message`, matching ROM descriptor delivery for
  connected players while preserving mailbox fallback for disconnected
  characters/tests.
- **Regression**: `tests/integration/test_shop_haggle_delivery_channel.py`
  checks connected delivery before mailbox drain for pet buy, item buy, and
  sell haggle success.

## Files Modified

- `mud/commands/shop.py` — haggle success lines use `push_message`
- `tests/integration/test_shop_haggle_delivery_channel.py` — new connected
  delivery regression coverage
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — closed the shop haggle
  wrong-channel cousin
- `CHANGELOG.md` — added 2.11.49 unreleased entry
- `pyproject.toml` — bumped `2.11.48` → `2.11.49`

## Verification

- `pytest -n0 tests/integration/test_shop_haggle_delivery_channel.py -q`
  - fail-first: all three haggle lines were absent from the connection and
    stranded in `char.messages`
  - after fix: `3 passed`
- `pytest -n0 tests/integration/test_shop_haggle_delivery_channel.py tests/integration/test_pet_buy_single_delivery.py tests/test_shops.py -q`
  - `39 passed`
- `ruff check mud/commands/shop.py tests/integration/test_shop_haggle_delivery_channel.py`
  - `All checks passed!`
- `gitnexus_detect_changes()` / `mcp__gitnexus__.detect_changes(scope="unstaged")`
  - risk `medium`; expected affected process is `Do_sell → Has_affect`

## Outstanding

- Known xdist flakes remain carried-open: `test_combat_death.py`,
  `test_backstab_uses_position_and_weapon`.
- Other carried-open items unchanged: `Character.pet` stale type annotation,
  `do_cast` object-targeting legs, unused imports in `group_commands.py`.
