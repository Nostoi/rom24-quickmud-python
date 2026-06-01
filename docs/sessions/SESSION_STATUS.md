# Session Status — 2026-06-01 — INV-025 command/music/level-fail/Mota ACT trigger dispatch (2.12.24)

## Current State

- **Active mode**: cross-file invariants (per-file audit tracker exhausted).
- **Last completed (this session, 2.12.24)**:
  - **INV-025 command/music/level-fail/Mota sweep — COMPLETED**.
    - `mud/music/__init__.py:_broadcast_jukebox_message`: Added per-NPC `mp_act_trigger` dispatch after the per-occupant delivery loop, with `$p` formatted for each NPC recipient, matching ROM `src/music.c:128,154` `act(TO_ALL)`.
    - `mud/commands/communication.py:do_pose`: Added `mp_act_trigger_room` dispatch after `broadcast_room`, matching ROM `src/act_comm.c:1420` `act(TO_ROOM)`.
    - `mud/commands/equipment.py:_broadcast_level_fail`: Added `mp_act_trigger_room` dispatch after `broadcast_room`, matching ROM `src/act_obj.c:1410` `act(TO_ROOM)`.
    - `mud/commands/obj_manipulation.py:do_sacrifice` (Mota decline branch): Added `mp_act_trigger_room` dispatch after `broadcast_room`, matching ROM `src/act_obj.c:1782` `act(TO_ROOM)`.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-01_INV025_COMMAND_MUSIC_ACT_TRIGGER.md](SESSION_SUMMARY_2026-06-01_INV025_COMMAND_MUSIC_ACT_TRIGGER.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.12.24 |
| Targeted tests | `test_inv025_spell_effect_act_trigger.py`: 12 passed; `test_inv025_*.py`: 78 passed |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Cross-file invariants | 25 enforced |
| Open correctness gaps | None currently filed; INV-025 fully applied to all major broadcast surfaces |

## Next Intended Task

INV-025 is now fully applied to all `broadcast_room` and `act(TO_ROOM)`/`act(TO_ALL)` call sites in production code. The `broadcast_global` paths (channels: yell, shout, gossip, grats, auction, question, clan, immtalk) are ROM `descriptor_list` per-PC delivery that bypasses `mp_act_trigger` — no gaps remain.

Potential next areas for cross-file invariant work:
1. Review any remaining `act(TO_CHAR)`/`act(TO_VICT)` per-recipient paths that might need `mp_act_trigger` for NPC recipients.
2. Pick a new INV candidate from the candidate list (affect ticks, position transitions, mob script triggers, group/follower chain).
