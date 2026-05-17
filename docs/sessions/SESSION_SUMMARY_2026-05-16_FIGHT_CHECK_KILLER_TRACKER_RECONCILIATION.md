# Session Summary — 2026-05-16 — fight.c check_killer tracker reconciliation

## Goal

Pick the next bounded ROM-source-first verification slice after the full-suite recertification.

## Slice chosen

- `fight.c` PK flagging / `check_killer()`
- Reason: the top-level tracker still carried a stale historical note claiming `check_killer()` was missing from the remaining 5% of `fight.c`.

## ROM source reviewed

- `src/fight.c:1226-1287` — `check_killer()`
- `src/fight.c:2758-2821` — `do_kill()`
- `src/fight.c:1018-1125` — `is_safe()` player-target gate

## What I found

This was **not** a production parity gap.

The live combat path already uses `mud/combat/engine.py:check_killer`, and it matches the ROM behavior on the currently risky cases:

- innocent player target sets `PLR_KILLER`
- already-flagged `PLR_KILLER` / `PLR_THIEF` target does not flag the attacker
- charmed attacker stops following instead of becoming `PLR_KILLER`

The stale note in `ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` was historical debt.

## Tests added

Added narrow proving coverage in `tests/test_combat.py`:

- `test_kill_does_not_flag_attacker_when_target_already_killer`
- `test_kill_with_charmed_attacker_stops_following_without_killer_flag`

## Verification

Focused proof:

- `./venv/bin/python -m pytest -q tests/test_combat.py -k 'target_already_killer or charmed_attacker_stops_following_without_killer_flag or flags_player_as_killer'`
- result: `3 passed, 29 deselected`

Broader PK slice:

- `./venv/bin/python -m pytest -q tests/test_combat.py tests/test_player_flags.py tests/test_combat_death.py tests/test_spec_fun_behaviors.py -k 'killer or thief or pardon or outlaw or criminal or kill'`
- result: `28 passed, 61 deselected in 9.21s`

## Docs updated

- `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`
  - removed the stale `check_killer()` missing-function note from the `fight.c` section
  - recorded the May 16 verification refresh

## Outcome

No production code change was required for this slice. The tracker is now more accurate, and the `fight.c` PK-flagging path has tighter regression coverage.
