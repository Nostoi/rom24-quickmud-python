# Session Status — 2026-06-10 — RECALL-002 + FIGHT-049 closed

## Current State

- **Active audit**: Cross-file invariants pass (all per-file P0/P1/P2 rows at 100%)
- **Last completed**: RECALL-002 (check_improve on recall fail/success) + FIGHT-049
  (_murder_safety_check PC-vs-PC clan/level guards)
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-06-10_RECALL002_FIGHT049_MURDER_SAFETY_PC_VS_PC.md](SESSION_SUMMARY_2026-06-10_RECALL002_FIGHT049_MURDER_SAFETY_PC_VS_PC.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.95 |
| Tests | 2903 passed, 3 skipped (prior full run; +8 new tests this session) |
| ROM C files audited | All P0/P1/P2 at 100% |
| Active focus | Cross-file invariants (next free ID: INV-044) |

## Next Intended Task

**FIGHT-050** — `mud/combat/safety.py:is_safe` missing three guards: ACT_PET check
("But $N looks so cute and cuddly..."), charm-ownership-for-non-owner ("You don't own
that monster."), NPC charmed-mob-PC-attack guard ("Players are your friends!"). Approach:
write three failing tests first, then add the sub-arms to the existing victim-NPC and NPC-
attacker branches in `is_safe`. Caution: `is_safe` has CRITICAL blast radius (46 transitive
impacts) — run full integration suite after. Alternatively, probe `do_kill`'s
`_kill_safety_message` for the same PC-vs-PC clan/level gap just closed in `_murder_safety_check`
(FIGHT-049) — quick grep check before starting FIGHT-050.
