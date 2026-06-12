# Session Status — 2026-06-12 — GL-039: obj_update spill gate (2.14.9)

## Current State

- **Active audit**: Cross-file invariants pass (all per-file P0/P1/P2 rows at 100%)
- **Last completed**: GL-039 — `obj_update` spill gate checked prototype `wear_flags & ITEM_WEAR_FLOAT`
  instead of runtime `wear_loc == WEAR_FLOAT`. A floating-capable disc stored in inventory/ground would
  incorrectly spill its contents on decay rather than silently destroying them. Fixed by removing the
  extra `elif` branch. ROM reference: `src/update.c:1025-1026`.
  Six probe candidates verified this session: `do_recall` move cost, `violence_update` mid-tick,
  `do_rescue` ordering, hit/mana/move regen, `gain_condition` tick — all CLEAN; `obj_update` spill
  gate — GL-039 filed and closed.
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-06-12_GL039_OBJ_UPDATE_SPILL_GATE.md](SESSION_SUMMARY_2026-06-12_GL039_OBJ_UPDATE_SPILL_GATE.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.9 |
| Tests | 5616/5616 passing (2026-06-12) |
| ROM C files audited | All P0/P1/P2 at 100% |
| Active focus | Cross-file invariants (next free ID: INV-045) |

## Next Intended Task

**Cross-file invariant probes** — three fresh candidates, probe-then-scope method:

1. **`obj_update` timer-decay ordering** — ROM `src/update.c:970-1005` decrements `timer` before
   acting on `timer <= 0`. Verify Python `obj_update` timer decrement happens in the correct order
   and doesn't accidentally skip or double-decrement on the same tick.
2. **`affect_update` count-down ordering** — ROM `src/update.c:330-420` processes affects by
   decrement-first. Verify Python `mud/game_loop.py` affect-update loop (or `mud/affects/engine.py`)
   follows the same decrement-before-trigger order.
3. **`do_look` / `do_exits` room-darkness flag** — ROM `src/act_info.c:look_in_room` guards on
   `room->light` and `IS_SET(room->room_flags, ROOM_DARK)`. Verify Python's darkness check uses the
   same two conditions with the same precedence (light count wins, then flag).

For each: read ROM C contract → read Python equivalent → write one failing test if divergence
found → close as single-gap commit or file as INV-NNN.
