# Session Summary — 2026-05-31 — INV-025 consumption ACT triggers

## Scope

Resumed the cross-file-invariants probe pass from `SESSION_STATUS.md`. The
remaining useful target was the broader **INV-025 MOBPROG-ACT-TRIGGER-DISPATCH**
sweep: ROM `act()` room narrations should dispatch `TRIG_ACT` to NPC recipients
unless wrapped in `MOBtrigger = FALSE`.

## Outcome

### INV-025 consumption sweep — ✅ FIXED (2.12.13)

- **ROM C**: `src/act_obj.c:1238-1241` (`do_drink`) and `:1317`
  (`do_eat`) emit the main consume room lines through `act(..., TO_ROOM)`.
  Poisoned consumption also uses `act("$n chokes and gags.", ..., TO_ROOM)` at
  `src/act_obj.c:1263` and `:1342`. Because these sites are not wrapped in
  `MOBtrigger = FALSE`, `src/comm.c:2384` dispatches `TRIG_ACT` for NPC
  recipients.
- **Python**: `mud/commands/consumption.py` now calls
  `mp_act_trigger_room(...)` after the existing `broadcast_room(...)` for
  `do_eat`, `do_drink`, and both poisoned choke room lines.
- **Regression**: new `tests/integration/test_inv025_consumption_act_trigger_dispatch.py`
  locks the positive eat/drink producer paths.

## Files Modified

- `mud/commands/consumption.py`
- `tests/integration/test_inv025_consumption_act_trigger_dispatch.py`
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`
- `CHANGELOG.md`
- `pyproject.toml`

## Verification

- `pytest -n0 tests/integration/test_inv025_consumption_act_trigger_dispatch.py -q`
  — 2 passed.
- `pytest -n0 tests/integration/test_consumables.py -q` — 51 passed.

## Next Steps

Continue the INV-025 sweep on remaining non-combat ROM `act()` room narrations,
with likely targets in `mud/commands/magic_items.py`, `mud/commands/liquids.py`,
`mud/commands/thief_skills.py`, and immortal command room narrations. Use the
same probe-then-scope flow: read ROM C call site, write one failing ACT-trigger
test, wire `mp_act_trigger_room` only for genuine `act()` producers.
