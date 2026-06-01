# Session Summary — 2026-06-01 — INV-025 clone ACT trigger dispatch

## Scope

Continued the INV-025 cross-file-invariant sweep from the session pointer.
The next target was `mud/commands/imm_search.py:do_clone`, whose matching ROM
`act_wiz.c` sites use unsuppressed `act(TO_ROOM)` for object and mobile clone
creation broadcasts.

## Outcomes

### `do_clone` — ✅ CLOSED

- **Python**: `mud/commands/imm_search.py:472-477`, `:541-546`
- **ROM C**: `src/act_wiz.c:2405`, `:2449`; dispatch mechanism at
  `src/comm.c:2384`
- **Fix**: after the existing visible room broadcasts, `do_clone` now dispatches
  `mp_act_trigger_room` for the same message. Object clones thread the cloned
  object as `arg1` (`$p`); mobile clones thread the cloned mobile as `arg2`
  (`$N`).
- **Tests**: `tests/integration/test_inv025_clone_act_trigger_dispatch.py`
  added two red-first enforcement tests.

## Files Modified

- `mud/commands/imm_search.py` — added INV-025 `TRIG_ACT` dispatch for both
  clone branches.
- `tests/integration/test_inv025_clone_act_trigger_dispatch.py` — new
  enforcement tests for object/mobile clone room broadcasts.
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-025 sweep entry:
  clone dispatch.
- `docs/sessions/SESSION_STATUS.md` — updated to 2.12.21.
- `CHANGELOG.md` — added INV-025 clone entry under Fixed.
- `pyproject.toml` — 2.12.20 → 2.12.21.

## Test Status

- `pytest -n0 tests/integration/test_inv025_clone_act_trigger_dispatch.py -v`
  — 2/2 passing.
- `pytest -n0 tests/integration/test_inv025_clone_act_trigger_dispatch.py tests/integration/test_clone_broadcasts.py tests/integration/test_act_wiz_command_parity.py -k 'clone' -v`
  — 8/8 passing.

## Next Steps

Continue the broader INV-025 sweep for remaining non-combat narrations whose
matching ROM sites use `act()` and Python still only calls `broadcast_room` or
another delivery primitive without `mp_act_trigger`. Re-check each remaining
`src/act_wiz.c` `act()` site against the current Python path before wiring
anything; echo/recho/zecho/pecho were already confirmed as descriptor
`send_to_char` paths, not producers.
