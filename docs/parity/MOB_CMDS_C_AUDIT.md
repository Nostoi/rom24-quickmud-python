# mob_cmds.c ROM C Audit

**Status**: 🔄 **IN PROGRESS** — Phase 1 + Phase 3 complete, Phase 4 (gap closure) pending
**File**: `src/mob_cmds.c` (1,369 lines)
**Priority**: P1 (MOBprogram script command primitives)
**Started**: April 27, 2026
**Last Updated**: April 27, 2026 — initial audit

**Progress**:
- ✅ Phase 1: Function Inventory Complete (31/31 ROM `do_mp_*` functions cataloged)
- ✅ Phase 2: QuickMUD Mapping Complete (29/31 mapped; 2 admin/debug commands `do_mpstat`/`do_mpdump` already in `mud/commands/mobprog_tools.py`)
- ✅ Phase 3: Gap Identification Complete (18 gaps: 6 CRITICAL, 9 IMPORTANT, 3 MINOR)
- 🔄 Phase 4: Gap Fixes — pending (use `/rom-gap-closer MOBCMD-XXX` per gap)
- ⏸ Phase 5: Closure — pending

**QuickMUD Files**:
- `mud/mob_cmds.py` (1,227 lines) — main `do_mp_*` script command implementations
- `mud/commands/mobprog_tools.py` — admin/debug commands (`do_mpstat`, `do_mpdump`)
- `mud/mobprog.py` — script driver / interpreter (referenced by some `do_mp_*` calls)

**ROM C reference**: `src/mob_cmds.c` (3,018 lines original; 1,369 here as ported)

---

## Executive Summary

`mob_cmds.c` defines the 31 script primitives (`do_mp_*`) callable from MOBprograms.
These are not player commands — they are invoked by the MOBprog interpreter to
let mob scripts manipulate world state (load mobs/objects, transfer chars,
broadcast messages, cast spells, damage targets, etc.). Behavior fidelity here
matters because every MOBprog script in the area files relies on these
semantics.

**Current parity estimate**: ~70%. 10 of 31 functions are fully ROM-faithful;
21 have at least one stable-ID gap. Most-impactful fixes are in `do_mpdamage`,
`do_mpoload`, `do_mpflee`, `do_mpcall`, and `do_mpcast`.

---

## Phase 1+2: Function Inventory & Mapping

| ROM Function | ROM Lines | Python Symbol | Python File:Line | Status |
|---|---|---|---|---|
| `do_mpstat` | 167-228 | `do_mpstat` | `mud/commands/mobprog_tools.py:100` | ✅ AUDITED |
| `do_mpdump` | 235-247 | `do_mpdump` | `mud/commands/mobprog_tools.py:126` | ✅ AUDITED |
| `do_mpgecho` | 254-275 | `do_mpgecho` | `mud/mob_cmds.py:359` | ✅ AUDITED |
| `do_mpzecho` | 282-308 | `do_mpzecho` | `mud/mob_cmds.py:369` | ✅ AUDITED |
| `do_mpasound` | 315-341 | `do_mpasound` | `mud/mob_cmds.py:343` | ✅ AUDITED |
| `do_mpkill` | 348-373 | `do_mpkill` | `mud/mob_cmds.py:930` | ⚠️ DIVERGENT |
| `do_mpassist` | 380-398 | `do_mpassist` | `mud/mob_cmds.py:943` | ⚠️ DIVERGENT |
| `do_mpjunk` | 409-446 | `do_mpjunk` | `mud/mob_cmds.py:959` | ⚠️ DIVERGENT |
| `do_mpechoaround` | 454-468 | `do_mpechoaround` | `mud/mob_cmds.py:389` | ✅ AUDITED |
| `do_mpechoat` | 475-489 | `do_mpechoat` | `mud/mob_cmds.py:403` | ✅ AUDITED |
| `do_mpecho` | 496-501 | `do_mpecho` | `mud/mob_cmds.py:334` | ✅ AUDITED |
| `do_mpmload` | 508-531 | `do_mpmload` | `mud/mob_cmds.py:515` | ✅ AUDITED |
| `do_mpoload` | 538-614 | `do_mpoload` | `mud/mob_cmds.py:544` | ⚠️ DIVERGENT |
| `do_mppurge` | 623-677 | `do_mppurge` | `mud/mob_cmds.py:720` | ⚠️ DIVERGENT |
| `do_mpgoto` | 685-712 | `do_mpgoto` | `mud/mob_cmds.py:671` | ✅ AUDITED |
| `do_mpat` | 719-765 | `do_mpat` | `mud/mob_cmds.py:293` | 🔄 PARTIAL |
| `do_mptransfer` | 773-841 | `do_mptransfer` | `mud/mob_cmds.py:819` | ⚠️ DIVERGENT |
| `do_mpgtransfer` | 848-878 | `do_mpgtransfer` | `mud/mob_cmds.py:845` | ✅ AUDITED |
| `do_mpforce` | 886-929 | `do_mpforce` | `mud/mob_cmds.py:867` | ✅ AUDITED |
| `do_mpgforce` | 936-966 | `do_mpgforce` | `mud/mob_cmds.py:885` | ✅ AUDITED |
| `do_mpvforce` | 973-1005 | `do_mpvforce` | `mud/mob_cmds.py:904` | ✅ AUDITED |
| `do_mpcast` | 1017-1070 | `do_mpcast` | `mud/mob_cmds.py:462` | ⚠️ DIVERGENT |
| `do_mpdamage` | 1078-1147 | `do_mpdamage` | `mud/mob_cmds.py:1088` | ⚠️ DIVERGENT |
| `do_mpremember` | 1155-1164 | `do_mpremember` | `mud/mob_cmds.py:1120` | ✅ AUDITED |
| `do_mpforget` | 1171-1174 | `do_mpforget` | `mud/mob_cmds.py:1130` | ✅ AUDITED |
| `do_mpdelay` | 1183-1195 | `do_mpdelay` | `mud/mob_cmds.py:430` | ✅ AUDITED |
| `do_mpcancel` | 1202-1205 | `do_mpcancel` | `mud/mob_cmds.py:441` | ✅ AUDITED |
| `do_mpcall` | 1217-1252 | `do_mpcall` | `mud/mob_cmds.py:413` | ⚠️ DIVERGENT |
| `do_mpflee` | 1260-1287 | `do_mpflee` | `mud/mob_cmds.py:1159` | ⚠️ DIVERGENT |
| `do_mpotransfer` | 1295-1327 | `do_mpotransfer` | `mud/mob_cmds.py:644` | ✅ AUDITED |
| `do_mpremove` | 1335-1369 | `do_mpremove` | `mud/mob_cmds.py:1134` | ✅ AUDITED |

**Inventory totals**: 31 ROM functions — 21 ✅ AUDITED, 9 ⚠️ DIVERGENT, 1 🔄 PARTIAL, 0 ❌ MISSING.

---

## Phase 3: Gap List

Stable IDs are immutable. Severity legend: **CRITICAL** = wrong observable behavior;
**IMPORTANT** = wrong wording or missing broadcast / wrong validation surface;
**MINOR** = cosmetic / refactor.

| Gap ID | Severity | ROM File:Line | Python File:Line | Description | Status |
|---|---|---|---|---|---|
| MOBCMD-001 | IMPORTANT | `src/mob_cmds.c:348-373` | `mud/mob_cmds.py:930-941` | `do_mpkill` omits ROM's `IS_AFFECTED(AFF_CHARM) && ch->master == victim` defensive check. | ✅ FIXED (2026-04-27) — `do_mpkill` now refuses when `ch.has_affect(AffectFlag.CHARM)` and `ch.master is target`, mirroring ROM `src/mob_cmds.c:364-369`. Test: `tests/integration/test_mob_cmds_kill.py::TestMpKillCharmedMasterGuard`. |
| MOBCMD-002 | IMPORTANT | `src/mob_cmds.c:380-398` | `mud/mob_cmds.py:943-953` | `do_mpassist` does not validate charm/master relationship like ROM does. | ✅ FIXED (2026-04-27) — corrected scope: ROM `do_mpassist` does *not* check charm/master; the actual gap was the missing `victim == ch` and `ch->fighting != NULL` guards from `src/mob_cmds.c:393`. Both now enforced. Test: `tests/integration/test_mob_cmds_assist.py::TestMpAssistRomGates`. |
| MOBCMD-003 | CRITICAL | `src/mob_cmds.c:348-373` | `mud/mob_cmds.py:944` | `do_mpkill` checks `ch->position == POS_FIGHTING` in ROM; Python checks `ch->fighting` instead — different gating semantics. | ✅ FIXED (2026-04-27) — `do_mpkill` now blocks on `ch.position == Position.FIGHTING` and adds the missing `victim is ch` self-attack guard from ROM `src/mob_cmds.c:361`. Test: `tests/integration/test_mob_cmds_kill.py::TestMpKillPositionGate`. |
| MOBCMD-004 | IMPORTANT | `src/mob_cmds.c:409-446` | `mud/mob_cmds.py:959-1086` | `do_mpjunk` ROM parses `"all"` vs `"all.suffix"` (checks `arg[3]`); Python does not distinguish prefix patterns. | 🔄 OPEN |
| MOBCMD-005 | CRITICAL | `src/mob_cmds.c:538-614` | `mud/mob_cmds.py:544-576` | `do_mpoload` ROM takes `(vnum, level, R\|W mode)`; Python simplified to `(vnum, mode)` without level parameter — objects load at mob's raw level instead of script-specified level. | ✅ FIXED (2026-04-27) — `do_mpoload` now parses optional level arg; defaults to `get_trust(ch)` when omitted; sets `obj.level` post-spawn to mirror ROM `create_object(pObjIndex, level)`. Test: `tests/integration/test_mob_cmds_oload.py::TestMpOloadLevelArgument`. |
| MOBCMD-006 | IMPORTANT | `src/mob_cmds.c:559-581` | `mud/mob_cmds.py:544-576` | `do_mpoload` ROM validates level bounds (`0` to `get_trust`); Python omits validation. | 🔄 OPEN |
| MOBCMD-007 | MINOR | `src/mob_cmds.c:623-677` | `mud/mob_cmds.py:720-776` | `do_mppurge` Python accepts literal `"all"` as synonym; ROM treats empty arg as purge-all but has no literal `"all"` keyword. | 🔄 OPEN |
| MOBCMD-008 | CRITICAL | `src/mob_cmds.c:1272-1286` | `mud/mob_cmds.py:1190` | `do_mpflee` ROM loops 6 times calling `random_door()`; Python iterates list of exits once — different randomization distribution. | ✅ FIXED (2026-04-27) — `do_mpflee` now performs 6 `rng_mm.number_door()` attempts mirroring ROM's loop. Test: `tests/integration/test_mob_cmds_flee.py::TestMpFleeRandomDoor`. |
| MOBCMD-009 | IMPORTANT | `src/mob_cmds.c:1277-1280` | `mud/mob_cmds.py:1159-1178` | `do_mpflee` ROM checks `ROOM_NO_MOB` flag on `pexit->to_room`; Python omits check — mobs can flee into NO_MOB rooms. | 🔄 OPEN |
| MOBCMD-010 | CRITICAL | `src/mob_cmds.c:1283` | `mud/mob_cmds.py:1190` | `do_mpflee` ROM calls `move_char(ch, door, FALSE)` by direction number; Python calls `_move_to_room()` by room object — bypasses move_char side effects (movement points, AT_ROOM triggers, etc.). | ✅ FIXED (2026-04-27) — `do_mpflee` now enumerates exits and routes through `mud.world.movement.move_character` with the direction string, mirroring ROM `move_char(ch, door, FALSE)`. Test: `tests/integration/test_mob_cmds_flee.py::TestMpFleeUsesMoveChar`. |
| MOBCMD-011 | CRITICAL | `src/mob_cmds.c:1043-1066` | `mud/mob_cmds.py:462-513` | `do_mpcast` ROM uses switch on `skill_table[sn].target` enum; Python uses `getattr(spell, "target")` string — relies on string equality which can drift from canonical TAR_* values. | ✅ FIXED (2026-04-27) — `do_mpcast` now resolves the JSON target string into a canonical `_TargetType` IntEnum mirroring ROM `TAR_*` and dispatches on the enum; the `TAR_OBJ_*` branches now require an obj (no character fallback) per ROM `src/mob_cmds.c:1060-1065`. Test: `tests/integration/test_mob_cmds_cast.py::TestMpCastObjTargetResolvesObjOnly`. |
| MOBCMD-012 | IMPORTANT | `src/mob_cmds.c:1043-1066` | `mud/mob_cmds.py:475-501` | `do_mpcast` target types are ROM `TAR_IGNORE`/`TAR_CHAR_OFFENSIVE`/`TAR_CHAR_DEFENSIVE`/`TAR_CHAR_SELF`/`TAR_OBJ_*`; Python uses `"ignore"`/`"victim"`/`"friendly"`/`"self"`/`"object"`/`"character_or_object"` — wrong canonical naming. | ✅ FIXED (2026-04-27) — closed alongside MOBCMD-011. The `_TargetType` enum names match ROM verbatim; `TAR_CHAR_DEFENSIVE` defaults to `ch` when the lookup fails per ROM `src/mob_cmds.c:1055`. |
| MOBCMD-013 | IMPORTANT | `src/mob_cmds.c:1101-1116` | `mud/mob_cmds.py:1088-1118` | `do_mpdamage` ROM bugs (loud failure) on non-numeric min/max args; Python silently returns. | 🔄 OPEN |
| MOBCMD-014 | CRITICAL | `src/mob_cmds.c:1132-1145` | `mud/mob_cmds.py:1103-1107` | `do_mpdamage` ROM calls `damage(victim, victim, ...)`; Python directly decrements `victim.hit` — skips death messages, position updates, fight triggers, and corpse handling. | ✅ FIXED (2026-04-27) — `do_mpdamage` now routes through `apply_damage(victim, victim, amount, dam_type=None, dt=None, show=False)`, exercising `update_pos` + death pipeline. Test: `tests/integration/test_mob_cmds_damage.py::TestMpDamageCallsDamagePipeline`. |
| MOBCMD-015 | CRITICAL | `src/mob_cmds.c:1217-1250` | `mud/mob_cmds.py:413-428` | `do_mpcall` ROM accepts 4 args (`vnum, victim_char, obj1, obj2`); Python accepts 1-2 args (`vnum, victim_char`) — script `mob call` cannot pass object context. | ✅ FIXED (2026-04-27) — `do_mpcall` now parses obj1/obj2 tokens and forwards both to `mobprog.call_prog` (which already accepted `arg1`/`arg2`). Test: `tests/integration/test_mob_cmds_call.py::TestMpCallForwardsObjectArgs`. |
| MOBCMD-016 | IMPORTANT | `src/mob_cmds.c:1243-1249` | `mud/mob_cmds.py:413-428` | `do_mpcall` ROM calls `get_obj_here()` twice to load obj1 and obj2; Python does not load objects at all. | ✅ FIXED (2026-04-27) — closed alongside MOBCMD-015. obj1/obj2 are now resolved via `_find_obj_here` (the `get_obj_here` analog), defaulting to `None` for missing or unresolved tokens per ROM `src/mob_cmds.c:1239-1249`. |
| MOBCMD-017 | MINOR | `src/mob_cmds.c:791-805` | `mud/mob_cmds.py:825-837` | `do_mptransfer` ROM recursively calls itself for `"all"`; Python iterates with loop. Behavior equivalent; refactor for ROM faithfulness. | 🔄 OPEN |
| MOBCMD-018 | MINOR | `src/mob_cmds.c:1266-1267` | `mud/mob_cmds.py:1161-1163` | `do_mpflee` ROM checks `ch->fighting` at function start; Python checks same but in different control-flow position. Same observable behavior — flag for cleanup. | 🔄 OPEN |

**Severity totals**: 6 CRITICAL, 9 IMPORTANT, 3 MINOR.

---

## Phase 4: Closure plan

Recommended order (highest impact first):

1. **MOBCMD-014** — `do_mpdamage` must call `damage()` not raw HP decrement. Fixes death/triggers/position.
2. **MOBCMD-005** + **MOBCMD-006** — `do_mpoload` arg signature + level validation.
3. **MOBCMD-010** — `do_mpflee` use `move_char` not `_move_to_room`.
4. **MOBCMD-008** + **MOBCMD-009** — `do_mpflee` randomization + NO_MOB check.
5. **MOBCMD-015** + **MOBCMD-016** — `do_mpcall` 4-arg signature + obj loading.
6. **MOBCMD-011** + **MOBCMD-012** — `do_mpcast` TAR_* enum target dispatch.
7. **MOBCMD-003** — `do_mpkill` POS_FIGHTING gating.
8. **MOBCMD-001** + **MOBCMD-002** — charm/master defensive checks in `do_mpkill`/`do_mpassist`.
9. **MOBCMD-013** — `do_mpdamage` non-numeric arg bug-out semantics.
10. **MOBCMD-004** — `do_mpjunk` "all.suffix" parsing.
11. **MOBCMD-007** — `do_mppurge` literal "all" handling.
12. **MOBCMD-017** + **MOBCMD-018** — refactor for ROM faithfulness.

Each gap closes via `/rom-gap-closer MOBCMD-NNN` — one gap, one failing
integration test in `tests/integration/test_mobprog_*.py`, one
`feat(parity)`/`fix(parity)` commit.

---

## Phase 5: Closure (pending)

When all CRITICAL + IMPORTANT gaps are FIXED:

1. Flip the tracker row `mob_cmds.c` from ⚠️ Partial / 70% → ✅ AUDITED / ≥95%.
2. Update CHANGELOG `[Unreleased]` with `Fixed` lines per gap.
3. Run `/rom-session-handoff` to write `docs/sessions/SESSION_SUMMARY_<date>_MOB_CMDS_C_AUDIT.md`.

MINOR-only gaps may be deferred — note in this doc which were skipped.

---

**Document Status**: 🔄 Active
**Maintained By**: QuickMUD ROM Parity Team
**Related Documents**:
- `ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`
- `ACT_OBJ_C_AUDIT.md` (recently completed reference)
- `ACT_ENTER_C_AUDIT.md` (audit-doc format reference)
