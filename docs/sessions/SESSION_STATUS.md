# Session Status — 2026-06-10 — FIGHT-050 is_safe NPC guards closed

## Current State

- **Active audit**: Cross-file invariants pass (all per-file P0/P1/P2 rows at 100%)
- **Last completed**: FIGHT-050 (`mud/combat/safety.py:is_safe` — ACT_PET, AFF_CHARM
  non-owner, charmed-mob-PC-attack guards added)
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-06-10_FIGHT050_IS_SAFE_NPC_GUARDS.md](SESSION_SUMMARY_2026-06-10_FIGHT050_IS_SAFE_NPC_GUARDS.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.96 |
| Tests | 2903 passed, 3 skipped (prior full run) + 6 new FIGHT-050 tests |
| ROM C files audited | All P0/P1/P2 at 100% |
| Active focus | Cross-file invariants (next free ID: INV-044) |

## Next Intended Task

**FIGHT-051 candidate** — `_murder_safety_check` in `mud/commands/murder.py` likely missing
ACT_PET and AFF_CHARM non-owner guards. ROM `do_murder` calls `is_safe(ch, victim)` (line
2861) before any murder-specific logic, so those guards ARE reached in ROM for the murder path.
Python bypasses `is_safe` entirely and goes directly to `_murder_safety_check`, which has
the charm-master guard for the attacker (`char.affected_by & CHARM and master is victim`) but
NOT the symmetric victim-side guards. Probe: read `mud/commands/murder.py:_murder_safety_check`
and verify. If confirmed, file as FIGHT-051 and close with the gap-closer workflow (one failing
test → fix → one commit).

**INV-044 candidate (stop_fighting invariant)** — Probe whether `stop_fighting` in
`mud/combat/engine.py` always clears both sides of the combat pointer to match ROM
`src/fight.c:1221-1241`. A one-sided clear leaves a ghost fighting pointer causing infinite
combat loops. Method: read ROM C contract → read Python → write one failing test → file INV-044.
