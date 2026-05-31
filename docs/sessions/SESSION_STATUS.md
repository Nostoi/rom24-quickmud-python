# Session Status — 2026-05-31 — INV-025 Plague Tick ACT Trigger

## Current State

- **Active mode**: cross-file invariants (per-file audit tracker exhausted — no
  ⚠️ Partial / ❌ Not Audited rows).
- **Last completed**:
  - **INV-025 plague tick ACT trigger follow-up (2.11.58)** — plague tick room
    messages in `char_update` now mirror ROM `src/update.c:803-804` and
    `:836-837` by flowing through an `act(TO_ROOM)`-style helper: actor excluded,
    `$n`/`$s` rendered per recipient via PERS, and NPC recipients dispatched to
    `mp_act_trigger` under the `MOBtrigger` guard.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-31_INV025_PLAGUE_TICK_ACT_TRIGGER.md](SESSION_SUMMARY_2026-05-31_INV025_PLAGUE_TICK_ACT_TRIGGER.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.11.58 |
| Tests | 5093 passed, 4 skipped |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Cross-file invariants | 31 enforced (INV-001..031) |
| Active focus | Cross-file invariants — continue probe/close cycle |

## Next Intended Task

Continue cross-file invariants as the primary pass. Candidate areas for probing:
- Remaining INV-025 act-dispatch sweep: non-combat `_push_message` /
  `broadcast_room` narration surfaces where the matching ROM site uses `act()`.
- Mob script trigger contracts beyond INV-025/INV-026.
- Position-transition edge cases during death/recovery.

Carried-open items: `Character.pet` type annotation hygiene;
`curse` handler type annotation hygiene.

## Commit / push state

- Working tree: pending commit/push for the 2.11.58 INV-025 plague tick follow-up.
