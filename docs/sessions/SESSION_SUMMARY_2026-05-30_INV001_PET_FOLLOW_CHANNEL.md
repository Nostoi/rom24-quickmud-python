# Session Summary — 2026-05-30 — INV-001 Pet Follow Channel

## Scope

Continued the cross-file invariants pass from
`SESSION_SUMMARY_2026-05-30_FIGHT-032_033_034_VISION-002.md`.

Targeted the carried-open INV-001 wrong-channel cousin in the pet-shop path:
`add_follower`'s `"$n now follows you."` line was mailbox-only for connected
buyers.

## Outcome

### `INV-001` pet-shop follow notification — ✅ FIXED (2.11.48)

- **Python**: `mud/characters/follow.py:add_follower`
- **ROM C**: `src/act_comm.c:1602-1605`
- **Fix**: The master and follower notification legs now route through
  `mud/utils/messaging.py:push_message`, matching ROM descriptor delivery for
  connected players while preserving mailbox fallback for disconnected
  characters/tests.
- **Regression**: `tests/integration/test_pet_buy_single_delivery.py` now checks
  that a connected pet buyer receives `"companion pet now follows you."` through
  the immediate connection channel before mailbox drain, and that the mailbox
  does not hold that line.

## Files Modified

- `mud/characters/follow.py` — `add_follower` uses `push_message`
- `tests/integration/test_pet_buy_single_delivery.py` — strengthened connected
  delivery assertions
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — noted the closed INV-001
  wrong-channel cousin and kept shop haggle open
- `CHANGELOG.md` — added 2.11.48 unreleased entry
- `pyproject.toml` — bumped `2.11.47` → `2.11.48`

## Verification

- `pytest -n0 tests/integration/test_pet_buy_single_delivery.py::test_buy_pet_delivers_enjoy_line_once_to_connected_pc -q`
  - fail-first: follow line was absent from the connection and stranded in
    `buyer.messages`
- `pytest -n0 tests/integration/test_pet_buy_single_delivery.py tests/integration/test_follow_can_see_gating.py tests/integration/test_do_follow_master_notification.py -q`
  - `5 passed`
- `ruff check mud/characters/follow.py tests/integration/test_pet_buy_single_delivery.py`
  - `All checks passed!`
- `gitnexus_detect_changes()` / `mcp__gitnexus__.detect_changes(scope="unstaged")`
  - risk `low`, no affected processes

## Outstanding

- Shop haggle wrong-channel remains open: `"You haggle the price down to N coins."`
  is still mailbox-only and spans pet/item buy plus sell branches.
- Known xdist flakes remain carried-open: `test_combat_death.py`,
  `test_backstab_uses_position_and_weapon`.
- Other carried-open items unchanged: `Character.pet` stale type annotation,
  `do_cast` object-targeting legs, unused imports in `group_commands.py`.
