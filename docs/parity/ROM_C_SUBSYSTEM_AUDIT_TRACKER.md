# ROM C Subsystem Audit Tracker

**Purpose**: Track audit status of all 43 ROM 2.4b6 C source files for QuickMUD parity  
**Created**: December 30, 2025  
**Status**: Active tracking document

---

## Overview

This document tracks the **audit status** of all ROM 2.4b6 C source files (`src/*.c`) to ensure QuickMUD has equivalent implementations and integration tests.

**Critical Principle**: Every ROM C function should have either:
1. A QuickMUD Python equivalent (verified)
2. A documented reason why it's not needed
3. A tracking ticket for implementation

### Audit Status Legend

- ✅ **Audited** - QuickMUD parity verified, integration tests exist
- ⚠️ **Partial** - Some functions ported, gaps exist
- ❌ **Not Audited** - No systematic audit performed
- 🔄 **In Progress** - Currently being audited
- N/A **Not Needed** - ROM feature not applicable to QuickMUD

---

## Audit Priority Levels

- **P0** - Critical gameplay (combat, movement, commands)
- **P1** - Core features (skills, spells, world, mobs)
- **P2** - Important features (OLC, admin, special procs)
- **P3** - Infrastructure (memory, networking, db)

---

## ROM C Source Files (43 files)

### Current Audit Status

**Overall**: ✅ **100% audit-bound coverage** (40 audited, 0 partial, 0 not audited, 3 N/A).
**Audit-bound files**: every ROM C file that applies to QuickMUD now has a completed audit document and a reconciled tracker row.
**N/A files**: `recycle.c`, `mem.c`, `imc.c` remain intentionally out of scope for parity because Python GC / the alternate IMC implementation replace the ROM surfaces.
**Last Updated**: May 17, 2026

| File | Priority | Status | QuickMUD Module | Coverage | Notes |
|------|----------|--------|-----------------|----------|-------|
| **Combat & Violence** | | | | | |
| `fight.c` | P0 | ✅ Audited (per-file) | `mud/combat/` | 95% | See `docs/parity/FIGHT_C_AUDIT.md`. Violence tick fixed Dec 2025. `FIGHT-001` (`do_kill → multi_hit`), `FIGHT-002` (`is_safe()` inside `damage()`), and `FIGHT-003` (player death XP penalty before `raw_kill`) are closed as of 2026-05-15. **Cross-file invariants (`CROSS_FILE_INVARIANTS_TRACKER.md`):** INV-001 (single-delivery, ✅), INV-005 (same-room combat, ✅), INV-006 (fighting-pointer coherence after death, ✅). |
| `skills.c` | P0 | ✅ Audited | `mud/skills/` | 100% | All 37 skills have ROM parity tests |
| `magic.c` | P0 | ✅ Audited | `mud/spells/` | 98% | 97 spells tested |
| `magic2.c` | P0 | ✅ Audited | `mud/spells/` | 98% | Continuation of magic.c |
| **Core Game Loop** | | | | | |
| `update.c` | P0 | ✅ Audited | `mud/game_loop.py`, `mud/advancement.py` | 100% | May 27, 2026 — `ARITH-203/204` closed: plague-tick mana/move drain floors removed (raw subtraction per `update.c:843-845`). `GL-024` closed: plague tick's `if (af->level == 1) continue;` skip (`update.c:818-819`) now mirrored — level-1 plague is dormant (drain + `damage()` moved under the `af_level > 1` guard). May 17 — `GL-010`/`GL-017` closed (affect-tick same-type wear-off handling); `GL-021` (point-pulse `wiznet("TICK!")` ordering); `GL-022` (level-up banner/log order); `GL-023` (combat→XP verification). |
| `handler.c` | P1 | ✅ **COMPLETE!** | `mud/handler.py`, `mud/world/`, `mud/models/` | **100%** | 🎉🎉🎉 **FULL PARITY ACHIEVED - ALL 74 FUNCTIONS IMPLEMENTED!** 🎉🎉🎉 Jan 4 - See HANDLER_C_AUDIT.md |
| `effects.c` | P1 | ✅ **COMPLETE!** | `mud/magic/effects.py` | **100%** | 🎉🎉🎉 **FULL PARITY ACHIEVED - ALL 5 FUNCTIONS IMPLEMENTED!** 🎉🎉🎉 Jan 5 - 23 integration tests - See EFFECTS_C_AUDIT.md |
| **Movement & Rooms** | | | | | |
| `act_move.c` | P0 | ✅ **AUDITED** | `mud/movement/`, `mud/commands/doors.py`, `mud/commands/session.py`, `mud/commands/advancement.py` | **85%** | ✅ **Phase 4 Complete!** Jan 8 - Door/portal/recall/train 100% parity. Position/furniture commands revalidated May 13, 2026: `tests/integration/test_position_commands.py`, `test_furniture_occupancy.py`, and `test_room_safety_features.py` all green (`54 passed`). See `ACT_MOVE_C_AUDIT.md`. |
| `act_enter.c` | P1 | ✅ **COMPLETE!** | `mud/commands/movement.py`, `mud/world/movement.py` | **100%** | 🎉 **FULL PARITY — all 15 gaps closed (ENTER-001..016), 25 integration tests** 🎉 Apr 27 — See ACT_ENTER_C_AUDIT.md |
| `scan.c` | P2 | ✅ AUDITED | `mud/commands/inspection.py` | **100%** | Apr 28, 2026 — all 3 gaps closed (SCAN-001 TO_ROOM "looks all around", SCAN-002 directional "peer intently" TO_CHAR/TO_ROOM pair + spurious header removed, SCAN-003 non-ROM fallback lines removed). 3 integration + 13 unit tests green. See SCAN_C_AUDIT.md |
| **Commands** | | | | | |
| `act_comm.c` | P0 | ✅ **Audited** | `mud/commands/communication.py`, `mud/commands/group_commands.py`, `mud/commands/channels.py` | **100% P0-P1** | ✅ **100% P0-P1 COMPLETE!** Jan 8 - All critical gaps fixed (yell, order, gtell) - 34/36 functions verified - See ACT_COMM_C_AUDIT.md |
| `act_info.c` | P1 | ✅ **COMPLETE!** | `mud/commands/info.py`, `mud/commands/character.py`, `mud/commands/auto_settings.py`, `mud/commands/misc_info.py` | **100%** | **🎉🎉🎉 FULL PARITY - ALL 38 FUNCTIONS IMPLEMENTED!** 🎉🎉🎉 Jan 8 - 273/273 integration tests - See ACT_INFO_C_AUDIT.md |
| `act_obj.c` | P1 | ✅ **COMPLETE!** | `mud/commands/inventory.py`, `mud/commands/obj_manipulation.py`, `mud/commands/equipment.py`, `mud/commands/shop.py`, `mud/commands/give.py`, `mud/commands/consumption.py`, `mud/commands/liquids.py`, `mud/commands/magic_items.py`, `mud/commands/thief_skills.py` | **100%** | 🎉 **FULL PARITY** — Apr 27, 2026 refresh sweep verified all 12 audited functions (get/put/drop/give/remove/sacrifice/quaff/drink/eat/fill/pour/recite/brandish/zap/wear/wield/hold/steal) at 100%; 193 integration tests green. See ACT_OBJ_C_AUDIT.md. |
| `act_wiz.c` | P1 | ✅ Audited | `mud/wiznet.py`, `mud/commands/imm_*.py`, `mud/commands/admin_commands.py`, `mud/commands/inventory.py`, `mud/commands/remaining_rom.py` | 100% | Apr 28, 2026 — ninth pass closed WIZ-033..038 (set/mset/oset/rset/sset/string). act_wiz.c fully audited. See ACT_WIZ_C_AUDIT.md |
| `interp.c` | P0 | ✅ **COMPLETE!** | `mud/commands/dispatcher.py` | **100%** | 🎉 **FULL PARITY** — Apr 28, 2026: 24/24 gaps fixed + 1 closed-deferred. All command-mapping (INTERP-009..014), prefix-order (INTERP-017), `do_commands` formatting (INTERP-024), `one_argument` port (INTERP-015), and `tail_chain` extension hook (INTERP-016 closed-deferred) verified. See INTERP_C_AUDIT.md. |
| **Database & World** | | | | | |
| `db.c` | P1 | ✅ **COMPLETE!** | `mud/loaders/`, `mud/spawning/`, `mud/utils/math_utils.py`, `mud/utils/rng_mm.py`, `mud/utils/text.py`, `mud/registry.py` | **100%** | 🎉🎉🎉 **FULL PARITY ACHIEVED - ALL 44 FUNCTIONS IMPLEMENTED!** 🎉🎉🎉 Jan 5 - See DB_C_AUDIT.md |
| `db2.c` | P1 | ✅ AUDITED | `mud/loaders/` | **100%** (CRITICAL/IMPORTANT) | Apr 28 — DB2-001/002/003/006 closed; DB2-004/005 MINOR deferred (not user-reachable). See DB2_C_AUDIT.md |
| `save.c` | P1 | ✅ Complete (historical per-file audit) | `mud/account/account_manager.py`, `mud/db/serializers.py`, `mud/world/time_persistence.py` | **100%** (canonical DB path) | Jan 5 audit originally targeted the deleted JSON-pfile path; the canonical SQLAlchemy/DB load-save path is now covered by INV-003 and INV-008, both ✅ enforced. `mud/persistence.py` was removed in 2.8.3. See `CROSS_FILE_INVARIANTS_TRACKER.md`. |
| **Mob Programs** | | | | | |
| `mob_prog.c` | P1 | ✅ Complete | `mud/mobprog.py` | 100% | Apr 27, 2026 — all 7 audit gaps closed (MOBPROG-001..007: 2 CRITICAL, 4 IMPORTANT, 1 MINOR). Integration coverage in `tests/integration/test_mobprog_predicates.py`, `test_mobprog_greet_trigger.py`, `test_mobprog_program_flow.py`. See `MOB_PROG_C_AUDIT.md`. |
| `mob_cmds.c` | P1 | ✅ Complete | `mud/mob_cmds.py`, `mud/commands/mobprog_tools.py` | 100% | Apr 27, 2026 — all 18 gaps closed (6 CRITICAL, 9 IMPORTANT, 3 MINOR). Integration coverage in `tests/integration/test_mob_cmds_*.py`. See `MOB_CMDS_C_AUDIT.md`. |
| **OLC (Online Creation)** | | | | | |
| `olc.c` | P2 | ✅ AUDITED | `mud/commands/build.py`, `mud/commands/dispatcher.py`, `mud/commands/imm_olc.py`, `mud/olc/editor_state.py`, `mud/utils/prompt.py` | **100%** | 2026-05-01 — all gaps closed. OLC-INFRA-001, OLC-001..023 all ✅ FIXED (including OLC-006 `aedit_age`, OLC-012/013/014 fallback verification). See `OLC_C_AUDIT.md`. |
| `olc_act.c` | P2 | ✅ AUDITED | `mud/commands/build.py`, `mud/olc/` | **100%** (CRITICAL/IMPORTANT) | 2026-05-01 — all 14 gaps closed (OLC_ACT-001..014): 6 CRITICAL (`*_create` builders, `redit reset`, `redit <vnum>`), 6 IMPORTANT (`*_show` completeness, message strings, `aedit reset`), 2 MINOR. TIER C (~78 functions) deep-audit deferred. See `OLC_ACT_C_AUDIT.md`. |
| `olc_save.c` | P2 | ✅ AUDITED | `mud/olc/save.py`, `mud/commands/build.py:cmd_asave` | **100%** (CRITICAL/IMPORTANT) | 2026-05-01 — all 17 CRITICAL/IMPORTANT/MINOR gaps closed (OLC_SAVE-001..017). OLC_SAVE-018..020 DEFERRED-by-design (JSON-authoritative framing; .are format normalization side-effects N/A). See `OLC_SAVE_C_AUDIT.md`. |
| `olc_mpcode.c` | P2 | ✅ AUDITED | `mud/commands/imm_olc.py:do_mpedit,_interpret_mpedit,_mpedit_*` + `mud/models/mob.py:MprogCode,mprog_code_registry` | **100%** | 2026-05-02 — all 6 gaps closed. `MprogCode` model + registry; `do_mpedit` correct vnum lookup + session open; `_interpret_mpedit` session loop; `mpedit_show` ROM exact format; `mpedit_code` string_append hook; `mpedit_list` area/all filter. 23 integration tests. See `OLC_MPCODE_C_AUDIT.md`. |
| `hedit.c` | P2 | ✅ AUDITED | `mud/commands/build.py:cmd_hedit,_interpret_hedit,_hedit_*` | **100%** | 2026-05-02 — all 14 gaps closed (11 CRITICAL, 3 IMPORTANT). `hedit_show` ROM exact format, `hedit_level` -1..MAX_LEVEL range, `hedit_keyword`/`hedit_text` ROM messages, `hedit_delete`, `hedit_list` ported; `do_hedit` `is_name` word-match, `done` silent, unknown-cmd fallback to command table. 24 integration tests. See `HEDIT_C_AUDIT.md`. |
| **Special Procedures** | | | | | |
| `special.c` | P2 | ✅ Audited | `mud/spec_funs.py` | 100% | Apr 28, 2026 — all 8 CRITICAL/IMPORTANT gaps closed (SPEC-001..SPEC-008: area-wide yell, guard NPC targeting, mayor gate messages, c_div integer math, do_murder, is_safe, mayor move_character, c_div gold). See SPECIAL_C_AUDIT.md |
| **Communication & Social** | | | | | |
| `comm.c` | P3 | ✅ Audited (per-file) | `mud/net/`, `mud/utils/prompt.py`, `mud/account/account_service.py`, `mud/utils/act.py`, `mud/utils/fix_sex.py`, `mud/net/ansi.py` | 100% | May 15, 2026 — non-networking surface fully audited (`COMM_C_AUDIT.md`); COMM-005 fixed. `_run_character_login` now mirrors ROM `check_parse_name`'s duplicate-newbie `descriptor_list` sweep by closing matching non-playing descriptors and wiznetting `"Double newbie alert (%s)"`. Networking layer remains deferred-by-design. **Cross-file invariants (`CROSS_FILE_INVARIANTS_TRACKER.md`):** INV-001 SINGLE-DELIVERY ✅ (root cause was in `mud/combat/engine.py`, fixed 2026-05-02 `59bebf0`); INV-002 PROMPT-CLAMP ✅ (fixed 2026-05-02 `f586d11`). Both broke the `write_to_buffer` / `bust_a_prompt` contracts that single-file audit treated as in-scope but missed. |
| `nanny.c` | P3 | ✅ Audited | `mud/net/connection.py`, `mud/account/account_service.py`, `mud/account/account_manager.py`, `mud/handler.py`, `mud/models/titles.py`, `mud/commands/imm_admin.py` | 100% | May 15, 2026 — `NANNY_C_AUDIT.md` is fully closed. NANNY-010 fixed: `_select_character()` now mirrors ROM `CON_BREAK_CONNECT` by sweeping the full lightweight `descriptor_list`, closing every extra matching descriptor and honoring the switched-immortal `original->name` branch. The canonical active session is still handed to `_disconnect_session(...)` so the takeover notice is preserved. Tests: `tests/test_account_auth.py::test_break_connect_closes_all_matching_descriptors`, `tests/test_telnet_server.py::test_telnet_break_connect_prompts_and_reconnects`. |
| `board.c` | P2 | ✅ Audited | `mud/notes.py`, `mud/models/board.py`, `mud/commands/notes.py` | **100%** | 2026-05-19 — board.c now fully closed: BOARD-001..005/008/010..014 closed, BOARD-006/007 subsumed, BOARD-009 no-gap. BOARD-014 note-editor AFK parity now mirrors ROM `src/board.c` via draft-owned AFK tracking and `note forget`. See `docs/parity/BOARD_C_AUDIT.md`. |
| `music.c` | P2 | ✅ Audited | `mud/music/__init__.py`, `mud/commands/player_info.py`, `mud/world/world_state.py`, `mud/utils/act.py` | 100% | May 19, 2026 — `MUSIC-005` and `MUSIC-006` closed. Global music now mirrors ROM `descriptor_list` delivery (`CON_PLAYING` + switched `original` comm flags), and jukebox output now resolves `$p` per viewer with `can_see_object` fallback to `"something"`. Tests: `tests/integration/test_music_play.py`, `tests/integration/test_music_load_songs.py`, `tests/test_music.py`. |
| **Utilities & Helpers** | | | | | |
| `const.c` | P3 | ✅ Audited | `mud/models/constants.py`, `mud/models/races.py`, `mud/models/classes.py`, `mud/skills/groups.py`, `mud/wiznet.py`, `mud/world/movement.py`, `mud/commands/equipment.py`, `mud/math/stat_apps.py`, `mud/advancement.py`, `mud/combat/engine.py`, `mud/commands/session.py`, `mud/commands/imm_search.py`, `mud/models/titles.py`, `mud/account/account_service.py`, `mud/models/weapon_table.py`, `mud/models/character.py`, `mud/handler.py` | 100% | May 14, 2026 — `CONST_C_AUDIT.md` fully closed. `CONST-007` fixed: canonical ROM `weapon_table` ported to `mud/models/weapon_table.py`, duplicated local subsets removed from combat, account creation, and character-load skill seeding. Tests: `tests/test_weapon_table_parity.py`. |
| `tables.c` | P3 | ✅ AUDITED | `mud/models/constants.py` | 100% | Apr 29, 2026 — TABLES-001 closed: `AffectFlag` renumbered to ROM `merc.h:953-982` bits + on-load pfile migration (`pfile_version` schema field, legacy bits translated via `translate_legacy_affect_bits`). TABLES-001/002/003 all closed. `tests/integration/test_tables_parity.py` (`test_affect_flag_letters_match_rom_merc_h`, `test_merc_h_letter_macros_match_python_intflag_values` now includes `AFF_*`) + `test_tables_001_affect_migration.py` green. See `docs/parity/TABLES_C_AUDIT.md`. |
| `lookup.c` | P3 | ✅ AUDITED | `mud/utils/prefix_lookup.py`, `mud/models/races.py`, `mud/models/clans.py`, `mud/commands/remaining_rom.py` | 100% | Apr 28, 2026 — all 8 gaps closed (LOOKUP-001..008). New `mud/utils/prefix_lookup.py` provides ROM-faithful prefix-match helpers + `position_lookup`, `sex_lookup`, `size_lookup`, `item_lookup`, `liq_lookup`. `race_lookup`, `_lookup_flag_bit`, `lookup_clan_id` migrated to prefix-match. help_lookup/had_lookup UNVERIFIED (help-system audit). See LOOKUP_C_AUDIT.md |
| `flags.c` | P3 | ✅ AUDITED | `mud/commands/remaining_rom.py:do_flag` | 100% | May 15, 2026 — FLAG-002 closed: `do_flag` now preserves ROM `settable=FALSE` rows across the `=` operator using explicit per-field masks derived from `src/tables.c` (`act`, `plr`, `comm`). `tests/integration/test_flag_command_parity.py` expanded to 14 green cases. See FLAGS_C_AUDIT.md |
| `bit.c` | P3 | ✅ AUDITED | `mud/utils/prefix_lookup.py`, `mud/utils/bit.py`, `mud/commands/remaining_rom.py` | 100% | Apr 29, 2026 — `flag_lookup` adjacent helper (lookup.c) ported as `prefix_lookup_intflag` (TABLES-002); `do_flag` inline accumulator faithfully mirrors ROM `do_flag` (not ROM `flag_value`). All 3 BIT gaps closed: BIT-001 `flag_value`, BIT-002 `flag_string`, BIT-003 `is_stat` — `mud/utils/bit.py` hosts the standalone helpers needed by the OLC cluster. See BIT_C_AUDIT.md |
| `string.c` | P3 | ✅ AUDITED 100% | `mud/utils/string_editor.py` (all 12 helpers), `mud/utils/text.py` (`smash_tilde`) | 100% | Apr 29, 2026 — all 12 gaps closed (STRING-001..012). Final gap STRING-004 (`string_add` OLC input dispatcher) closed with 24 integration tests. See `STRING_C_AUDIT.md`. |
| `recycle.c` | P3 | N/A | - | N/A | Python GC handles this |
| `mem.c` | P3 | N/A | - | N/A | Python memory management |
| **Admin & Security** | | | | | |
| `ban.c` | P2 | ✅ AUDITED | `mud/security/bans.py`, `mud/commands/admin_commands.py` | 100% | Apr 28, 2026 — all 4 gaps closed (`BAN-001`..`004`): listing level alignment, empty type-text fallback, ROM `str_prefix` abbreviation in `_apply_ban`, and `BanEntry.matches` no longer exact-match-falls-through. See `BAN_C_AUDIT.md`. |
| `alias.c` | P2 | ✅ AUDITED | `mud/commands/alias_cmds.py`, `mud/commands/dispatcher.py`, `mud/commands/typo_guards.py`, `mud/rom_api.py` | 100% | Apr 28, 2026 — all 5 gaps closed (`ALIAS-001`..`005`): `alia` guard, ROM alias messages/validation/limit, single-pass substitution, ROM `unalias`, and prefix-length warning parity. See `ALIAS_C_AUDIT.md`. |
| **Healing & Services** | | | | | |
| `healer.c` | P2 | ✅ AUDITED | `mud/commands/healer.py` | 100% | Apr 28, 2026 — all 4 gaps closed (`HEALER-001`..`004`): `ACT_IS_HEALER` detection, exact service list/aliases, silver-aware pricing + utterance + payout, and real spell dispatch. See `HEALER_C_AUDIT.md`. |
| **External Systems** | | | | | |
| `imc.c` | P3 | N/A | `mud/imc/` | N/A | Different IMC implementation |
| `sha256.c` | P3 | ✅ AUDITED | `mud/security/hash_utils.py` | 100% | Uses Python hashlib + PBKDF2 (security upgrade, see SHA256_C_AUDIT.md) |

---

## Priority 0: Critical Gameplay Files (REQUIRED)

### ✅ P0-1: fight.c (AUDITED - 95%)

**Status**: ✅ **Audited December 2025**

**ROM Functions**: 32 functions
**QuickMUD Module**: `mud/combat/`

**Audit Results**:
- ✅ `violence_update()` → `violence_tick()` (FIXED Dec 2025)
- ✅ `multi_hit()` → `multi_hit()` (100% parity)
- ✅ `one_hit()` → `one_hit()` (100% parity)
- ✅ `damage()` → `damage()` (100% parity with ROM formula)
- ✅ All combat mechanics verified with ROM parity tests

**Missing Functions**: None

**Integration Tests**: ✅ Complete (`tests/integration/test_player_npc_interaction.py`)

**May 16, 2026 verification refresh**:
- Re-checked the historical `check_killer()` note against ROM `src/fight.c:1226-1287` and the live Python path in `mud/combat/engine.py`.
- Added/ran proving tests for:
  - innocent player target sets `PLR_KILLER`
  - already-flagged `PLR_KILLER` target does **not** flag the attacker
  - charmed attacker stops following instead of becoming `PLR_KILLER`
- Verification:
  - `tests/test_combat.py -k 'target_already_killer or charmed_attacker_stops_following_without_killer_flag or flags_player_as_killer'`
  - broader slice: `tests/test_combat.py tests/test_player_flags.py tests/test_combat_death.py tests/test_spec_fun_behaviors.py -k 'killer or thief or pardon or outlaw or criminal or kill'`
- Result: the old tracker note was stale; `check_killer()` is implemented on the active combat path.

**Next Steps**: None - 95% coverage acceptable

---

### ✅ P0-2: skills.c (AUDITED - 100%)

**Status**: ✅ **Audited December 2025**

**ROM Functions**: 37 skills
**QuickMUD Module**: `mud/skills/`

**Audit Results**:
- ✅ All 37 ROM skills implemented
- ✅ 89 ROM parity tests created
- ✅ Skill formulas match ROM C exactly
- ✅ Backstab, bash, disarm, etc. verified

**Missing Functions**: None

**Integration Tests**: ✅ Complete (`tests/integration/test_skills_integration.py`, `tests/integration/test_skills_integration_combat_specials.py`)

**Notes**:
- `tests/integration/test_skills_integration.py` now covers skill command → `game_tick()` combat progression and ROM wait-state recovery on `PULSE_VIOLENCE` cadence.
- `tests/integration/test_skills_integration_combat_specials.py` covers the remaining combat-skill command surfaces (`disarm`, `trip`, `kick`, `dirt`, `berserk`).

---

### ✅ P0-3: magic.c + magic2.c (AUDITED - 100%)

**Status**: ✅ **Audited December 2025 — closed May 2026**

**ROM Functions**: 97 spells
**QuickMUD Module**: `mud/skills/handlers.py`

**Audit Results**:
- ✅ All 97 ROM spells implemented
- ✅ 378 spell parity tests created
- ✅ Spell formulas match ROM C exactly
- ✅ Spell affects verified
- ✅ `spell_pass_door()` parity confirmed (`mud/skills/handlers.py:5884`, mirrors `src/magic.c:3864`)

**Missing Functions**: None

**Integration Tests**: ✅ Complete (`tests/integration/test_spell_affects_persistence.py` — includes `TestSpellPassDoorIntegration`)

**Next Steps**: None — subsystem closed.

---

### ✅ P0-4: update.c (AUDITED - 100%)

**Status**: ✅ **Re-audited May 2026 — GL gaps closed**

**ROM Functions**: 9 update functions
**QuickMUD Module**: `mud/game_loop.py`

**Audit Results**:
- ✅ `update_handler()` → `game_tick()` (100% parity — GL-order fixed)
- ✅ `violence_update()` → `violence_tick()` (FIXED — GL-combat-fast)
- ✅ `mobile_update()` → `mobile_update()` (FIXED — GL-healer-spam)
- ✅ `weather_update()` → `weather_tick()` (100% parity)
- ✅ `char_update()` → `char_update()` (GL-004/005/009/011/012/013/014/015 FIXED May 2026)
- ✅ `obj_update()` → `obj_update()` (GL-018 FIXED May 2026)
- ✅ `aggr_update()` → `aggressive_update()` (100% parity)
- ✅ `area_update()` → `reset_tick()` (100% parity)
- ✅ `song_update()` → `song_update()` (100% parity)

**Closed Gaps (May 2026)**:
- GL-004: `mana_gain` now uses `room.mana_rate` (was `heal_rate`)
- GL-005: `mana_gain` furniture uses `value[4]` (was `value[3]`)
- GL-009: NPC out-of-zone wanders-home → `extract_char` (was missing entirely)
- GL-011: Plague tick: spread + mana/move drain + damage (was missing)
- GL-012: Poison tick: shiver message + damage (was missing)
- GL-013: INCAP tick 50% chance 1 HP damage (was missing)
- GL-014: MORTAL tick 1 HP damage (was missing)
- GL-015: `_idle_to_limbo` uses `stop_fighting(ch, both=True)` (was `fighting=None`)
- GL-010: `tick_spell_effects` now preserves active merged spell effects while following ROM same-type wear-off handling
- GL-017: `_tick_object_affects` now suppresses duplicate same-type zero-duration wear-off messages
- GL-018: Pit (vnum 3010) decay message suppression (was missing)

**Integration Tests**: ✅ Complete (`tests/test_game_loop.py`, `tests/integration/test_update_c_parity.py`)

**Next Steps**:
- [x] Add TICK! wiznet message

---

### ✅ P0-5: act_move.c (AUDITED - 85%)

**Status**: ✅ **Phase 4 Complete** (January 8, 2026)

**ROM Functions**: Movement, doors, portals, position, recall, training
**QuickMUD Modules**: `mud/movement/`, `mud/commands/doors.py`, `mud/commands/session.py`, `mud/commands/advancement.py`

**Detailed Audit Document**: `docs/parity/ACT_MOVE_C_AUDIT.md`

**Audit Results**:
- ✅ `move_char()` → `move_character()` (98% parity)
- ✅ **Door Commands** (100% parity - ALL FIXED!) ⭐
  - ✅ `do_open()` (100%)
  - ✅ `do_close()` (100%) - Portal support added
  - ✅ `do_lock()` (100%) - Portal support added
  - ✅ `do_unlock()` (100%) - Portal support added
  - ✅ `do_pick()` (100%) - Guard/wait/improve/immortal bypass added
  - ✅ `_has_key()` (100%)
  - ✅ `_find_door()` (100%)
- ✅ **Utility Commands** (100% parity - ALL FIXED!) ⭐
  - ✅ `do_recall()` (100%) - Combat recall, pet recursion, all ROM C features
  - ✅ `do_train()` (100%) - Stat training, prime stat costs, perm_stat array fix
- ✅ **Thief Skills** (95% parity)
  - ✅ `do_sneak()`, `do_hide()`, `do_visible()`
- ⚠️ **Position Commands** (39% parity - Deferred to P2)
  - ⚠️ `do_stand()`, `do_rest()`, `do_sit()`, `do_sleep()`, `do_wake()` - Missing furniture support

**Phase 4 Implementation Highlights**:
- ✅ Portal support: All door commands now support ITEM_PORTAL objects
- ✅ Portal flags: EX_NOCLOSE, EX_NOLOCK, EX_PICKPROOF implemented
- ✅ Portal key vnum: Correctly uses `obj.value[4]` (not value[2])
- ✅ do_pick() enhancements: WAIT_STATE, guard detection, skill checks, immortal bypass
- ✅ do_recall() complete: Combat recall, pet recursion, exp loss, room checks
- ✅ do_train() complete: Stat training with perm_stat array, prime stat costs, HP/mana training

**Test Results**:
- ✅ 24/24 door command unit tests passing (100%)
- ✅ 39/39 recall unit tests passing (100%)
- ✅ 11/11 train unit tests passing (100%)
- ⏳ 7/12 train integration tests passing
- ⏳ 14 door/portal integration tests created (needs refinement)

**Integration Tests**: ⏳ In Progress
- ✅ Created: `tests/integration/test_door_portal_commands.py` (290 lines, 14 tests)
- ✅ Created: `tests/integration/test_recall_train_commands.py` (287 lines, 12 tests)

**Deferred to P2** (Furniture system):
- [ ] `do_stand()` - Furniture support (6-8 hours)
- [ ] `do_rest()` - Furniture support
- [ ] `do_sit()` - Furniture support
- [ ] `do_sleep()` - Furniture support
- [ ] `do_wake()` - Target wake support

**Next Steps**:
- [ ] Refine integration tests for door/portal workflows
- [ ] P2: Implement furniture support in position commands (~400 lines ROM C)

---

### ✅ P0-6: act_comm.c (AUDITED - 90%)

**Status**: ✅ **Audited December 2025**

**ROM Functions**: Communication commands
**QuickMUD Module**: `mud/commands/communication.py`

**Audit Results**:
- ✅ `do_tell()` (FIXED Dec 2025 - get_char_world)
- ✅ `do_say()` (100% parity)
- ✅ `do_shout()` (100% parity)
- ✅ `do_yell()` (90% parity - missing area check)
- ✅ `do_emote()` (100% parity)

**Missing Functions**:
- [ ] `do_afk()` - AFK status (5%)
- [ ] `do_replay()` - Tell history (5%)

**Integration Tests**: ⚠️ Partial (`tests/integration/test_player_npc_interaction.py`)

**Next Steps**:
- [ ] Add AFK and replay commands (P2)
- [ ] Add integration tests for shout/yell range

---

### ✅ P0-7: interp.c (COMPLETE - 100%)

**Status**: ✅ **FULL PARITY** (Apr 28, 2026 — 24/24 gaps fixed + 1 closed-deferred)

**ROM Functions**: Command interpreter
**QuickMUD Module**: `mud/commands/dispatcher.py`

**Audit Results**:
- ✅ Command table (`COMMANDS` list in QuickMUD)
- ✅ Command dispatch (`process_command()`)
- ✅ All 255 ROM commands registered
- ✅ Alias expansion (basic)

**Missing Functions**:
- [ ] `check_social()` integration in main dispatch
- [ ] Command abbreviation edge cases
- [ ] Trust level enforcement (partial)
- [ ] Position enforcement (partial)

**Integration Tests**: ✅ Complete (43/43 passing)

**Next Steps**:
- [ ] Audit `interpret()` function line-by-line
- [ ] Verify all ROM command checks present

---

## Priority 1: Core Features (IMPORTANT)

### ✅ P1-1: handler.c (AUDITED - 73%)

**Status**: ✅ **Audited January 2-3, 2026** - extract_char complete with full ROM C parity

**ROM Functions**: Object/character manipulation (79 functions total)
**QuickMUD Modules**: `mud/world/`, `mud/game_loop.py`, `mud/commands/`, `mud/affects/`, `mud/handler.py`, `mud/mob_cmds.py`

**Detailed Audit Document**: `docs/parity/HANDLER_C_AUDIT.md`

**Audit Status** (35/79 fully implemented, 5 partial):

**✅ Fully Implemented (35 functions)**:
- ✅ `get_char_world()` (100% - `mud/world/char_find.py`)
- ✅ `get_char_room()` (100% - `mud/world/char_find.py`)
- ✅ `is_name()` (100% - `mud/world/char_find.py`)
- ✅ `get_obj_carry()` (100% - `mud/world/obj_find.py`)
- ✅ `get_obj_world()` (100% - `mud/world/obj_find.py`)
- ✅ `obj_to_char()` (100% - `mud/game_loop.py:_obj_to_char`)
- ✅ `obj_from_char()` (100% - `mud/game_loop.py:_remove_from_character`)
- ✅ `obj_to_obj()` (100% - `mud/game_loop.py:_obj_to_obj`) ✅ **FIXED Jan 2** - carrier weight update
- ✅ `obj_from_obj()` (100% - `mud/game_loop.py:_obj_from_obj`) ✅ **FIXED Jan 2** - carrier weight decrement
- ✅ `obj_to_room()` (100% - `mud/game_loop.py:_obj_to_room`)
- ✅ `get_obj_weight()` (100% - `mud/game_loop.py:_get_obj_weight_recursive`) ✅ **FIXED Jan 2** - WEIGHT_MULT applied
- ✅ `get_true_weight()` (100% - same as `_get_obj_weight_recursive`) ✅ **FIXED Jan 2**
- ✅ `apply_ac()` (100% - `mud/handler.py:apply_ac`) ✅ **FIXED Jan 2** - 3x body multiplier, 13/13 tests passing
- ✅ `get_eq_char()` (100% - `ch.equipment[slot]` dict) ✅ **AUDITED Jan 2** - Equivalent implementation
- ✅ `equip_char()` (100% - `mud/handler.py` + `equipment.py:_can_wear_alignment`) ✅ **AUDITED Jan 2**
- ✅ `unequip_char()` (100% - `mud/handler.py:unequip_char`) ✅ **FIXED Jan 2** - APPLY_SPELL_AFFECT removal
- ✅ `count_obj_list()` (100% - `mud/spawning/reset_handler.py:_count_existing_objects`) ✅ **AUDITED Jan 2**
- ✅ `extract_obj()` (95% - `mud/game_loop.py:_extract_obj`) ✅ **AUDITED Jan 2** - Missing prototype count only
- ✅ `extract_char()` (100% - `mud/mob_cmds.py:_extract_character`) ✅ **FIXED Jan 3** - Full ROM C parity
- ✅ `char_to_room()` (100% - `mud/models/room.py:char_to_room`) ✅ **Jan 2** - light tracking + temple fallback
- ✅ `char_from_room()` (100% - `mud/models/room.py:Room.remove_character`) ✅ **Jan 2** - light tracking + furniture
- ✅ `die_follower()` (100% - `mud/characters/follow.py`)
- ✅ `affect_modify()` (100% - `mud/handler.py:affect_modify`)
- ✅ `affect_to_char()` (100% - `mud/models/character.py:add_affect`)
- ✅ `affect_remove()` (100% - `mud/models/character.py:remove_affect`)
- ✅ `affect_strip()` (100% - `mud/models/character.py:strip_affect`)
- ✅ `is_affected()` (100% - `mud/models/character.py:has_affect`)
- ✅ `room_is_dark()` (100% - `mud/world/vision.py:room_is_dark`)
- ✅ `can_see_room()` (100% - `mud/world/vision.py:can_see_room`)
- ✅ `can_see()` (100% - `mud/world/vision.py:can_see_character`)
- ✅ `can_see_obj()` (100% - `mud/world/vision.py:can_see_object`)
- ✅ Plus 4 more utility functions

**⚠️ Partial Implementation (5 functions)**:
- ⚠️ `is_exact_name()` (Handled by `_is_name_match()` - no direct 1:1)
- ⚠️ `get_obj_list()` (Internal logic in get_obj_carry - no standalone)
- ⚠️ `obj_from_room()` (Partial in `_extract_obj` logic)
- ⚠️ `extract_char_old()` (Old version exists but superseded)
- ⚠️ `affect_join()` (May be in add_affect internal logic)

**❌ Missing Functions (39 functions)**:
- [ ] Object lookup: `get_obj_type`, `get_obj_wear`, `get_obj_here`, `get_obj_number` (4)
- [ ] Affects: `affect_enchant`, `affect_find`, `affect_check`, `affect_to_obj`, `affect_remove_obj` (5)
- [ ] Vision: 3 functions (can_drop_obj, is_room_owner, room_is_private)
- [ ] Character attributes: 8 functions (get_skill, get_trust, etc.)
- [ ] Utility/Lookup: 14 functions
- [ ] Money: 2 functions
- [ ] Encumbrance: 2 functions

**🎉 Critical Bug Fixes** (January 2, 2026):

**Bug #1**: `obj_to_obj()` missing carrier weight update loop (ROM C handler.c:1978-1986)
- ❌ **Exploit**: Players could carry infinite items in containers
- ✅ **Fixed**: Added 8-line weight update loop walking up container hierarchy
- ✅ **Tests**: 4/4 integration tests passing (100%)

**Bug #2**: `obj_from_obj()` missing carrier weight decrement loop (ROM C handler.c:2033-2041)
- ❌ **Exploit**: Weight never decreased when removing items from containers
- ✅ **Fixed**: Added weight decrement loop mirroring obj_to_obj()
- ✅ **Tests**: Verified in `test_obj_from_obj_decreases_carrier_weight`

**Bug #3**: `get_obj_weight()` missing WEIGHT_MULT multiplier (ROM C handler.c:2509-2519)
- ❌ **Broken**: Bags of holding (value[4]=0) and weight-reducing containers didn't work
- ✅ **Fixed**: Implemented `_get_weight_mult()` helper with prototype fallback
- ✅ **Tests**: Verified 0%, 50%, 100% multipliers work correctly

**Bug #4**: `apply_ac()` missing 3x body slot multiplier (ROM C handler.c:1688-1726)
- ❌ **Game Breaking**: Body armor provided only 1/3rd AC it should (platemail -10 AC gave -10 instead of -30)
- ✅ **Fixed**: Implemented correct ROM C multiplier table (body 3x, head/legs/about 2x, others 1x)
- ✅ **Tests**: 13/13 integration tests passing (`tests/integration/test_equipment_ac_calculations.py`)

**ROM C Behavioral Quirk Discovered**:
- Nested container multipliers are NOT cumulative in `obj_to_obj()`
- When adding item (10 lbs) to inner_bag (50% mult) in outer_bag (100% mult):
  - ROM C adds: `10 * 100 / 100 = 10 lbs` (NOT `10 * 50 / 100 = 5 lbs`)
  - Inner bag multiplier only applied during `get_obj_weight(inner_bag)` calls
- QuickMUD now matches this exact behavior

**Session Reports**: 
- `SESSION_SUMMARY_2026-01-02_HANDLER_C_WEIGHT_BUG_FIXES.md` (Bugs #1-3)
- `SESSION_SUMMARY_2026-01-02_HANDLER_C_ROOM_AND_EQUIPMENT_AUDIT.md` (Bug #4)

**Integration Tests**: ✅ Complete
- ✅ 4/4 container weight tests passing (`tests/test_encumbrance.py`)
- ✅ 15/15 encumbrance tests passing (100%)
- ✅ 13/13 equipment AC tests passing (`tests/integration/test_equipment_ac_calculations.py`)
- ✅ 3/3 alignment restriction tests passing (`tests/test_player_equipment.py`)
- ✅ Group combat tests verify get_char_room/die_follower

**Estimated Work**: 2-4 days for remaining 41 functions

**Next Steps**:
1. [ ] Continue line-by-line audit of remaining 41 functions
2. [ ] Focus on P1 functions: extract_obj, affect functions
3. [ ] Add integration tests for missing affect functions
3. [ ] Implement missing container functions

---

### ✅ P1-2: effects.c (AUDITED - 100% + Integration Tests Complete)

**Status**: ✅ **AUDIT COMPLETE + Integration Tests Passing** (January 5, 2026)

**ROM Functions**: Environmental damage effects (5 functions total)
**QuickMUD Module**: `mud/magic/effects.py`

**Detailed Audit Document**: `docs/parity/EFFECTS_C_AUDIT.md`

**Audit Status** (5/5 functions implemented - 100%):

**✅ Fully Implemented (5 functions)**:
- ✅ `acid_effect()` (ROM C lines 39-193) - Object destruction, armor AC degradation, container dumping
- ✅ `cold_effect()` (ROM C lines 195-297) - Potion/drink shattering, chill touch affect
- ✅ `fire_effect()` (ROM C lines 299-439) - Scroll/staff/wand burning, blindness affect
- ✅ `poison_effect()` (ROM C lines 441-528) - Food/drink poisoning (does NOT destroy)
- ✅ `shock_effect()` (ROM C lines 530-615) - Wand/staff/jewelry destruction, daze effect

**Key Features Verified**:
- ✅ ROM C probability formulas with diminishing returns (level/damage based)
- ✅ Item type specific behaviors (CONTAINER, ARMOR, CLOTHING, STAFF, WAND, SCROLL, etc.)
- ✅ Immunity checks (BURN_PROOF, NOPURGE, BLESS, 20% random chance)
- ✅ Armor AC degradation (increases AC by +1, doesn't destroy armor)
- ✅ Container dumping with recursive effects (half level/damage)
- ✅ Character affects (poison, daze, chill touch, blindness)
- ✅ Object destruction mechanics (all item types)

**Critical Implementation Details**:
- Probability formula: `chance = c_div(level, 4) + c_div(damage, 10)` with diminishing returns at 25 and 50
- Armor AC degradation: Calls `affect_enchant()`, increases AC (higher = worse), updates carrier's armor array
- Container dumping: Dumps contents to room/carrier's room, applies effect with half level/damage, then destroys container
- Poison immunity: BLESS provides complete immunity (NOT just chance reduction like other effects)

**Integration Tests**: ✅ **23/23 tests passing** (`tests/integration/test_environmental_effects.py` - 466 lines, January 5, 2026)

**Test Coverage**:
- ✅ `TestPoisonEffect` (5 tests) - Food/drink poisoning, immunity checks
- ✅ `TestColdEffect` (3 tests) - Potion/drink shattering, BURN_PROOF immunity
- ✅ `TestFireEffect` (3 tests) - Scroll/food burning, BURN_PROOF immunity
- ✅ `TestShockEffect` (4 tests) - Wand/staff/jewelry destruction, character daze
- ✅ `TestAcidEffect` (4 tests) - Armor degradation, clothing destruction, immunity
- ✅ `TestProbabilityFormula` (4 tests) - Formula verification, clamping edge cases

**ROM C Behavioral Patterns Preserved**:
- Object destruction with level/damage probability
- Container dumping before destruction (contents spill out)
- Armor degrades but doesn't destroy (special case)
- Character affects applied with save checks
- Item type specific messages and behaviors
- Immunity checks (BURN_PROOF, NOPURGE, BLESS, 20% random)

**QuickMUD Efficiency**: 740 Python lines replace ~577 ROM C lines (28% expansion for clarity and type safety)

**No Missing Functions**: All ROM C environmental damage functions implemented!

---

### ✅ P1-3: db.c + db2.c (AUDITED - 100%)

**Status**: ✅ **Both files fully audited** — see per-file detailed sections below (P1-5 covers db.c; db2.c covered in summary table line 77).

**ROM Functions**: World database loading + ROM 2.4 format parsers
**QuickMUD Modules**: `mud/loaders/`, `mud/spawning/`, `mud/utils/math_utils.py`, `mud/utils/rng_mm.py`, `mud/utils/text.py`, `mud/registry.py`

**Audit Outcome** (Apr 29, 2026 reconciliation):
- ✅ **db.c** — 44/44 functional functions implemented (24 N/A — Python built-ins / GC / logging). 1 P2-deferred (`check_pet_affected`, part of pet persistence in save.c). See `DB_C_AUDIT.md`.
- ✅ **db2.c** — 4 CRITICAL/IMPORTANT gaps closed (DB2-001 ACT_IS_NPC merge, DB2-002 race-table flag merge, DB2-003 first-char uppercase, DB2-006 AC ×10). 2 MINOR deferred (DB2-004 kill_table — not user-reachable; DB2-005 single-line vs multi-line `fread_string` — theoretical only). See `DB2_C_AUDIT.md`.

**Integration Tests**: ✅ Complete (`tests/integration/test_db2_loader_parity.py` — 8/8 passing; reset/spawning verified across `test_mob_spawning.py`, `test_architectural_parity.py`).

**Architectural Note**: QuickMUD's canonical area format is JSON (mirrored from ROM .are via `convert_are_to_json.py`); the .are parser exists for parity verification and third-party area support. `load_socials` is N/A by deviation (`data/socials.json` is the canonical source). `convert_objects/convert_object/convert_mobile` are N/A — no MERC legacy areas exist.

---

### ✅ P1-4: save.c (historical section — canonical DB path now enforced)

**Status**: ✅ Historical JSON-path audit complete; canonical DB/login persistence path is now enforced by INV-003 and INV-008.

**ROM Functions**: Player save/load (8 functions total)
**QuickMUD Module**: `mud/account/account_manager.py`, `mud/db/serializers.py`, `mud/world/time_persistence.py`

**Detailed Audit Document**: `docs/parity/SAVE_C_AUDIT.md`

**Status Note**:

- This subsection documents the original January 2026 JSON-persistence audit.
- `mud/persistence.py` was deleted in 2.8.3.
- The live canonical path is the SQLAlchemy/DB loader-save stack, tracked by `CROSS_FILE_INVARIANTS_TRACKER.md` INV-003 and INV-008, both ✅ enforced.

**Historical Audit Status** (6/8 functions implemented at the time):

**✅ Fully Implemented (6 functions)**:
- ✅ `save_char_obj()` → `save_character()` (100% - atomic saves with temp file pattern)
- ✅ `load_char_obj()` → `load_character()` (100% - backward compatible with legacy formats)
- ✅ `fwrite_char()` → `_write_character_data()` (100% - all fields saved)
- ✅ `fread_char()` → `_read_character_data()` (100% - with `_upgrade_legacy_save()`)
- ✅ `fwrite_obj()` → `_write_object_data()` (100% - recursive container nesting)
- ✅ `fread_obj()` → `_read_object_data()` (100% - object affects restored)

**❌ Not Implemented (2 functions - P2 priority)**:
- ❌ `fwrite_pet()` - Pet persistence (deferred to P2)
- ❌ `fread_pet()` - Pet loading (deferred to P2)

**Key Features Verified**:
- ✅ Atomic saves (temp file + rename pattern prevents corruption)
- ✅ Container nesting (recursive save/load works correctly)
- ✅ Object affects (saved and restored on load)
- ✅ Equipment slots (all 18 slots saved/loaded)
- ✅ Backward compatibility (`_upgrade_legacy_save()` handles old formats)
- ⚠️ Pet persistence (NOT implemented - P2 feature)

**Critical Gaps** (P2 - Optional):
- [ ] Pet/follower persistence (2 functions missing)
- [ ] Pet affect checking (`check_pet_affected()` from db.c)

**Integration Tests**: ✅ **9/9 tests passing** (`tests/integration/test_save_load_parity.py` - 488 lines, January 5, 2026)

**Test Coverage**:
- ✅ Container nesting (3+ levels deep) - 2 tests
- ✅ Equipment affects preservation - 2 tests
- ✅ Backward compatibility (missing/extra fields) - 2 tests
- ✅ Atomic save corruption resistance - 2 tests
- ✅ Full integration workflow - 1 test

**Next Steps** (Optional P2 work):
1. [ ] Implement pet persistence (1-2 days) - DEFERRED

**QuickMUD Efficiency**: 509 Python lines replace 1,928 ROM C lines (73.6% reduction!)

---

### ✅ P1-5: db.c (AUDITED - 100%)

**Status**: 🎉 **100% COMPLETE** (44/44 functional functions implemented!) 🎉

**ROM Functions**: Database/world loading (68 functions total, excluding system calls)
**QuickMUD Modules**: `mud/loaders/*.py` (2,217 lines), `mud/spawning/*.py` (855 lines), `mud/utils/math_utils.py` (22 lines), `mud/utils/rng_mm.py` (160 lines), `mud/utils/text.py` (140 lines), `mud/registry.py` (13 lines)

**Detailed Audit Document**: `docs/parity/DB_C_AUDIT.md`

**Audit Status** (44/44 functional functions implemented - 100% PARITY, 24/68 total N/A):

**✅ Area Loading (8/8 needed functions - 100%)**:
- ✅ `load_area()` → `area_loader.load_area_file()` (177 lines)
- ✅ `load_helps()` → `help_loader.load_helps()` (66 lines)
- ✅ `load_mobiles()` → `mob_loader.load_mobiles()` (239 lines)
- ✅ `load_objects()` → `obj_loader.load_objects()` (405 lines)
- ✅ `load_resets()` → `reset_loader.load_resets()` (350 lines)
- ✅ `load_rooms()` → `room_loader.load_rooms()` (302 lines)
- ✅ `load_shops()` → `shop_loader.load_shops()` (99 lines)
- ✅ `load_specials()` → `specials_loader.load_specials()` (67 lines)

**✅ Mobprog Loading (2/2 needed functions - 100%)**:
- ✅ `load_mobprogs()` → `mobprog_loader.load_mobprogs()` (136 lines)
- ✅ `fix_mobprogs()` → `mobprog_loader._link_mobprogs()` (27 lines)

**✅ Reset System (2/2 needed functions - 100%)**:
- ✅ `area_update()` → `game_tick._area_update_tick()` (game tick integration)
- ✅ `reset_area()` → `reset_handler.reset_area()` (641 lines)

**✅ Entity Instantiation (2/2 needed functions - 100%)**:
- ✅ `create_mobile()` → `spawn_mob()` + `MobInstance.from_prototype()` (64 lines)
- ✅ `create_object()` → `spawn_object()` + `ObjInstance.from_prototype()` (similar)

**✅ Character Initialization (2/2 functions - 100%)**:
- ✅ `clear_char()` → `Character.__init__()` (model initialization)
- ✅ `get_extra_descr()` → `handler.get_extra_descr()` (handler.c 100% complete)

**✅ Prototype Lookups (4/4 functions - 100%)**:
- ✅ `get_mob_index()` → `mob_registry.get(vnum)` (global dict)
- ✅ `get_obj_index()` → `obj_registry.get(vnum)` (global dict)
- ✅ `get_room_index()` → `room_registry.get(vnum)` (global dict)
- ✅ `get_mprog_index()` → `mprog_registry.get(vnum)` (stored in mob_registry)

**✅ File I/O Helpers (8/8 functions - 100%)**:
- ✅ `fread_letter()` → `BaseTokenizer.next_line()[0]` (76 lines total tokenizer)
- ✅ `fread_number()` → `int(BaseTokenizer.next_line())`
- ✅ `fread_flag()` → `BaseTokenizer.read_flag()`
- ✅ `flag_convert()` → `BaseTokenizer._flag_to_int()`
- ✅ `fread_string()` → `BaseTokenizer.read_string()`
- ✅ `fread_string_eol()` → `BaseTokenizer.next_line()`
- ✅ `fread_to_eol()` → `BaseTokenizer.next_line()`
- ✅ `fread_word()` → `BaseTokenizer.next_line().split()[0]`

**✅ RNG Functions (8/8 functions - 100%)**:
- ✅ `init_mm()` → `rng_mm._init_state()` (Mitchell-Moore init)
- ✅ `number_mm()` → `rng_mm.number_mm()` (Mitchell-Moore generator)
- ✅ `number_fuzzy()` → `rng_mm.number_fuzzy()` (ROM fuzzy number)
- ✅ `number_range()` → `rng_mm.number_range()` (exact C semantics)
- ✅ `number_percent()` → `rng_mm.number_percent()` (1..100)
- ✅ `number_bits()` → `rng_mm.number_bits()` (bitmask random)
- ✅ `dice()` → `rng_mm.dice()` (nDm dice rolls)
- ✅ `number_door()` → `rng_mm.number_door()` (random door 0-5) **[IMPLEMENTED Jan 5]**

**✅ String Utilities (3/3 needed functions - 100%)**:
- ✅ `smash_tilde()` → `text.format_rom_string()` (140 lines)
- ✅ `smash_dollar()` → `text.smash_dollar()` (mobprog security) **[IMPLEMENTED Jan 5]**
- ✅ `capitalize()` → `str.capitalize()` (Python built-in)

**✅ Math Utilities (1/1 needed functions - 100%)**:
- ✅ `interpolate()` → `math_utils.interpolate()` (level-based scaling) **[IMPLEMENTED Jan 5]**

**🎉 Session 2026-01-05: IMPLEMENTED ALL MISSING FUNCTIONS! 🎉**

**3 Critical Functions Implemented** (~1 hour total):
1. ✅ `interpolate()` - Level-based value scaling (`mud/utils/math_utils.py` - 22 lines)
   - Formula: `value_00 + level * (value_32 - value_00) / 32`
   - Usage: Damage calculations, stat scaling, THAC0 interpolation
   - ROM C Reference: `src/db.c:3652-3662`

2. ✅ `number_door()` - Random door direction (`mud/utils/rng_mm.py` - added 19 lines)
   - Returns random value 0-5 (NORTH, EAST, SOUTH, WEST, UP, DOWN)
   - Usage: Mobprogs, random movement, door selection
   - ROM C Reference: `src/db.c:3541-3549`

3. ✅ `smash_dollar()` - Mobprog security (`mud/utils/text.py` - added 24 lines)
   - Replaces '$' with 'S' to prevent mobprog variable injection
   - Security-critical for mobprog interpreter
   - ROM C Reference: `src/db.c:3677-3694`

**N/A Functions (24/68 - Python replaces ROM C)**:
- Memory management (3): `alloc_mem()`, `free_mem()`, `alloc_perm()` → Python GC
- String comparison (4): `str_cmp()`, `str_prefix()`, `str_infix()`, `str_suffix()` → Python built-ins
- Logging (4): `append_file()`, `bug()`, `log_string()`, `tail_chain()` → Python `logging` module
- Bootstrap (1): `boot_db()` → QuickMUD uses lazy loading
- Backward compat (2): `load_old_mob()`, `load_old_obj()` → QuickMUD only supports ROM 2.4 format
- OLC creation (2): `new_load_area()`, `new_reset()` → QuickMUD uses JSON for new areas
- Object cloning (2): `clone_mobile()`, `clone_object()` → Python uses `copy.deepcopy()`
- String utils (2): `str_dup()`, `free_string()` → Python immutable strings
- Admin commands (2): `do_memory()`, `do_dump()` → ROM C memory debugging (irrelevant)
- Admin commands (1): `do_areas()` → ✅ Implemented in `mud/commands/info.py`

**Key Features Verified**:
- ✅ All loaders working (areas, rooms, mobs, objects, resets, shops, specials, mobprogs, helps)
- ✅ RNG system complete (Mitchell-Moore parity achieved)
- ✅ Reset system functional (LastObj/LastMob tracking verified in handler.c audit)
- ✅ Modular architecture (13+ specialized files vs 1 monolithic db.c)
- ✅ 13.8% code reduction (3,407 Python lines vs 3,952 ROM C lines)
- ✅ **100% FUNCTIONAL PARITY CERTIFIED!** 🎉

**Integration Tests**: ✅ Partial (`tests/integration/test_mob_spawning.py`, `test_architectural_parity.py` - reset system verified)

**Next Steps** (Optional P2 work):
1. [ ] Create `tests/integration/test_area_loading.py` (1 day)
2. [ ] Behavioral verification - Compare ROM C vs QuickMUD area loading (2-3 days)
3. [ ] Pet persistence completion (from save.c audit - P2 feature)

**QuickMUD Efficiency**: 3,407 Python lines replace 3,952 ROM C lines (13.8% reduction!)

**db.c is 100% ROM Parity Certified! This is a MAJOR milestone for QuickMUD.** 🎉🚀

---

### ⚠️ P1-6: act_info.c (COMPLETE - 100%)

**Status**: ✅ **AUDIT COMPLETE** (January 8, 2026)

**ROM Functions**: Information commands (look, examine, who, where, etc.)
**QuickMUD Module**: `mud/commands/info.py`, `mud/commands/character.py`, `mud/commands/auto_settings.py`, `mud/commands/misc_info.py`

**Audit Status**:
- ✅ All 38 ROM C functions implemented (100%)
- ✅ 273/273 integration tests passing (100%)
- ✅ P0: do_score, do_look, do_who, do_help (4/4)
- ✅ P1: do_exits, do_examine, do_affects, do_worth, do_time, do_weather, do_where, do_compare, do_consider, do_inventory, do_equipment, do_practice, do_password, etc. (24/24)
- ✅ P2: Auto-flags, config commands, character commands (3/3)
- ✅ P3: do_imotd, do_telnetga (2/2)

**Missing Functions**: None - **100% complete!**

**Integration Tests**: ✅ Complete (273/273 passing)

**Next Steps**: None - act_info.c is now 100% ROM C parity!

---

### ✅ P1-7: act_obj.c (COMPLETE - 100%)

**Status**: ✅ **Full parity verified.** The earlier in-progress notes in this section are historical; the canonical state matches the top summary row and `docs/parity/ACT_OBJ_C_AUDIT.md`.

**ROM Functions**: Object commands (get, drop, put, give, wear, remove, shops, consumables)
**QuickMUD Modules**: `mud/commands/inventory.py`, `mud/commands/obj_manipulation.py`, `mud/commands/equipment.py`, `mud/commands/shop.py`, `mud/commands/give.py`, `mud/commands/consumption.py`, `mud/commands/liquids.py`, `mud/commands/magic_items.py`, `mud/commands/thief_skills.py`

**Audit Status**:
- ✅ `do_get()` / `do_put()` / `do_drop()` / `do_give()` - complete
- ✅ `do_wear()` / `do_remove()` / `wear_obj()` / `remove_obj()` - complete
- ✅ Consumables and magic items (`do_quaff`, `do_drink`, `do_eat`, `do_fill`, `do_pour`, `do_recite`, `do_brandish`, `do_zap`) - complete
- ✅ `do_sacrifice()` / `do_steal()` - complete
- ✅ No remaining act_obj parity gaps are scheduled

**Recent Verification**:
- ✅ `_obj_from_char()` inventory bug fixed (`char.inventory`, not `char.carrying`)
- ✅ Deprecated `.carrying` cleanup verified on April 23, 2026
- ✅ Targeted pytest run passes: `test_player_npc_interaction.py`, `test_mobprog_scenarios.py`, `test_new_player_workflow.py` (24/24)

**Critical Gaps Remaining**:
- None

**Integration Tests**: ✅ Verified complete. Latest targeted slice: `215 passed, 1 skipped` across container retrieval, drop, give, remove, equipment, consumables, and steal suites on 2026-05-14.

**Estimated Work**: None

**Next Steps**:
- None — `act_obj.c` is complete. Pick the next real open non-deferred tracker row instead of this historical section.

---

### ✅ P1-8: mob_prog.c + mob_cmds.c (COMPLETE - 100%)

**Status**: ✅ **Both audits are complete.** The earlier partial notes in this section are historical; canonical status lives in `MOB_PROG_C_AUDIT.md` and `MOB_CMDS_C_AUDIT.md`.

**ROM Functions**: Mob programs and mob commands
**QuickMUD Modules**: `mud/mobprog.py`, `mud/mob_cmds.py`, `mud/commands/mobprog_tools.py`
**Audit Docs**:
- `docs/parity/MOB_PROG_C_AUDIT.md`
- `docs/parity/MOB_CMDS_C_AUDIT.md`

**Audit Status**:
- ✅ `mob_prog.c` complete — all 7 audit gaps closed (`MOBPROG-001..007`)
- ✅ `mob_cmds.c` complete — all 18 audit gaps closed (`MOBCMD-001..018`)
- ✅ Trigger dispatch, control flow, `$`-code substitution, and edge-case command semantics verified
- ✅ Admin/debug helpers (`do_mpstat`, `do_mpdump`) covered via `mud/commands/mobprog_tools.py`

**Integration Tests**:
- `tests/integration/test_mobprog_predicates.py`
- `tests/integration/test_mobprog_greet_trigger.py`
- `tests/integration/test_mobprog_program_flow.py`
- `tests/integration/test_mobprog_edge_cases.py`
- `tests/integration/test_mob_cmds_*.py`

**Remaining Work**: None in the audited parity set

---

## Priority 2: Important Features

### ✅ P2-1: olc.c + olc_act.c + olc_save.c (AUDITED - 100% on audit-bound gaps)

**Status**: ✅ **OLC cluster audited.** Earlier “not audited” text here is historical and superseded by the audit docs and top matrix.

**ROM Functions**: Online building system
**QuickMUD Modules**: `mud/commands/build.py`, `mud/commands/imm_olc.py`, `mud/commands/dispatcher.py`, `mud/olc/`, `mud/utils/prompt.py`
**Audit Docs**:
- `docs/parity/OLC_C_AUDIT.md`
- `docs/parity/OLC_ACT_C_AUDIT.md`
- `docs/parity/OLC_SAVE_C_AUDIT.md`
- `docs/parity/OLC_MPCODE_C_AUDIT.md`

**Known Status**:
- ✅ `olc.c` complete — OLC-INFRA-001 and OLC-001..023 closed
- ✅ `olc_act.c` audit-bound gaps complete — OLC_ACT-001..014 closed
- ✅ `olc_save.c` audit-bound gaps complete — OLC_SAVE-001..017 closed
- ✅ `olc_mpcode.c` complete — mpcode editor parity closed

**Deferred / Architectural Notes**:
- `OLC_SAVE-018..020` remain deferred-by-design under JSON-authoritative save semantics
- `OLC_ACT_C_AUDIT.md` explicitly defers deep TIER C coverage beyond the closed audit-bound gaps

**Integration Tests**: ✅ Present across the OLC cluster; see the per-file audit docs for the dedicated suites

**Estimated Work**: None in the current audit-bound scope

**Next Steps**:
- None — only deferred/design-scoped OLC items remain

---

### ✅ P2-2: special.c (AUDITED - 100%)

**Status**: ✅ **Per-file audit completed and re-verified**

**ROM Functions**: Special procedures (shopkeepers, guards, etc.)
**QuickMUD Module**: `mud/spec_funs.py`
**Audit Doc**: `docs/parity/SPECIAL_C_AUDIT.md`

**Known Status**:
- ✅ Full ROM `special.c` function inventory mapped
- ✅ Gameplay-visible spec-proc gaps closed (`executioner`, `guard`, `mayor`, `thief`, `nasty`, faction members)
- ✅ Existing spec-function test slice re-verified green on 2026-05-14

**Critical Gaps**:
- [x] Complete inventory of ROM spec procs
- [x] Which spec procs are essential vs. optional
- [x] Spec proc integration with mobprogs

**Verification**:
- `./venv/bin/python -m pytest -q tests/test_spec_funs.py tests/test_spec_fun_behaviors.py tests/test_healer.py` → `54 passed`

**Estimated Work**: complete

**Next Steps**:
- [x] None — row reconciled to completed audit state

---

### ✅ P2-3: act_wiz.c (AUDITED - 100%)

**Status**: ✅ **Fully audited and covered by dedicated integration parity tests**

**ROM Functions**: Immortal/admin commands
**QuickMUD Modules**: `mud/wiznet.py`, `mud/commands/imm_*.py`, `mud/commands/admin_commands.py`, `mud/commands/inventory.py`, `mud/commands/remaining_rom.py`
**Audit Doc**: `docs/parity/ACT_WIZ_C_AUDIT.md`

**Known Status**:
- ✅ Full immortal/admin command surface audited against ROM `src/act_wiz.c`
- ✅ `stat` family (`do_stat` / `do_rstat` / `do_ostat` / `do_mstat`) closed and covered
- ✅ `log`, `force`, punishments, echo family, invis/incognito, load/clone/set, and copyover flows closed
- ✅ Dedicated parity suite remains green

**Critical Gaps**:
- [x] `protect` command (`WIZ-003`)
- [x] canonical snoop-proof check in `snoop` (`WIZ-004`)
- [x] owner/private-room admin movement gates (`WIZ-001`)
- [x] ROM `violate` location semantics (`WIZ-002`)
- [x] `stat` command family (`WIZ-005`)
- [x] `log` command (`WIZ-006`)
- [x] `force` ROM flow/message parity (`WIZ-007`)
- [x] residual stat parity fixes (`WIZ-039`..`WIZ-044`)

**Integration Tests**: ✅ `tests/integration/test_act_wiz_command_parity.py` (`108 passed` on 2026-05-14)

**Estimated Work**: complete

**Next Steps**:
- [x] None — row reconciled to completed audit state

---

### ✅ P2-4: scan.c (AUDITED - 100%)

**Status**: ✅ **Implemented and verified**

**ROM Functions**: `do_scan`
**QuickMUD Module**: `mud/commands/inspection.py`

**Audit doc**: `docs/parity/SCAN_C_AUDIT.md`

**Verified**:
- `scan` command is wired in `mud/commands/dispatcher.py`
- directional scan tokens and depth handling match ROM `src/scan.c`
- room broadcasts match ROM act-pair behavior
- no Python-only fallback lines are emitted on empty scans
- `spell_farsight` delegates to `do_scan`, matching ROM call structure

**Test coverage**:
- `tests/test_scan_parity.py`
- `tests/integration/test_scan_broadcasts.py`
- `tests/test_commands.py`
- `tests/test_spell_farsight_rom_parity.py`

---

### ✅ P2-5: healer.c (AUDITED - 100%)

**Status**: ✅ **Fully audited and covered by dedicated healer parity tests**

**ROM Functions**: `do_heal`
**QuickMUD Module**: `mud/commands/healer.py`
**Audit Doc**: `docs/parity/HEALER_C_AUDIT.md`

**Known Status**:
- ✅ `ACT_IS_HEALER` lookup and ROM price table restored
- ✅ Silver-aware affordability, `deduct_cost`, healer payout, and room utterance restored
- ✅ `mana`, `refresh`, and `heal` route through ROM-faithful logic

**Critical Gaps**:
- [x] `HEALER-001` healer detection + price table
- [x] `HEALER-002` mana/economy/utterance parity
- [x] `HEALER-003` refresh spell parity
- [x] `HEALER-004` heal spell parity

**Verification**:
- `./venv/bin/python -m pytest -q tests/integration/test_healer_command_parity.py tests/test_healer.py tests/test_healer_parity.py tests/test_healer_rom_parity.py` → `23 passed`

**Estimated Work**: complete

---

## Priority 3: Infrastructure & Utilities

### ✅ P3-1: const.c / tables.c / lookup.c (AUDITED - 100%)

**Status**: ✅ **Fully audited**

**ROM Functions**: Constants, tables, lookups
**QuickMUD Modules**: `mud/models/constants.py`, `mud/models/titles.py`, `mud/models/races.py`, `mud/models/classes.py`, `mud/models/weapon_table.py`, `mud/models/character.py`, `mud/skills/groups.py`, `mud/utils/prefix_lookup.py`, `mud/wiznet.py`, `mud/account/account_service.py`, `mud/combat/engine.py`, `mud/handler.py`
**Audit Docs**:
- `docs/parity/CONST_C_AUDIT.md`
- `docs/parity/LOOKUP_C_AUDIT.md`
- `docs/parity/TABLES_C_AUDIT.md`

**Known Status**:
- ✅ `lookup.c` fully audited — all 8 gaps closed
- ✅ `tables.c` fully audited — all 3 gaps closed
- ✅ `const.c` fully closed (`CONST-001`..`CONST-007`)

**Critical Gaps**:
- [x] Verify all ROM constants present
- [x] Verify enum values match ROM bit positions
- [x] Verify lookup tables complete
- [x] Port canonical `weapon_table` as shared data (`CONST-007`)

**Verification**:
- `./venv/bin/python -m pytest -q tests/integration/test_lookup_parity.py tests/test_nanny_rom_parity.py tests/integration/test_nanny_login_parity.py tests/test_healer_rom_parity.py tests/integration/test_do_equipment.py -k 'lookup or weapon or title or equipment or liq'` → `22 passed, 24 deselected`
- `./venv/bin/python -m pytest -q tests/test_weapon_table_parity.py tests/integration/test_nanny_login_parity.py tests/test_nanny_rom_parity.py tests/integration/test_do_equipment.py -k 'weapon or equipment or chosen_weapon_skill'` → `14 passed, 19 deselected`

**Estimated Work**: complete

---

### ✅ P3-2: flags.c / bit.c (AUDITED - 100%)

**Status**: ✅ **Audited 100%.** `bit.c` is fully closed and `flags.c` now has no open gaps.

**ROM Functions**: Flag manipulation utilities
**QuickMUD Modules**: `mud/commands/remaining_rom.py`, `mud/utils/bit.py`, `mud/utils/prefix_lookup.py`
**Audit Docs**:
- `docs/parity/FLAGS_C_AUDIT.md`
- `docs/parity/BIT_C_AUDIT.md`

**Known Status**:
- ✅ `flags.c` `FLAG-001` closed — `do_flag` fully implemented and tested
- ✅ `flags.c` `FLAG-002` closed — `=` now preserves non-`settable` rows exactly like ROM
- ✅ `bit.c` fully closed — `BIT-001`, `BIT-002`, `BIT-003` all fixed

**Verification**:
- `tests/integration/test_flag_command_parity.py`
- `tests/integration/test_bit_flag_value.py`
- `tests/integration/test_bit_flag_string.py`
- `tests/integration/test_bit_is_stat.py`

**Estimated Work**:
- None

---

### ✅ P3-3: string.c (AUDITED - 100%, all 12 gaps closed)

**Status**: ✅ **AUDITED 100% — all 12 helpers FIXED**

**ROM Functions**: OLC string-editor backend (12 public functions — `string_edit`, `string_append`, `string_replace`, `string_add`, `format_string`, `first_arg`, `string_unpad`, `string_proper`, `string_linedel`, `string_lineadd`, `merc_getline`, `numlines`)
**QuickMUD Module**: `mud/utils/string_editor.py` (all 12 helpers), `mud/utils/text.py` (`smash_tilde`)

**Known Status (Apr 29, 2026)**:
- ✅ Phase 1 inventory: all 12 functions catalogued with ROM line ranges in `STRING_C_AUDIT.md`
- ✅ Phase 2 verification: confirmed every function operates on descriptor-level OLC editor state
- ✅ Phase 3 gaps STRING-001..012: all closed (STRING-004 final, closed Apr 29, 2026)
- ✅ Phase 4: ROM deviation noted — `~` terminator checked before `smash_tilde` (pragmatic fix for ROM dead-code bug at src/string.c:128 vs 230)
- ✅ Phase 5: 24 integration tests in `tests/integration/test_string_editor_string_add.py`

---

### N/A P3-4: recycle.c / mem.c (NOT NEEDED)

**Status**: N/A **Python garbage collection handles this**

**ROM Functions**: Memory management
**QuickMUD**: Python's GC

**No action needed** - architectural difference.

---

### ✅ P3-5: sha256.c (AUDITED - 100%)

**Status**: ✅ **Audited 2026-04-28** — see `docs/parity/SHA256_C_AUDIT.md`

**ROM Functions**: SHA-256 primitive (Init/Update/Final/Transform/Pad) + `sha256_crypt` password hashing
**QuickMUD Module**: `mud/security/hash_utils.py` (delegates to stdlib `hashlib`)

**Status**: ✅ Audited. SHA-256 primitive delegated to Python's `hashlib` (byte-for-byte equivalent). `sha256_crypt` replaced by PBKDF2-HMAC-SHA256 + 16-byte salt — deliberate security upgrade with no observable gameplay parity surface (account credentials are internal; no pfile compatibility goal).

---

### ✅ P3-6: comm.c (AUDITED - 95%)

**Status**: ✅ **Non-networking surface fully audited; networking deferred-by-design**

**ROM Functions**: Network I/O and socket handling — **and** `bust_a_prompt`, `act_new`, `colour`, `check_parse_name`, `stop_idling`, `fix_sex`, `show_string`.

**QuickMUD Modules**: `mud/net/`, `mud/utils/prompt.py`, `mud/account/account_service.py`, `mud/utils/act.py`, `mud/utils/fix_sex.py`, `mud/net/ansi.py`.

**Audit doc**: [`COMM_C_AUDIT.md`](COMM_C_AUDIT.md) — 9 stable gap IDs (COMM-001..COMM-009). Closed: COMM-001 (`bust_a_prompt` rendering), COMM-002 (`show_string` pager input semantics), COMM-003 (`check_parse_name` length floor), COMM-004 (mob-keyword collision), COMM-005 (double-newbie descriptor sweep + wiznet alert), COMM-006 (clan-name reject), COMM-007 (`stop_idling` act-broadcast), COMM-008 (ANSI specials `{D {* {/ {- {{`), COMM-009 (`fix_sex` standalone helper). Only the asyncio networking architecture itself remains deferred-by-design.

**Networking** (`main`, `init_socket`, `game_loop_*`, descriptor I/O, telnet protocol): intentional architectural divergence — QuickMUD uses asyncio. Not audit-bound.

---

## Audit Statistics

### Overall Progress

| Priority | Total Files | Audited | Partial | Not Audited | Coverage % |
|----------|-------------|---------|---------|-------------|------------|
| P0 | 8 | 8 | 0 | 0 | **100%** ✅ |
| P1 | 11 | 11 | 0 | 0 | **100%** ✅ |
| P2 | 12 | 12 | 0 | 0 | **100%** ✅ |
| P3 | 12 | 9 | 0 | 0 | **75%** ✅ (3 N/A) |
| **Total** | **43** | **40** | **0** | **0** | **93%** ✅ (3 N/A) |

### Work Estimates

| Priority | Estimated Audit Days | Estimated Implementation Days |
|----------|----------------------|-------------------------------|
| P0 | 0 (complete) | 0 (complete) |
| P1 | 3-5 days | 5-10 days |
| P2 | 7-10 days | 15-20 days |
| P3 | 3-5 days | 5-7 days |
| **Total** | **13-20 days** | **25-37 days** |

### Next 5 Follow-up Targets

1. Re-triage deferred-by-design audit items for any architecture that is now practical to port.
2. Broaden regression coverage around recently completed OLC, board, and nanny clusters.
3. Sweep the broader test suite for stale expectations that still contradict ROM behavior.
4. Revisit remaining 95%-coverage audited files only where the documented gap is still user-visible.
5. Keep `docs/sessions/SESSION_STATUS.md` pointed at the next concrete non-deferred parity target.

**Total**: ~8-13 days for next 5 audits

---

## Audit Process Template

### For Each ROM C File

**Step 1: Inventory Functions**
```bash
# Extract all function definitions
grep "^[a-zA-Z_].*\(.*\)$" src/FILE.c | grep -v "^{" | grep -v "^}"
```

**Step 2: Create Audit Checklist**
- [ ] List all functions
- [ ] Find QuickMUD equivalents
- [ ] Verify ROM formulas preserved
- [ ] Check edge cases
- [ ] Document intentional differences

**Step 3: Integration Tests**
- [ ] Create integration test file
- [ ] Test end-to-end workflows
- [ ] Verify game loop integration

**Step 4: Document Results**
- [ ] Update this tracker
- [ ] Note coverage percentage
- [ ] List missing functions
- [ ] Estimate implementation effort

---

## Success Criteria

### Definition of "Audited"

A ROM C file is **fully audited** when:

1. ✅ All functions inventoried
2. ✅ QuickMUD equivalents identified or documented as missing
3. ✅ ROM formulas verified preserved
4. ✅ Integration tests exist
5. ✅ Coverage ≥ 90%

### Acceptable Gaps

These do NOT count against audit completion:

- **Intentional architectural differences** (e.g., async networking vs blocking I/O)
- **Python-native replacements** (e.g., GC vs manual memory management)
- **Format differences** (e.g., JSON vs .are files)
- **Deprecated features** (e.g., ROM 1.4 backwards compat)

**Must be documented** with reasoning.

---

## Re-audit Triggers from In-Game Debug Pass (2026-04-30)

A live in-game debug session surfaced four runtime bugs that earlier audits
missed. Each points to a previously-audited file or audit doc that needs a
focused parity re-review. Source of truth remains ROM C (`src/`); the Python
ports below are what require another pass against the C.

| Bug | Live symptom | Affected Python | ROM C reference | Audit doc to re-review | Re-audit reason |
|-----|--------------|-----------------|-----------------|------------------------|-----------------|
| BUG-NLOWER | `'NoneType' object has no attribute 'lower'` on `look corpse`, `open south` | `mud/world/{obj_find,char_find}.py`; `mud/commands/{obj_manipulation,combat,misc_player,info_extended,imm_commands,imm_search,socials,remaining_rom}.py` | `src/handler.c` (`is_name`, `get_obj_carry`, `get_obj_wear`, `get_char_room`); `src/act_obj.c`; `src/act_info.c` | `HANDLER_C_AUDIT.md`, `ACT_OBJ_C_AUDIT.md`, `ACT_INFO_C_AUDIT.md` | Defensive coalesce (`getattr(x, "name", None) or ""`) was missing across ~15 sites. Must verify each helper handles the JSON-loaded prototype shape (`name=None`). |
| BUG-EDDICT | `'dict' object has no attribute 'description'` on `look fountain`, `read letter` | `mud/world/look.py` | `src/act_info.c:do_look` (extra_descr lookup); `src/db.c:fread_obj` (extra_descr load) | `ACT_INFO_C_AUDIT.md`, `DB_C_AUDIT.md` | JSON loader stores `extra_descr` as raw dicts; look code accessed `.description` attribute-style. Must verify the JSON loader constructs `ExtraDescr` instances per ROM `EXTRA_DESCR_DATA`. |
| BUG-CORPSEINT | `int('npc_corpse')` ValueError on `get coins corpse` | `mud/loaders/json_loader.py:_load_objects_from_json`; `mud/commands/inventory.py:do_get` | `src/db.c:load_objects` (item_type via `flag_value`) | `DB_C_AUDIT.md` | JSON loader skipped item_type token→int normalization that the legacy `.are` loader performs (`mud/loaders/obj_loader.py:_resolve_item_type_code`). |
| BUG-MOBHP | All mobs spawn at HP=1 ("awful condition" universal); level 1 one-shots Hassan (level 45) | `mud/spawning/templates.py:_parse_dice/from_prototype`; `mud/loaders/json_loader.py` | `src/db.c:fread_mobile` (writes `pMobIndex->hit[NUMBER/TYPE/BONUS]` as ints); `src/db.c:create_mobile` | `DB_C_AUDIT.md` | JSON loader writes `hit_dice` / `mana_dice` / `damage_dice` as strings only; `_parse_dice` short-circuited on the default `(0,0,0)` primary tuple before consulting the string fallback. ROM stores both forms. |

### Common root cause

All four bugs trace back to **`mud/loaders/json_loader.py` being a partial
port of `src/db.c:load_objects` / `load_mobiles` / `load_rooms` / `fread_obj`
/ `fread_mobile`**. The legacy `.are` loader (`mud/loaders/obj_loader.py`,
`mud/loaders/mob_loader.py`) is more complete; the JSON path silently drops
fields (separate `name`/keyword list), skips token-to-int normalization
(`item_type`), fails to construct typed instances (`ExtraDescr`), and
doesn't populate parallel tuple fields (`proto.hit` from `hit_dice`).

### Action items (next parity passes)

1. **`mud/loaders/json_loader.py` ↔ `src/db.c`** — ✅ audit doc landed
   2026-04-30 as [`JSON_LOADER_C_AUDIT.md`](JSON_LOADER_C_AUDIT.md).
   18 gaps documented (7 CRITICAL, 8 IMPORTANT, 3 MINOR). **7 of 18 closed
   in v2.6.103**: JSONLD-002 (ExtraDescr instances), JSONLD-004 (dice tuples
   parsed), JSONLD-005 (wear_flags int), JSONLD-006 (Affect instances),
   JSONLD-007 (hitroll key), JSONLD-008 (off/imm/res/vuln ints), JSONLD-011
   (form/parts ints). Remaining open: JSONLD-001 (keyword list — schema),
   JSONLD-003 (obj level — converter), JSONLD-009 (area security default),
   JSONLD-010 (area credits), JSONLD-012 (race as string), JSONLD-013 (room
   clan lookup), JSONLD-014 (D-reset semantics), JSONLD-015 (value coercion),
   JSONLD-016/017/018 (MINOR).
2. **`mud/world/{obj_find,char_find}.py` ↔ `src/handler.c`** — verify every
   `is_name` / `get_*` helper handles the documented `name: str | None`
   prototype shape. Defense applied 2026-04-30 (commit `658d319`).
3. **`mud/world/look.py` ↔ `src/act_info.c:do_look`** — verify `EXTRA_DESCR`
   handling matches ROM (keyword match semantics, prototype-fallback order,
   container/weapon/etc. branches). Patch landed 2026-04-30 (commit
   `cb4eed7`).
4. **`mud/spawning/templates.py:from_prototype` ↔ `src/db.c:create_mobile`**
   — verify dice rolls (`hit`, `mana`, `damage`) match ROM rolling order
   exactly. The spawn now consumes RNG that previously was silently skipped,
   which can shift seeded-test outcomes (handled in commit `715469d`).

    The `db.c` "100% complete" badge currently overstates the JSON loader's
    parity. ~~Recommend downgrading to ⚠️ Partial pending the `json_loader.py`
    re-audit, or adding a clear "JSON-path" caveat.~~ **Resolved v2.6.108**: JSON
    loader parity audit now complete (18/18 gaps closed in
    `JSON_LOADER_C_AUDIT.md`). The `db.c` badge remains at 100% because the JSON
    format is a serialization of the same data, not a separate implementation
    surface.

---

## Maintenance Notes

### When to Update

- ✅ After completing ROM C file audit
- ✅ After discovering parity gaps during bug fixes
- ✅ After adding new QuickMUD systems
- ✅ During quarterly ROM parity reviews

### Review Schedule

- **Weekly**: Update coverage percentages
- **Monthly**: Review P0/P1 audit status
- **Quarterly**: Full ROM C source audit

---

**Document Status**: 🔄 Active  
**Last Updated**: January 2, 2026  
**Maintained By**: QuickMUD Development Team  
**Related Documents**:
- `ROM_PARITY_VERIFICATION_GUIDE.md` - How to verify parity
- `INTEGRATION_TEST_COVERAGE_TRACKER.md` - Integration test status
- `HANDLER_C_AUDIT.md` - handler.c detailed audit
- `SESSION_SUMMARY_2026-01-02_HANDLER_C_WEIGHT_BUG_FIXES.md` - Weight bug fixes
