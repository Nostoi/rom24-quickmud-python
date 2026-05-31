# Session Summary — 2026-05-31 — INV-025 do_open ACT Trigger

## Scope

Continued the cross-file invariants primary pass from
`SESSION_SUMMARY_2026-05-31_INV025_PLAGUE_TICK_ACT_TRIGGER.md`. Picked the next
INV-025 follow-up from the broader non-combat act-dispatch sweep: `do_open`
door/container/portal actor-room broadcasts that mirror ROM `act(..., TO_ROOM)`
but did not dispatch `TRIG_ACT` to listening NPCs.

## Outcome

### INV-025 `do_open` actor-room `act()` — ✅ FIXED (2.11.59)

**ROM verification**:

- `src/act_move.c:384` — open portal emits `act("$n opens $p.", ..., TO_ROOM)`.
- `src/act_move.c:412` — open container emits `act("$n opens $p.", ..., TO_ROOM)`.
- `src/act_move.c:436` — open door emits `act("$n opens the $d.", ..., TO_ROOM)`.
- `src/comm.c:2384-2385` — NPC recipients of `act()` receive `mp_act_trigger`
  when `MOBtrigger` is true.

**Python divergence**:

`mud/commands/doors.py:do_open` sent the visible room line through
`broadcast_room` only. Players saw the text, but TRIG_ACT mobprogs keyed on
door-open messages silently no-opped.

**Fix**:

Added `mud/commands/doors.py:_broadcast_act_to_room`, a narrow helper for the
`do_open` actor-room `TO_ROOM` legs. It preserves the existing room broadcast
and then calls `mp_act_trigger_room` with the relevant ROM act arguments.

## Files Modified

- `mud/commands/doors.py` — added `_broadcast_act_to_room`; routed open portal,
  container, and door actor-room broadcasts through it.
- `tests/integration/test_inv025_do_open_act_trigger_dispatch.py` — new
  failing-first regression for the door `TO_ROOM` trigger dispatch.
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — recorded the INV-025
  `do_open` follow-up closure.
- `CHANGELOG.md` — added the INV-025 `do_open` follow-up entry.
- `pyproject.toml` — 2.11.58 → 2.11.59.

## Verification

- `pytest -n0 tests/integration/test_inv025_do_open_act_trigger_dispatch.py::test_do_open_door_fires_act_trigger_on_listening_npc -q`
  - fail-first: failed because no `mp_act_trigger` fired.
  - after fix: passed.
- `pytest -n0 tests/integration/test_inv025_do_open_act_trigger_dispatch.py tests/integration/test_door_broadcasts.py tests/integration/test_door_portal_commands.py tests/integration/test_inv025_mobprog_act_trigger_dispatch.py -q`
  - 20 passed.
- `ruff check mud/commands/doors.py tests/integration/test_inv025_do_open_act_trigger_dispatch.py`
  - all checks passed.
- `ruff check .`
  - not clean due to 1,830 pre-existing unrelated lint issues in `.claude/skills`,
    diagnostic scripts, and unrelated tests; changed-file Ruff is clean.
- `pytest -q`
  - 5094 passed, 4 skipped.

## Outstanding

- Continue cross-file invariant probe/close cycle.
- Remaining INV-025 act-dispatch sweep: broader non-combat `_push_message` /
  `broadcast_room` narration surfaces where the matching ROM site uses `act()`,
  especially the remaining door command branches (`do_close`/`do_lock`/
  `do_unlock`/`do_pick`) and other command room broadcasts.
- Mob script trigger contracts beyond INV-025/INV-026.
- Position-transition edge cases during death/recovery.
- `Character.pet` type annotation hygiene.
- `curse` handler type annotation hygiene.
