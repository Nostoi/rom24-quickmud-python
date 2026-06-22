# Session Summary — 2026-06-22 — Descriptor Wait Buffers Input (INV-054)

## Scope

Investigated a live combat report: after `kill monster`, typing `cast magic`
produced `You are still recovering.` before a later `cast magic` succeeded.

## Outcome

- Filed and enforced **INV-054 DESCRIPTOR-WAIT-BUFFERS-INPUT**.
- ROM C (`src/comm.c:619-623`) gates descriptor input while `ch->wait > 0`
  before `read_from_buffer()` / `interpret()`, leaving typed bytes buffered
  until recovery clears. It does not dispatch into `do_cast`, so no visible
  recovery line is produced on the live descriptor path.
- Python now mirrors that at `mud/net/connection.py:_read_player_command`:
  commands read while `character.wait > 0` are held in
  `Session.pending_command`; the read task stays pending until wait clears, so
  the outer prompt loop cannot render a duplicate prompt before replaying the
  command.
- Direct command/helper behavior is otherwise unchanged; existing
  `"You are still recovering."` tests still pass for direct command calls and
  skill-registry delivery.

## Files Modified

- `mud/net/session.py` — added `Session.pending_command`.
- `mud/net/connection.py` — wait-state descriptor buffering in
  `_read_player_command`.
- `tests/test_networking_telnet.py` — new INV-054 regression test.
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — added INV-054 row.
- `CHANGELOG.md` — Unreleased fixed entry.

## Verification

- `pytest -n0 tests/test_networking_telnet.py::test_wait_state_buffers_command_until_recovered_per_rom`
- `pytest -n0 tests/test_networking_telnet.py tests/integration/test_inv038_idle_timer_input_reset.py tests/integration/test_still_recovering_single_delivery.py tests/integration/test_skill_registry_delivery_channel.py`
- `pytest -n0 tests/test_telnet_server.py::test_excessive_repeats_trigger_spam_warning tests/test_telnet_server.py::test_repeat_command_after_blank_line_uses_last_non_empty tests/test_skills_spells_cast_listing.py::test_do_cast_prefix_matches_single_token_name tests/test_skills_spells_cast_listing.py::test_do_cast_magic_missile_dispatches_handler_and_damages_target`
- `ruff check .`
- `gitnexus_detect_changes()` — low risk, no affected processes.

## Next Steps

- Continue the active cross-file invariant / differential-harness pass.
