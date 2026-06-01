# Session Summary — 2026-05-31 — INV025 immortal command ACT trigger dispatch

## Scope

Continued the INV-025 cross-file-invariant sweep from the session pointer,
focusing on immortal command room narrations (`do_transfer`, `do_goto`,
`do_violate`, `do_force`) whose ROM C sites use unsuppressed `act()` calls.

## Outcomes

### INV-025 — ✅ FIXED (imm command sweep)

- **`mud/commands/imm_commands.py:do_transfer`** — mushroom-cloud departure
  (`:870`) and puff-of-smoke arrival (`:873`) TO_ROOM broadcasts now dispatch
  `mp_act_trigger_room` to NPC room occupants. The TO_VICT "has transferred
  you" line (`:875`) dispatches `mp_act_trigger` on NPC victims.

- **`mud/commands/imm_commands.py:_act_room_invis_gated`** — shared by
  `do_goto` and `do_violate` for bamfout/bamfin per-recipient trust-gated
  lines. Each NPC that passes the trust gate now also receives
  `mp_act_trigger(formatted_line, person, char, None, None, Trigger.ACT)`,
  matching ROM `src/act_wiz.c:969-994` and `:1026-1051`.

- **`mud/commands/imm_commands.py:do_force`** — single-target TO_VICT line
  (`src/act_wiz.c:4316`) dispatches `mp_act_trigger` on NPC victims.

- **Tests**: 8/8 passing —
  `tests/integration/test_inv025_imm_act_trigger_dispatch.py`

## Files Modified

- `mud/commands/imm_commands.py` — INV-025: added `mp_act_trigger_room` /
  `mp_act_trigger` dispatch in `do_transfer`, `_act_room_invis_gated`,
  and `do_force` single-target; lint cleanup
- `mud/commands/imm_server.py` — unchanged (inherits `_act_room_invis_gated`
  from imm_commands via import)
- `tests/integration/test_inv025_imm_act_trigger_dispatch.py` — new (8 tests)
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-025 sweep entry:
  imm command dispatch
- `docs/sessions/SESSION_STATUS.md` — updated to 2.12.17
- `CHANGELOG.md` — INV-025 imm command entry under Fixed
- `pyproject.toml` — 2.12.16 → 2.12.17

## Test Status

- `pytest tests/integration/test_inv025_imm_act_trigger_dispatch.py -n0 -v` — 8/8 passing
- `pytest tests/integration/test_inv025_steal_act_trigger_dispatch.py -n0 -v` — 4/4 passing
- `pytest tests/integration/test_inv025_liquids_act_trigger_dispatch.py -n0 -v` — 4/4 passing
- Full integration suite: 2589 passed, 3 skipped (143s)
- `ruff check mud/commands/imm_commands.py` — clean

## Next Steps

Continue the INV-025 sweep for remaining non-combat room narrations:

1. `mud/commands/imm_display.py:_act_room` — `do_visible`, `do_invis`,
   `do_cloak`, `do_decloak` room narrations (7 calls, all unsuppressed).
2. `mud/commands/communication.py` — `do_say`, `do_tell` (deferred cousins
   per INV-029).