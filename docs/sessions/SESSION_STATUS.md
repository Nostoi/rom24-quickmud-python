# Session Status — 2026-06-10 — FIGHT-044/047 check_killer call-site completeness

## Current State

- **Active audit**: Cross-file invariants pass (all per-file audits complete at 100% P0/P1/P2)
- **Last completed**: FIGHT-044/045/046/047 (check_killer call-site completeness, 2.13.88–2.13.91)
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-06-10_FIGHT044_047_CHECK_KILLER_CALLSITES.md](SESSION_SUMMARY_2026-06-10_FIGHT044_047_CHECK_KILLER_CALLSITES.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.91 |
| Tests | 2900 passed, 3 skipped |
| ROM C files audited | 43 / 43 (all P0/P1/P2 at 100%; P3 at 75% + 3 N/A) |
| Cross-file INVs enforced | 28 (next free: INV-044) |
| Active focus | Cross-file invariants — check_killer surface closed; next: do_murder audit or check_killer internal parity |

## Next Intended Task

Cross-file invariants remains the active pass. Three probes resolved this session
(stop_fighting caller survey clean, do_flee/do_recall position reset clean, check_killer
call-site completeness → FIGHT-044/045/046/047 closed).

Suggested next probes:

1. **`check_killer` internal parity audit** — Python's `check_killer` has an
   `is_clan_member(attacker)` guard that ROM C `src/fight.c:1226-end` does not have.
   This was either a deliberate design choice or an unintentional addition. Verify against
   ROM C and document in FIGHT_C_AUDIT.md. If unintentional, file as FIGHT-048.

2. **`do_murder` delivery gap** — Python `do_murder` returns the victim yell as a return
   value string. ROM `src/fight.c:2875` delivers it via `act(TO_ROOM)`. Quick read of
   `mud/commands/murder.py` vs `src/fight.c:2831-2895` to check if there's an
   INV-001/INV-025 class gap in how the yell is broadcast.

3. **`do_recall` message ordering vs ROM** — `session.py:do_recall` calls `stop_fighting`
   then moves the character. Confirm message delivery order (flee/recall announcement,
   landing-room look) matches `src/act_move.c:do_recall`. Quick 5-minute probe.
