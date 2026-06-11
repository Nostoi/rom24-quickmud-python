# Session Status — 2026-06-10 — FIGHT-051 murder safety NPC guards closed

## Current State

- **Active audit**: Cross-file invariants pass (all per-file P0/P1/P2 rows at 100%)
- **Last completed**: FIGHT-051 (`mud/commands/murder.py:_murder_safety_check` — ACT_PET and
  AFF_CHARM non-owner victim-NPC guards added)
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-06-10_FIGHT051_MURDER_SAFETY_NPC_GUARDS.md](SESSION_SUMMARY_2026-06-10_FIGHT051_MURDER_SAFETY_NPC_GUARDS.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.97 |
| Tests | 2903 passed, 3 skipped (prior full run) + 10 new tests this session (FIGHT-050: 6, FIGHT-051: 4) |
| ROM C files audited | All P0/P1/P2 at 100% |
| Active focus | Cross-file invariants (next free ID: INV-044) |

## Next Intended Task

**INV-044 candidate — `stop_fighting` both-sides invariant** — Probe whether `stop_fighting`
in `mud/combat/engine.py` always clears both sides of the combat pointer to match ROM
`src/fight.c:1221-1241`. A one-sided clear could leave a ghost fighting pointer causing
infinite combat loops. Method: read ROM C `stop_fighting` → read Python equivalent → write one
failing test → file as INV-044 if the contract crosses modules.

Also candidate: **FIGHT-052** — `_kill_safety_message` in `mud/commands/combat.py` checks the
charmed-mob guard before the safe-room check (ordering inverted vs ROM `is_safe` `:1083-1093`).
Quick read-and-compare to confirm severity before filing.
