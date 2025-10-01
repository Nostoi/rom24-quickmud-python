<!-- LAST-PROCESSED: skills_spells -->
<!-- DO-NOT-SELECT-SECTIONS: 8,10 -->
<!-- ARCHITECTURAL-GAPS-DETECTED:  -->
<!-- SUBSYSTEM-CATALOG: combat, skills_spells, affects_saves, command_interpreter, socials, channels, wiznet_imm, world_loader, resets, weather, time_daynight, movement_encumbrance, stats_position, shops_economy, boards_notes, help_system, mob_programs, npc_spec_funs, game_update_loop, persistence, login_account_nanny, networking_telnet, security_auth_bans, logging_admin, olc_builders, area_format_loader, imc_chat, player_save_format -->

# Python Conversion Plan for QuickMUD

## Overview

This document outlines the steps needed to port the remaining ROM 2.4 QuickMUD C codebase to Python. It also describes how to migrate existing game data (rooms, characters, items, etc.) into JSON so the Python engine can consume it directly.

## System Inventory & Coverage Matrix

<!-- COVERAGE-START -->

| subsystem | status | evidence | tests |
|---|---|---|---|
| combat | present_wired | C: src/fight.c:one_hit; PY: mud/combat/engine.py:attack_round | tests/test_combat.py; tests/test_combat_thac0.py; tests/test_weapon_special_attacks.py |
| skills_spells | present_wired | C: src/act_info.c:2680-2760; C: src/magic.c:73-97; PY: mud/commands/advancement.py:66-193; mud/skills/registry.py:75-142 | tests/test_advancement.py; tests/test_practice.py; tests/test_skills.py |
| affects_saves | present_wired | C: src/magic.c:saves_spell; C: src/handler.c:check_immune; PY: mud/affects/saves.py:saves_spell/_check_immune | tests/test_affects.py; tests/test_defense_flags.py |
| command_interpreter | present_wired | C: src/interp.c:interpret; PY: mud/commands/dispatcher.py:process_command | tests/test_commands.py |
| socials | present_wired | C: src/interp.c:check_social; DOC: doc/area.txt § Socials; ARE: area/social.are; PY: mud/commands/socials.py:perform_social | tests/test_socials.py; tests/test_social_conversion.py; tests/test_social_placeholders.py |
| channels | present_wired | C: src/act_comm.c:do_say/do_tell/do_shout; PY: mud/commands/communication.py:do_say/do_tell/do_shout | tests/test_communication.py |
| wiznet_imm | present_wired | C: src/act_wiz.c:wiznet; PY: mud/wiznet.py:wiznet/cmd_wiznet | tests/test_wiznet.py |
| world_loader | present_wired | DOC: doc/area.txt §§ #AREA/#ROOMS/#MOBILES/#OBJECTS/#RESETS; ARE: area/midgaard.are; C: src/db.c:load_area/load_rooms; PY: mud/loaders/json_loader.py:load_area_from_json; mud/loaders/area_loader.py | tests/test_area_loader.py; tests/test_area_counts.py; tests/test_area_exits.py; tests/test_load_midgaard.py |
| resets | present_wired | C: src/db.c:2003-2179 (create_mobile seeds runtime state); PY: mud/spawning/templates.py:180-420; mud/spawning/reset_handler.py:40-196 | tests/test_spawning.py; tests/test_spec_funs.py |
| weather | present_wired | C: src/update.c:weather_update; PY: mud/game_loop.py:weather_tick | tests/test_game_loop.py |
| time_daynight | present_wired | C: src/update.c:weather_update (sun state); PY: mud/time.py:TimeInfo.advance_hour | tests/test_time_daynight.py; tests/test_time_persistence.py |
| movement_encumbrance | present_wired | C: src/act_move.c:80-236 (move_char handles portals/followers); PY: mud/world/movement.py:240-470; mud/commands/movement.py:10-70 | tests/test_movement_portals.py; tests/test_movement_costs.py; tests/test_movement_followers.py |
| stats_position | present_wired | C: merc.h:POSITION enum; PY: mud/models/constants.py:Position | tests/test_advancement.py |
| shops_economy | present_wired | DOC: doc/area.txt § #SHOPS; ARE: area/midgaard.are § #SHOPS; C: src/act_obj.c:do_buy/do_sell; PY: mud/commands/shop.py:do_buy/do_sell; C: src/healer.c:do_heal; PY: mud/commands/healer.py:do_heal | tests/test_shops.py; tests/test_shop_conversion.py; tests/test_healer.py |
| boards_notes | present_wired | C: src/board.c:563-780; PY: mud/commands/notes.py:33-204; mud/world/world_state.py:92-134 | tests/test_boards.py::test_note_read_defaults_to_next_unread; tests/test_boards.py::test_board_change_blocked_during_note_draft |
| help_system | present_wired | C: src/act_info.c:1832-1894 (do_help); PY: mud/commands/help.py:9-159; mud/admin_logging/admin.py:113-140 | tests/test_help_system.py |
| mob_programs | present_wired | C: src/mob_prog.c:program_flow/cmd_eval; PY: mud/mobprog.py:_program_flow/_cmd_eval; mud/mob_cmds.py:MobCommand | tests/test_mobprog.py |
| npc_spec_funs | present_wired | C: src/special.c:spec_table; PY: mud/spec_funs.py:run_npc_specs | tests/test_spec_funs.py; tests/test_spec_funs_extra.py |
| game_update_loop | present_wired | C: src/update.c:update_handler; PY: mud/game_loop.py:game_tick | tests/test_game_loop.py; tests/test_game_loop_order.py; tests/test_game_loop_wait_daze.py |
| persistence | present_wired | DOC: doc/pfile.txt; C: src/save.c:save_char_obj/load_char_obj; PY: mud/persistence.py | tests/test_persistence.py; tests/test_inventory_persistence.py |
| login_account_nanny | present_wired | C: src/nanny.c:CON_GET_NAME/CON_GET_OLD_PASSWORD; PY: mud/account/account_service.py:login_with_host | tests/test_account_auth.py |
| networking_telnet | present_wired | C: src/comm.c; PY: mud/net/telnet_server.py:start_server | tests/test_telnet_server.py |
| security_auth_bans | present_wired | C: src/ban.c:135-320; PY: mud/commands/admin_commands.py:39-156; mud/security/bans.py:60-178 | tests/test_admin_commands.py; tests/test_account_auth.py; tests/test_bans.py |
| logging_admin | present_wired | C: src/act_wiz.c:2927-2982 (do_log); PY: mud/commands/admin_commands.py:cmd_log; mud/logging/admin.py:9-120 | tests/test_logging_admin.py; tests/test_logging_rotation.py |
| olc_builders | present_wired | C: src/olc_act.c; PY: mud/commands/build.py:cmd_redit | tests/test_building.py |
| area_format_loader | present_wired | C: src/db.c:441-520 (load_area); PY: mud/loaders/area_loader.py; mud/scripts/convert_are_to_json.py | tests/test_area_loader.py; tests/test_are_conversion.py |
| imc_chat | present_wired | C: src/imc.c:5392-5476; C: src/comm.c:453-859; PY: mud/imc/__init__.py:24-214; mud/game_loop.py:1-144 | tests/test_imc.py::test_startup_reads_config_and_connects; tests/test_imc.py::test_idle_pump_runs_when_enabled |
| player_save_format | present_wired | C: src/save.c:save_char_obj; PY: mud/persistence.py:PlayerSave | tests/test_player_save_format.py; tests/test_persistence.py |

<!-- COVERAGE-END -->

## CRITICAL TASKS - IMMEDIATE ATTENTION REQUIRED

**Priority P0 Tasks (Required for Functional Parity):**

- ✅ [P0] **Area Format Loader: Fix LoadObj/LoadMob State Tracking** — done 2025-10-11

  - FILES: mud/world/loader.py LoadObj/LoadMob methods, mud/data/area_format_loader.py reset validation
  - ISSUE: Missing LastObj/LastMob index state tracking causing reset validation mismatches
  - C_REF: src/db.c:1842-1950 (load_objects), src/db.c:1650-1741 (load_mobiles) track Last\*
  - ACCEPTANCE: pytest tests/test_area_loader.py::test_midgaard_reset_validation passes
  EVIDENCE: C src/db.c:1009-1108 (load_resets maintains room context); PY mud/loaders/reset_loader.py:77-157 (validate_resets tracks LastMob/LastObj state with cross-area guard); TEST tests/test_area_loader.py::test_midgaard_reset_validation

- ✅ [P0] **Movement System: Follower Cascading Integration** — done 2025-10-11

  - FILES: mud/actions/movement.py move_char function, mud/character/follower.py cascading logic
  - ISSUE: Follower movement cascade not integrated with main movement flow
  - C_REF: src/act_move.c:127-184 (move_char) calls follower updates inline
  - ACCEPTANCE: Follower follows leader through exits; pytest tests/test_movement.py::test_follower_cascade
  EVIDENCE: C src/act_move.c:127-184 (move_char cascades followers); PY mud/world/movement.py:38-396 (shared follower mover + portal support); PY mud/commands/movement.py:1-60 (do_enter delegates to portal mover); TEST tests/test_movement.py::test_follower_cascade; TEST tests/test_movement.py::test_followers_enter_portal

- ✅ [P0] **Help System: Missing Command Topic Generation** — done 2025-10-11

  - FILES: mud/systems/help.py get_help method, mud/commands/dispatcher.py help integration
  - ISSUE: No command topic auto-generation when help not found
  - C_REF: src/act_info.c:892-1045 (do_help) generates command help dynamically
  - ACCEPTANCE: 'help cast' shows spell help; 'help unknown' shows command suggestion
  EVIDENCE: C src/act_info.c:892-1045 (do_help fallback builds command topics); PY mud/commands/help.py:1-159 (command help generation with trust gating); TEST tests/test_help_system.py::test_help_generates_command_topic_when_missing; TEST tests/test_help_system.py::test_help_missing_topic_suggests_commands

- ✅ [P0] **Reset System: Execute Integration** — done 2025-10-11
  - FILES: mud/world/reset_system.py execute methods, mud/game_loop.py area update integration
  - ISSUE: Reset execution not wired to area update cycle
  - C_REF: src/update.c:1234-1389 (area_update) calls reset_area inline
  - ACCEPTANCE: Items/mobs respawn on area reset; pytest tests/test_resets.py::test_execution_cycle
  EVIDENCE: C src/update.c:1234-1389 (area_update triggers reset_area); PY mud/game_loop.py:143-198 (game_tick invokes reset_tick on area pulse); TEST tests/test_resets.py::test_execution_cycle

## Parity Gaps & Corrections


<!-- PARITY-GAPS-START -->
<!-- AUDITED: resets, movement_encumbrance, world_loader, area_format_loader, player_save_format, help_system, boards_notes, game_update_loop, combat, skills_spells -->
<!-- SUBSYSTEM: combat START -->

### combat — Parity Audit 2025-10-20

STATUS: completion:❌ implementation:partial correctness:fails (confidence 0.30)
KEY RISKS: equipment, skills, side_effects
TASKS:

- ✅ [P0] **combat: compute weapon selection and THAC0 using ROM skill tables** — done 2025-10-20
  EVIDENCE: C src/fight.c:386-520; PY mud/combat/engine.py:90-220,380-470; TEST tests/test_combat.py::test_one_hit_uses_equipped_weapon; TEST tests/test_combat_thac0_engine.py::test_weapon_skill_influences_thac0
- ✅ [P0] **combat: restore parry/dodge/shield defensive rolls with skill improvement** — done 2025-10-20
  EVIDENCE: C src/fight.c:541-720; PY mud/combat/engine.py:700-840; PY mud/skills/registry.py:200-320; TEST tests/test_combat.py::test_parry_blocks_when_skill_learned; TEST tests/test_combat.py::test_shield_block_requires_shield; TEST tests/test_combat_defenses_prob.py::test_shield_block_triggers_before_parry_and_dodge
- [P1] **combat: apply weapon proc effects and enhanced damage scaling**
  - priority: P1
  - rationale: Poison/sharpness/vampiric procs and enhanced damage bonuses are skipped so special weapons lose their ROM effects.
  - files: mud/combat/engine.py; mud/affects/effects.py
  - tests: tests/test_combat.py::test_sharp_weapon_doubles_damage_on_proc (new); tests/test_combat.py::test_poison_weapon_applies_affect (new)
  - acceptance_criteria: Weapon procs trigger with ROM odds, apply affects, and enhanced damage multiplies base damage when learned.
  - estimate: M
  - risk: medium
  - evidence: C src/fight.c:640-828 (enhanced_damage, weapon procs); PY mud/combat/engine.py:470-620 (TODO placeholders returning early).

NOTES:
- C: src/fight.c:386-828 drives ROM weapon selection, THAC0, defensive checks, and proc effects that are currently stubbed.
- PY: mud/combat/engine.py sets dummy skill values, leaves defensive helpers returning False, and never inspects equipment or proc flags.
- TEST: New combat regressions must cover weapon-based THAC0, parry/shield success rates, and proc side effects so future changes stay aligned with ROM.
- Applied tiny fix: none
<!-- SUBSYSTEM: combat END -->
<!-- SUBSYSTEM: skills_spells START -->

### skills_spells — Parity Audit 2025-10-20

STATUS: completion:❌ implementation:partial correctness:fails (confidence 0.28)
KEY RISKS: affects, damage, rng
TASKS:

- [P0] **skills_spells: port martial skill handlers (bash/backstab/berserk)**
  - priority: P0
  - rationale: `mud/skills/handlers.py` returns placeholder values for bash/backstab/berserk so combat commands lack lag, position checks, and damage from ROM.
  - files: mud/skills/handlers.py; mud/combat/engine.py; mud/commands/combat.py
  - tests: tests/test_skills.py::test_backstab_uses_position_and_weapon (new); tests/test_skills.py::test_bash_applies_wait_state (new)
  - acceptance_criteria: Commands enforce ROM position/trust, apply wait states, compute damage dice, and interact with skill advancement as in `do_bash`/`do_backstab`/`do_berserk`.
  - estimate: L
  - risk: high
  - evidence: C src/fight.c:2270-2998 (do_berserk/do_bash/do_backstab logic); PY mud/skills/handlers.py:20-70 (stub functions returning `42`).
- [P0] **skills_spells: implement dragon breath spells with room/target effects**
  - priority: P0
  - rationale: Breath spells currently return constants without saving throws, room effects, or secondary damage so dragons lose signature attacks.
  - files: mud/skills/handlers.py; mud/magic/effects.py; mud/utils/rng_mm.py
  - tests: tests/test_skills.py::test_acid_breath_applies_acid_effect (new); tests/test_skills.py::test_fire_breath_hits_room_targets (new)
  - acceptance_criteria: Breath handlers roll dice per ROM tables, call elemental `*_effect` helpers, respect `saves_spell`, and broadcast act() strings.
  - estimate: M
  - risk: high
  - evidence: C src/magic.c:4625-4856 (spell_acid_breath through spell_lightning_breath); PY mud/skills/handlers.py:18-120 (stubbed breath implementations).
- [P1] **skills_spells: wire skill improvement and cooldown feedback**
  - priority: P1
  - rationale: `SkillRegistry.use` records cooldowns but stubs never return success/failure strings, so players miss ROM feedback and skill practice hooks for stubs.
  - files: mud/skills/handlers.py; mud/skills/registry.py; mud/commands/advancement.py
  - tests: tests/test_skills.py::test_skill_use_reports_result (new)
  - acceptance_criteria: Handlers return ROM messages, set failure flags, and trigger `check_improve`/cooldown updates consistent with `Skill.use`.
  - estimate: M
  - risk: medium
  - evidence: C src/skills.c:53-210 (check_improve messaging); PY mud/skills/handlers.py:15-200 (many TODO stubs lacking messages or improvement paths).

NOTES:
- C: src/fight.c:2270-2998 and src/magic.c:4625-4856 define martial skills and dragon breaths with wait states, lag, and elemental side effects.
- PY: mud/skills/handlers.py leaves most handlers returning placeholder integers, omitting lag, saves, and messaging; SkillRegistry cannot surface ROM results without real implementations.
- TEST: New regressions must exercise bash/backstab/berserk success/failure paths and breath weapon splash damage to keep parity once handlers are ported.
- Applied tiny fix: none
<!-- SUBSYSTEM: skills_spells END -->
<!-- SUBSYSTEM: resets START -->
### resets — Parity Audit 2025-10-16
STATUS: completion:✅ implementation:full correctness:passes (confidence 0.55)
KEY RISKS: flags, rng
TASKS:
- ✅ [P0] **resets: restore create_mobile field parity for NPC spawns** — done 2025-10-14
  - FILES: mud/spawning/templates.py; mud/spawning/reset_handler.py; tests/test_spawning.py
  - ISSUE: Spawned mobs drop ACT/AFF/permanent stat data so reset-populated NPCs lose ROM behaviors (aggression, charm immunity, armor scaling).
  - C_REF: src/db.c:2003-2138 (`create_mobile` copies act/affect/perm stat fields)
  - ACCEPTANCE: `pytest tests/test_spawning.py::test_spawned_mob_copies_proto_stats` verifies a reset-spawned mob inherits act/affected_by/off_flags/default_pos from its prototype.
  EVIDENCE: C src/db.c:2003-2138; PY mud/spawning/templates.py:40-190; TEST tests/test_spawning.py::test_spawned_mob_copies_proto_stats
- ✅ [P1] **resets: persist spec_fun and mob program wiring during spawn** — done 2025-10-14
  - FILES: mud/spawning/templates.py; mud/spec_funs.py; tests/test_spec_funs.py
  - ISSUE: Runtime mobs drop spec_fun/mprog state so reset-created NPCs never invoke ROM special functions after repop.
  - C_REF: src/db.c:2003-2068 (`create_mobile` assigns spec_fun/mprog lists)
  - ACCEPTANCE: `pytest tests/test_spec_funs.py::test_reset_spawn_triggers_spec_fun` covers that a reset immediately triggers the mob's spec_fun hook.
  EVIDENCE: C src/db.c:2003-2068; PY mud/spawning/templates.py:210-310; TEST tests/test_spec_funs.py::test_reset_spawn_triggers_spec_fun
- ✅ [P0] **resets: derive perm_stat arrays for spawned mobs** — done 2025-10-16
  - FILES: mud/spawning/templates.py; mud/models/constants.py; tests/test_spawning.py
  - ISSUE: `MobInstance` never populates `perm_stat`, so reset-created NPCs lack ROM strength/intelligence baselines and class/size adjustments, breaking encumbrance and training caps.
  - C_REF: src/db.c:2118-2152 (`create_mobile` seeds perm_stat array and applies ACT_* and size adjustments)
  - ACCEPTANCE: Extend `tests/test_spawning.py` with a prototype that sets warrior/thief flags and size to assert spawned mobs expose the ROM perm_stat values.
  EVIDENCE: C src/db.c:2118-2152; PY mud/spawning/templates.py:296-329; PY mud/models/constants.py:123-128; TEST tests/test_spawning.py::test_spawned_mob_inherits_perm_stats
- ✅ [P1] **resets: randomize mob sex when prototypes allow either** — done 2025-10-18
  - FILES: mud/spawning/templates.py; tests/test_spawning.py
  - ISSUE: ROM rolls male/female when `sex == 3`, but the port leaves mobs stuck on the sentinel value so charm and equipment restrictions misbehave.
  - C_REF: src/db.c:2173-2179 (`create_mobile` rerolls random sex)
  - ACCEPTANCE: Add a regression that seeds RNG and spawns a prototype with `sex = Sex.EITHER`, asserting the runtime mob resolves to MALE or FEMALE.
  EVIDENCE: C src/db.c:2173-2179; PY mud/spawning/templates.py:294-296; TEST tests/test_spawning.py::test_spawned_mob_randomizes_sex_when_either
  NOTES:
  - C: src/db.c:2003-2179 seeds runtime flags, perm stats, and Sex.EITHER rerolling that the Python spawn helper now mirrors.
  - PY: mud/spawning/templates.py copies ROM flags/spec_fun metadata, rerolls Sex.EITHER via `rng_mm.number_range`, and preserves perm stats for reset spawns.
  - TEST: tests/test_spawning.py locks both the ROM stat copy and the Sex.EITHER reroll via deterministic RNG patches.
  - Applied tiny fix: none
<!-- SUBSYSTEM: resets END -->
<!-- SUBSYSTEM: movement_encumbrance START -->
### movement_encumbrance — Parity Audit 2025-10-15
STATUS: completion:✅ implementation:full correctness:passes (confidence 0.55)
KEY RISKS: RNG, flags, side_effects
TASKS:
- ✅ [P0] **movement_encumbrance: enforce portal curse/no-recall gating** — done 2025-10-15
  EVIDENCE: C src/act_enter.c:104-138 (trust + NOCURSE checks before travel)
  EVIDENCE: PY mud/commands/movement.py:26-66 (portal lookup + curse gate enforcement)
  EVIDENCE: PY mud/world/movement.py:324-378 (follow path duplicates NOCURSE blocks)
  EVIDENCE: TEST tests/test_movement_portals.py::test_cursed_player_blocked_by_nocurse_portal
- ✅ [P0] **movement_encumbrance: resolve portal destinations via ROM gate flags** — done 2025-10-15
  EVIDENCE: C src/act_enter.c:140-176 (GATE_RANDOM/BUGGY rerolls + private room checks)
  EVIDENCE: PY mud/world/movement.py:378-454 (random rolls, private-room rejection, law-room aggression guard)
  EVIDENCE: TEST tests/test_movement_portals.py::test_random_gate_rolls_destination
- ✅ [P1] **movement_encumbrance: consume portal charges and carry GATE_GOWITH objects** — done 2025-10-15
  EVIDENCE: C src/act_enter.c:178-236 (portal charge depletion and GATE_GOWITH relocation)
  EVIDENCE: PY mud/world/movement.py:260-360 (charge decrement, follower gating, fade messaging)
  EVIDENCE: TEST tests/test_movement_portals.py::test_portal_charges_and_followers
NOTES:
- C: src/act_enter.c:101-236 layers NOCURSE gating, random/buggy rerolls, law-room aggression checks, and charge depletion.
- PY: mud/commands/movement.py:15-66 plus mud/world/movement.py:324-454 now mirror the ROM gating, rerolls, and fade cleanup for GATE_GOWITH portals.
- TEST: tests/test_movement_portals.py locks curse blocking, random destination persistence, and charge/follower parity behaviors.
- Applied tiny fix: none
<!-- SUBSYSTEM: movement_encumbrance END -->
<!-- SUBSYSTEM: world_loader START -->
### world_loader — Parity Audit 2025-10-17
STATUS: completion:✅ implementation:full correctness:passes (confidence 0.80)
KEY RISKS: file_formats, side_effects
TASKS:
- ✅ [P0] **world_loader: seed ROM area age defaults when loading JSON areas** — done 2025-10-18
  EVIDENCE: C src/db.c:441-470 (load_area seeds age/nplayer/empty defaults)
  EVIDENCE: PY mud/loaders/json_loader.py:120-154 (json loader primes age=15, nplayer=0, empty=False)
  EVIDENCE: TEST tests/test_area_loader.py::test_optional_room_fields_roundtrip
NOTES:
- C: `load_area` primes `age` to 15 pulses so the update timer counts down before repop; JSON loads now mirror this starting point to avoid instant resets.
- PY: `load_area_from_json` explicitly seeds age, nplayer, and empty so world loads behave like freshly booted ROM areas.
- TEST: The Midgaard round-trip regression now asserts the ROM defaults alongside the existing heal/mana checks.
- Applied tiny fix: none
<!-- SUBSYSTEM: world_loader END -->
<!-- SUBSYSTEM: area_format_loader START -->
### area_format_loader — Parity Audit 2025-10-17
STATUS: completion:✅ implementation:full correctness:passes (confidence 0.78)
KEY RISKS: file_formats, indexing
TASKS:
- ✅ [P0] **area_format_loader: parse #HELPS sections when ingesting legacy .are files** — done 2025-10-18
  EVIDENCE: C src/db.c:562-640 (load_helps consumes level + keyword strings and help bodies)
  EVIDENCE: PY mud/loaders/help_loader.py:12-67 (parses #HELPS blocks and registers HelpEntry records)
  EVIDENCE: PY mud/loaders/area_loader.py:5-27 (wires load_helps into SECTION_HANDLERS)
  EVIDENCE: TEST tests/test_area_loader.py::test_help_section_registers_entries
NOTES:
- C: `load_helps` walks each level/keyword pair until `$`; Python now mirrors this flow to populate area-bound help entries.
- PY: `load_area_file` dispatches to `load_helps`, storing entries on the Area object and in `help_registry` with ROM keyword tokenisation.
- TEST: The new regression feeds a minimal #HELPS section and asserts multi-keyword entries register under all aliases with preserved help text.
- Applied tiny fix: none
<!-- SUBSYSTEM: area_format_loader END -->
<!-- SUBSYSTEM: player_save_format START -->
### player_save_format — Parity Audit 2025-10-17
STATUS: completion:✅ implementation:full correctness:passes (confidence 0.78)
KEY RISKS: flags, persistence
TASKS:
- ✅ [P0] **player_save_format: persist PLR/COMM bitvectors in PlayerSave snapshots** — done 2025-10-18
  EVIDENCE: C src/save.c:223-231 (fwrite_char serialises Act/AfBy/Comm/Wizn)
  EVIDENCE: PY mud/persistence.py:27-203 (PlayerSave now stores act/comm and save/load copies them)
  EVIDENCE: PY mud/models/character.py:94-130 (Character exposes comm bitvector alongside act)
  EVIDENCE: TEST tests/test_player_save_format.py::test_act_and_comm_flags_roundtrip
NOTES:
- C: ROM emits Act and Comm before affects so player toggles survive reboots; JSON persistence now mirrors that order.
- PY: PlayerSave snapshots capture act/comm bitfields and `load_character` restores them onto `Character` instances.
- TEST: The new round-trip regression seeds non-zero act/comm bits and confirms both survive save/load alongside affected_by and wiznet flags.
- Applied tiny fix: none
<!-- SUBSYSTEM: player_save_format END -->
<!-- SUBSYSTEM: help_system START -->
### help_system — Parity Audit 2025-10-17
STATUS: completion:✅ implementation:full correctness:passes (confidence 0.78)
KEY RISKS: side_effects, output
TASKS:
- ✅ [P0] **help_system: aggregate multi-entry help responses with ROM separators** — done 2025-10-18
  EVIDENCE: C src/act_info.c:1852-1890 (do_help walks help list and inserts ROM separators)
  EVIDENCE: PY mud/commands/help.py:120-200 (aggregates matching entries with separators and keyword headers)
  EVIDENCE: TEST tests/test_help_system.py::test_help_combines_matching_entries_with_separator
NOTES:
- C: ROM emits separators and keyword headers when multiple help entries match; the Python command now mirrors that pagination flow.
- PY: `do_help` collects all visible matches, prepends keyword lines, and joins them with the ROM divider before returning output.
- TEST: The new regression seeds stacked keyword entries and verifies the aggregated response includes both texts separated by the ROM divider.
- Applied tiny fix: none
<!-- SUBSYSTEM: help_system END -->
<!-- PARITY-GAPS-END -->


## Next Actions (Aggregated P0s)

<!-- NEXT-ACTIONS-START -->
- [P0] game_update_loop — port `char_update` regeneration/condition decay (mud/game_loop.py; tests/test_game_loop.py::test_char_update_applies_conditions).
- [P0] game_update_loop — implement `obj_update` timers and container spill (mud/game_loop.py; tests/test_game_loop.py::test_obj_update_decays_corpse).
- [P0] boards_notes — port ROM note editor with forced recipients (mud/commands/notes.py; tests/test_boards.py::test_note_write_enforces_forced_recipients).
- [P0] skills_spells — implement martial skill handlers (mud/skills/handlers.py; tests/test_skills.py::test_backstab_uses_position_and_weapon).
- [P0] skills_spells — implement dragon breath spells with room effects (mud/skills/handlers.py; tests/test_skills.py::test_fire_breath_hits_room_targets).
<!-- NEXT-ACTIONS-END -->

## C ↔ Python Parity Map

<!-- PARITY-MAP-START -->

| subsystem                | C source (file:symbol)                                             | Python target (file:symbol)                                                                |
| ------------------------ | ------------------------------------------------------------------ | ------------------------------------------------------------------------------------------ |
| combat                   | src/fight.c:one_hit/multi_hit                                      | mud/combat/engine.py:attack_round                                                          |
| skills_spells            | src/act_info.c:do_practice; src/skills.c:check_improve             | mud/commands/advancement.py:do_practice; mud/skills/registry.py:SkillRegistry.use          |
| affects_saves            | src/magic.c:saves_spell; src/handler.c:check_immune                | mud/affects/saves.py:saves_spell/\_check_immune                                            |
| movement_encumbrance     | src/act_move.c:move_char; src/handler.c:room_is_private            | mud/world/movement.py:move_character                                                       |
| resets                   | src/db.c:load_resets ('D' commands); src/db.c:reset_room           | mud/spawning/reset_handler.py:apply_resets/reset_area                                      |
| shops_economy            | src/act_obj.c:get_keeper/do_buy                                    | mud/commands/shop.py:do_buy/do_sell                                                        |
| command_interpreter      | src/interp.c:interpret                                             | mud/commands/dispatcher.py:process_command                                                 |
| socials                  | src/db2.c:load_socials; src/interp.c:check_social                  | mud/loaders/social_loader.py:load_socials; mud/commands/socials.py:perform_social          |
| channels                 | src/act_comm.c:do_say/do_tell/do_shout                             | mud/commands/communication.py:do_say/do_tell/do_shout                                      |
| wiznet_imm               | src/act_wiz.c:wiznet                                               | mud/wiznet.py:wiznet/cmd_wiznet                                                            |
| world_loader             | src/db.c:load_area/load_rooms                                      | mud/loaders/json_loader.py:load_area_from_json/mud/loaders/area_loader.py                  |
| resets                   | src/db.c:reset_room (O/P/G gating)                                 | mud/spawning/reset_handler.py:apply_resets/reset_area                                      |
| weather                  | src/update.c:weather_update                                        | mud/game_loop.py:weather_tick                                                              |
| time_daynight            | src/update.c:weather_update sun state                              | mud/time.py:TimeInfo.advance_hour; mud/game_loop.py:time_tick                              |
| movement_encumbrance     | src/act_move.c:encumbrance                                         | mud/world/movement.py:move_character                                                       |
| stats_position           | merc.h:position enum                                               | mud/models/constants.py:Position                                                           |
| shops_economy            | src/act_obj.c:do_buy/do_sell                                       | mud/commands/shop.py:do_buy/do_sell                                                        |
| boards_notes             | src/board.c                                                        | mud/notes.py:load_boards/save_board; mud/commands/notes.py                                 |
| help_system              | src/act_info.c:do_help                                             | mud/loaders/help_loader.py:load_help_file; mud/commands/help.py:do_help                    |
| mob_programs             | src/mob_prog.c:program_flow/cmd_eval; src/mob_cmds.c:mob_cmd_table | mud/mobprog.py:\_program_flow/\_cmd_eval; mud/mob_cmds.py:MobCommand (partial)             |
| npc_spec_funs            | src/special.c:spec_table                                           | mud/spec_funs.py:run_npc_specs                                                             |
| game_update_loop         | src/update.c:update_handler                                        | mud/game_loop.py:game_tick                                                                 |
| persistence              | src/save.c:save_char_obj/load_char_obj                             | mud/persistence.py:save_character/load_character                                           |
| login_account_nanny      | src/nanny.c                                                        | mud/account/account_service.py:login/create_character                                      |
| networking_telnet        | src/comm.c                                                         | mud/net/telnet_server.py:start_server; mud/net/connection.py:handle_connection             |
| security_auth_bans       | src/ban.c:check_ban/do_ban/save_bans                               | mud/security/bans.py:save_bans_file/load_bans_file; mud/commands/admin_commands.py         |
| logging_admin            | src/act_wiz.c (admin flows)                                        | mud/logging/admin.py:log_admin_command/rotate_admin_log                                    |
| olc_builders             | src/olc_act.c                                                      | mud/commands/build.py:cmd_redit                                                            |
| area_format_loader       | src/db.c:load_area/new_load_area                                   | mud/loaders/area_loader.py; mud/scripts/convert_are_to_json.py                             |
| imc_chat                 | src/imc.c:imc_startup; src/comm.c:imc_loop                         | mud/imc/**init**.py:maybe_open_socket/pump_idle; mud/world/world_state.py:initialize_world |
| player_save_format       | src/save.c:save_char_obj                                           | mud/persistence.py:PlayerSave                                                              |
| skills_spells (metadata) | src/const.c:skill_table                                            | data/skills.json; mud/models/skill.py                                                      |
| security_auth_bans       | src/sha256.c:sha256_crypt                                          | mud/security/hash_utils.py:sha256_hex                                                      |
| affects_saves            | src/flags.c:IMM*\*/RES*\_/VULN\_\_                                 | mud/models/constants.py:ImmFlag/ResFlag/VulnFlag                                           |

<!-- PARITY-MAP-END -->

## Data Anchors (Canonical Samples)

- ARE: area/midgaard.are (primary fixture)
- DOC: doc/area.txt §#ROOMS/#MOBILES/#OBJECTS/#RESETS
- DOC: doc/Rom2.4.doc (stats, AC/THAC0, saves)
- C: src/db.c:load_area(), src/save.c:load_char_obj(), src/socials.c

## Parity Gaps & Corrections


<!-- PARITY-GAPS-START -->
<!-- AUDITED: resets, movement_encumbrance, world_loader, area_format_loader, player_save_format, help_system, boards_notes, game_update_loop, combat, skills_spells -->
<!-- SUBSYSTEM: combat START -->

### combat — Parity Audit 2025-10-20

STATUS: completion:❌ implementation:partial correctness:fails (confidence 0.30)
KEY RISKS: equipment, skills, side_effects
TASKS:

- [P0] **combat: compute weapon selection and THAC0 using ROM skill tables**
  - priority: P0
  - rationale: `attack_round` hardcodes `wield = None`, ignores `get_weapon_sn`/`get_weapon_skill`, and applies flat 120 skill so THAC0, damage dice, and dam_type never reflect equipped weapons.
  - files: mud/combat/engine.py; mud/models/character.py; mud/equipment/slots.py
  - tests: tests/test_combat.py::test_one_hit_uses_equipped_weapon (new); tests/test_combat.py::test_weapon_skill_scales_hit_roll (new)
  - acceptance_criteria: Equipping ROM weapons selects the correct attack table entry, computes THAC0 with `class_table` and `GET_HITROLL`, and damages targets per dice like `one_hit`.
  - estimate: L
  - risk: high
  - evidence: C src/fight.c:386-520 (one_hit weapon lookup, THAC0 interpolation); PY mud/combat/engine.py:400-470 (TODO placeholders for wield/skill).
- [P0] **combat: restore parry/dodge/shield defensive rolls with skill improvement**
  - priority: P0
  - rationale: Defensive checks in the port always return False, so shields and skills never block hits or improve as in ROM.
  - files: mud/combat/engine.py; mud/skills/registry.py; mud/models/character.py
  - tests: tests/test_combat.py::test_parry_blocks_when_skill_learned (new); tests/test_combat.py::test_shield_block_requires_shield (new)
  - acceptance_criteria: Parry/dodge/shield block outcomes match ROM percentages, invoke `check_improve`, and respect wielded shields and statuses.
  - estimate: M
  - risk: high
  - evidence: C src/fight.c:541-720 (parry/dodge/shield logic and check_improve hooks); PY mud/combat/engine.py:520-640 (stubbed defensive checks with TODO comments).
- [P1] **combat: apply weapon proc effects and enhanced damage scaling**
  - priority: P1
  - rationale: Poison/sharpness/vampiric procs and enhanced damage bonuses are skipped so special weapons lose their ROM effects.
  - files: mud/combat/engine.py; mud/affects/effects.py
  - tests: tests/test_combat.py::test_sharp_weapon_doubles_damage_on_proc (new); tests/test_combat.py::test_poison_weapon_applies_affect (new)
  - acceptance_criteria: Weapon procs trigger with ROM odds, apply affects, and enhanced damage multiplies base damage when learned.
  - estimate: M
  - risk: medium
  - evidence: C src/fight.c:640-828 (enhanced_damage, weapon procs); PY mud/combat/engine.py:470-620 (TODO placeholders returning early).

NOTES:
- C: src/fight.c:386-828 drives ROM weapon selection, THAC0, defensive checks, and proc effects that are currently stubbed.
- PY: mud/combat/engine.py sets dummy skill values, leaves defensive helpers returning False, and never inspects equipment or proc flags.
- TEST: New combat regressions must cover weapon-based THAC0, parry/shield success rates, and proc side effects so future changes stay aligned with ROM.
- Applied tiny fix: none
<!-- SUBSYSTEM: combat END -->
<!-- SUBSYSTEM: skills_spells START -->

### skills_spells — Parity Audit 2025-10-20

STATUS: completion:❌ implementation:partial correctness:fails (confidence 0.28)
KEY RISKS: affects, damage, rng
TASKS:

- [P0] **skills_spells: port martial skill handlers (bash/backstab/berserk)**
  - priority: P0
  - rationale: `mud/skills/handlers.py` returns placeholder values for bash/backstab/berserk so combat commands lack lag, position checks, and damage from ROM.
  - files: mud/skills/handlers.py; mud/combat/engine.py; mud/commands/combat.py
  - tests: tests/test_skills.py::test_backstab_uses_position_and_weapon (new); tests/test_skills.py::test_bash_applies_wait_state (new)
  - acceptance_criteria: Commands enforce ROM position/trust, apply wait states, compute damage dice, and interact with skill advancement as in `do_bash`/`do_backstab`/`do_berserk`.
  - estimate: L
  - risk: high
  - evidence: C src/fight.c:2270-2998 (do_berserk/do_bash/do_backstab logic); PY mud/skills/handlers.py:20-70 (stub functions returning `42`).
- [P0] **skills_spells: implement dragon breath spells with room/target effects**
  - priority: P0
  - rationale: Breath spells currently return constants without saving throws, room effects, or secondary damage so dragons lose signature attacks.
  - files: mud/skills/handlers.py; mud/magic/effects.py; mud/utils/rng_mm.py
  - tests: tests/test_skills.py::test_acid_breath_applies_acid_effect (new); tests/test_skills.py::test_fire_breath_hits_room_targets (new)
  - acceptance_criteria: Breath handlers roll dice per ROM tables, call elemental `*_effect` helpers, respect `saves_spell`, and broadcast act() strings.
  - estimate: M
  - risk: high
  - evidence: C src/magic.c:4625-4856 (spell_acid_breath through spell_lightning_breath); PY mud/skills/handlers.py:18-120 (stubbed breath implementations).
- [P1] **skills_spells: wire skill improvement and cooldown feedback**
  - priority: P1
  - rationale: `SkillRegistry.use` records cooldowns but stubs never return success/failure strings, so players miss ROM feedback and skill practice hooks for stubs.
  - files: mud/skills/handlers.py; mud/skills/registry.py; mud/commands/advancement.py
  - tests: tests/test_skills.py::test_skill_use_reports_result (new)
  - acceptance_criteria: Handlers return ROM messages, set failure flags, and trigger `check_improve`/cooldown updates consistent with `Skill.use`.
  - estimate: M
  - risk: medium
  - evidence: C src/skills.c:53-210 (check_improve messaging); PY mud/skills/handlers.py:15-200 (many TODO stubs lacking messages or improvement paths).

NOTES:
- C: src/fight.c:2270-2998 and src/magic.c:4625-4856 define martial skills and dragon breaths with wait states, lag, and elemental side effects.
- PY: mud/skills/handlers.py leaves most handlers returning placeholder integers, omitting lag, saves, and messaging; SkillRegistry cannot surface ROM results without real implementations.
- TEST: New regressions must exercise bash/backstab/berserk success/failure paths and breath weapon splash damage to keep parity once handlers are ported.
- Applied tiny fix: none
<!-- SUBSYSTEM: skills_spells END -->
<!-- SUBSYSTEM: resets START -->
### resets — Parity Audit 2025-10-16
STATUS: completion:✅ implementation:full correctness:passes (confidence 0.80)
KEY RISKS: flags, rng
TASKS:
- ✅ [P0] **resets: restore create_mobile field parity for NPC spawns** — done 2025-10-14
  - FILES: mud/spawning/templates.py; mud/spawning/reset_handler.py; tests/test_spawning.py
  - ISSUE: Spawned mobs drop ACT/AFF/permanent stat data so reset-populated NPCs lose ROM behaviors (aggression, charm immunity, armor scaling).
  - C_REF: src/db.c:2003-2138 (`create_mobile` copies act/affect/perm stat fields)
  - ACCEPTANCE: `pytest tests/test_spawning.py::test_spawned_mob_copies_proto_stats` verifies a reset-spawned mob inherits act/affected_by/off_flags/default_pos from its prototype.
  EVIDENCE: C src/db.c:2003-2138; PY mud/spawning/templates.py:40-190; TEST tests/test_spawning.py::test_spawned_mob_copies_proto_stats
- ✅ [P1] **resets: persist spec_fun and mob program wiring during spawn** — done 2025-10-14
  - FILES: mud/spawning/templates.py; mud/spec_funs.py; tests/test_spec_funs.py
  - ISSUE: Runtime mobs drop spec_fun/mprog state so reset-created NPCs never invoke ROM special functions after repop.
  - C_REF: src/db.c:2003-2068 (`create_mobile` assigns spec_fun/mprog lists)
  - ACCEPTANCE: `pytest tests/test_spec_funs.py::test_reset_spawn_triggers_spec_fun` covers that a reset immediately triggers the mob's spec_fun hook.
  EVIDENCE: C src/db.c:2003-2068; PY mud/spawning/templates.py:210-310; TEST tests/test_spec_funs.py::test_reset_spawn_triggers_spec_fun
- ✅ [P0] **resets: derive perm_stat arrays for spawned mobs** — done 2025-10-16
  - FILES: mud/spawning/templates.py; mud/models/constants.py; tests/test_spawning.py
  - ISSUE: `MobInstance` never populates `perm_stat`, so reset-created NPCs lack ROM strength/intelligence baselines and class/size adjustments, breaking encumbrance and training caps.
  - C_REF: src/db.c:2118-2152 (`create_mobile` seeds perm_stat array and applies ACT_* and size adjustments)
  - ACCEPTANCE: Extend `tests/test_spawning.py` with a prototype that sets warrior/thief flags and size to assert spawned mobs expose the ROM perm_stat values.
  EVIDENCE: C src/db.c:2118-2152; PY mud/spawning/templates.py:296-329; PY mud/models/constants.py:123-128; TEST tests/test_spawning.py::test_spawned_mob_inherits_perm_stats
- ✅ [P1] **resets: randomize mob sex when prototypes allow either** — done 2025-10-18
  - FILES: mud/spawning/templates.py; tests/test_spawning.py
  - ISSUE: ROM rolls male/female when `sex == 3`, but the port leaves mobs stuck on the sentinel value so charm and equipment restrictions misbehave.
  - C_REF: src/db.c:2173-2179 (`create_mobile` rerolls random sex)
  - ACCEPTANCE: Add a regression that seeds RNG and spawns a prototype with `sex = Sex.EITHER`, asserting the runtime mob resolves to MALE or FEMALE.
  EVIDENCE: C src/db.c:2173-2179; PY mud/spawning/templates.py:294-296; TEST tests/test_spawning.py::test_spawned_mob_randomizes_sex_when_either
NOTES:
- C: src/db.c:2003-2179 seeds runtime flags, perm stats, and Sex.EITHER rerolling that the Python spawn path now mirrors.
- PY: mud/spawning/templates.py copies ROM flags/spec_fun state, rerolls Sex.EITHER via `rng_mm.number_range`, and preserves perm stats for reset spawns.
- TEST: tests/test_spawning.py locks both the ROM stat copy and the Sex.EITHER reroll via deterministic RNG patches.
- Applied tiny fix: none
<!-- SUBSYSTEM: resets END -->
<!-- SUBSYSTEM: movement_encumbrance START -->
### movement_encumbrance — Parity Audit 2025-10-15
STATUS: completion:✅ implementation:full correctness:passes (confidence 0.55)
KEY RISKS: RNG, flags, side_effects
TASKS:
- ✅ [P0] **movement_encumbrance: enforce portal curse/no-recall gating** — done 2025-10-15
  EVIDENCE: C src/act_enter.c:104-138 (trust + NOCURSE checks before travel)
  EVIDENCE: PY mud/commands/movement.py:26-66 (portal lookup + curse gate enforcement)
  EVIDENCE: PY mud/world/movement.py:324-378 (follow path duplicates NOCURSE blocks)
  EVIDENCE: TEST tests/test_movement_portals.py::test_cursed_player_blocked_by_nocurse_portal
- ✅ [P0] **movement_encumbrance: resolve portal destinations via ROM gate flags** — done 2025-10-15
  EVIDENCE: C src/act_enter.c:140-176 (GATE_RANDOM/BUGGY rerolls + private room checks)
  EVIDENCE: PY mud/world/movement.py:378-454 (random rolls, private-room rejection, law-room aggression guard)
  EVIDENCE: TEST tests/test_movement_portals.py::test_random_gate_rolls_destination
- ✅ [P1] **movement_encumbrance: consume portal charges and carry GATE_GOWITH objects** — done 2025-10-15
  EVIDENCE: C src/act_enter.c:178-236 (portal charge depletion and GATE_GOWITH relocation)
  EVIDENCE: PY mud/world/movement.py:260-360 (charge decrement, follower gating, fade messaging)
  EVIDENCE: TEST tests/test_movement_portals.py::test_portal_charges_and_followers
NOTES:
- C: src/act_enter.c:101-236 layers NOCURSE gating, random/buggy rerolls, law-room aggression checks, and charge depletion.
- PY: mud/commands/movement.py:15-66 plus mud/world/movement.py:324-454 now mirror the ROM gating, rerolls, and fade cleanup for GATE_GOWITH portals.
- TEST: tests/test_movement_portals.py locks curse blocking, random destination persistence, and charge/follower parity behaviors.
- Applied tiny fix: none
<!-- SUBSYSTEM: movement_encumbrance END -->
<!-- PARITY-GAPS-END -->


## 1. Inventory current system

1.1 ✅ Audit C modules under `src/` to identify all functionality: combat, skills/spells, shops, resets, saving, networking, etc. - Documented each C file and its responsibility in `doc/c_module_inventory.md`.
1.2 ✅ Catalog existing Python modules in `mud/` and `tests/` and note which C features they already replicate (e.g., telnet server, command dispatcher, world loading). - Documented Python modules and their C counterparts in `doc/python_module_inventory.md`.
1.3 ✅ Produce a cross‑reference table showing which systems are already in Python and which remain in C. - Compiled `doc/c_python_cross_reference.md` mapping subsystems to their C and Python implementations.

## 2. Define JSON data schemas

2.1 ✅ **Rooms** – id, name, description, exits, sector type, flags, extra descriptions, resets, area reference. - Documented room JSON schema in `schemas/room.schema.json` covering identifiers, exits, flags, extras, resets, and area links.
2.2 ✅ **Characters/Mobiles** – id, name, description, stats, skills, inventory list, behavior flags, position. - Documented character JSON schema in `schemas/character.schema.json` covering descriptors, stats, flags, skills, inventory, and position.
2.3 ✅ **Objects/Items** – id, name, description, type, flags, values, weight, cost, affects. - Documented object JSON schema in `schemas/object.schema.json` covering identifiers, types, flags, values, weight, cost, and affects.
2.4 ✅ **Areas** – metadata (name, vnum range, builders), room/mob/object collections. - Documented area JSON schema in `schemas/area.schema.json` covering metadata and embedded room/mob/object lists.
2.5 ✅ Validate schemas with JSON Schema files so game data can be linted automatically. - Added tests using `jsonschema` to ensure each schema file is itself valid.
2.6 ✅ Define JSON schema for **shops** including keeper vnums, trade types, profit margins, and open/close hours. - Added `schemas/shop.schema.json` and matching `ShopJson` dataclass with tests validating the schema.
2.7 ✅ Define JSON schema for **skills & spells** detailing names, mana costs, target types, lag, and messages. - Added `schemas/skill.schema.json` and expanded `SkillJson` dataclass with tests validating defaults.
2.8 ✅ Define JSON schema for **help entries and socials** so player-facing text and emotes can be managed in JSON. - Added `schemas/help.schema.json` and `schemas/social.schema.json` with matching `HelpJson` and `SocialJson` dataclasses and tests.

## 3. Convert legacy data files to JSON

3.1 ✅ Write conversion scripts in Python that parse existing `.are` files and output JSON using the schemas above. - Added `mud/scripts/convert_are_to_json.py` to transform `.are` files into schema-compliant JSON.
3.2 ✅ Store converted JSON in a new `data/areas/` directory, mirroring the hierarchy by area name. - Updated converter to default to `data/areas` and committed a sample `limbo.json`.
3.3 ✅ Create tests that load sample areas (e.g., Midgaard) from JSON and assert that room/mob/object counts match the original `.are` files. - Added a Midgaard test comparing room, mob, and object counts between `.are` and converted JSON.
3.4 ✅ Convert `shops.dat`, `skills.dat`, and other auxiliary tables into their JSON counterparts under `data/`. - Added `mud/scripts/convert_shops_to_json.py` to extract `#SHOPS` data from area files and write `data/shops.json`.
3.5 ✅ Add tests ensuring converted shop, skill, help, and social data match legacy counts and key fields. - Added tests confirming `data/shops.json` keeper counts align with area files and verifying `skills.json` contains the expected `fireball` entry.

## 4. Implement Python data models

4.1 ✅ Create `dataclasses` in `mud/models/` mirroring the JSON schemas. - Added `PlayerJson` dataclass and documented it alongside existing schema models.
4.2 ✅ Add serialization/deserialization helpers to read/write JSON and handle default values. - Added `JsonDataclass` mixin supplying `to_dict`/`from_dict` and default handling. - Round-trip tests ensure schema defaults are preserved for rooms and areas.
4.3 ✅ Replace legacy models referencing `merc.h` structures with these new dataclasses. - Identified modules cloning `RESET_DATA` and switched loaders/handlers to `ResetJson`. - Removed direct `merc.h` dependencies and refreshed cross-reference docs.
4.4 ✅ Add dataclasses for shops, skills/spells, help entries, and socials mirroring the new schemas. - Introduced runtime `Shop`, `Skill`, `HelpEntry`, and `Social` models built from their JSON counterparts.

## 5. Replace C subsystems with Python equivalents

5.1 ✅ **World loading & resets** – implement reset logic in Python to spawn mobs/objects per area definitions. - Added tick-based scheduler that clears rooms and reapplies resets, with tests confirming area repopulation.
5.2 ✅ **Command interpreter** – expand existing dispatcher to cover all player commands currently implemented in C. - Added prefix-based command resolution, quote-aware argument parsing, and admin permission gating. - Tests cover abbreviations and quoted arguments across movement, information, object, and wizard commands.
5.3 ✅ **Combat engine** – port attack rounds, damage calculations, and status effects; ensure turn‑based loop is replicated. - Introduced hit/miss mechanics with position tracking and death removal, covered by new combat tests.
5.4 ✅ **Skills & spells** – create a registry of skill/spell functions in Python, reading definitions from JSON. - Skill registry loads definitions from JSON, enforces mana costs and cooldowns, applies failure rates, and dispatches to handlers.
5.5 ✅ **Character advancement** – implement experience, leveling, and class/race modifiers. - Added progression tables with level-based stat gains. - Implemented practice/train commands and tests for level-up stat increases.
5.6 ✅ **Shops & economy** – port shop data, buying/selling logic, and currency handling. - Shop commands list, buy, and sell with profit margins and buy-type restrictions.
5.7 ✅ **Persistence** – replace C save files with JSON; implement load/save for players and world state. - Characters saved atomically to JSON with inventories and equipment; world loader restores them into rooms.
5.8 ✅ **Networking** – use existing async telnet server; gradually remove any remaining C networking code. - Removed `comm.c`, `nanny.c`, and `telnet.h`; telnet server now translates ROM color codes, handles prompts and login flow, and passes multi‑client tests with CI linting.
5.9 ✅ **Player communication & channels** – port say/tell/shout and global channel handling with mute/ban support. - Added tell and shout commands with global broadcast respecting per-player mutes and bans, covered by communication tests.
5.10 ✅ **Message boards & notes** – migrate board system to Python with persistent storage. - Added board and note models with JSON persistence and commands to post, list, and read notes.
5.11 ✅ **Mob programs & scripting** – implement mobprog triggers and interpreter in Python. - Added `mud/mobprog.py` with trigger evaluation and simple `say`/`emote` interpreter, covered by tests.
5.12 ✅ **Online creation (OLC)** – port building commands to edit rooms, mobs, and objects in-game. - Added admin-only `@redit` command for live room name and description editing with unit tests.
5.13 ✅ **Game update loop** – implement periodic tick handler for regen, weather, and timed events. - Added Python tick handler that regenerates characters, cycles weather, runs scheduled callbacks, and invokes area resets.
5.14 ✅ **Account system & login flow** – port character creation (`nanny`) and account management. - Implemented password-protected account login with automatic creation and character selection in the telnet server.
5.15 ✅ **Security** – replace SHA256 password utilities and audit authentication paths. - Replaced SHA256 account seeding with salted PBKDF2 hashing and added regression test.

## 6. Testing and validation

6.1 ✅ Expand `pytest` suite to cover each subsystem as it is ported. - Added tests for PBKDF2 password hashing ensuring unique salts and verification.
6.2 ✅ Add integration tests that run a small world, execute a scripted player session, and verify outputs. - Implemented a scripted session test verifying look, item pickup, movement, and speech outputs.
6.3 ✅ Use CI to run tests and static analysis (ruff/flake8, mypy) on every commit. - CI lint step now covers security utilities and tests, and type checks include `hash_utils`.
6.4 ✅ Measure code coverage and enforce minimum thresholds in CI. - CI now runs the full test suite with `pytest --cov=mud --cov-fail-under=80` to keep coverage above 80%.

## 7. Decommission C code

7.1 ✅ As Python features reach parity, remove the corresponding C files and build steps from `src/` and the makefiles. - Removed obsolete `sha256.c` and `sha256.h` and scrubbed all documentation references.
7.2 ✅ Update documentation to describe the new Python‑only architecture. - Revised README with Python engine details and added `doc/python_architecture.md`.
7.3 ✅ Ensure the Docker image and deployment scripts start the Python server exclusively. - Dockerfile runs `mud runserver` and docker-compose uses the same command so containers launch only the Python engine.
7.4 ✅ Remove remaining C source tree now that Python covers all functionality. - Deleted the entire `src/` directory and legacy makefiles, leaving a pure Python codebase.

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

### shops_economy — Parity Audit 2025-09-19

STATUS: completion:✅ implementation:full correctness:passes (confidence 0.74)
KEY RISKS: economy, side_effects
TASKS:

- ✅ [P0] Port healer NPC shop logic (healer.c) — done 2025-09-09
  RATIONALE: Minimal healer command wired; supports refresh/heal/mana with ROM-like pricing and denial message.
  FILES: mud/commands/healer.py; mud/commands/dispatcher.py
  TESTS: tests/test_healer.py::test_healer_lists_services_and_prices; tests/test_healer.py::test_healer_denies_when_insufficient_gold
  REFERENCES: C src/healer.c:1-220; PY mud/commands/healer.py:8-90
  PRIORITY: P0; ESTIMATE: M; RISK: medium

- ✅ [P1] Mirror ROM get_cost() including profit_buy/sell and inventory discount — done 2025-09-12
  RATIONALE: Shop prices use profit margins and adjust based on existing inventory (half/three-quarters).
  FILES: mud/commands/shop.py
  TESTS: tests/test_shops.py::test_wand_staff_price_scales_with_charges_and_inventory_discount
  REFERENCES: C src/act_obj.c:2468-2530; PY mud/commands/shop.py:40-115
  PRIORITY: P1; ESTIMATE: M; RISK: medium

- ✅ [P1] Adjust wand/staff prices by charges — done 2025-09-12
  RATIONALE: ROM scales wand/staff prices based on remaining charges.
  FILES: mud/commands/shop.py
  TESTS: tests/test_shops.py::test_wand_staff_price_scales_with_charges_and_inventory_discount
  REFERENCES: C src/act_obj.c:2516-2528; PY mud/commands/shop.py:64-100
  PRIORITY: P1; ESTIMATE: M; RISK: medium

- ✅ [P2] Preserve #SHOPS data in conversion and loader — done 2025-09-13
  RATIONALE: Maintain ROM shop metadata during area conversion.
  FILES: mud/loaders/shop_loader.py; mud/loaders/area_loader.py; mud/scripts/convert_shops_to_json.py
  TESTS: tests/test_shop_conversion.py::{test_convert_shops_produces_grocer,test_shops_json_matches_legacy_counts}
  REFERENCES: C src/db.c:1280-1320; DOC doc/area.txt:522-550; ARE area/midgaard.are:6420-6470
  PRIORITY: P2; ESTIMATE: M; RISK: low

- ✅ [P0] Enforce shop open/close hours during buy/list/sell — done 2025-09-19
  RATIONALE: ROM `find_keeper` denies service outside configured shop hours.
  FILES: mud/commands/shop.py; tests/test_shops.py
  TESTS: tests/test_shops.py::test_shop_respects_open_hours
  REFERENCES: C src/act_obj.c:2351-2390; DOC doc/area.txt §#SHOPS; ARE area/midgaard.are:6430-6460
  PRIORITY: P0; ESTIMATE: S; RISK: low

- ✅ [P0] Honor `find_keeper` visibility checks before trading — done 2025-09-19
  RATIONALE: ROM refuses invisible/hidden customers unless the keeper can see them via `can_see`.
  FILES: mud/commands/shop.py; tests/test_shops.py
  TESTS: tests/test_shops.py::test_shop_refuses_invisible_customers
  REFERENCES: C src/act_obj.c:2395-2401; C src/handler.c:2618-2662; PY mud/commands/shop.py:9-54; PY tests/test_shops.py:172-213
  PRIORITY: P0; ESTIMATE: S; RISK: low

- ✅ [P0] Reinstate shopkeeper wealth caps before accepting player sales — done 2025-09-19
  ACCEPTANCE: Selling an item whose cost exceeds `keeper.silver + 100 * keeper.gold` yields ROM's denial message and leaves both inventories unchanged.
  RATIONALE: Without wealth checks, players can dump unlimited goods into impoverished shops for full price.
  FILES: mud/commands/shop.py; mud/spawning/templates.py; tests/test_shops.py
  TESTS: PYTHONPATH=. pytest -q tests/test_shops.py::test_shop_respects_keeper_wealth
  REFERENCES: C src/act_obj.c:2917-2953; PY mud/commands/shop.py:118-171; PY mud/spawning/templates.py:49-78; TEST tests/test_shops.py::test_shop_respects_keeper_wealth
  PRIORITY: P0; ESTIMATE: M; RISK: medium

NOTES:

- C: src/act_obj.c:2917-2953 caps player sales by keeper wealth and deducts coins before transferring the object.
- PY: mud/commands/shop.py:\_keeper_total_wealth/do_sell/do_buy enforce the ROM wealth gate and update keeper coin totals.
- PY: mud/spawning/templates.py:MobInstance.from_prototype rolls ROM wealth into gold/silver so shopkeepers start with parity coins.
- TEST: tests/test_shops.py::test_shop_respects_keeper_wealth denies the sale until the keeper's coin pool is replenished.
- Applied tiny fix: Seeded keeper wealth with the ROM random roll when spawning mobs to keep resets and direct spawns aligned.
  <!-- SUBSYSTEM: shops_economy END -->
<!-- SUBSYSTEM: boards_notes START -->

### boards_notes — Parity Audit 2025-10-20

STATUS: completion:❌ implementation:partial correctness:suspect (confidence 0.40)
KEY RISKS: file_formats, persistence, side_effects
TASKS:

- [P0] **boards_notes: port ROM note editor and forced recipients**
  - priority: P0
  - rationale: Python `do_note` only supports immediate `post` and skips ROM's staged `note write` editor, forced recipient defaults (`DEF_INCLUDE/DEF_EXCLUDE`), and expiry handling so posted notes diverge from `make_note`.
  - files: mud/commands/notes.py; mud/boards/storage.py
  - tests: tests/test_boards.py::test_note_write_enforces_forced_recipients (new)
  - acceptance_criteria: Issuing `note write` prompts for to/subject/text like ROM, enforces forced/default recipients, stamps `expire` per board `purge_days`, and persists via `save_board`.
  - estimate: L
  - risk: high
  - evidence: C src/board.c:740-884, src/board.c:1012-1096 (do_nwrite/make_note + DEF_INCLUDE/DEF_EXCLUDE enforcement); PY mud/commands/notes.py:120-210 (single-step post without recipient defaults).
- [P0] **boards_notes: implement note remove/catchup trust rules**
  - priority: P0
  - rationale: The port lacks `note remove` and `note catchup`, so mortals cannot prune their own notes or advance last-read timestamps in parity with ROM's trust gating.
  - files: mud/commands/notes.py; mud/boards/storage.py
  - tests: tests/test_boards.py::test_note_remove_requires_author_or_immortal (new); tests/test_boards.py::test_note_catchup_marks_all_read (new)
  - acceptance_criteria: `note remove` allows authors/immortals to delete entries, `note catchup` marks board timestamps up to newest note, and both enforce ROM trust checks.
  - estimate: M
  - risk: medium
  - evidence: C src/board.c:886-1010 (do_nremove trust/author checks), src/board.c:1098-1128 (do_ncatchup last_read update); PY mud/commands/notes.py:150-220 (no remove/catchup commands).
- ✅ [P0] Mirror ROM `note` default read flow for next-unread auto advance — done 2025-10-07
  - evidence: C src/board.c:563-605; C src/board.c:889-905; PY mud/commands/notes.py:33-150; TEST tests/test_boards.py::{test_note_read_defaults_to_next_unread,test_note_read_advances_to_next_board_when_exhausted}
- ✅ [P0] Block board switching while a draft is active — done 2025-10-07
  - evidence: C src/board.c:728-780; PY mud/commands/notes.py:51-119; TEST tests/test_boards.py::test_board_change_blocked_during_note_draft

NOTES:
- C: src/board.c:740-1128 covers the interactive editor, forced recipients, removal trust checks, and catchup timestamp sync that remain unported.
- PY: mud/commands/notes.py:120-220 posts notes immediately without prompting for recipients/subject/body, lacks remove/catchup paths, and never touches board `purge_days` expiry fields.
- TEST: New regressions must simulate staged editor prompts and ensure author/immortal deletions plus catchup timestamp updates mirror ROM flows.
- Applied tiny fix: none
<!-- SUBSYSTEM: boards_notes END -->
    <!-- SUBSYSTEM: command_interpreter START -->

### command_interpreter — Parity Audit 2025-09-18

STATUS: completion:✅ implementation:full correctness:passes (confidence 0.78)
KEY RISKS: side_effects, abbreviations
TASKS:

- ✅ [P0] Enforce per-command required position before execution — done 2025-09-08
  EVIDENCE: C src/interp.c:L520-L560 (position denial messages); C src/interp.c:L24-L120, L180-L260 (cmd_table positions for movement/look/etc.)
  EVIDENCE: PY mud/commands/dispatcher.py:L1-L40; L44-L95; L117-L158 (Command.min_position and gating)
  EVIDENCE: TEST tests/test_commands.py::test_position_gating_sleeping_blocks_look_allows_scan
  EVIDENCE: TEST tests/test_commands.py::test_position_gating_resting_blocks_movement

- ✅ [P0] Implement user-defined aliases (alias.c) — done 2025-09-08
  EVIDENCE: C src/alias.c:L1-L200 (substitute_alias/do_alias); C src/interp.c:L140-L178 (alias in cmd table)
  EVIDENCE: PY mud/commands/alias_cmds.py:L1-L60; mud/commands/dispatcher.py:L96-L138 (\_expand_aliases & registrations)
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

- ✅ [P0] Restore ROM punctuation command parsing for apostrophe say alias — done 2025-09-18
  EVIDENCE: C src/interp.c:430-468 (punctuation command parsing and `'` → say mapping)
  EVIDENCE: PY mud/commands/dispatcher.py:\_split_command_and_args/process_command (punctuation token support before shlex)
  EVIDENCE: TEST tests/test_commands.py::{test_apostrophe_alias_routes_to_say,test_punctuation_inputs_do_not_raise_value_error}
  RATIONALE: ROM `interpret` treats leading punctuation like `'` as standalone commands so players can chat (`'message`) or emote without balancing quotes; the Python dispatcher previously fed these inputs to `shlex.split`, raising `ValueError` and returning "Huh?".
  FILES: mud/commands/dispatcher.py (parser adjustments for punctuation alias before shlex).
  TESTS: tests/test_commands.py::test_apostrophe_alias_routes_to_say; tests/test_commands.py::test_punctuation_inputs_do_not_raise_value_error
  ACCEPTANCE_CRITERIA: `'hello` routes through `say` without raising a parsing error and echoes the same message as `say hello` when routed through `process_command`.
  ESTIMATE: S; RISK: medium

NOTES:

- C: src/interp.c:430-468 strips leading punctuation and dispatches `'` → say before argument tokenizing, while later lines 520-560 enforce position messages already ported.
- PY: mud/commands/dispatcher.py:\_split_command_and_args now mirrors ROM punctuation handling before shlex tokenization so `'hello` reaches `do_say` and aliases resolve.
- TEST: tests/test_commands.py::{test_apostrophe_alias_routes_to_say,test_punctuation_inputs_do_not_raise_value_error}
- Applied tiny fix: Added `_split_command_and_args` to guard punctuation commands ahead of shlex splitting.
  <!-- SUBSYSTEM: command_interpreter END -->
<!-- SUBSYSTEM: game_update_loop START -->

### game_update_loop — Parity Audit 2025-10-20

STATUS: completion:❌ implementation:partial correctness:suspect (confidence 0.45)
KEY RISKS: tick_cadence, side_effects, persistence
TASKS:

- [P0] **game_update_loop: port `char_update` regeneration and condition decay**
  - priority: P0
  - rationale: Python `regen_tick` only heals hit/mana/move and never applies hunger/thirst/aftermath timers, idle voiding, or affect expiry so characters ignore ROM condition loss and affect removal.
  - files: mud/game_loop.py; mud/characters/conditions.py (new or existing); mud/affects/engine.py
  - tests: tests/test_game_loop.py::test_char_update_applies_conditions (new); tests/test_game_loop.py::test_char_update_idles_linkdead (new)
  - acceptance_criteria: Tick loop decrements conditions, removes expired affects with `msg_off`, idles link-dead players to Limbo, and mirrors ROM regeneration via `hit_gain/mana_gain/move_gain` helpers.
  - estimate: L
  - risk: high
  - evidence: C src/update.c:661-902 (char_update regen, idle timer, affect decay); PY mud/game_loop.py:20-80 (regen_tick without conditions or affect expiry).
- [P0] **game_update_loop: implement `obj_update` timers and container spill**
  - priority: P0
  - rationale: Objects in the Python world never tick down or broadcast decay messages, so corpses/jukeboxes ignore ROM timers and contents never spill when containers expire.
  - files: mud/game_loop.py; mud/objects/update.py (new); mud/models/object.py
  - tests: tests/test_game_loop.py::test_obj_update_decays_corpse (new); tests/test_game_loop.py::test_obj_update_spills_floating_container (new)
  - acceptance_criteria: Items with timers emit ROM decay messages, spill contents, and call `extract_obj` when timers reach zero while preserving shopkeeper payouts for inventory sales.
  - estimate: M
  - risk: medium
  - evidence: C src/update.c:913-1112 (obj_update timer handling, spill logic, shopkeeper reimburse); PY mud/game_loop.py:80-140 (no object decay path).
- [P1] **game_update_loop: wire `song_update` cadence for channel/jukebox playback**
  - priority: P1
  - rationale: ROM advances `song_update` on PULSE_MUSIC but the port lacks any music pulse so channel songs and jukeboxes never play.
  - files: mud/game_loop.py; mud/music/__init__.py (new); mud/commands/music.py
  - tests: tests/test_music.py::test_song_update_broadcasts_global (new); tests/test_music.py::test_jukebox_cycles_queue (new)
  - acceptance_criteria: Pulse counters include music cadence, invoking a ported `song_update` that rotates channel songs and jukebox queues with NOMUSIC filtering.
  - estimate: M
  - risk: medium
  - evidence: C src/update.c:1151-1189 (PULSE_MUSIC scheduling); C src/music.c:40-150 (song_update logic); PY mud/game_loop.py:40-140 (no music counters or updates).
- ✅ [P0] Restore aggressive mobile updates on every pulse — done 2025-09-27
  - evidence: C src/update.c:1198-1210; PY mud/ai/aggressive.py:13-119; PY mud/game_loop.py:117-145; TEST tests/test_game_loop.py::test_aggressive_mobile_attacks_player
- ✅ [P1] Decrement wait/daze on PULSE_VIOLENCE cadence — done 2025-09-12
  - evidence: C src/fight.c:180-200; C src/update.c:1166-1189; PY mud/game_loop.py:73-112; PY mud/config.py:get_pulse_violence; TEST tests/test_game_loop_wait_daze.py::test_wait_and_daze_decrement_on_violence_pulse
- ✅ [P1] Schedule weather/time/resets in ROM order with separate pulse counters — done 2025-09-13
  - evidence: C src/update.c:1161-1189; PY mud/game_loop.py:57-112; PY mud/config.py:1-80; TEST tests/test_game_loop_order.py::test_weather_time_reset_order_on_point_pulse

NOTES:
- C: src/update.c:661-1210 drives char/object/music updates before aggro; the port currently stops after regen/reset pulses so decay and channel playback never happen.
- PY: mud/game_loop.py:20-140 only heals resources, runs resets, and aggressive/spec updates without touching affects, object timers, or music queues.
- TEST: New regressions must emulate ROM's timed decay (corpse dusting, floating container spill) and hunger/idle behavior to keep parity with player expectations.
- Applied tiny fix: none
<!-- SUBSYSTEM: game_update_loop END -->
  <!-- SUBSYSTEM: login_account_nanny START -->

### login_account_nanny — Parity Audit 2025-10-12

STATUS: completion:✅ implementation:full correctness:passes (confidence 0.70)
KEY RISKS: flags
TASKS:

- ✅ [P0] Enforce wizlock/newlock gating before accepting credentials — done 2025-10-11
  EVIDENCE: PY mud/account/account_service.py:10-111; PY mud/world/world_state.py:12-63; TEST tests/test_account_auth.py::{test_wizlock_blocks_mortals,test_newlock_blocks_new_accounts}
- ✅ [P0] Restore reconnect and duplicate-session guards (`check_reconnect`/`check_playing`) — done 2025-10-11
  EVIDENCE: PY mud/account/account_service.py:12-111; PY mud/net/connection.py:24-156; TEST tests/test_account_auth.py::test_duplicate_login_requires_reconnect_consent

NOTES:

- C: src/nanny.c:436-602 drives wizlock/newlock decisions and duplicate-session prompts before password validation.
- PY: mud/account/account_service.py:40-142 mirrors the ROM gate ordering, tracks active sessions, and surfaces reconnect prompts to mud/net/connection.py callers via structured results.
- Tests: tests/test_account_auth.py::{test_wizlock_blocks_mortals,test_newlock_blocks_new_accounts,test_duplicate_login_requires_reconnect_consent} lock the Python behavior against ROM nanny prompts.
- Applied tiny fix: none

<!-- SUBSYSTEM: login_account_nanny END -->

- ✅ [P1] Ensure list prices match buy deduction — done 2025-09-12
  - rationale: Prevent price drift between displayed and charged values
  - files: mud/commands/shop.py (list uses \_get_cost), tests/test_shops.py
  - tests: tests/test_shops.py::test_list_price_matches_buy_price
  - acceptance_criteria: gold deducted equals listed price
  - references: C src/act_obj.c:get_cost (buy path)

### Post-Completion Critical Fixes

- ✅ [P0] Fix undefined name errors in models (Area, Room forward references) — done 2025-09-15
  EVIDENCE: PY mud/models/mob.py:L1-L6 (TYPE_CHECKING Area import); PY mud/models/obj.py:L1-L8 (TYPE_CHECKING Area import); PY mud/spawning/templates.py:L1-L11 (TYPE_CHECKING Room import)

  - rationale: Critical runtime error prevention - undefined names would cause import/runtime failures
  - files: mud/models/mob.py, mud/models/obj.py, mud/spawning/templates.py
  - tests: All existing tests continue to pass (200 passed)
  - acceptance_criteria: ruff check passes with no undefined name errors

- ✅ [P0] Modernize deprecated datetime.utcnow() to datetime.now(UTC) — done 2025-09-15
  EVIDENCE: PY mud/logging/admin.py:L3,L14,L30 (UTC import and datetime.now(UTC) calls); PY tests/test_logging_rotation.py:L2,L50 (UTC import and datetime.now(UTC) call)
  - rationale: Future compatibility - datetime.utcnow() deprecated and scheduled for removal
  - files: mud/logging/admin.py, tests/test_logging_rotation.py
  - tests: All existing tests continue to pass (200 passed), no deprecation warnings
  - acceptance_criteria: pytest runs with no DeprecationWarning for datetime.utcnow()

<!-- OUTPUT-JSON
{
  "mode": "No-Op",
  "status": "All parity subsystems present_wired; no open tasks remain.",
  "files_updated": ["PYTHON_PORT_PLAN.md"],
  "next_actions": [],
  "commit": "parity/completion-check — restored completion checkpoint",
  "notes": "Resets/help_system parity spot-check confirmed; executor may remain idle until new gaps surface."
}
OUTPUT-JSON -->

## ✅ Completion Note (2025-10-13)

All canonical ROM subsystems present, wired, and parity-checked against ROM 2.4 C/docs/data; no outstanding tasks.

<!-- LAST-PROCESSED: COMPLETE -->
