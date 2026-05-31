# Session Summary — 2026-05-31 — INV-025 Plague Tick ACT Trigger

## Scope

Continued the cross-file invariants primary pass from
`SESSION_SUMMARY_2026-05-30_GL025_CHAR_UPDATE_ORDER.md`. Closed the carried-open
INV-025 follow-up for plague tick room messages: ROM emits those lines through
`act(..., TO_ROOM)`, so they must use per-recipient PERS masking and dispatch
`TRIG_ACT` to NPC listeners.

## Outcome

### INV-025 plague tick room `act()` — ✅ FIXED (2.11.58)

**ROM verification**:

- `src/update.c:803-804` — plagued character room message uses `act("$n ... $s skin.", ch, NULL, NULL, TO_ROOM)`.
- `src/update.c:836-837` — plague-spread room message uses `act("$n shivers and looks very ill.", vch, NULL, NULL, TO_ROOM)`.
- `src/comm.c:2233-2385` — `TO_ROOM` skips the actor, formats `$n` through `PERS(ch, to)`, then calls `mp_act_trigger(..., TRIG_ACT)` for NPC recipients when `MOBtrigger` is true.

**Python divergence**:

`mud/game_loop.py:_char_update_tick_effects` baked `character.name` into a single
string and sent it through `_message_room`. That echoed the TO_ROOM line back to
the plagued character, leaked invisible actor names to non-seeing witnesses, and
never fired `mp_act_trigger` for listening NPCs.

**Fix**:

Added `mud/game_loop.py:_act_to_room`, a narrow per-recipient `act(TO_ROOM)`
helper for update-loop callsites. It skips the actor, renders through
`act_format(..., recipient=recipient)` for PERS masking, sends the message, and
dispatches `mp_act_trigger` for NPC recipients under the existing `MOBtrigger`
guard. Swapped both plague tick room lines to the helper.

## Files Modified

- `mud/game_loop.py` — added `_act_to_room`; routed plague tick room messages through it.
- `tests/integration/test_inv025_plague_tick_act_trigger_dispatch.py` — new regression for PERS masking, actor exclusion, and `TRIG_ACT` dispatch.
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — recorded the INV-025 plague tick follow-up closure.
- `CHANGELOG.md` — added the INV-025 follow-up entry.
- `pyproject.toml` — 2.11.57 → 2.11.58.

## Verification

- `pytest -n0 tests/integration/test_inv025_plague_tick_act_trigger_dispatch.py::test_plague_tick_room_act_masks_name_and_fires_act_trigger -q`
  - fail-first: failed because the plagued character received `"Wraith writhes ..."` via the TO_ROOM path.
  - after fix: passed.
- `pytest -n0 tests/integration/test_inv025_plague_tick_act_trigger_dispatch.py tests/integration/test_update_c_parity.py tests/integration/test_arith_203_204_plague_drain_no_floor.py tests/integration/test_gl_024_level1_plague_dormant.py -q`
  - 16 passed.
- `pytest -n0 tests/integration/test_inv025_mobprog_act_trigger_dispatch.py tests/integration/test_inv025_position_transition_act_trigger_dispatch.py tests/integration/test_inv025_equipment_act_trigger_dispatch.py tests/integration/test_inv025_do_drop_act_trigger_dispatch.py tests/integration/test_inv025_do_put_act_trigger_dispatch.py tests/integration/test_inv025_do_sacrifice_act_trigger_dispatch.py -q`
  - 10 passed.
- `ruff check mud/game_loop.py tests/integration/test_inv025_plague_tick_act_trigger_dispatch.py`
  - all checks passed.
- `pytest -q`
  - 5093 passed, 4 skipped.
- `gitnexus_detect_changes(scope=all)`
  - low risk, 0 affected execution flows.

## Outstanding

- Continue cross-file invariant probe/close cycle.
- Remaining INV-025 act-dispatch sweep: broader non-combat `_push_message` /
  `broadcast_room` narration surfaces where the matching ROM site uses `act()`.
- Mob script trigger contracts beyond INV-025/INV-026.
- Position-transition edge cases during death/recovery.
- `Character.pet` type annotation hygiene.
- `curse` handler type annotation hygiene.
