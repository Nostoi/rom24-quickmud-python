# Session Status — 2026-05-31 — TRAIN-004 + INV-025 door-command family

## Current State

- **Active mode**: cross-file invariants (per-file audit tracker exhausted).
- **Last completed (this session)**:
  - **TRAIN-004 / WIZ-050 (2.12.2)** — stat training (`do_train`) and the
    `set char <stat>` ranges (`do_mset`) now use ROM's race/class-specific
    `get_max_train` instead of a hardcoded cap. Root cause was a shared broken
    helper: `mud.handler.get_max_train` compared the int `ch.race` index
    against PC-race *name* strings and read a non-existent `class_num`, so it
    fell through `return 18` for every real PC — `do_train` shadowed that with
    its own literal 22, and `do_mset` inherited the broken 18 cap. Fixed at the
    root (int-race→name bridge, `ch_class`, +3 human / +2 other prime bonus,
    fallback 25); both call sites route through the one helper. Corrected the
    false-✅ `get_max_train` row in HANDLER_C_AUDIT.
  - **INV-025 door family (2.12.3)** — `do_close`/`do_lock`/`do_unlock`/
    `do_pick` now dispatch `TRIG_ACT` to listening NPCs (was only `do_open`),
    via the existing `_broadcast_act_to_room` helper. The reverse-side
    linked-room broadcasts are left plain (uniform open follow-up; see summary).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-31_TRAIN004_AND_INV025_DOOR_COMMANDS.md](SESSION_SUMMARY_2026-05-31_TRAIN004_AND_INV025_DOOR_COMMANDS.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.12.3 |
| Tests | 5116 passed, 4 skipped |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Cross-file invariants | 24 enforced — INV-025 follow-up sweep extended to the door-command family |
| Open correctness gaps | none |
| Active focus | cross-file invariants probe pass |

## Next Intended Task

No open correctness gaps. Resume the **cross-file invariants probe pass**:

1. **INV-025 reverse-side door broadcasts** (uniform open follow-up): close
   `do_open:209` ("The $d opens.") + `do_close:302` ("The $d closes.") together
   — ROM's `act(..., rch, TO_CHAR)` loop in the linked room
   (`src/act_move.c:447-448`/`:545-547`) dispatches TRIG_ACT to a far-room NPC
   via `src/comm.c:2384`. Left untouched this session to stay symmetric with
   the `do_open` precedent. (lock/unlock/pick have no reverse-side broadcast.)
2. Broader INV-025 sweep: remaining non-combat `_push_message`/`broadcast_room`
   narration surfaces where the matching ROM site uses `act()`.
3. Other probe candidates: affect ticks, position transitions, mob script
   triggers, group/follower chain.

Method: probe-then-scope (read ROM C contract → read Python equivalent →
one failing test for the contract → close as a gap or file as next INV-NNN).
