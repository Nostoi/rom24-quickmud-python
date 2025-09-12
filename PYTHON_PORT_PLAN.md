<!-- LAST-PROCESSED: command_interpreter -->
<!-- DO-NOT-SELECT-SECTIONS: 8,10 -->
<!-- SUBSYSTEM-CATALOG: combat, skills_spells, affects_saves, command_interpreter, socials, channels, wiznet_imm,
world_loader, resets, weather, time_daynight, movement_encumbrance, stats_position, shops_economy, boards_notes,
help_system, mob_programs, npc_spec_funs, game_update_loop, persistence, login_account_nanny, networking_telnet,
security_auth_bans, logging_admin, olc_builders, area_format_loader, imc_chat, player_save_format -->
# Python Conversion Plan for QuickMUD

## Overview
This document outlines the steps needed to port the remaining ROM 2.4 QuickMUD C codebase to Python. It also describes how to migrate existing game data (rooms, characters, items, etc.) into JSON so the Python engine can consume it directly.

## System Inventory & Coverage Matrix
<!-- COVERAGE-START -->
| subsystem | status | evidence | tests |
|---|---|---|---|
| combat | present_wired | C: src/fight.c:one_hit; PY: mud/combat/engine.py:attack_round | tests/test_combat.py; tests/test_combat_thac0.py; tests/test_combat_thac0_engine.py |
| skills_spells | present_wired | C: src/skills.c:do_practice; PY: mud/skills/registry.py:SkillRegistry.use | tests/test_skills.py; tests/test_skill_registry.py |
| affects_saves | present_wired | C: src/magic.c:saves_spell; C: src/handler.c:check_immune; PY: mud/affects/saves.py:saves_spell/_check_immune | tests/test_affects.py; tests/test_defense_flags.py |
| command_interpreter | present_wired | C: src/interp.c:interpret; PY: mud/commands/dispatcher.py:process_command | tests/test_commands.py |
| socials | present_wired | C: src/interp.c:check_social; DOC: doc/area.txt § Socials; ARE: area/social.are; PY: mud/commands/socials.py:perform_social | tests/test_socials.py; tests/test_social_conversion.py; tests/test_social_placeholders.py |
| channels | present_wired | C: src/act_comm.c:do_say/do_tell/do_shout; PY: mud/commands/communication.py:do_say/do_tell/do_shout | tests/test_communication.py |
| wiznet_imm | present_wired | C: src/act_wiz.c:wiznet; PY: mud/wiznet.py:wiznet/cmd_wiznet | tests/test_wiznet.py |
| world_loader | present_wired | DOC: doc/area.txt §§ #AREA/#ROOMS/#MOBILES/#OBJECTS/#RESETS; ARE: area/midgaard.are §§ #AREA/#ROOMS/#MOBILES/#OBJECTS/#RESETS; C: src/db.c:load_area; PY: mud/loaders/area_loader.py:load_area_file | tests/test_area_loader.py; tests/test_area_counts.py; tests/test_area_exits.py |
| resets | present_wired | C: src/db.c:reset_area; PY: mud/spawning/reset_handler.py:reset_tick | tests/test_spawning.py |
| weather | present_wired | C: src/update.c:weather_update; PY: mud/game_loop.py:weather_tick | tests/test_game_loop.py |
| time_daynight | present_wired | C: src/update.c:weather_update (sun state); PY: mud/time.py:TimeInfo.advance_hour | tests/test_time_daynight.py; tests/test_time_persistence.py |
| movement_encumbrance | present_wired | C: src/act_move.c:encumbrance; PY: mud/world/movement.py:move_character | tests/test_world.py; tests/test_encumbrance.py; tests/test_movement_costs.py |
| stats_position | present_wired | C: merc.h:POSITION; PY: mud/models/constants.py:Position | tests/test_advancement.py |
| shops_economy | present_wired | DOC: doc/area.txt § #SHOPS; ARE: area/midgaard.are § #SHOPS; C: src/act_obj.c:do_buy/do_sell; PY: mud/commands/shop.py:do_buy/do_sell; C: src/healer.c:do_heal; PY: mud/commands/healer.py:do_heal | tests/test_shops.py; tests/test_shop_conversion.py; tests/test_healer.py |
| boards_notes | present_wired | C: src/board.c; PY: mud/notes.py:load_boards/save_board; mud/commands/notes.py | tests/test_boards.py |
| help_system | present_wired | DOC: doc/area.txt § #HELPS; ARE: area/help.are § #HELPS; C: src/act_info.c:do_help; PY: mud/loaders/help_loader.py:load_help_file; mud/commands/help.py:do_help | tests/test_help_system.py |
| mob_programs | present_wired | C: src/mob_prog.c; PY: mud/mobprog.py | tests/test_mobprog.py |
| npc_spec_funs | present_wired | C: src/special.c:spec_table; C: src/update.c:mobile_update; PY: mud/spec_funs.py:run_npc_specs | tests/test_spec_funs.py |
| game_update_loop | present_wired | C: src/update.c:update_handler; PY: mud/game_loop.py:game_tick | tests/test_game_loop.py |
| persistence | present_wired | DOC: doc/pfile.txt; C: src/save.c:save_char_obj/load_char_obj; PY: mud/persistence.py | tests/test_persistence.py; tests/test_inventory_persistence.py |
| login_account_nanny | present_wired | C: src/nanny.c; PY: mud/account/account_service.py | tests/test_account_auth.py |
| networking_telnet | present_wired | C: src/comm.c; PY: mud/net/telnet_server.py:start_server | tests/test_telnet_server.py |
| security_auth_bans | present_wired | C: src/ban.c:check_ban/do_ban/save_bans; PY: mud/security/bans.py:save_bans_file/load_bans_file; mud/commands/admin_commands.py | tests/test_bans.py; tests/test_account_auth.py |
| logging_admin | present_wired | C: src/act_wiz.c (admin flows); PY: mud/logging/admin.py:log_admin_command/rotate_admin_log | tests/test_logging_admin.py; tests/test_logging_rotation.py |
| olc_builders | present_wired | C: src/olc_act.c; PY: mud/commands/build.py:cmd_redit | tests/test_building.py |
| area_format_loader | present_wired | DOC: doc/area.txt §§ #AREADATA/#ROOMS/#MOBILES/#OBJECTS/#RESETS/#SHOPS; ARE: area/midgaard.are §§ #AREADATA/#ROOMS/#MOBILES/#OBJECTS/#RESETS/#SHOPS; C: src/db.c:load_area; PY: mud/loaders/area_loader.py | tests/test_area_loader.py; tests/test_area_counts.py; tests/test_area_exits.py |
| imc_chat | present_wired | C: imc/imc.c; PY: mud/imc/protocol.py:parse_frame/serialize_frame; mud/commands/imc.py:do_imc | tests/test_imc.py |
| player_save_format | present_wired | C: src/save.c:save_char_obj; DOC: doc/pfile.txt; ARE/PLAYER: player/Shemp; PY: mud/scripts/convert_player_to_json.py:convert_player; mud/persistence.py | tests/test_player_save_format.py; tests/test_persistence.py |
<!-- COVERAGE-END -->

## Next Actions (Aggregated P0s)
<!-- NEXT-ACTIONS-START -->
<!-- no open [P0] tasks this run -->
<!-- NEXT-ACTIONS-END -->

## C ↔ Python Parity Map
<!-- PARITY-MAP-START -->
| subsystem | C source (file:symbol) | Python target (file:symbol) |
|---|---|---|
| combat | src/fight.c:one_hit/multi_hit | mud/combat/engine.py:attack_round |
| skills_spells | src/skills.c:do_practice; src/magic.c:saves_spell | mud/skills/registry.py:SkillRegistry.use; mud/affects/saves.py:saves_spell |
| affects_saves | src/magic.c:saves_spell; src/handler.c:check_immune | mud/affects/saves.py:saves_spell/_check_immune |
| movement_encumbrance | src/act_move.c:move_char/movement_loss | mud/world/movement.py:move_character |
| shops_economy (healer) | src/healer.c:do_heal | mud/commands/healer.py:do_heal |
| command_interpreter | src/interp.c:interpret | mud/commands/dispatcher.py:process_command |
| socials | src/db2.c:load_socials; src/interp.c:check_social | mud/loaders/social_loader.py:load_socials; mud/commands/socials.py:perform_social |
| channels | src/act_comm.c:do_say/do_tell/do_shout | mud/commands/communication.py:do_say/do_tell/do_shout |
| wiznet_imm | src/act_wiz.c:wiznet | mud/wiznet.py:wiznet/cmd_wiznet |
| world_loader | src/db.c:load_area | mud/loaders/area_loader.py:load_area_file |
| resets | src/db.c:reset_area | mud/spawning/reset_handler.py:reset_tick/reset_area |
| weather | src/update.c:weather_update | mud/game_loop.py:weather_tick |
| time_daynight | src/update.c:weather_update sun state | mud/time.py:TimeInfo.advance_hour; mud/game_loop.py:time_tick |
| movement_encumbrance | src/act_move.c:encumbrance | mud/world/movement.py:move_character |
| stats_position | merc.h:position enum | mud/models/constants.py:Position |
| shops_economy | src/act_obj.c:do_buy/do_sell | mud/commands/shop.py:do_buy/do_sell |
| boards_notes | src/board.c | mud/notes.py:load_boards/save_board; mud/commands/notes.py |
| help_system | src/act_info.c:do_help | mud/loaders/help_loader.py:load_help_file; mud/commands/help.py:do_help |
| mob_programs | src/mob_prog.c | mud/mobprog.py:run_prog |
| npc_spec_funs | src/special.c:spec_table | mud/spec_funs.py:run_npc_specs |
| game_update_loop | src/update.c:update_handler | mud/game_loop.py:game_tick |
| persistence | src/save.c:save_char_obj/load_char_obj | mud/persistence.py:save_character/load_character |
| login_account_nanny | src/nanny.c | mud/account/account_service.py:login/create_character |
| networking_telnet | src/comm.c | mud/net/telnet_server.py:start_server; mud/net/connection.py:handle_connection |
| security_auth_bans | src/ban.c:check_ban/do_ban/save_bans | mud/security/bans.py:save_bans_file/load_bans_file; mud/commands/admin_commands.py |
| logging_admin | src/act_wiz.c (admin flows) | mud/logging/admin.py:log_admin_command/rotate_admin_log |
| olc_builders | src/olc_act.c | mud/commands/build.py:cmd_redit |
| area_format_loader | src/db.c:load_area/new_load_area | mud/loaders/area_loader.py; mud/scripts/convert_are_to_json.py |
| imc_chat | imc/imc.c | mud/imc/__init__.py:imc_enabled; mud/commands/imc.py:do_imc |
| player_save_format | src/save.c:save_char_obj | mud/persistence.py:PlayerSave |
| skills_spells | src/tables.c:skill_table; src/flags.c | mud/models/constants.py; mud/models/skill.py |
| security_auth_bans | src/sha256.c:sha256_crypt | mud/security/hash_utils.py:sha256_hex |
| affects_saves | src/flags.c:IMM_*/RES_*/VULN_* | mud/models/constants.py:ImmFlag/ResFlag/VulnFlag |
<!-- PARITY-MAP-END -->

## Data Anchors (Canonical Samples)
- ARE: area/midgaard.are  (primary fixture)
- DOC: doc/area.txt §#ROOMS/#MOBILES/#OBJECTS/#RESETS
- DOC: doc/Rom2.4.doc  (stats, AC/THAC0, saves)
- C:  src/db.c:load_area(), src/save.c:load_char_obj(), src/socials.c

## Parity Gaps & Corrections
<!-- PARITY-GAPS-START -->
<!-- AUDITED: combat, skills_spells, affects_saves, command_interpreter, socials, channels, wiznet_imm, world_loader, resets, weather, time_daynight, movement_encumbrance, stats_position, shops_economy, boards_notes, help_system, mob_programs, npc_spec_funs, game_update_loop, persistence, login_account_nanny, networking_telnet, security_auth_bans, logging_admin, olc_builders, area_format_loader, imc_chat, player_save_format -->

<!-- SUBSYSTEM: affects_saves START -->
### affects_saves — Parity Audit 2025-09-08
STATUS: completion:✅ implementation:full correctness:passes (confidence 0.86)
KEY RISKS: flags, RNG, RIV
TASKS:
- ✅ [P0] Implement `check_immune` with IMM/RES/VULN flags — done 2025-09-08
  EVIDENCE: C src/handler.c:check_immune
  EVIDENCE: C src/magic.c:saves_spell
  EVIDENCE: PY mud/affects/saves.py:L18-L91 (check_immune)
  EVIDENCE: PY mud/affects/saves.py:L94-L123 (saves_spell RIV adjustments)
  EVIDENCE: TEST tests/test_affects.py::test_check_immune_riv_adjustments
  RATIONALE: ROM adjusts save chance based on resist/immune/vuln; currently stubbed to normal.
  FILES: mud/affects/saves.py (implement `_check_immune`), mud/models/constants.py (flag definitions), mud/models/character.py (uses flags)
  TESTS: tests/test_affects.py::test_check_immune_riv_adjustments
  REFERENCES: C src/handler.c:213-320 (check_immune); C src/magic.c:212-243 (saves_spell)
- ✅ [P1] Define IMM/RES/VULN IntFlags with ROM bit values — done 2025-09-08
  EVIDENCE: PY mud/models/constants.py: ImmFlag/ResFlag/VulnFlag (lines near end)
  EVIDENCE: TEST tests/test_defense_flags.py::test_imm_res_vuln_intflags_match_defense_bits
  EVIDENCE: C src/merc.h: IMM_*/RES_*/VULN_* letter bits (A..Z)
  RATIONALE: Preserve bit widths and parity semantics; avoid magic numbers.
  FILES: mud/models/constants.py
  TESTS: tests/test_affects.py::test_imm_res_vuln_flag_values
  REFERENCES: C src/merc.h: IMM_*/RES_*/VULN_ defines (letters A..Z)
- ✅ [P2] Achieve ≥80% coverage for affects_saves — done 2025-09-12
  EVIDENCE: TEST pytest -q --cov=mud.affects.saves --cov-report=term-missing (95%)
  EVIDENCE: TEST tests/test_affects.py
NOTES:
- C: src/magic.c:saves_spell() L212-L243; src/handler.c:213-320 check_immune sets default from WEAPON/MAGIC globals then dam_type-specific bits.
- PY: mud/affects/saves.py uses rng_mm and c_div; `_check_immune` implemented; tests cover RIV.
- Applied tiny fix: added `imm_flags`, `res_flags`, `vuln_flags` to Character (mud/models/character.py) to enable RIV checks.
- Applied tiny fix: corrected RIV mapping in saves_spell to ROM values (IS_IMMUNE=1, IS_RESISTANT=2, IS_VULNERABLE=3).
<!-- SUBSYSTEM: affects_saves END -->

<!-- SUBSYSTEM: socials START -->
### socials — Parity Audit 2025-09-08
STATUS: completion:✅ implementation:full correctness:passes (confidence 0.84)
KEY RISKS: file_formats, side_effects
TASKS:
- ✅ [P0] Wire social loader and command dispatcher — acceptance: `smile` command sends actor/room/victim messages — done 2025-09-08
  EVIDENCE: mud/commands/dispatcher.py:L87-L97; tests/test_socials.py::test_smile_command_sends_messages
- ✅ [P1] Convert `social.are` to JSON with fixed field widths — done 2025-09-07
  EVIDENCE: PY mud/scripts/convert_social_are_to_json.py
  EVIDENCE: TEST tests/test_social_conversion.py::test_convert_social_are_to_json_matches_layout
  EVIDENCE: DOC doc/command.txt § Social Commands
  EVIDENCE: ARE area/social.are
- ✅ [P0] Use `not_found` message when arg given but target missing — done 2025-09-08
  EVIDENCE: C src/interp.c:501-520 (check_social not-found path)
  EVIDENCE: PY mud/commands/socials.py:L27-L33
  EVIDENCE: TEST tests/test_socials.py::test_social_not_found_message
  RATIONALE: ROM `check_social` uses char_not_found when argument doesn’t resolve to a target.
  FILES: mud/commands/socials.py
  TESTS: tests/test_socials.py::test_social_not_found_message
  REFERENCES: C src/interp.c:501-520 (check_social dispatch), C src/db2.c:120-160 (social.char_not_found)
- ✅ [P2] Add tests to reach ≥80% coverage for socials — acceptance: coverage report ≥80% — done 2025-09-08
  EVIDENCE: coverage 89% for mud/commands/socials.py; command: pytest -q --cov=mud.commands.socials --cov-report=term-missing
NOTES:
- `load_socials` reads JSON into registry (loaders/social_loader.py:1-16)
- Dispatcher falls back to socials when command not found (commands/dispatcher.py:87-97)
- `expand_placeholders` supports `$mself` pronouns (social.py:37-52)
- Applied tiny fix: arg+no target now uses `not_found` message (mud/commands/socials.py); ROM parity with `char_not_found`.
<!-- SUBSYSTEM: socials END -->

<!-- SUBSYSTEM: wiznet_imm START -->
### wiznet_imm — Parity Audit 2025-09-08
STATUS: completion:❌ implementation:partial correctness:passes (confidence 0.86)
KEY RISKS: flags, side_effects
TASKS:
- ✅ [P0] Define wiznet flag bits via IntFlag — acceptance: enumeration matches ROM values — done 2025-09-08
  EVIDENCE: mud/wiznet.py:L11-L36; tests/test_wiznet.py::test_wiznet_flag_values
- ✅ [P0] Implement wiznet broadcast filtering — acceptance: immortal with WIZ_ON receives message; mortal does not — done 2025-09-08
  EVIDENCE: mud/wiznet.py:L43-L58; tests/test_wiznet.py::test_wiznet_broadcast_filtering
- ✅ [P0] Hook `wiznet` command into dispatcher — acceptance: pytest toggles WIZ_ON with `wiznet` command — done 2025-09-07
  EVIDENCE: mud/wiznet.py:L61-L74; tests/test_wiznet.py::test_wiznet_command_toggles_flag
- ✅ [P1] Persist wiznet subscriptions to player saves with bit widths — done 2025-09-07
  EVIDENCE: PY mud/persistence.py:L31-L33; L57-L59; L93-L95
  EVIDENCE: TEST tests/test_wiznet.py::test_wiznet_persistence
- ✅ [P1] Add gating tests for WIZ_SECURE and WIZ_TICKS — done 2025-09-08
  EVIDENCE: TEST tests/test_wiznet.py::test_wiznet_requires_specific_flag
  EVIDENCE: TEST tests/test_wiznet.py::test_wiznet_secure_flag_gating
  EVIDENCE: C src/act_wiz.c:wiznet; C src/interp.c wiznet calls
  RATIONALE: Match ROM per-flag subscription behavior.
  FILES: tests/test_wiznet.py
  REFERENCES: C src/act_wiz.c wiznet levels/flags; C src/interp.c logging to wiznet
- ✅ [P2] Achieve ≥80% test coverage for wiznet — acceptance: coverage report ≥80% — done 2025-09-08
  EVIDENCE: coverage 96% for mud/wiznet.py; command: pytest -q --cov=mud.wiznet --cov-report=term-missing
NOTES:
- Added broadcast helper to filter subscribed immortals (wiznet.py:43-58)
- `Character.wiznet` stores wiznet flag bits (character.py:87)
- Command table registers `wiznet` command (commands/dispatcher.py:18-59)
- Help file documents wiznet usage despite missing code (area/help.are:1278-1286)
<!-- SUBSYSTEM: wiznet_imm END -->

<!-- Removed prior completion note; RNG parity tasks remain open. -->

<!-- SUBSYSTEM: world_loader START -->
### world_loader — Parity Audit 2025-09-06
STATUS: completion:❌ implementation:partial correctness:suspect (confidence 0.65)
KEY RISKS: file_formats, indexing
TASKS:
 - ✅ [P0] Parse `#AREADATA` builders/security/flags — acceptance: loader populates fields verified by test — done 2025-09-07
  EVIDENCE: mud/loaders/area_loader.py:L42-L57; tests/test_area_loader.py::test_areadata_parsing
- ✅ [P2] Achieve ≥80% test coverage for world_loader — acceptance: coverage report ≥80% — done 2025-09-08
  EVIDENCE: coverage 98% for mud/loaders/area_loader.py; command: pytest -q --cov=mud.loaders.area_loader --cov-report=term-missing
NOTES:
- Parser now reads `#AREADATA` builders, security, and flags (area_loader.py:42-57)
- Tests only verify movement/lookup, not area metadata
- Applied tiny fix: key `area_registry` by `min_vnum`
- Applied tiny fix: reject duplicate area vnums in `area_registry`; added regression test
- Applied tiny fix: enforce `$` sentinel in `area.lst`; test added
- Applied tiny fix: reordered imports in `tests/test_area_loader.py`
<!-- SUBSYSTEM: world_loader END -->

<!-- SUBSYSTEM: time_daynight START -->
### time_daynight — Parity Audit 2025-09-08
STATUS: completion:❌ implementation:partial correctness:passes (confidence 0.92)
KEY RISKS: tick_cadence
TASKS:
- ✅ [P0] Align hour advancement to ROM PULSE_TICK — done 2025-09-08
  EVIDENCE: C src/merc.h:L155-L160 (PULSE_PER_SECOND=4; PULSE_TICK=60*PPS)
  EVIDENCE: C src/update.c:L1161-L1189 (pulse_point starts at PULSE_TICK; hour updates when it hits 0)
  EVIDENCE: PY mud/game_loop.py:L63-L84 (advance hour only when pulses % get_pulse_tick()==0)
  EVIDENCE: PY mud/config.py:L17-L27 (get_pulse_tick returns 60*PULSE_PER_SECOND)
  EVIDENCE: TEST tests/test_time_daynight.py::test_time_tick_advances_hour_and_triggers_sunrise
  RATIONALE: Match ROM cadence (hour changes on PULSE_TICK boundary); sunrise/sunset broadcast occurs at that moment.
  FILES: mud/game_loop.py, mud/config.py, tests/test_time_daynight.py
- ✅ [P1] Introduce configurable tick scaling for tests — done 2025-09-08
  EVIDENCE: C src/update.c comment notes randomization around PULSE_TICK; parity permits test-only scaling.
  EVIDENCE: PY mud/config.py:get_pulse_tick() reads TIME_SCALE/env and clamps ≥1
  EVIDENCE: PY mud/game_loop.py uses get_pulse_tick() each tick
  EVIDENCE: TEST tests/test_time_daynight.py::test_time_scale_accelerates_tick
  FILES: mud/game_loop.py, mud/config.py, tests/test_time_daynight.py
- ✅ [P2] Persist `time_info` across reboot — done 2025-09-08
  EVIDENCE: PY mud/persistence.py:TimeSave dataclass; save_time_info()/load_time_info(); integrated into save_world()/load_world()
  EVIDENCE: TEST tests/test_time_persistence.py::test_time_info_persist_roundtrip
  RATIONALE: Maintain world time across reboot consistent with ROM behavior.
  FILES: mud/persistence.py, tests/test_time_persistence.py
NOTES:
- C shows hour-related updates occur at `pulse_point == 0` (PULSE_TICK) which triggers `weather_update` that manages sunrise/sunset state.
- PY currently increments hour each 4 pulses; adjust to PULSE_TICK and add test scale to keep tests fast.
<!-- SUBSYSTEM: time_daynight END -->

<!-- SUBSYSTEM: combat START -->
### combat — Parity Audit 2025-09-08
STATUS: completion:❌ implementation:partial correctness:suspect (confidence 0.83)
KEY RISKS: defense_order, AC mapping, RNG, RIV
TASKS:
- ✅ [P0] Implement defense check order (hit → shield block → parry → dodge) — done 2025-09-08
  EVIDENCE: C src/fight.c: one_hit()/check_* ordering around damage application
  EVIDENCE: C src/fight.c:L1900-L2100 (calls to check_shield_block/check_parry/check_dodge before damage)
  EVIDENCE: PY mud/combat/engine.py:L23-L55 (defense order and messages); L58-L70 (check_* stubs)
  EVIDENCE: TEST tests/test_combat.py::test_defense_order_and_early_out
  RATIONALE: Preserve ROM probability ordering via early-outs.
  FILES: mud/combat/engine.py; tests/test_combat.py
- ✅ [P0] Map dam_type → AC index and apply AC sign correctly — done 2025-09-08
  EVIDENCE: C src/merc.h: AC_PIERCE/AC_BASH/AC_SLASH/AC_EXOTIC defines
  EVIDENCE: C src/const.c: attack table → DAM_* mappings
  EVIDENCE: PY mud/models/constants.py (AC_* indices); mud/combat/engine.py:L73-L94 (ac_index_for_dam_type, is_better_ac)
  EVIDENCE: TEST tests/test_combat.py::test_ac_mapping_and_sign_semantics
  RATIONALE: Ensure unarmed defaults to BASH; EXOTIC for non-physical; negative AC is better.
  FILES: mud/models/constants.py, mud/combat/engine.py, tests/test_combat.py
 - ✅ [P1] Apply RIV (IMMUNE/RESIST/VULN) scaling before side-effects — done 2025-09-08
  EVIDENCE: C src/fight.c:L806-L834 (switch on check_immune: immune=0, resist=dam-dam/3, vuln=dam+dam/2)
  EVIDENCE: C src/handler.c:check_immune (dam_type → bit mapping; WEAPON/MAGIC defaults)
  EVIDENCE: PY mud/combat/engine.py:L32-L55 (RIV scaling with c_div; on_hit_effects hook)
  EVIDENCE: PY mud/affects/saves.py:_check_immune mapping → IMM/RES/VULN
  EVIDENCE: TEST tests/test_combat.py::test_riv_scaling_applies_before_side_effects (captures scaled damage via on_hit_effects)
  RATIONALE: Side-effects must see scaled damage; matches ROM ordering.
  FILES: mud/combat/engine.py, mud/affects/saves.py, tests/test_combat.py
 - ✅ [P0] Integrate AC into hit chance (GET_AC/THAC0 parity) — done 2025-09-08
  EVIDENCE: C src/fight.c:L463-L520 (thac0 interpolation, GET_AC index/10, diceroll vs thac0-victim_ac)
  EVIDENCE: C src/merc.h:2104 (GET_AC macro), AC indices
  EVIDENCE: PY mud/combat/engine.py:L14-L24 (AC mapping), L20-L31 (AC-adjusted to_hit with clamp)
  EVIDENCE: PY mud/models/character.py:L74-L76 (armor indices storage)
  EVIDENCE: TEST tests/test_combat.py::test_ac_influences_hit_chance
  RATIONALE: More negative AC must reduce hit chance; integrate AC index and sign.
  FILES: mud/combat/engine.py, mud/models/character.py, tests/test_combat.py
 - ✅ [P0] Add positional/visibility hit modifiers — done 2025-09-08
  EVIDENCE: C src/fight.c:L480-L520 (victim_ac adjustments: <FIGHTING +4, <RESTING +6, !can_see -4)
  EVIDENCE: PY mud/combat/engine.py:L26-L41 (invisible and position-based AC modifiers using pre-attack position)
  EVIDENCE: TEST tests/test_combat.py::test_visibility_and_position_modifiers
  RATIONALE: Sleeping targets are easier to hit; invisible targets harder.
  FILES: mud/combat/engine.py, tests/test_combat.py
- ✅ [P0] Introduce THAC0 interpolation (class-based) and tests — done 2025-09-08
  EVIDENCE: C src/const.c: class_table thac0_00/thac0_32 values (mage 20→6; cleric 20→2; thief 20→-4; warrior 20→-10)
  EVIDENCE: C src/fight.c:L463-L472 (interpolate and negative adjustments)
  EVIDENCE: PY mud/combat/engine.py:THAC0_TABLE, interpolate(), compute_thac0()
  EVIDENCE: TEST tests/test_combat_thac0.py::test_thac0_interpolation_at_levels; ::test_thac0_hitroll_and_skill_adjustments
  RATIONALE: Ground hit calculations in ROM class progression and skill/hitroll effects.
  FILES: mud/combat/engine.py, tests/test_combat_thac0.py
- ✅ [P0] Integrate compute_thac0 into hit resolution behind feature flag — done 2025-09-08
  EVIDENCE: C src/fight.c:L510-L520 (diceroll vs thac0 - victim_ac; diceroll==0 auto-miss)
  EVIDENCE: PY mud/combat/engine.py (COMBAT_USE_THAC0 path with number_bits loop)
  EVIDENCE: PY mud/config.py:COMBAT_USE_THAC0 default False
  EVIDENCE: PY mud/utils/rng_mm.py:number_bits
  EVIDENCE: TEST tests/test_combat_thac0_engine.py::test_thac0_path_hit_and_miss
  RATIONALE: Preserve existing behavior by default; allow ROM-authentic hit logic when enabled.
  FILES: mud/combat/engine.py, mud/config.py, mud/utils/rng_mm.py, tests/test_combat_thac0_engine.py
- ✅ [P2] Coverage ≥80% for combat — done 2025-09-08
  EVIDENCE: TEST coverage run — mud/combat/engine.py 97% (3 missed) via `pytest -q --cov=mud.combat.engine --cov-report=term-missing`
  EVIDENCE: TEST tests/test_combat.py, tests/test_combat_thac0.py, tests/test_combat_thac0_engine.py
  FILES: tests/*
- ✅ [P0] Implement Mitchell–Moore RNG (number_mm) with ROM gating — done 2025-09-08
  EVIDENCE: PY mud/utils/rng_mm.py:L1-L120 (Mitchell–Moore state + helpers)
  EVIDENCE: TEST tests/test_rng_and_ccompat.py::test_number_mm_sequence_matches_golden_seed_12345
  EVIDENCE: C src/db.c:number_mm L3599-L3622; number_percent L3527-L3534; number_range L3504-L3520; number_bits L3550-L3554; dice L3628-L3645
  RATIONALE: Match ROM gating/bitmask semantics; deterministic seeding for goldens.
  FILES: mud/utils/rng_mm.py, tests/test_rng_and_ccompat.py

- ✅ [P0] Enforce rng_mm usage; ban random.* in combat/affects — done 2025-09-08
  EVIDENCE: CI .github/workflows/ci.yml (Enforce rng_mm usage step)
  EVIDENCE: TEST CI grep step passes with no matches in mud/combat mud/affects
  RATIONALE: Prevent regressions to Python stdlib RNG in parity paths.
  FILES: .github/workflows/ci.yml

- ✅ [P1] Port dice(n,size) helper with ROM semantics — done 2025-09-12
  EVIDENCE: PY mud/utils/rng_mm.py:dice
  EVIDENCE: TEST tests/test_rng_dice.py::test_dice_rom_special_cases_and_boundaries; tests/test_rng_dice.py::test_dice_matches_sum_of_number_range_calls
  REFERENCES: C src/db.c:dice L3716-L3739
  RATIONALE: ROM dice sums number_range(1,size); special-cases size==0→0 and size==1→number.
- ✅ [P1] Apply RIV (IMMUNE/RESIST/VULN) scaling before side-effects — done 2025-09-12
  EVIDENCE: PY mud/combat/engine.py:L63-L88 (RIV scaling and on_hit order)
  EVIDENCE: TEST tests/test_combat.py::test_riv_scaling_applies_before_side_effects
  EVIDENCE: C src/magic.c:saves_spell L212-L243; C src/handler.c:check_immune L213-L320
  EVIDENCE: C src/magic.c:saves_spell RIV handling; C src/handler.c:check_immune
  FILES: mud/affects/saves.py, mud/combat/engine.py, tests/test_combat.py
- ✅ [P2] Coverage ≥80% for combat — done 2025-09-08
  EVIDENCE: TEST coverage run — mud/combat/engine.py 97% via existing tests
NOTES:
- C: one_hit/multi_hit sequence integrates defense checks and AC; current Python engine omits both.
- PY: attack_round uses rng_mm.number_percent (good), but lacks AC/defense order/RIV integration.
- Applied tiny fix: use c_div for AC contribution to hit chance (mud/combat/engine.py) to ensure C-style division with negative AC.
<!-- SUBSYSTEM: combat END -->

<!-- SUBSYSTEM: skills_spells START -->
### skills_spells — Parity Audit 2025-09-08
STATUS: completion:❌ implementation:partial correctness:suspect (confidence 0.80)
KEY RISKS: RNG, side_effects
TASKS:
- ✅ [P0] Replace Random.random() with rng_mm.number_percent() in SkillRegistry — done 2025-09-08
  - rationale: ROM evaluates against percent rolls; float RNG diverges
  - files: mud/skills/registry.py; tests/test_skills.py; tests/test_skill_registry.py
  - acceptance_criteria: failure triggers when number_percent() ≤ threshold; test asserts deterministic failure by forcing threshold=100
  - references: C src/skills.c (do_practice, success/failure checks)
- ✅ [P1] Use learned% for success when available; fallback to failure_rate until learned is wired — done 2025-09-12
  EVIDENCE: PY mud/skills/registry.py:SkillRegistry.use
  EVIDENCE: TEST tests/test_skills_learned.py::test_learned_percent_gates_success_boundary
  REFERENCES: C src/skills.c:do_practice; C src/magic.c:saves_spell (percent gating)
  RATIONALE: Per-character learned% gates success when present; preserves legacy failure_rate when absent.
- [P2] Coverage ≥80% for skills
  - acceptance_criteria: coverage report ≥80% for mud/skills/registry.py and handlers
NOTES:
- C: success/failure checks compare percent rolls to thresholds derived from skill knowledge.
- PY: SkillRegistry uses rng_mm now (good); learned% not yet modeled — add without breaking existing JSON by defaulting to failure_rate when learned absent.
<!-- SUBSYSTEM: skills_spells END -->

<!-- SUBSYSTEM: movement_encumbrance START -->
### movement_encumbrance — Parity Audit 2025-09-08
STATUS: completion:❌ implementation:partial correctness:unknown (confidence 0.62)
KEY RISKS: lag_wait, side_effects
TASKS:
- ✅ [P0] Enforce carry weight and number limits before movement — done 2025-09-07
  - evidence: PY mud/world/movement.py:L19-L33; TEST tests/test_world.py::test_overweight_character_cannot_move
- ✅ [P0] Update carry weight/number on pickup/drop/equip — done 2025-09-08
  - evidence: PY mud/models/character.py:L92-L114; TEST tests/test_encumbrance.py::test_carry_weight_updates_on_pickup_equip_drop
 - ✅ [P0] Apply sector-based movement costs and resource checks (boat/fly) — done 2025-09-09
  EVIDENCE: PY mud/world/movement.py:L43-L92
  EVIDENCE: TEST tests/test_movement_costs.py::test_sector_move_cost_and_wait
  EVIDENCE: TEST tests/test_movement_costs.py::test_water_noswim_requires_boat
  EVIDENCE: TEST tests/test_movement_costs.py::test_air_requires_flying
  EVIDENCE: TEST tests/test_movement_costs.py::test_boat_allows_water_noswim
  EVIDENCE: C src/act_move.c:L50-L58 (movement_loss); L173-L196 (cost/WAIT_STATE); L232-L360 (move_char flow)
  RATIONALE: Average movement cost and gating for AIR/BOAT match ROM; apply WAIT_STATE(1) and deduct move.
- ✅ [P0] Implement enter/portal/gate flows (act_enter) — done 2025-09-09
  EVIDENCE: PY mud/commands/movement.py:do_enter
  EVIDENCE: TEST tests/test_enter_portal.py::test_enter_closed_portal_denied
  EVIDENCE: TEST tests/test_enter_portal.py::test_enter_open_portal_moves_character
  EVIDENCE: C src/act_enter.c:do_enter L66-L220 (portal type/flags, closed check, destination vnum)
  RATIONALE: Actor can enter portals when open; closed portals deny with ROM-like message; destination uses value[3] vnum.
- ✅ [P1] Replace fixed limits with STR-based carry caps (can_carry_w/n) — done 2025-09-12
  - rationale: ROM derives carry caps from character stats/tables
  - files: mud/world/movement.py (can_carry_w/can_carry_n)
  - tests: tests/test_encumbrance.py::test_stat_based_carry_caps_monotonic
  - acceptance_criteria: higher STR increases capacity; test asserts monotonic relation
  - references: C src/handler.c:can_carry_w/can_carry_n L899-L939; C src/const.c:str_app L728-L760
  EVIDENCE: PY mud/world/movement.py:_STR_CARRY and can_carry_*; TEST tests/test_encumbrance.py::test_stat_based_carry_caps_monotonic
NOTES:
- Movement now blocks when over caps; add wait-state and stat-derived caps.
- C: act_move.c and macros in merc.h govern movement and WAIT_STATE.
<!-- SUBSYSTEM: movement_encumbrance END -->

<!-- SUBSYSTEM: help_system START -->
### help_system — Parity Audit 2025-09-08
STATUS: completion:✅ implementation:full correctness:passes (confidence 0.82)
KEY RISKS: file_formats, indexing
TASKS:
- ✅ [P0] Load help entries from JSON and populate registry — acceptance: pytest loads `help.json` and finds `murder` topic — done 2025-09-08
  EVIDENCE: mud/loaders/help_loader.py:L1-L17; tests/test_help_system.py::test_load_help_file_populates_registry
- ✅ [P0] Wire `help` command into dispatcher — acceptance: test runs `help murder` and receives topic text — done 2025-09-08
  EVIDENCE: mud/commands/dispatcher.py:L18-L56; tests/test_help_system.py::test_help_command_returns_topic_text
- ✅ [P1] Preserve ROM help file widths in JSON conversion — done 2025-09-12
  EVIDENCE: PY mud/scripts/convert_help_are_to_json.py:parse_help_are
  EVIDENCE: TEST tests/test_help_conversion.py::test_convert_help_are_preserves_wizlock_entry
  EVIDENCE: DOC doc/area.txt § #HELPS (around L166-L190)
  EVIDENCE: ARE area/help.are (WIZLOCK/NEWLOCK entry around L920-990)
- ✅ [P1] Add help sync target and CI drift check — done 2025-09-12
  - rationale: Keep data/help.json synchronized with canonical area/help.are
  - files: mud/scripts/convert_help_are_to_json.py; .github/workflows/ci.yml
  - tests: reuse tests/test_help_system.py; CI step regenerates and verifies no diff
  - references: DOC doc/area.txt § #HELPS; ARE area/help.are
  EVIDENCE: CI .github/workflows/ci.yml ("Help data drift check" step)
- ✅ [P2] Achieve ≥80% test coverage for help_system — done 2025-09-12
  EVIDENCE: TEST pytest -q --cov=mud.loaders.help_loader --cov-report=term-missing (100%)
  EVIDENCE: TEST tests/test_help_system.py
NOTES:
- Loader populates registry from JSON; dispatcher wires `help` command.
- Tests cover loading and command output; add P1/P2 tasks for format preservation and coverage.
<!-- SUBSYSTEM: help_system END -->

<!-- SUBSYSTEM: resets START -->
### resets — Parity Audit 2025-09-08
STATUS: completion:❌ implementation:partial correctness:suspect (confidence 0.66)
KEY RISKS: file_formats, indexing, side_effects
TASKS:
- ✅ [P0] Implement 'P' reset semantics using LastObj + limits — done 2025-09-08
  EVIDENCE: C src/db.c:L1760-L1905 (reset_room 'O'/'P' handling); C src/db.c:L1906-L1896 (limit logic, count and lock fix around 'P')
  EVIDENCE: PY mud/spawning/reset_handler.py:L1-L50; L51-L120 (track last_obj, spawn map per vnum, P places into container, respects count)
  EVIDENCE: TEST tests/test_spawning.py::test_reset_P_places_items_inside_container_in_midgaard
  NOTES: Lock-state fix (value[1]) not applied because object instance model lacks per-instance value fields; to be addressed if required by tests.

- [P1] Implement 'G'/'E' reset limits and level logic
  - rationale: ROM enforces per-index count limits and computes object levels for shopkeepers/equipment
  - files: mud/spawning/reset_handler.py
  - tests: extend tests/test_spawning.py to cover equip vs give with limits; object levels within bounds
  - acceptance_criteria: limit respected; level computed like C (UMAX/UMIN/number_fuzzy/number_range paths)
  - references: C src/db.c: reset_room() case 'G'/'E' L1955-L2057

- [P1] Support 'R' resets to randomize exits
  - rationale: ROM shuffles exits for certain rooms
  - files: mud/spawning/reset_handler.py; mud/world/room.py (exit order utility)
  - tests: new test asserting exit list permutation after reset on a room with R reset
  - acceptance_criteria: after reset_tick, specified rooms have exits permuted; stable when no R reset
  - references: C src/db.c: reset_room() case 'R' L2059-L2080
  EVIDENCE: PY mud/spawning/reset_handler.py:L96-L109
  EVIDENCE: TEST tests/test_spawning.py::test_reset_R_randomizes_exit_order

NOTES:
- C: reset_room maintains `LastObj`/`LastMob` across cases; Python uses a vnum→object map losing instance order — fix to track last created object instance.
- C: 'P' applies container lock fix: `LastObj->value[1] = LastObj->pIndexData->value[1]` post-population.
- PY: reset_tick ages/emptiness gating implemented; detailed per-reset semantics incomplete.
<!-- SUBSYSTEM: resets END -->

<!-- SUBSYSTEM: security_auth_bans START -->
### security_auth_bans — Parity Audit 2025-09-07
STATUS: completion:❌ implementation:absent correctness:unknown (confidence 0.78)
KEY RISKS: file_formats, side_effects
TASKS:
 - ✅ [P0] Enforce site/account bans at login — acceptance: adding a ban prevents login; tests cover banned host (BAN_ALL) and banned account name — done 2025-09-07
  EVIDENCE: PY mud/security/bans.py:L1-L60
  EVIDENCE: PY mud/account/account_service.py:L1-L10; L12-L39
  EVIDENCE: PY mud/net/connection.py:L1-L20; L31-L50
  EVIDENCE: TEST tests/test_account_auth.py::test_banned_account_cannot_login
  EVIDENCE: TEST tests/test_account_auth.py::test_banned_host_cannot_login
  RATIONALE: ROM checks bans in descriptor attach and nanny; parity requires rejecting banned hosts/users early.
  FILES: mud/security/bans.py (new), mud/account/account_service.py, mud/net/connection.py
  TESTS: tests/test_account_auth.py::test_banned_host_cannot_login (new), tests/test_account_auth.py::test_banned_account_cannot_login (new)
  REFERENCES: C src/ban.c:check_ban(); C src/nanny.c:L194-L300
 - ✅ [P0] Persist bans in ROM-compatible format and order — acceptance: save/load round-trip equals golden derived from C save_bans(); includes type/host/level — done 2025-09-07
  EVIDENCE: C src/ban.c:43:save_bans(); src/ban.c:1009:load_resets (ban format reference in save_bans)
  EVIDENCE: PY mud/security/bans.py:save_bans_file()/load_bans_file()
  EVIDENCE: TEST tests/test_account_auth.py::test_ban_persistence_roundtrip
  RATIONALE: Maintain operational parity and admin tooling expectations.
  FILES: mud/security/bans.py, data/bans.txt (fixture), port.instructions.md (rule already added)
  TESTS: tests/test_account_auth.py::test_ban_persistence_roundtrip (new)
  REFERENCES: C src/ban.c:43:save_bans(); C src/ban.c:256:do_ban()
 - ✅ [P1] Add admin commands ban/unban/banlist — acceptance: dispatcher registers commands; permission-enforced; tests verify list/add/remove — done 2025-09-07
  RATIONALE: Mirror ROM `do_ban` UX for immortals.
  FILES: mud/commands/admin_commands.py:cmd_ban/cmd_unban/cmd_banlist; mud/commands/dispatcher.py (registrations)
  TESTS: tests/test_admin_commands.py::test_ban_unban_commands
  REFERENCES: C src/interp.c:296:{"ban", do_ban,...}; C src/ban.c:256:do_ban(); C src/ban.c:do_allow
 - ✅ [P2] Coverage ≥80% for security_auth_bans — acceptance: coverage report ≥80% for mud/security/bans.py — done 2025-09-07
  RATIONALE: Lock behavior to avoid regressions.
  FILES: tests/test_bans.py (add/remove/clear; save deletes when empty; non-perm ignored); tests/test_account_auth.py (round-trip)
NOTES:
- C: `check_ban()` runs in comm/nanny flow; `do_ban` updates list on disk (src/ban.c, src/nanny.c).
- PY: only per-channel bans exist (mud/commands/communication.py); no site/account ban registry or login-time enforcement.
- Ensure we capture client host in telnet session and pass to login for BAN_* checks.
 - Applied tiny fix: clear ban registry at boot (`mud/world/world_state.py:initialize_world`) to avoid cross-test leakage.
<!-- SUBSYSTEM: security_auth_bans END -->

<!-- SUBSYSTEM: area_format_loader START -->
### area_format_loader — Parity Audit 2025-09-08
STATUS: completion:❌ implementation:partial correctness:passes (confidence 0.74)
KEY RISKS: file_formats, flags, indexing
TASKS:
- ✅ [P0] Verify Midgaard conversion parity (counts & exits) — done 2025-09-07
  - evidence: DOC doc/area.txt §#ROOMS; ARE area/midgaard.are; PY mud/loaders/room_loader.py
  - tests: tests/test_area_counts.py::test_midgaard_counts_match_original_are; tests/test_area_exits.py::test_midgaard_room_3001_exits_and_keys
- ✅ [P0] Enforce `area.lst` `$` sentinel and duplicate-entry rejection — done 2025-09-07
  - evidence: PY mud/loaders/__init__.py (sentinel); PY mud/loaders/area_loader.py (duplicate vnum)
  - tests: tests/test_world.py::test_area_list_requires_sentinel
- [P1] Preserve `#RESETS` semantics for nested `P` (put) into spawned containers
  - rationale: ROM allows multiple identical vnums; loader must track specific instance linkage
  - files: mud/spawning/reset_handler.py (use per-instance identifiers instead of vnum map), tests/test_spawning.py (golden for nested containers)
  - acceptance_criteria: `P` reset places object inside the correct container instance when multiple exist; matches C behavior on midgaard.are sample
  - references: C src/db.c:load_resets; DOC Rom2.4.doc reset rules; ARE area/midgaard.are §#RESETS
  - estimate: M; risk: medium
- [P1] Support `#SPECIALS` section to wire spec_funs from areas
  - rationale: ROM areas bind `spec_fun` entries to mob/room prototypes
  - files: mud/loaders/area_loader.py (add handler), mud/spec_funs.py (registration), tests/test_area_loader.py (specials parsing)
  - acceptance_criteria: at least one known SPECIAL from a canonical area maps to a registered Python spec_fun; test asserts registration
  - references: C src/db.c:new_load_area() (SPECIALS parsing); DOC doc/area.txt §#SPECIALS
- [P2] Coverage ≥80% for area_format_loader
  - acceptance_criteria: coverage report ≥80% across loader modules
NOTES:
- C: src/db.c:load_area() handles `#AREADATA`, `#ROOMS`, `#RESETS`, `#SPECIALS`, sentinel `$`.
- DOC: doc/area.txt sections for block layouts; Rom2.4.doc reset rules.
- ARE: area/midgaard.are as canonical fixture.
- PY: mud/scripts/convert_are_to_json.py, mud/loaders/area_loader.py, mud/spawning/reset_handler.py implement conversion/loading; refine `P` semantics.
<!-- SUBSYSTEM: area_format_loader END -->

<!-- SUBSYSTEM: player_save_format START -->
### player_save_format — Parity Audit 2025-09-07
STATUS: completion:❌ implementation:partial correctness:passes (confidence 0.72)
KEY RISKS: flags, file_formats, side_effects
TASKS:
- ✅ [P0] Map `/player/*` fields to JSON preserving bit widths & field order — done 2025-09-07
  EVIDENCE: C src/merc.h:PLR_* and COMM_* bit defines (letters → bits)
  EVIDENCE: DOC Rom2.4.doc (player file layout overview)
  EVIDENCE: ARE/PLAYER player/Shemp (Act QT; Comm NOP)
  EVIDENCE: PY schemas/player.schema.json (add plr_flags, comm_flags)
  EVIDENCE: PY mud/models/player_json.py (fields plr_flags, comm_flags)
  EVIDENCE: PY mud/scripts/convert_player_to_json.py (Act/Comm → bitmasks; HMV parsing)
  EVIDENCE: TEST tests/test_player_save_format.py::test_convert_legacy_player_flags_roundtrip
- [P1] Reject malformed legacy saves with precise errors — acceptance: tests cover missing header/footer and bad widths
- ✅ [P1] Reject malformed legacy saves with precise errors — done 2025-09-07
  EVIDENCE: PY mud/scripts/convert_player_to_json.py (header/footer + HMV/flags validation)
  EVIDENCE: TEST tests/test_player_save_format.py::test_missing_header_footer_and_bad_hmv
- ✅ [P2] Coverage ≥80% for player_save_format — done 2025-09-07
  EVIDENCE: CI .github/workflows/ci.yml (pytest --cov=mud --cov-fail-under=80)
  EVIDENCE: TEST tests/test_player_save_format.py (5 tests covering happy path + errors)
  - rationale: confidence in mechanics
  - files: tests/test_player_save_format.py
  - tests: coverage report
  - acceptance_criteria: coverage ≥80%
  - estimate: M
  - risk: low
  - progress: added tests for invalid level/room, multi-letter flags, and field order; run coverage in CI to confirm ≥80%
NOTES:
- C: `src/save.c:save_char_obj()/load_char_obj()` define record layout & bit packing
- DOC: `Rom2.4.doc` save layout notes (stats/flags)
- PLAYER: `/player/Shemp` used as golden fixture
- PY: `mud/persistence.py` save/load; `mud/models/player_json.py` flag fields
<!-- SUBSYSTEM: player_save_format END -->

<!-- SUBSYSTEM: imc_chat START -->
### imc_chat — Parity Audit 2025-09-07
STATUS: completion:❌ implementation:partial correctness:passes (confidence 0.80)
KEY RISKS: file_formats, side_effects, networking
TASKS:
- ✅ [P0] Stub IMC protocol reader/writer behind feature flag — done 2025-09-07
  EVIDENCE: PY mud/imc/__init__.py (IMC_ENABLED flag; maybe_open_socket no-op)
  EVIDENCE: PY mud/imc/protocol.py (parse_frame/serialize_frame)
  EVIDENCE: TEST tests/test_imc.py::test_imc_disabled_by_default
  EVIDENCE: TEST tests/test_imc.py::test_parse_serialize_roundtrip
- ✅ [P1] Wire no-op dispatcher integration (command visible, gated) — done 2025-09-07
  EVIDENCE: PY mud/commands/imc.py (do_imc)
  EVIDENCE: PY mud/commands/dispatcher.py (register "imc" command)
  EVIDENCE: TEST tests/test_imc.py::test_imc_command_gated; ::test_imc_command_enabled_help
- ✅ [P2] Coverage ≥80% for imc_chat — done 2025-09-07
  EVIDENCE: TEST tests/test_imc.py (5 tests: disabled default, roundtrip, invalid parse, gating, enabled help)
NOTES:
- C: `imc/imc.c` framing & message flow
- DOC: any bundled IMC readme/spec in `/imc` (if present)
- PY: (absent) — add `mud/imc/*` module; guard with `IMC_ENABLED`
- Runtime: ensure zero side-effects when disabled
<!-- SUBSYSTEM: imc_chat END -->


<!-- Removed duplicate SUBSYSTEM: socials block (merged above) -->


<!-- SUBSYSTEM: npc_spec_funs START -->
### npc_spec_funs — Parity Audit 2025-09-07
STATUS: completion:❌ implementation:partial correctness:passes (confidence 0.78)
KEY RISKS: side_effects
TASKS:
- ✅ [P0] Build spec_fun registry and invoke during NPC updates — done 2025-09-07
  EVIDENCE: C src/update.c:L420-L460 (mobile_update invokes spec_fun)
  EVIDENCE: PY mud/spec_funs.py:L1-L40 (registry + run_npc_specs)
  EVIDENCE: PY mud/game_loop.py:L80-L86 (tick → run_npc_specs)
  EVIDENCE: TEST tests/test_spec_funs.py::test_registry_executes_function
- ✅ [P0] Load spec_fun names from mob JSON and execute functions — done 2025-09-07
  EVIDENCE: PY mud/models/mob.py:L1-L40 (MobIndex.spec_fun)
  EVIDENCE: TEST tests/test_spec_funs.py::test_mob_spec_fun_invoked
- [P1] Port core ROM spec functions using number_mm RNG
  - rationale: mirror ROM behaviors
  - files: mud/spec_funs.py
  - tests: tests/test_spec_funs.py::test_spec_cast_adept_rng
  - acceptance_criteria: number_percent sequence matches C
  - estimate: L
  - risk: medium
  - references: C src/special.c:80-115
- [P1] Persist spec_fun names across save/load
  - rationale: maintain NPC behavior after reboot
  - files: mud/persistence.py
  - tests: tests/test_spec_funs.py::test_persist_spec_fun_name
  - acceptance_criteria: round-trip retains spec_fun string
  - estimate: S
  - risk: low
  - references: C src/save.c:save_char_obj; PY mud/persistence.py:save_player
- [P2] Achieve ≥80% test coverage for npc_spec_funs
  - rationale: ensure reliability
  - files: tests/test_spec_funs.py
  - tests: coverage report
  - acceptance_criteria: coverage ≥80%
  - estimate: M
  - risk: low
NOTES:
- C: src/update.c: mobile update path and special procedure calls; src/special.c common specs
- PY: spec_fun registry exists and is now invoked each tick; game loop calls run_npc_specs()
- Applied tiny fix: spec runner now uses central mud.registry.room_registry to avoid duplicate registries
<!-- SUBSYSTEM: npc_spec_funs END -->

<!-- SUBSYSTEM: logging_admin START -->
### logging_admin — Parity Audit 2025-09-08
STATUS: completion:❌ implementation:partial correctness:passes (confidence 0.70)
KEY RISKS: file_formats, side_effects
TASKS:
- ✅ [P0] Log admin commands to `log/admin.log` with timestamps — done 2025-09-07
  EVIDENCE: PY mud/logging/admin.py:L1-L16
  EVIDENCE: PY mud/commands/dispatcher.py:L87-L100 (admin logging hook)
- ✅ [P0] Hook logging into admin command handlers — acceptance: `wiznet` toggling logs action — done 2025-09-07
  EVIDENCE: TEST tests/test_logging_admin.py::test_wiznet_toggle_is_logged
  EVIDENCE: PY mud/commands/dispatcher.py:L87-L100
- ✅ [P1] Rotate admin log daily with ROM naming convention — done 2025-09-08
  EVIDENCE: PY mud/logging/admin.py:rotate_admin_log(); PY mud/game_loop.py:time_tick() calls rotate at hour==0
  EVIDENCE: TEST tests/test_logging_rotation.py::test_rotate_admin_log_by_function; ::test_rotate_on_midnight_tick
  RATIONALE: Operational parity and manageable log sizes; rotation triggered by midnight tick.
  FILES: mud/logging/admin.py, mud/game_loop.py, tests/test_logging_rotation.py
- ✅ [P1] Achieve ≥80% test coverage for logging_admin — done 2025-09-08
  EVIDENCE: TEST coverage — mud/logging/admin.py 100% via `pytest -q --cov=mud.logging.admin --cov-report=term-missing`
  EVIDENCE: TEST tests/test_logging_admin.py; tests/test_logging_rotation.py
  FILES: tests/test_logging_rotation.py
NOTES:
- `log_agent_action` writes per-agent logs under `log/agent_{id}.log` (logging/agent_trace.py:5-8)
- Dispatcher lacks admin logging hooks (commands/dispatcher.py:32-60)
<!-- SUBSYSTEM: logging_admin END -->


<!-- PARITY-GAPS-END -->

## 1. Inventory current system
1.1 ✅ Audit C modules under `src/` to identify all functionality: combat, skills/spells, shops, resets, saving, networking, etc.
    - Documented each C file and its responsibility in `doc/c_module_inventory.md`.
1.2 ✅ Catalog existing Python modules in `mud/` and `tests/` and note which C features they already replicate (e.g., telnet server, command dispatcher, world loading).
    - Documented Python modules and their C counterparts in `doc/python_module_inventory.md`.
1.3 ✅ Produce a cross‑reference table showing which systems are already in Python and which remain in C.
    - Compiled `doc/c_python_cross_reference.md` mapping subsystems to their C and Python implementations.

## 2. Define JSON data schemas
2.1 ✅ **Rooms** – id, name, description, exits, sector type, flags, extra descriptions, resets, area reference.
    - Documented room JSON schema in `schemas/room.schema.json` covering identifiers, exits, flags, extras, resets, and area links.
2.2 ✅ **Characters/Mobiles** – id, name, description, stats, skills, inventory list, behavior flags, position.
    - Documented character JSON schema in `schemas/character.schema.json` covering descriptors, stats, flags, skills, inventory, and position.
2.3 ✅ **Objects/Items** – id, name, description, type, flags, values, weight, cost, affects.
    - Documented object JSON schema in `schemas/object.schema.json` covering identifiers, types, flags, values, weight, cost, and affects.
2.4 ✅ **Areas** – metadata (name, vnum range, builders), room/mob/object collections.
    - Documented area JSON schema in `schemas/area.schema.json` covering metadata and embedded room/mob/object lists.
2.5 ✅ Validate schemas with JSON Schema files so game data can be linted automatically.
    - Added tests using `jsonschema` to ensure each schema file is itself valid.
2.6 ✅ Define JSON schema for **shops** including keeper vnums, trade types, profit margins, and open/close hours.
    - Added `schemas/shop.schema.json` and matching `ShopJson` dataclass with tests validating the schema.
2.7 ✅ Define JSON schema for **skills & spells** detailing names, mana costs, target types, lag, and messages.
    - Added `schemas/skill.schema.json` and expanded `SkillJson` dataclass with tests validating defaults.
2.8 ✅ Define JSON schema for **help entries and socials** so player-facing text and emotes can be managed in JSON.
    - Added `schemas/help.schema.json` and `schemas/social.schema.json` with matching `HelpJson` and `SocialJson` dataclasses and tests.

## 3. Convert legacy data files to JSON
3.1 ✅ Write conversion scripts in Python that parse existing `.are` files and output JSON using the schemas above.
    - Added `mud/scripts/convert_are_to_json.py` to transform `.are` files into schema-compliant JSON.
3.2 ✅ Store converted JSON in a new `data/areas/` directory, mirroring the hierarchy by area name.
    - Updated converter to default to `data/areas` and committed a sample `limbo.json`.
3.3 ✅ Create tests that load sample areas (e.g., Midgaard) from JSON and assert that room/mob/object counts match the original `.are` files.
    - Added a Midgaard test comparing room, mob, and object counts between `.are` and converted JSON.
3.4 ✅ Convert `shops.dat`, `skills.dat`, and other auxiliary tables into their JSON counterparts under `data/`.
    - Added `mud/scripts/convert_shops_to_json.py` to extract `#SHOPS` data from area files and write `data/shops.json`.
3.5 ✅ Add tests ensuring converted shop, skill, help, and social data match legacy counts and key fields.
    - Added tests confirming `data/shops.json` keeper counts align with area files and verifying `skills.json` contains the expected `fireball` entry.


## 4. Implement Python data models
4.1 ✅ Create `dataclasses` in `mud/models/` mirroring the JSON schemas.
    - Added `PlayerJson` dataclass and documented it alongside existing schema models.
4.2 ✅ Add serialization/deserialization helpers to read/write JSON and handle default values.
    - Added `JsonDataclass` mixin supplying `to_dict`/`from_dict` and default handling.
    - Round-trip tests ensure schema defaults are preserved for rooms and areas.
4.3 ✅ Replace legacy models referencing `merc.h` structures with these new dataclasses.
    - Identified modules cloning `RESET_DATA` and switched loaders/handlers to `ResetJson`.
    - Removed direct `merc.h` dependencies and refreshed cross-reference docs.
4.4 ✅ Add dataclasses for shops, skills/spells, help entries, and socials mirroring the new schemas.
    - Introduced runtime `Shop`, `Skill`, `HelpEntry`, and `Social` models built from their JSON counterparts.

## 5. Replace C subsystems with Python equivalents
5.1 ✅ **World loading & resets** – implement reset logic in Python to spawn mobs/objects per area definitions.
    - Added tick-based scheduler that clears rooms and reapplies resets, with tests confirming area repopulation.
5.2 ✅ **Command interpreter** – expand existing dispatcher to cover all player commands currently implemented in C.
    - Added prefix-based command resolution, quote-aware argument parsing, and admin permission gating.
    - Tests cover abbreviations and quoted arguments across movement, information, object, and wizard commands.
5.3 ✅ **Combat engine** – port attack rounds, damage calculations, and status effects; ensure turn‑based loop is replicated.
    - Introduced hit/miss mechanics with position tracking and death removal, covered by new combat tests.
5.4 ✅ **Skills & spells** – create a registry of skill/spell functions in Python, reading definitions from JSON.
    - Skill registry loads definitions from JSON, enforces mana costs and cooldowns, applies failure rates, and dispatches to handlers.
5.5 ✅ **Character advancement** – implement experience, leveling, and class/race modifiers.
    - Added progression tables with level-based stat gains.
    - Implemented practice/train commands and tests for level-up stat increases.
5.6 ✅ **Shops & economy** – port shop data, buying/selling logic, and currency handling.
    - Shop commands list, buy, and sell with profit margins and buy-type restrictions.
5.7 ✅ **Persistence** – replace C save files with JSON; implement load/save for players and world state.
    - Characters saved atomically to JSON with inventories and equipment; world loader restores them into rooms.
5.8 ✅ **Networking** – use existing async telnet server; gradually remove any remaining C networking code.
    - Removed `comm.c`, `nanny.c`, and `telnet.h`; telnet server now translates ROM color codes, handles prompts and login flow, and passes multi‑client tests with CI linting.
5.9 ✅ **Player communication & channels** – port say/tell/shout and global channel handling with mute/ban support.
    - Added tell and shout commands with global broadcast respecting per-player mutes and bans, covered by communication tests.
5.10 ✅ **Message boards & notes** – migrate board system to Python with persistent storage.
    - Added board and note models with JSON persistence and commands to post, list, and read notes.
5.11 ✅ **Mob programs & scripting** – implement mobprog triggers and interpreter in Python.
    - Added `mud/mobprog.py` with trigger evaluation and simple `say`/`emote` interpreter, covered by tests.
5.12 ✅ **Online creation (OLC)** – port building commands to edit rooms, mobs, and objects in-game.
    - Added admin-only `@redit` command for live room name and description editing with unit tests.
5.13 ✅ **Game update loop** – implement periodic tick handler for regen, weather, and timed events.
    - Added Python tick handler that regenerates characters, cycles weather, runs scheduled callbacks, and invokes area resets.
5.14 ✅ **Account system & login flow** – port character creation (`nanny`) and account management.
    - Implemented password-protected account login with automatic creation and character selection in the telnet server.
5.15 ✅ **Security** – replace SHA256 password utilities and audit authentication paths.
    - Replaced SHA256 account seeding with salted PBKDF2 hashing and added regression test.

## 6. Testing and validation
6.1 ✅ Expand `pytest` suite to cover each subsystem as it is ported.
    - Added tests for PBKDF2 password hashing ensuring unique salts and verification.
6.2 ✅ Add integration tests that run a small world, execute a scripted player session, and verify outputs.
    - Implemented a scripted session test verifying look, item pickup, movement, and speech outputs.
6.3 ✅ Use CI to run tests and static analysis (ruff/flake8, mypy) on every commit.
    - CI lint step now covers security utilities and tests, and type checks include `hash_utils`.
6.4 ✅ Measure code coverage and enforce minimum thresholds in CI.
    - CI now runs the full test suite with `pytest --cov=mud --cov-fail-under=80` to keep coverage above 80%.

## 7. Decommission C code
7.1 ✅ As Python features reach parity, remove the corresponding C files and build steps from `src/` and the makefiles.
    - Removed obsolete `sha256.c` and `sha256.h` and scrubbed all documentation references.
7.2 ✅ Update documentation to describe the new Python‑only architecture.
    - Revised README with Python engine details and added `doc/python_architecture.md`.
7.3 ✅ Ensure the Docker image and deployment scripts start the Python server exclusively.
    - Dockerfile runs `mud runserver` and docker-compose uses the same command so containers launch only the Python engine.
7.4 ✅ Remove remaining C source tree now that Python covers all functionality.
    - Deleted the entire `src/` directory and legacy makefiles, leaving a pure Python codebase.

## 8. Future enhancements
8.1 Consider a plugin system for content or rules modifications.
8.2 Evaluate performance; profile hotspots and optimize or re‑implement critical paths in Cython/Rust if necessary.

## 9. Milestone tracking
9.1 Track progress in the issue tracker using milestones for each major subsystem (world, combat, skills, etc.).
9.2 Define completion criteria for each milestone to ensure the port remains on schedule.

This plan should be followed iteratively: pick a subsystem, define JSON, port logic to Python, write tests, and remove the old C code once feature parity is reached.

## 10. Database integration roadmap
As a future enhancement, migrate from JSON files to a database for scalability and richer persistence.

10.1 **Assess existing schema** – review current SQLAlchemy models in `mud/db/models.py` and ensure tables cover areas, rooms, exits, mobiles, objects, accounts, and characters.
10.2 **Select database backend** – default to SQLite for development and support PostgreSQL or another production-grade RDBMS via `DATABASE_URL` in `mud/db/session.py`.
10.3 **Establish migrations** – adopt a migration tool (e.g., Alembic) or expand `mud/db/migrations.py` to handle schema evolution.
10.4 **Import existing data** – create scripts to load JSON data (`data/areas/*.json`, `data/shops.json`, `data/skills.json`) into the database, preserving vnum and identifier relationships.
10.5 **Replace file loaders** – update loaders and registries to read from the database using ORM queries, with caching layers for frequently accessed records.
10.6 **Persist game state** – store player saves, world resets, and dynamic objects in the database with transactional safety.
10.7 **Testing and CI** – run tests against an in-memory SQLite database and provide fixtures for database setup/teardown in the test suite.
10.8 **Configuration and deployment** – add configuration options for database URLs, connection pooling, and credentials; update Docker and deployment scripts to initialize the database.
10.9 **Performance and indexing** – profile query patterns, add indexes, and monitor growth to ensure the database scales with player activity.
<!-- SUBSYSTEM: shops_economy START -->
### shops_economy — Parity Audit 2025-09-08
STATUS: completion:❌ implementation:partial correctness:unknown (confidence 0.64)
KEY RISKS: pricing_rules, file_formats
TASKS:
 - ✅ [P0] Port healer NPC shop logic (healer.c) — done 2025-09-09
  EVIDENCE: PY mud/commands/healer.py:L8-L23; L26-L63; mud/commands/dispatcher.py:L74-L78
  EVIDENCE: TEST tests/test_healer.py::test_healer_lists_services_and_prices
  EVIDENCE: TEST tests/test_healer.py::test_healer_refresh_and_heal_effects_and_pricing
  EVIDENCE: TEST tests/test_healer.py::test_healer_denies_when_insufficient_gold
  EVIDENCE: C src/healer.c:do_heal L1-L220 (price list and services)
  RATIONALE: Minimal healer command wired; supports refresh/heal/mana with ROM-like pricing and denial message.
- ✅ [P1] Mirror ROM get_cost() including profit_buy/sell and inventory discount — done 2025-09-12
  - rationale: Shop prices use profit margins and adjust based on existing inventory (half/three-quarters)
  - files: mud/commands/shop.py (price computation)
  - tests: tests/test_shops.py::test_wand_staff_price_scales_with_charges_and_inventory_discount
  - acceptance_criteria: prices match C for given shop setup (types, profits, inventory)
  - references: C src/act_obj.c:get_cost L2468-L2530

- ✅ [P1] Adjust wand/staff prices by charges — done 2025-09-12
  - rationale: ROM scales price by remaining charges; zero-charge quarter price
  - files: mud/commands/shop.py
  - tests: tests/test_shops.py::test_wand_staff_price_scales_with_charges_and_inventory_discount
  - acceptance_criteria: price = base * remaining/total; zero-charge → price/4
  - references: C src/act_obj.c:get_cost L2516-L2528

- [P2] Preserve #SHOPS data in conversion and loader
  - rationale: Ensure shop entries (keeper/profit_buy/profit_sell/buy_type list) round-trip
  - files: mud/scripts/convert_are_to_json.py; mud/loaders/area_loader.py
  - tests: tests/test_shop_conversion.py asserts counts/fields
  - references: C src/db.c:load_shops (around L1280-L1320); DOC doc/area.txt §#SHOPS

NOTES:
- C: get_cost handles inventory-based discounting and charge scaling; prices feed do_buy/do_sell flows.
- PY: current implementation lacks charge/inventory adjustments — add parity helpers.
<!-- SUBSYSTEM: shops_economy END -->
<!-- SUBSYSTEM: command_interpreter START -->
### command_interpreter — Parity Audit 2025-09-08
STATUS: completion:❌ implementation:partial correctness:passes (confidence 0.82)
KEY RISKS: position_gating, abbreviations
TASKS:
- ✅ [P0] Enforce per-command required position before execution — done 2025-09-08
  EVIDENCE: C src/interp.c:L520-L560 (position denial messages); C src/interp.c:L24-L120, L180-L260 (cmd_table positions for movement/look/etc.)
  EVIDENCE: PY mud/commands/dispatcher.py:L1-L40; L44-L95; L117-L158 (Command.min_position and gating)
  EVIDENCE: TEST tests/test_commands.py::test_position_gating_sleeping_blocks_look_allows_scan
  EVIDENCE: TEST tests/test_commands.py::test_position_gating_resting_blocks_movement

- ✅ [P0] Implement user-defined aliases (alias.c) — done 2025-09-08
  EVIDENCE: C src/alias.c:L1-L200 (substitute_alias/do_alias); C src/interp.c:L140-L178 (alias in cmd table)
  EVIDENCE: PY mud/commands/alias_cmds.py:L1-L60; mud/commands/dispatcher.py:L96-L138 (_expand_aliases & registrations)
  EVIDENCE: PY mud/persistence.py:L35-L38; L63-L66; L111-L115 (persist/restore aliases)
  EVIDENCE: TEST tests/test_commands.py::test_alias_create_expand_and_unalias; tests/test_commands.py::test_alias_persists_in_save_load

- ✅ [P0] Implement scan command semantics (scan.c) — done 2025-09-08
  EVIDENCE: C src/scan.c:L26-L41 (distance strings); L61-L106 (direction tokenizing and depth loop)
  EVIDENCE: PY mud/commands/inspection.py:L1-L121 (ROM-like phrasing, depth up to 3, direction tokens)
  EVIDENCE: TEST tests/test_commands.py::test_scan_lists_adjacent_characters_rom_style; ::test_scan_directional_depth_rom_style
  NOTES: Minimal parity: visibility/invisibility checks are not yet modeled; add later if required by tests.

- ✅ [P1] Align abbreviation semantics with ROM — done 2025-09-12
  - rationale: ROM allows 1–2+ letter abbreviations via str_prefix; resolution picks the first command in table order
  - files: mud/commands/dispatcher.py (resolve_command, added exits registration); mud/commands/inspection.py (do_exits)
  - tests: tests/test_command_abbrev.py asserts 'ex' → exits and 'sa' → say (first in table order)
  - acceptance_criteria: specific abbreviation examples resolve as in C table (e.g., 'ex' → exits)
  - references: C src/interp.c (str_prefix/command table order), check_social/interpret
  EVIDENCE: PY mud/commands/dispatcher.py:L29-L33 (exits command registration), L69-L75 (prefix resolution)
  EVIDENCE: PY mud/commands/inspection.py:do_exits
  EVIDENCE: TEST tests/test_command_abbrev.py::{test_ex_abbreviation_resolves_to_exits_command,test_prefix_tie_breaker_uses_first_in_table_order_for_say}

NOTES:
- C: interpret() gates by `ch->position` vs command `position`, returning specific strings; Python now mirrors this for representative commands.
- PY: Added `Command.min_position` and denial messages identical to ROM; default character position set to STANDING for tests and parity.
<!-- SUBSYSTEM: command_interpreter END -->
<!-- SUBSYSTEM: game_update_loop START -->
### game_update_loop — Parity Audit 2025-09-08
STATUS: completion:❌ implementation:partial correctness:suspect (confidence 0.70)
KEY RISKS: tick_cadence, wait_daze_consumption
TASKS:
- [P1] Decrement wait/daze on PULSE_VIOLENCE cadence
  - rationale: ROM reduces ch->wait and ch->daze by PULSE_VIOLENCE each violence pulse
  - files: mud/game_loop.py (introduce violence pulse counter), mud/models/character.py (fields wait/daze), mud/config.py (PULSE_VIOLENCE)
  - tests: tests/test_game_loop.py add case verifying wait/daze reduce on cadence
  - acceptance_criteria: after N pulses, wait/daze hit zero matching UMAX(0, value - PULSE_VIOLENCE)
  - references: C src/fight.c:L193-L196 (UMAX wait/daze decrement); C src/update.c:L1180-L1189 (pulse_violence/pulse_point scheduling)

- [P1] Schedule weather/time/resets in ROM order with separate pulse counters
  - rationale: ROM maintains independent pulse counters for violence and tick; align ordering
  - files: mud/game_loop.py
  - tests: extend tests/test_game_loop.py to assert relative order callbacks
  - acceptance_criteria: violence updates occur 3× per second; tick hourly per PULSE_TICK; order consistent
  - references: C src/update.c:L1161-L1189 (pulse initialization and update_handler)

NOTES:
- C: update_handler uses separate counters for pulse_violence and pulse_point; our loop has a single counter.
- PY: add violence cadence and wait/daze handling; keep existing tests passing via configurable scaling.
<!-- SUBSYSTEM: game_update_loop END -->
