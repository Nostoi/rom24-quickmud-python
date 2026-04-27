# Session Status — 2026-04-27 — `mob_cmds.c` audit complete (all 18 gaps closed)

## Current State

- **Active audit**: `mob_cmds.c` — ✅ COMPLETE (Phase 5 closed; all 18 gaps FIXED)
- **Last completed**: MOBCMD-017 + MOBCMD-018 (recursive `do_mptransfer` dispatch + verified `do_mpflee` fighting-check position); also MOBCMD-001/002/004/006/007/009/011/012/013/015/016 closed earlier in the same session
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-04-27_MOB_CMDS_C_AUDIT_COMPLETE.md](SESSION_SUMMARY_2026-04-27_MOB_CMDS_C_AUDIT_COMPLETE.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.6.4 |
| Tests | 3534 passed / 11 skipped / 2 pre-existing failures (full suite) |
| ROM C files audited | 15 / 43 |
| P1 audited | 7 / 11 (94%) |
| Active focus | next P1 file from `ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` |

## Recent Commits (this session)

- `b9063cb` — `fix(parity): mob_cmds.c:MOBCMD-005 — do_mpoload accepts level arg`
- `c4af60b` — `fix(parity): mob_cmds.c:MOBCMD-010 — do_mpflee uses move_character`
- `53911be` — `fix(parity): mob_cmds.c:MOBCMD-008 — do_mpflee uses 6 random_door() attempts`
- `bc2b8e4` — `fix(parity): mob_cmds.c:MOBCMD-003 — do_mpkill POS_FIGHTING + self gates`
- `8a52aa6` — `fix(parity): mob_cmds.c:MOBCMD-011 + MOBCMD-012 — do_mpcast canonical TAR_* enum dispatch`
- `3bef29d` — `fix(parity): mob_cmds.c:MOBCMD-015 + MOBCMD-016 — do_mpcall forwards obj1/obj2`
- `457f83c` — `fix(parity): mob_cmds.c:MOBCMD-001 — do_mpkill refuses to attack charmer`
- `e893021` — `fix(parity): mob_cmds.c:MOBCMD-002 — do_mpassist gates on victim==ch and ch.fighting`
- `c54f495` — `fix(parity): mob_cmds.c:MOBCMD-004 — do_mpjunk 'all.' matches nothing`
- `d26615d` — `fix(parity): mob_cmds.c:MOBCMD-006 — do_mpoload validates level bounds`
- `b8869e8` — `fix(parity): mob_cmds.c:MOBCMD-009 — do_mpflee skips ROOM_NO_MOB destinations`
- `7586417` — `fix(parity): mob_cmds.c:MOBCMD-013 — do_mpdamage emits bug log on bad min/max`
- `fd13117` — `fix(parity): mob_cmds.c:MOBCMD-007 — do_mppurge drops literal 'all' synonym`
- `17aa955` — `fix(parity): mob_cmds.c:MOBCMD-017 + MOBCMD-018 — final mob_cmds.c gaps`
- (pending) — version bump 2.6.3 → 2.6.4 + tracker flip + session handoff

## Next Intended Task

Pick the next P1 ROM C file from
`docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` that is still ⚠️ Partial
or 🔴 Not Audited and run `/rom-parity-audit <file>.c` to produce the
audit doc + gap IDs, then close gaps with `/rom-gap-closer`. The
audit tracker P1 section is the source of priority order — do not
deviate based on memory of "what feels next".

Background backlog (do not block on these):

- `tests/test_game_loop.py::test_mobile_update_returns_home_when_out_of_zone` — wanderer settles in room 401 instead of 400; pre-existing.
- `tests/test_mobprog_triggers.py::test_event_hooks_fire_rom_triggers` — `'delay'` trigger not in fired-events list; pre-existing.

Both predate this session and should be triaged as separate parity
bugs once a P1 audit lull permits.
