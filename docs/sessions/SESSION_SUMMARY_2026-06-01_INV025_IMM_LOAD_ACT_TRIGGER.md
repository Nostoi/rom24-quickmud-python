# Session Summary — 2026-06-01 — INV-025 imm_load ACT trigger dispatch

## Scope

Continued the INV-025 cross-file-invariant sweep from the session pointer.
First verified `do_echo` / `do_recho` against ROM, then closed the next real
`act()` producer cluster in `mud/commands/imm_load.py`.

## Outcomes

### Echo/recho probe — no INV-025 producer

- ROM `src/act_wiz.c:674-777` implements `do_echo`, `do_recho`, `do_zecho`,
  and `do_pecho` by iterating `descriptor_list` and calling `send_to_char`.
- Because these paths do not call `act()`, they do not dispatch
  `mp_act_trigger` at `src/comm.c:2384`. No Python trigger wiring was added.

### INV-025 — imm_load sweep COMPLETED

- **`do_mload`** — ROM `src/act_wiz.c:2512` emits
  `act("$n has created $N!", ..., TO_ROOM)`. Python now dispatches
  `mp_act_trigger_room(..., arg2=victim)` after the visible room line.
- **`do_oload`** — ROM `src/act_wiz.c:2566` emits
  `act("$n has created $p!", ..., TO_ROOM)`. Python now dispatches
  `mp_act_trigger_room(..., arg1=obj)`.
- **`do_purge`** — ROM `src/act_wiz.c:2605,2633,2645` emits unsuppressed
  room / TO_NOTVICT `act()` lines. Python now dispatches room purge triggers
  to remaining NPCs and TO_NOTVICT triggers to bystander NPCs.
- **`do_restore`** — ROM `src/act_wiz.c:2809,2842,2863` emits
  `act("$n has restored you.", ..., TO_VICT)`. Python now dispatches
  `mp_act_trigger` when the restored victim is an NPC.

## Files Modified

- `mud/commands/imm_load.py` — added INV-025 `TRIG_ACT` dispatch for
  `do_mload`, `do_oload`, `do_purge`, and `do_restore`
- `tests/integration/test_inv025_imm_load_act_trigger_dispatch.py` — new
  enforcement tests (5)
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-025 sweep entry:
  imm_load dispatch
- `docs/sessions/SESSION_STATUS.md` — updated to 2.12.20
- `CHANGELOG.md` — INV-025 imm_load entry under Fixed
- `pyproject.toml` — 2.12.19 → 2.12.20

## Test Status

- `pytest -n0 tests/integration/test_inv025_imm_load_act_trigger_dispatch.py -v`
  — 5/5 passing
- `pytest -n0 tests/integration/test_inv025_imm_load_act_trigger_dispatch.py tests/integration/test_inv025_imm_act_trigger_dispatch.py tests/integration/test_inv025_imm_display_act_trigger_dispatch.py -v`
  — 20/20 passing
- `pytest -n0 tests/integration/test_mload_oload_broadcasts.py tests/integration/test_purge_broadcasts.py tests/integration/test_do_purge_nopurge_bits.py tests/integration/test_purge_routes_through_extract_character.py tests/integration/test_restore_strips_affects.py -v`
  — 10/10 passing
- `ruff check mud/commands/imm_load.py tests/integration/test_inv025_imm_load_act_trigger_dispatch.py`
  — clean
- `ruff check .` — not clean in this worktree due to pre-existing unrelated
  lint failures under `.claude/skills/`, diagnostic scratch files, and
  unrelated test modules; not introduced by this slice.

## Next Steps

Continue INV-025 on remaining `act_wiz.c` producers:

1. `mud/commands/imm_search.py:do_clone` — ROM `src/act_wiz.c:2405,2449`
   TO_ROOM clone broadcasts are unsuppressed `act()` calls.
2. Re-check any other uncovered `src/act_wiz.c` `act()` sites against the
   current Python path before adding trigger dispatch.
