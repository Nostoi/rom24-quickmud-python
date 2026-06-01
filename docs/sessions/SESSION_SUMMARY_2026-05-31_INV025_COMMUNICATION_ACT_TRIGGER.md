# Session Summary — 2026-05-31 — INV-025 communication ACT trigger dispatch

## Scope

Continued the INV-025 cross-file-invariant sweep from the session pointer,
focusing on communication command act() sites that were already capped by
INV-029 but still lacked act-level mobprog dispatch.

## Outcomes

### INV-025 — communication sweep COMPLETED

- **`mud/commands/communication.py:do_say`** — ROM `src/act_comm.c:776` emits
  `act("{6$n says ...", ..., TO_ROOM)` with no `MOBtrigger = FALSE` wrapper.
  Python now dispatches `TRIG_ACT` to NPC listeners with `TRIG_ACT` programs
  for each per-recipient rendered say line.
- **`mud/commands/communication.py:_deliver_tell` / `do_tell`** — ROM
  `src/act_comm.c:942` emits `act_new("{k$n tells you ...", ..., TO_VICT,
  POS_DEAD)` before the separate `TRIG_SPEECH` hook at `:946-947`. Python now
  dispatches `TRIG_ACT` to NPC tell targets with `TRIG_ACT` programs.
- The existing NPC-speaker anti-cascade behavior remains intact: NPC say/tell
  still does not fire `TRIG_SPEECH`; the new ACT dispatch is gated on
  `HAS_TRIGGER(TRIG_ACT)` and `MOBtrigger`.

## Files Modified

- `mud/commands/communication.py` — added local `TRIG_ACT` program gate and
  dispatch for `do_say` / `do_tell` act lines
- `tests/integration/test_inv025_communication_act_trigger_dispatch.py` — new
  enforcement tests (2)
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-025 communication sweep
  entry
- `docs/sessions/SESSION_STATUS.md` — updated to 2.12.19
- `CHANGELOG.md` — INV-025 communication entry under Fixed
- `pyproject.toml` — 2.12.18 → 2.12.19

## Test Status

- `pytest -n0 tests/integration/test_inv025_communication_act_trigger_dispatch.py -v` — 2/2 passing
- `pytest -n0 tests/integration/test_inv025_communication_act_trigger_dispatch.py tests/integration/test_say_parity.py tests/integration/test_tell_parity.py tests/integration/test_npc_speaker_does_not_trigger_speech.py tests/integration/test_act_cap_003_communication_capitalize.py tests/test_mobprog_triggers.py -v` — 29/29 passing

## Next Steps

Continue INV-025 by verifying `do_echo` / `do_recho` in `src/act_wiz.c` against
`mud/commands/imm_display.py`. Only wire `TRIG_ACT` if ROM uses unsuppressed
`act()`; if ROM iterates descriptors with `send_to_char`, document it as not an
INV-025 producer and move to the next candidate.
