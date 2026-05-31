# Session Status — 2026-05-31 — INV-025 consumption ACT triggers (2.12.13)

## Current State

- **Active mode**: cross-file invariants (per-file audit tracker exhausted).
- **Last completed (this session, 2.12.13)**:
  - **INV-025 consumption sweep — CLOSED**. ROM `do_eat` / `do_drink`
    room-visible lines are `act(..., TO_ROOM)` producers (`src/act_obj.c:1238-1241,
    1263, 1317, 1342`), so `src/comm.c:2384` dispatches `TRIG_ACT` to NPC
    recipients. `mud/commands/consumption.py` now calls `mp_act_trigger_room`
    after the existing `broadcast_room` for eat, drink, and poisoned choke room
    lines.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-31_INV025_CONSUMPTION_ACT_TRIGGER.md](SESSION_SUMMARY_2026-05-31_INV025_CONSUMPTION_ACT_TRIGGER.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.12.13 |
| Targeted tests | `test_inv025_consumption_act_trigger_dispatch.py`: 2 passed; `test_consumables.py`: 51 passed |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Cross-file invariants | 24 enforced |
| Open correctness gaps | None currently filed in `UPDATE_C_AUDIT`; INV-025 sweep remains an active follow-up class, not a new gap ID. |
| Active focus | cross-file invariants probe pass |

## Next Intended Task

Continue the broader **INV-025** sweep for non-combat room narrations where the
matching ROM site uses `act()` and Python currently only calls `broadcast_room`
or another delivery primitive.

Likely next targets:

1. `mud/commands/magic_items.py` (`quaff` / `recite` / `brandish` / `zap`
   room narrations).
2. `mud/commands/liquids.py` (`fill` / `pour` room narrations).
3. `mud/commands/thief_skills.py` and immortal command room narrations.

Method: probe-then-scope (read ROM C contract → read Python equivalent →
one failing ACT-trigger test → wire only genuine ROM `act()` producers).
