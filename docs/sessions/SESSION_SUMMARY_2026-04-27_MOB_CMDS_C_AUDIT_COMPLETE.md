# Session Summary — 2026-04-27 — `mob_cmds.c` audit complete (all 18 gaps closed)

## Scope

Continued the `mob_cmds.c` parity audit opened earlier the same day
(MOBCMD-014 had already been closed in the prior session). This session
closed the remaining 17 gaps: 5 CRITICAL, 9 IMPORTANT, 3 MINOR. The
audit doc moved from Phase 4 (open gaps) to Phase 5 (closed). One
session-local follow-up (`pyproject.toml` 2.6.3 → 2.6.4 + tracker flip
to 100%) is included.

## Outcomes

### MOBCMD-005 — ✅ FIXED

- **Python**: `mud/mob_cmds.py:585` (`do_mpoload`)
- **ROM C**: `src/mob_cmds.c:538-614`
- **Fix**: parse optional `level` arg; default to `get_trust(ch)`; set
  `obj.level` post-spawn (mirrors ROM `create_object(pObjIndex, level)`).
- **Tests**: `tests/integration/test_mob_cmds_oload.py` — 3/3 pass.
- **Commit**: `b9063cb`.

### MOBCMD-010 — ✅ FIXED

- **Python**: `mud/mob_cmds.py:1288` (`do_mpflee`)
- **ROM C**: `src/mob_cmds.c:1283`
- **Fix**: route through `mud.world.movement.move_character` (canonical
  movement pipeline) instead of silent `_move_to_room`.
- **Tests**: `tests/integration/test_mob_cmds_flee.py::TestMpFleeUsesMoveChar`.
- **Commit**: `c4af60b`.

### MOBCMD-008 — ✅ FIXED

- **Python**: `mud/mob_cmds.py:1288` (`do_mpflee`)
- **ROM C**: `src/mob_cmds.c:1272-1286`
- **Fix**: 6 `rng_mm.number_door()` random-door attempts mirroring
  ROM's loop, instead of in-order exit iteration.
- **Tests**: `tests/integration/test_mob_cmds_flee.py::TestMpFleeRandomDoor`.
- **Commit**: `53911be`.

### MOBCMD-003 — ✅ FIXED

- **Python**: `mud/mob_cmds.py:985` (`do_mpkill`)
- **ROM C**: `src/mob_cmds.c:361`
- **Fix**: gate on `ch.position == Position.FIGHTING` (not
  `ch.fighting is not None`); add missing `victim is ch` self-attack
  guard.
- **Tests**: `tests/integration/test_mob_cmds_kill.py::TestMpKillPositionGate`.
- **Commit**: `bc2b8e4`.

### MOBCMD-011 + MOBCMD-012 — ✅ FIXED (closed together)

- **Python**: `mud/mob_cmds.py:462` (`do_mpcast`)
- **ROM C**: `src/mob_cmds.c:1043-1066`
- **Fix**: introduce `_TargetType` IntEnum mirroring ROM `TAR_*`;
  switch on the canonical enum. `TAR_OBJ_*` branches now require an
  obj (no character fallback) per ROM lines 1060-1065;
  `TAR_CHAR_DEFENSIVE` defaults to `ch` per line 1055.
- **Tests**: `tests/integration/test_mob_cmds_cast.py` — 2/2 pass.
- **Commit**: `8a52aa6`.

### MOBCMD-015 + MOBCMD-016 — ✅ FIXED (closed together)

- **Python**: `mud/mob_cmds.py:413` (`do_mpcall`)
- **ROM C**: `src/mob_cmds.c:1217-1252`
- **Fix**: parse obj1/obj2 tokens, resolve via `_find_obj_here`, and
  forward both to `mobprog.call_prog`. Defaults to `None` for missing
  or unresolved tokens, mirroring ROM lines 1239-1249.
- **Tests**: `tests/integration/test_mob_cmds_call.py` — 2/2 pass.
- **Commit**: `3bef29d`.

### MOBCMD-001 — ✅ FIXED

- **Python**: `mud/mob_cmds.py:985` (`do_mpkill`)
- **ROM C**: `src/mob_cmds.c:364-369`
- **Fix**: refuse to attack when `ch.has_affect(AffectFlag.CHARM)` and
  `ch.master is target`.
- **Tests**: `tests/integration/test_mob_cmds_kill.py::TestMpKillCharmedMasterGuard`.
- **Commit**: `457f83c`.

### MOBCMD-002 — ✅ FIXED (audit description corrected)

- **Python**: `mud/mob_cmds.py:1004` (`do_mpassist`)
- **ROM C**: `src/mob_cmds.c:393`
- **Fix**: enforce ROM's full guard set —
  `victim == ch || ch->fighting != NULL || victim->fighting == NULL`.
  Audit row originally claimed a "charm/master relationship" gap; ROM
  `do_mpassist` actually has no charm/master check — the real gap was
  the two missing self/in-fight guards. Audit description corrected.
- **Tests**: `tests/integration/test_mob_cmds_assist.py` — 2/2 pass.
- **Commit**: `e893021`.

### MOBCMD-004 — ✅ FIXED

- **Python**: `mud/mob_cmds.py:1136` (`do_mpjunk`)
- **ROM C**: `src/mob_cmds.c:436`
- **Fix**: `mob junk all.` (trailing dot, no suffix) now discards
  nothing — ROM's `is_name(&arg[4], ...)` returns FALSE on an empty
  needle. Bare `mob junk all` still clears inventory.
- **Tests**: `tests/integration/test_mob_cmds_junk.py` — 2/2 pass.
- **Commit**: `c54f495`.

### MOBCMD-006 — ✅ FIXED

- **Python**: `mud/mob_cmds.py:603` (`do_mpoload`)
- **ROM C**: `src/mob_cmds.c:575-580`
- **Fix**: refuse the explicit level when `level < 0 || level > get_trust(ch)`.
- **Tests**: `tests/integration/test_mob_cmds_oload.py` — added 2 cases.
- **Commit**: `d26615d`.

### MOBCMD-009 — ✅ FIXED

- **Python**: `mud/mob_cmds.py:1288` (`do_mpflee`)
- **ROM C**: `src/mob_cmds.c:1277-1280`
- **Fix**: NPC fleers now skip exits whose `to_room.room_flags &
  ROOM_NO_MOB`.
- **Tests**: `tests/integration/test_mob_cmds_flee.py::TestMpFleeNoMobRoomFlag`.
- **Commit**: `b8869e8`.

### MOBCMD-013 — ✅ FIXED

- **Python**: `mud/mob_cmds.py:1175` (`do_mpdamage`)
- **ROM C**: `src/mob_cmds.c:1101-1116`
- **Fix**: emit ROM-style `bug()` warnings via the standard `logging`
  module on non-numeric min/max. Added a module-local `_bug()` helper
  that prefixes `<message> from vnum N.` (the ROM convention); reused
  by MOBCMD-007.
- **Tests**: `tests/integration/test_mob_cmds_damage.py::TestMpDamageNonNumericArgsBugLog`.
- **Commit**: `7586417`.

### MOBCMD-007 — ✅ FIXED

- **Python**: `mud/mob_cmds.py:795` (`do_mppurge`)
- **ROM C**: `src/mob_cmds.c:631-665`
- **Fix**: dropped the Python-only literal `"all"` synonym so the token
  falls through to name resolution exactly like ROM. Added the missing
  `Mppurge - Bad argument` (line 663) and `Mppurge - Purging a PC`
  (line 671) bug logs. The previously divergent
  `test_mppurge_all_cleans_room` unit test was rewritten to use the
  ROM-faithful empty-arg form.
- **Tests**: `tests/integration/test_mob_cmds_purge.py` — 2/2 pass.
- **Commit**: `fd13117`.

### MOBCMD-017 + MOBCMD-018 — ✅ FIXED (closed together)

- **Python**: `mud/mob_cmds.py:914` (`do_mptransfer`); `1290` (`do_mpflee`).
- **ROM C**: `src/mob_cmds.c:791-806`, `1266-1267`.
- **Fix**: 017 — `do_mptransfer` for `"all"` now recursively dispatches
  `do_mptransfer(ch, "<pcname> <loc>")` once per PC via the module
  attribute, mirroring ROM exactly. 018 — verified `do_mpflee` already
  checks `ch.fighting` as the first guard; audit row was stale, no
  code change required.
- **Tests**: `tests/integration/test_mob_cmds_transfer.py::TestMpTransferAllRecursesThroughDispatch`.
- **Commit**: `17aa955`.

## Files Modified

- `mud/mob_cmds.py` — every gap above; added `_TargetType` IntEnum +
  `_TARGET_STRINGS` map (MOBCMD-011/012); added module-local `_bug()`
  helper used by MOBCMD-007 and MOBCMD-013; added recursive
  `do_mptransfer` dispatch (MOBCMD-017).
- `tests/integration/test_mob_cmds_assist.py` — new (MOBCMD-002).
- `tests/integration/test_mob_cmds_call.py` — new (MOBCMD-015/016).
- `tests/integration/test_mob_cmds_cast.py` — new (MOBCMD-011/012).
- `tests/integration/test_mob_cmds_damage.py` — extended with
  `TestMpDamageNonNumericArgsBugLog` (MOBCMD-013).
- `tests/integration/test_mob_cmds_flee.py` — extended with
  `TestMpFleeNoMobRoomFlag` (MOBCMD-009); pre-existing classes cover
  MOBCMD-008 + MOBCMD-010.
- `tests/integration/test_mob_cmds_junk.py` — new (MOBCMD-004).
- `tests/integration/test_mob_cmds_kill.py` — extended with
  `TestMpKillCharmedMasterGuard` (MOBCMD-001); pre-existing class
  covers MOBCMD-003.
- `tests/integration/test_mob_cmds_oload.py` — extended with the
  level-bounds cases (MOBCMD-006); pre-existing cases cover
  MOBCMD-005.
- `tests/integration/test_mob_cmds_purge.py` — new (MOBCMD-007).
- `tests/integration/test_mob_cmds_transfer.py` — new (MOBCMD-017).
- `tests/test_mobprog_commands.py` — `test_mppurge_all_cleans_room`
  rewritten to use the ROM-faithful empty-arg form.
- `docs/parity/MOB_CMDS_C_AUDIT.md` — all 18 rows ✅; Phase 5 marked
  complete.
- `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` — `mob_cmds.c` row
  flipped from ⚠️ Partial / 70% to ✅ Complete / 100%.
- `CHANGELOG.md` — `[Unreleased]` content moved into a new
  `[2.6.4] - 2026-04-27` section with one bullet per gap.
- `pyproject.toml` — `2.6.3` → `2.6.4`.

## Test Status

- `pytest tests/integration/test_mob_cmds_*.py` — green across all 10
  files (assist, call, cast, damage, flee, junk, kill, oload, purge,
  transfer).
- Full suite (`pytest`): **3534 passed / 11 skipped / 2 pre-existing
  failures**, 442.88s. The 2 pre-existing failures
  (`tests/test_game_loop.py::test_mobile_update_returns_home_when_out_of_zone`
  and `tests/test_mobprog_triggers.py::test_event_hooks_fire_rom_triggers`)
  predate this session and are documented in CLAUDE.md /
  prior `SESSION_STATUS.md`.
- `ruff check .` — clean for every commit.

## Next Steps

`mob_cmds.c` is closed. The next P1 candidate from
`docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` should be picked up next
session — start by reading the tracker for the highest-priority
remaining ⚠️ Partial / Not Audited file, then run
`/rom-parity-audit <file>.c` to produce the gap doc. The two
pre-existing failing tests
(`test_mobile_update_returns_home_when_out_of_zone`,
`test_event_hooks_fire_rom_triggers`) remain on the triage backlog.
