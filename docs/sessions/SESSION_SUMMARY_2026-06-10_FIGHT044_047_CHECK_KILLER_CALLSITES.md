# Session Summary — 2026-06-10 — FIGHT-044/045/046/047 check_killer call-site completeness

## Scope

Continuation from v2.13.87 (MATH-002/003/004 + FIGHT-043 flee XP). Active pass:
cross-file invariants. Session resolved all three suggested probes from the previous
handoff, then filed and closed four `check_killer` call-site gaps discovered by probe 3.

**Probe 1 — `stop_fighting` caller survey**: Grepped all `stop_fighting` call sites in
`mud/`. Seven sites confirmed: `do_flee` (both=True), `do_recall` (both=True),
`do_surrender` (both=True + redundant manual clear — harmless), `spell_calm` (both=False),
`word_of_recall` spell (both=True), `raw_kill` (both=True), `nuke_pets` (both=False). All
`both` parameters match ROM C (`src/fight.c`, `src/act_move.c`, `src/magic.c`). No gap;
no INV row warranted.

**Probe 2 — `do_flee`/`do_recall` position reset after move**: ROM `src/act_move.c:do_recall`
relocates the character then calls `stop_fighting(ch, TRUE)`. Python `stop_fighting` already
resets `position` to `Position.STANDING` for PCs internally. Python `do_recall`
(`mud/commands/session.py:394`) calls `stop_fighting(ch, True)` correctly. No explicit
post-move position assignment needed; probe is CLEAN.

**Probe 3 — `check_killer` call-site completeness**: ROM calls `check_killer` in 10 places
(`one_hit`, `do_bash`, `do_dirt`, `do_trip`, `do_kill`, `do_murder`, `do_backstab`,
`do_rescue`, `do_kick`, `do_disarm`). Python had correct calls for `do_kill`, `do_dirt`,
`do_disarm`, `do_murder`, `do_cast` (offensive spell path), and `do_rescue`
(FIGHT-030). Four sites were missing or wrong: `do_bash` (absent), `do_trip` (success-only),
`do_backstab` (absent), `do_kick` (absent). Filed as FIGHT-044 through FIGHT-047; all
closed this session.

**Behavioral significance analysis**: `apply_damage` sets `attacker.fighting = victim`
inside its fighting-state setup block (`engine.py:694`), which triggers `check_killer`'s
`attacker.fighting is resolved_victim` guard. This means for `do_bash`, `do_trip`, and
`do_kick` the KILLER flag is never set in practice — same as ROM C. The gaps were
structural (the call must exist to match ROM). `do_backstab` is the exception: it requires
`char.fighting is None` (hard guard at entry), so check_killer fires without hitting the
fighting guard. FIGHT-046 was a real behavioral gap where a clan PC backstabbing another
clan PC escaped the KILLER flag.

## Outcomes

### FIGHT-044 `do_bash` missing `check_killer` — ✅ FIXED (2.13.88)

- **Python**: `mud/commands/combat.py:do_bash` — no `check_killer` call
- **ROM C**: `src/fight.c:2486` — unconditional after both success and failure branches
- **Fix**: added `check_killer(char, victim)` after `skill_registry._check_improve` in `do_bash`
- **Note**: structural parity only — `apply_damage` sets `attacker.fighting` before
  `check_killer` runs, so the KILLER flag is never set in practice (same in ROM C)
- **Tests**: `tests/integration/test_fight044_bash_killer_flag.py` — **2/2 passing**
  (monkeypatch-based: verifies call happens on both success and failure paths)

### FIGHT-045 `do_trip` check_killer success-only — ✅ FIXED (2.13.89)

- **Python**: `mud/commands/combat.py:do_trip` — `check_killer` only inside success branch
- **ROM C**: `src/fight.c:2753` — unconditional after the entire if/else block
- **Fix**: refactored if/else to collect message in a variable; `check_killer(char, victim)`
  moved after both branches before `return message`
- **Tests**: `tests/integration/test_fight045_trip_killer_flag.py` — **2/2 passing**
  (failure test uses `skill_level=10` + `roll=99` to force the failure path)

### FIGHT-046 `do_backstab` missing `check_killer` — ✅ FIXED (2.13.90)

- **Python**: `mud/commands/combat.py:do_backstab` — no `check_killer` call
- **ROM C**: `src/fight.c:2951` — before `WAIT_STATE` and the skill roll, after guards
- **Fix**: added `check_killer(char, victim)` after the `wait > 0` guard and before the
  roll, matching ROM's pre-WAIT placement
- **Note**: REAL behavioral gap — `do_backstab` requires `char.fighting is None`, so
  `check_killer`'s fighting guard does NOT fire and the KILLER flag IS set
- **Tests**: `tests/integration/test_fight046_backstab_killer_flag.py` — **2/2 passing**
  (KILLER flag + "*** You are now a KILLER!! ***" message verified; weapon and handler
  stubbed via monkeypatch)

### FIGHT-047 `do_kick` missing `check_killer` — ✅ FIXED (2.13.91)

- **Python**: `mud/commands/combat.py:do_kick` — no `check_killer` call
- **ROM C**: `src/fight.c:3138` — unconditional after both success and failure branches
- **Fix**: added `check_killer(char, opponent)` after `skill_registry._check_improve` in `do_kick`
- **Note**: structural parity only — `do_kick` requires `char.fighting` to be non-None,
  so `check_killer`'s fighting guard fires and KILLER is never set in practice
- **Tests**: `tests/integration/test_fight047_kick_killer_flag.py` — **2/2 passing**
  (test sets `ch_class=3` + `level=50` to pass kick's level-requirement guard)

## Files Modified

- `mud/commands/combat.py` — FIGHT-044: `check_killer` after `do_bash`; FIGHT-045: refactored
  `do_trip` if/else + unconditional `check_killer`; FIGHT-046: `check_killer` before roll in
  `do_backstab`; FIGHT-047: `check_killer` after `do_kick`
- `tests/integration/test_fight044_bash_killer_flag.py` — new file, 2 enforcement tests
- `tests/integration/test_fight045_trip_killer_flag.py` — new file, 2 enforcement tests
- `tests/integration/test_fight046_backstab_killer_flag.py` — new file, 2 enforcement tests
- `tests/integration/test_fight047_kick_killer_flag.py` — new file, 2 enforcement tests
- `docs/parity/FIGHT_C_AUDIT.md` — rows FIGHT-044 through FIGHT-047 filed and flipped to ✅ FIXED
- `CHANGELOG.md` — `[2.13.88]` through `[2.13.91]` Fixed entries
- `pyproject.toml` — 2.13.87 → 2.13.91

## Test Status

- `pytest tests/integration/test_fight04{4,5,6,7}*.py -v` — **8/8 passing**
- Full integration suite: **2900 passed, 3 skipped** (64.9s)

## Next Steps

Cross-file invariants remains the active pass. Next free INV ID: **INV-044**. The
`check_killer` call-site surface is now fully covered.

Suggested next candidates:

1. **`check_killer` internal parity audit** — Python's `check_killer` has an
   `is_clan_member(attacker)` guard that ROM C does not have (`src/fight.c:1226-end` has no
   clan check). This was a deliberate design choice but should be verified as intentional
   and documented in the audit doc. If it was unintentional, it would be FIGHT-048.

2. **`do_murder` full audit** — `do_murder` skips `_kill_safety_message` (uses its own
   `_murder_safety_check`). ROM `do_murder` (`src/fight.c:2831-2895`) does not call
   `is_safe()` directly but has its own guard sequence. A quick read confirms the victim
   yell is a Python-invented return value (ROM delivers it via `act`); there may be a
   broadcast/delivery gap. Low-risk; quick probe.

3. **`stop_fighting` / `set_fighting` symmetry after `do_recall`** — the position probe
   is clean. The next edge: does `do_recall` send the "You recall to..." message AFTER
   `stop_fighting`, matching ROM's act() order? A quick read of `session.py:do_recall`
   vs `src/act_move.c:do_recall` would confirm.
