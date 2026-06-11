# Session Status — 2026-06-10 — FIGHT-048/RECALL-001 do_murder yell + gain_exp floor

## Current State

- **Active audit**: Cross-file invariants pass (all per-file audits complete at 100% P0/P1/P2)
- **Last completed**: FIGHT-048 (do_murder victim yell, 2.13.92), RECALL-001 (do_recall gain_exp floor, 2.13.93)
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-06-10_FIGHT048_RECALL001_MURDER_YELL_GAIN_EXP.md](SESSION_SUMMARY_2026-06-10_FIGHT048_RECALL001_MURDER_YELL_GAIN_EXP.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.93 |
| Tests | 2903 passed, 3 skipped |
| ROM C files audited | 43 / 43 (all P0/P1/P2 at 100%; P3 at 75% + 3 N/A) |
| Active focus | Cross-file invariants — do_murder + do_recall surface explored; next: FIGHT-049 or RECALL-002 |

## Next Intended Task

Cross-file invariants remains the active pass. Next free INV ID: **INV-044**.
Three probes resolved this session (check_killer internal parity CLEAN,
do_murder victim yell gap FIGHT-048 closed, do_recall message ordering CLEAN
with incidental RECALL-001 closed).

Suggested next candidates:

1. **FIGHT-049 — `_murder_safety_check` level-difference gap** — `do_murder`
   missing `ch->level > victim->level + 8` ("Pick on someone your own size.")
   and other `is_safe` PC-vs-PC guards. Python `is_safe` (`mud/combat/safety.py`)
   also lacks these checks — may require extending `is_safe` before routing
   `do_murder` through it. Quick read of Python `is_safe` + ROM C lines 1095-1122.

2. **RECALL-002 — `check_improve` for recall skill** — Minor: ROM calls
   `check_improve(ch, gsn_recall, FALSE/TRUE, 4/6)` on failure and success.
   Python has stale `# TODO` comments. Locate `check_improve` in Python and
   add the two calls in `mud/commands/session.py:do_recall`.

3. **Next cross-file invariants probe** — Candidates from AGENTS.md: affect ticks,
   position transitions, group/follower chain. INV-044 slot available.
