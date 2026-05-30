# Session Status — 2026-05-30 — Group Commands Lint Cleanup

## Current State

- **Active mode**: cross-file invariants (per-file audit tracker exhausted — no
  ⚠️ Partial / ❌ Not Audited rows).
- **Last completed**:
  - **Group-command lint cleanup ✅ DONE (2.11.51)** — removed two stale unused
    imports from `mud/commands/group_commands.py` (`Position` and the inner
    `character_registry` import in `do_group`). No behavior change.
  - **Before that**: `INV-025` position-command TRIG_ACT follow-up ✅ FIXED
    (2.11.50).
- **Earlier today**: `INV-001` shop haggle wrong-channel cousin (2.11.49),
  FIGHT-032 (2.11.44), FIGHT-033 (2.11.45), FIGHT-034 (2.11.46), VISION-002
  (2.11.47), ACT-CAP-001/002/003/004, FIGHT-031, INV-029.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-30_GROUP_COMMANDS_LINT_CLEANUP.md](SESSION_SUMMARY_2026-05-30_GROUP_COMMANDS_LINT_CLEANUP.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.11.51 |
| Tests | Focused group-command slice: 46 passed, 1 skipped |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Active focus | Cross-file invariants — continue probe/close cycle |

## Next Intended Task

Continue cross-file invariants as the primary pass. Pick the next candidate area
not yet covered by an INV row, or address a carried-open maintenance item with
appropriate impact analysis.

Carried-open items: known xdist flakes (`test_combat_death.py`,
`test_backstab_uses_position_and_weapon`); `Character.pet` stale type annotation
(GitNexus reports HIGH risk on the field, so handle deliberately); `do_cast`
object-targeting legs.

## Commit / push state

- Working tree has uncommitted 2.11.51 cleanup/session-bookkeeping changes.
