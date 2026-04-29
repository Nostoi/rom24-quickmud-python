# Session Summary — 2026-04-28 — `act_wiz.c` second parity pass

## Scope

Continued the `act_wiz.c` audit (Phase 2–4 of rom-parity-audit), closing two gaps.

## Gaps closed

### WIZ-006: `do_log` — ROM-faithful PLR_LOG toggle
- **ROM C**: `src/act_wiz.c:2927-2982`
- **Python**: `mud/commands/admin_commands.py:341` (`cmd_log`)
- **Fix**:
  - Replaced `character_registry` prefix-match lookup with `get_char_world()`
  - Replaced `log_commands` bool toggle with `PlayerFlag.LOG` bit toggle on `victim.act`
  - Added ROM `\n\r` line endings to all messages
  - NPCs correctly rejected with `"Not on NPC's.\n\r"`
- **Tests**: `test_log_toggles_plr_log_on_act_not_bool_field`, `test_log_rejects_npc`, `test_log_all_toggles_global_flag`, `test_log_empty_arg_and_not_found`

### WIZ-007: `do_force` — ROM all/players/gods + private-room + trust
- **ROM C**: `src/act_wiz.c:4183-4322`
- **Python**: `mud/commands/imm_commands.py:293` (`do_force`)
- **Fix**:
  - Added `force gods` branch for hero-level immortals (ROM lines 4256-4278)
  - Added private-room check using `_is_room_owner` / `_room_is_private` before forcing individuals (ROM 4295-4301)
  - Changed trust check to apply to all victims, not just non-NPCs (ROM 4304-4308)
  - Added `MAX_LEVEL-3` threshold for forcing PCs (ROM 4310-4313)
  - Iterated `descriptor_list` for `force all` and `char_list` for `force players`/`force gods` (ROM 4221-4277)
  - Changed `mob` prefix check to ROM `str_prefix` semantics (`startswith("mob")`)
  - Added canonical `\n\r` line endings to all messages
- **Tests**: `test_force_rejects_delete_and_mob_prefix`, `test_force_empty_arg`, `test_force_self_returns_aye_aye`, `test_force_gods_branch_rejects_low_trust`, `test_force_private_room_blocks_non_owner`, `test_force_single_target_trust_check`, `test_force_returns_ok_after_single_force`

## Still open

| ID | Description | ROM lines |
|----|-------------|-----------|
| WIZ-005 | `do_stat`/`do_rstat`/`do_ostat`/`do_mstat` — ROM-faithful detailed stat views missing | 1059-1742 |
| (many) | Remaining echo, punishment, load/clone, server-control functions need line-by-line audit | Various |

## Files touched

- `mud/commands/admin_commands.py` — `cmd_log` rewritten
- `mud/commands/imm_commands.py` — `do_force` rewritten
- `tests/integration/test_act_wiz_command_parity.py` — 7 new tests
- `docs/parity/ACT_WIZ_C_AUDIT.md` — WIZ-006, WIZ-007 flipped to ✅ FIXED
- `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` — act_wiz.c updated to 55%
- `docs/sessions/SESSION_STATUS.md` — updated
- `CHANGELOG.md` — WIZ-006, WIZ-007 entries

## Validation

```
pytest tests/integration/test_act_wiz_command_parity.py -q  →  15 passed
ruff check mud/commands/admin_commands.py mud/commands/imm_commands.py tests/integration/test_act_wiz_command_parity.py  →  clean
```