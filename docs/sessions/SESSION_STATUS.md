# Session Status — 2026-05-24 — `skills.c` game-loop integration

## Current State

- **Active audit**: `magic.c + magic2.c` (integration follow-up — affect persistence tests still partial)
- **Last completed**: `skills.c` integration follow-up — game-loop combat cadence and wait-state runtime parity restored; tracker note closed locally in `2.8.71`
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-05-24_SKILLS_GAME_LOOP_INTEGRATION.md](SESSION_SUMMARY_2026-05-24_SKILLS_GAME_LOOP_INTEGRATION.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.8.71 |
| Tests | `pytest tests/integration/ -v` → `2108 passed, 3 skipped` |
| ROM C files audited | `skills.c` integration note closed; next partial integration row is `magic.c + magic2.c` |
| Active focus | `magic.c + magic2.c` (98%, affect-persistence integration still partial) |

## Next Intended Task

Pick up `magic.c + magic2.c` from `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` and close the remaining integration note by adding spell-affect persistence coverage through the real runtime path (`game_tick()`, duration decay, and wear-off behavior). Keep ROM `src/magic.c` / `src/update.c` as the source of truth and verify against the existing spell-affects persistence slice before changing behavior.
