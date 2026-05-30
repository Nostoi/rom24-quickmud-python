# Session Summary — 2026-05-30 — INV-025 Position Act Trigger

## Scope

Continued the cross-file invariants pass from
`SESSION_SUMMARY_2026-05-30_INV001_SHOP_HAGGLE_CHANNEL.md`.

Before new work, committed and pushed the carried local state on `master`:
`811834aa chore: update codex config` (`origin/master` updated).

Targeted the open `INV-025` follow-up sweep for one additional ROM `act()`
surface: position-command room broadcasts from `do_stand` / `do_rest` /
`do_sit` / `do_sleep`.

## Outcome

### `INV-025` position-command TRIG_ACT dispatch — ✅ FIXED (2.11.50)

- **Python**: `mud/commands/position.py:_broadcast`
- **ROM C**: `src/act_move.c:999-1449`, `src/comm.c:2384`
- **Fix**: The shared position-command room broadcast helper now calls
  `mud.mobprog.mp_act_trigger_room` after `broadcast_room`, so NPC recipients
  with `TRIG_ACT` see the same room `act(..., TO_ROOM)` lines ROM routes
  through `mp_act_trigger`.
- **Regression**:
  `tests/integration/test_inv025_mobprog_act_trigger_dispatch.py::test_position_act_room_broadcast_fires_act_trigger_on_listening_npc`
  fails first without the dispatcher and passes after the fix.

## Files Modified

- `mud/commands/position.py` — position room broadcasts dispatch `TRIG_ACT`
- `tests/integration/test_inv025_mobprog_act_trigger_dispatch.py` — new
  position-command regression
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — records this follow-up as
  closed
- `CHANGELOG.md` — added 2.11.50 unreleased entry
- `pyproject.toml` — bumped `2.11.49` → `2.11.50`

## Verification

- `pytest -n0 tests/integration/test_inv025_mobprog_act_trigger_dispatch.py::test_position_act_room_broadcast_fires_act_trigger_on_listening_npc -q`
  - fail-first: `fired == []`
  - after fix: `1 passed`
- `pytest -n0 tests/integration/test_inv025_mobprog_act_trigger_dispatch.py -q`
  - `4 passed`
- `ruff check mud/commands/position.py tests/integration/test_inv025_mobprog_act_trigger_dispatch.py`
  - `All checks passed!`

## Outstanding

- Continue cross-file invariant probe/close cycle.
- Known xdist flakes remain carried-open: `test_combat_death.py`,
  `test_backstab_uses_position_and_weapon`.
- Other carried-open items unchanged: `Character.pet` stale type annotation,
  `do_cast` object-targeting legs, unused imports in `group_commands.py`.
