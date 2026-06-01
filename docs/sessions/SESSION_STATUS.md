# Session Status — 2026-06-01 — INV-025 movement/quit/scan ACT trigger dispatch (2.12.22)

## Current State

- **Active mode**: cross-file invariants (per-file audit tracker exhausted).
- **Last completed (this session, 2.12.22)**:
  - **INV-025 movement/quit/scan sweep — COMPLETED**.
    - `mud/world/movement.py:move_character` departure and arrival broadcasts
      now dispatch `mp_act_trigger_room` on NPC recipients, matching ROM
      `src/act_move.c:197,202` (no `MOBtrigger` wrap). Sneaking characters
      correctly suppress both broadcast and TRIG_ACT, matching ROM's
      `!IS_AFFECTED(ch, AFF_SNEAK)` guard.
    - `mud/world/movement.py:move_character_through_portal` portal entry
      departure and arrival broadcasts dispatch TRIG_ACT, matching ROM
      `src/act_enter.c:134,151`. Portal fade-out same-room and cross-room
      broadcasts dispatch with the correct actor.
    - `mud/commands/session.py:do_quit` quit broadcast dispatches TRIG_ACT,
      matching ROM `src/act_comm.c:1482`.
    - `mud/commands/inspection.py:do_scan` all-around and directional scan
      peer broadcasts dispatch TRIG_ACT, matching ROM `src/scan.c:60,90`.
  - ROM sources verified: `src/act_move.c:197,202`, `src/act_enter.c:134,151,204,209-210`,
    `src/act_comm.c:1482`, `src/scan.c:60,90` — all `act(TO_ROOM)` with no
    `MOBtrigger` wrap.
  - Enforcement tests: `tests/integration/test_inv025_movement_act_trigger_dispatch.py`
    (8 passed: departure, arrival, sneaking suppression, portal departure,
    portal arrival, quit, scan-all, scan-direction).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-01_INV025_MOVEMENT_ACT_TRIGGER.md](SESSION_SUMMARY_2026-06-01_INV025_MOVEMENT_ACT_TRIGGER.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.12.22 |
| Targeted tests | `test_inv025_movement_act_trigger_dispatch.py`: 8 passed |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Cross-file invariants | 24 enforced |
| Open correctness gaps | None currently filed; INV-025 sweep continues. |
| Active focus | INV-025 cross-file-invariant sweep (remaining non-combat ROM `act()` narrations) |

## Next Intended Task

Continue the broader **INV-025** sweep for remaining non-combat narrations whose
matching ROM sites use `act()` and Python currently still calls `broadcast_room`
without `mp_act_trigger`. Remaining high-value surfaces:

1. **Spell-effect room broadcasts** in `mud/skills/handlers.py` (~30+ broadcast_room
   calls without mp_act_trigger). These are the largest remaining surface: bless,
   cancellation wear-off messages, chain_lightning, faerie_fire/fog, gate, invis,
   mass_invis, holy_word, etc.
2. **Healer utterance** in `mud/commands/healer.py:234` — ROM `src/healer.c:183`
   uses `act("$n utters the words '$T'.", mob, NULL, words, TO_ROOM)` (no MOBtrigger wrap).
3. **Spec_fun broadcasts** in `mud/spec_funs.py` — the `_broadcast_room` and
   `_broadcast_room_message` helpers do not dispatch TRIG_ACT.
4. **Remaining movement-adjacent calls**: recall (`do_recall` departure/arrival),
    gate spell, etc.
