# Session Status — 2026-05-30 — INV-031 PC Death Preserves Group

## Current State

- **Active mode**: cross-file invariants (per-file audit tracker exhausted — no
  ⚠️ Partial / ❌ Not Audited rows).
- **Last completed**:
  - **INV-031 PC-DEATH-PRESERVES-GROUP (2.11.56)** — `raw_kill` now gates
    `die_follower(victim)` behind `is_npc`, matching ROM
    `extract_char(ch, IS_NPC(ch))` where `fPull=FALSE` for PCs preserves
    group/follower relationships. Also fixed `is_same_group` identity
    comparison (`==` → `is`). Four new enforcement tests.
  - Probed affect-tick / SINGLE-DELIVERY — covered by existing INVs.
  - Probed char_update operation ordering divergence (light/timer/conditions
    BEFORE vs AFTER affect ticks) — minor impact, carried open.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-30_INV031_PC_DEATH_PRESERVES_GROUP.md](SESSION_SUMMARY_2026-05-30_INV031_PC_DEATH_PRESERVES_GROUP.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.11.56 |
| Tests | 5091 passed, 4 skipped |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Cross-file invariants | 31 enforced (INV-001..031) |
| Active focus | Cross-file invariants — continue probe/close cycle |

## Next Intended Task

Continue cross-file invariants as the primary pass. Candidate areas for probing:
- char_update operation ordering (light decay / timer / conditions BEFORE
  affect ticks per ROM, vs Python's AFTER) — minor impact but real divergence
- Mob script trigger contracts beyond INV-025/INV-026
- Position-transition edge cases during death/recovery
- More INV-025 follow-up TRIG_ACT dispatch wiring (plague tick, other
  `_message_room` callers that correspond to ROM `act()` callsites)

Carried-open items: `Character.pet` type annotation hygiene;
`curse` handler type annotation hygiene; char_update ordering divergence.

## Commit / push state

- Working tree: clean (all changes included in the 2.11.56 commit).