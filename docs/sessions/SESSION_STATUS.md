# Session Status — 2026-05-30 — GL-025 char_update Ordering

## Current State

- **Active mode**: cross-file invariants (per-file audit tracker exhausted — no
  ⚠️ Partial / ❌ Not Audited rows).
- **Last completed**:
  - **GL-025 char_update operation ordering (2.11.57)** — `char_update` now
    mirrors ROM `src/update.c:721-862` by processing PC worn-light decay, idle
    timer handling, and condition decay before affect expiry and
    plague/poison/incap/mortal damage. This prevents lethal affect ticks from
    moving a one-tick worn light into the corpse before burnout.
  - Recorded as an `UPDATE_C_AUDIT.md` gap closure, not a new INV row, because
    the defect was local ordering inside `mud/game_loop.py:char_update`.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-30_GL025_CHAR_UPDATE_ORDER.md](SESSION_SUMMARY_2026-05-30_GL025_CHAR_UPDATE_ORDER.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.11.57 |
| Tests | 5092 passed, 4 skipped |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Cross-file invariants | 31 enforced (INV-001..031) |
| Active focus | Cross-file invariants — continue probe/close cycle |

## Next Intended Task

Continue cross-file invariants as the primary pass. Candidate areas for probing:
- Mob script trigger contracts beyond INV-025/INV-026
- Position-transition edge cases during death/recovery
- More INV-025 follow-up TRIG_ACT dispatch wiring (plague tick, other
  `_message_room` callers that correspond to ROM `act()` callsites)

Carried-open items: `Character.pet` type annotation hygiene;
`curse` handler type annotation hygiene; INV-025 plague tick message
TRIG_ACT/PERS masking follow-up.

## Commit / push state

- Working tree: clean after the 2.11.57 GL-025 commit/push.
