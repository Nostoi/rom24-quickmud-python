# Session Status — 2026-05-31 — INV-025 do_open ACT Trigger

## Current State

- **Active mode**: cross-file invariants (per-file audit tracker exhausted — no
  ⚠️ Partial / ❌ Not Audited rows).
- **Last completed**:
  - **INV-025 `do_open` ACT trigger follow-up (2.11.59)** — actor-room open
    portal/container/door messages in `do_open` now mirror ROM
    `src/act_move.c:384`, `:412`, and `:436` by preserving the room broadcast
    and dispatching `TRIG_ACT` to NPC recipients via `mp_act_trigger_room`.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-31_INV025_DO_OPEN_ACT_TRIGGER.md](SESSION_SUMMARY_2026-05-31_INV025_DO_OPEN_ACT_TRIGGER.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.11.59 |
| Tests | 5094 passed, 4 skipped |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Cross-file invariants | 31 enforced (INV-001..031) |
| Active focus | Cross-file invariants — continue probe/close cycle |

## Next Intended Task

Continue cross-file invariants as the primary pass. Candidate areas for probing:
- Remaining INV-025 act-dispatch sweep: non-combat `_push_message` /
  `broadcast_room` narration surfaces where the matching ROM site uses `act()`;
  likely next slices are `do_close`, `do_lock`, `do_unlock`, and `do_pick` in
  `mud/commands/doors.py`.
- Mob script trigger contracts beyond INV-025/INV-026.
- Position-transition edge cases during death/recovery.

Carried-open items: `Character.pet` type annotation hygiene;
`curse` handler type annotation hygiene.

## Commit / push state

- Working tree: pending commit/push for the 2.11.59 INV-025 `do_open`
  follow-up.
