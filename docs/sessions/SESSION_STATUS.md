# Session Status — 2026-04-27 — mob_cmds.c audit opened, MOBCMD-014 closed

## Current State

- **Active audit**: `mob_cmds.c` (Phase 4 — gap closure; 1 of 18 closed)
- **Last completed**: `MOBCMD-014` (`do_mpdamage` routes through `apply_damage`); also reconciled `act_obj.c` audit doc + tracker to 100%
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-04-27_ACT_OBJ_RECONCILE_AND_MOB_CMDS_AUDIT.md](SESSION_SUMMARY_2026-04-27_ACT_OBJ_RECONCILE_AND_MOB_CMDS_AUDIT.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.6.3 (unbumped — nothing pushed yet this session) |
| Tests | 3506 passed / 11 skipped / 2 pre-existing failures (full suite) |
| ROM C files audited | 14 / 43 |
| P1 audited | 6 / 11 (86%) |
| Active focus | `mob_cmds.c` (~70% — 17 open gaps remaining) |

## Recent Commits (this session)

- `f5c5d25` — `docs(parity): reconcile act_obj.c audit doc + tracker to 100%`
- `6ef31e4` — `docs(parity): add mob_cmds.c audit doc with 18 stable gap IDs`
- `3365720` — `fix(parity): mob_cmds.c:MOBCMD-014 — route do_mpdamage through apply_damage`

## Next Intended Task

Close `MOBCMD-005` next (`do_mpoload` ROM signature is `(vnum, level, R|W mode)`; Python is missing the level parameter, so script-loaded objects always get the mob's raw level instead of the script-specified level). Single function in `mud/mob_cmds.py:544-576`, single integration test, single `fix(parity)` commit. Audit doc: `docs/parity/MOB_CMDS_C_AUDIT.md`.

After MOBCMD-005, continue down the CRITICAL list: MOBCMD-010 → MOBCMD-008 → MOBCMD-015 → MOBCMD-011 → MOBCMD-003. When all 6 CRITICAL + 9 IMPORTANT close, bump `pyproject.toml` patch version (2.6.3 → 2.6.4), flip the `mob_cmds.c` tracker row to ✅, and write the closing session summary.

## Known Pre-existing Failures (not session-caused)

- `tests/test_game_loop.py::test_mobile_update_returns_home_when_out_of_zone` — wanderer settles in room 401 instead of 400; verified failing on `HEAD~1` (commit `3365720`).
- `tests/test_mobprog_triggers.py::test_event_hooks_fire_rom_triggers` — `'delay'` trigger not in fired-events list; verified failing on `HEAD~1`.

Both predate this session and should be triaged as separate parity bugs.
