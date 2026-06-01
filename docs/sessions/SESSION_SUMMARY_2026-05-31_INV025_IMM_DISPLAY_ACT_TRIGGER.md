# Session Summary — 2026-05-31 — INV-025 imm_display ACT trigger dispatch

## Scope

Continued the INV-025 cross-file-invariant sweep from the session pointer,
focusing on immortal display command room narrations (`do_invis`, `do_wizinvis`,
`do_incognito`) whose ROM sites use unsuppressed `act()` calls.

## Outcomes

### INV-025 — imm_display sweep COMPLETED

- **`mud/commands/imm_display.py:_act_room`** — the shared helper used by
  `do_invis`, `do_wizinvis` (alias), and `do_incognito` for their room-wide
  `$n` messages. ROM `src/act_wiz.c:4342` (fade-into-existence),
  `:4348-4350` (fade-into-thin-air), `:4366` (level-set fade),
  `:4388` (uncloak), `:4398` (cloak), `:4412` (level-set cloak) all use
  `act(..., TO_ROOM)` with no `MOBtrigger = FALSE` wrapper, so `comm.c:2384`
  fires `mp_act_trigger` on NPC recipients unconditionally. Python's
  `_act_room` previously only delivered visible messages. Now dispatches
  `mp_act_trigger(display_msg, person, char, None, None, Trigger.ACT)` on
  every NPC recipient that passes the `MOBtrigger` gate.

- **INV-029 continuation:** `capitalize_act_line` applied to all `_act_room`
  rendered messages (matching ROM `act_new`'s first-letter cap at
  `src/comm.c:2376-2379`).

- **Tests:** 7/7 passing —
  `tests/integration/test_inv025_imm_display_act_trigger_dispatch.py`

## Files Modified

- `mud/commands/imm_display.py` — INV-025: added `mp_act_trigger` dispatch on
  NPC recipients inside `_act_room` (shared by `do_invis`/`do_incognito`);
  added `capitalize_act_line` per INV-029; local `import mud.mobprog as mobprog`
  for monkeypatch-safe test probes
- `tests/integration/test_inv025_imm_display_act_trigger_dispatch.py` — new (7 tests)
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-025 sweep entry:
  imm display dispatch
- `docs/sessions/SESSION_STATUS.md` — updated to 2.12.18
- `CHANGELOG.md` — INV-025 imm display entry under Changed
- `pyproject.toml` — 2.12.17 → 2.12.18

## Test Status

- `pytest tests/integration/test_inv025_imm_display_act_trigger_dispatch.py -n0 -v` — 7/7 passing
- `pytest tests/integration/test_inv025_imm_act_trigger_dispatch.py -n0 -v` — 8/8 passing
- Full integration suite: 2596 passed, 3 skipped
- Full suite: 5165 passed, 4 skipped
- `ruff check mud/commands/imm_display.py` — clean

## Next Steps

Continue the INV-025 sweep for remaining non-combat room narrations:

1. `mud/commands/communication.py` — `do_say`, `do_tell` (deferred cousins
   per INV-029 — capitalize-act-line is enforced, but the ACT trigger
   dispatch for NPC recipients may still be missing).
2. Other `imm_display.py` commands — `do_echo`, `do_recho` (echo/
   driver-level broadcasts — check if ROM echo functions use `act()` or
   `send_to_char` descriptor iteration).