<!-- LAST-PROCESSED: logging_admin -->
<!-- DO-NOT-SELECT-SECTIONS: 8,10 -->
<!-- SUBSYSTEM-CATALOG: combat, skills_spells, affects_saves, command_interpreter, socials, channels, wiznet_imm,
world_loader, resets, weather, time_daynight, movement_encumbrance, stats_position, shops_economy, boards_notes,
help_system, mob_programs, npc_spec_funs, game_update_loop, persistence, login_account_nanny, networking_telnet,
security_auth_bans, logging_admin, olc_builders -->
# Python Conversion Plan for QuickMUD

## Overview
This document outlines the steps needed to port the remaining ROM 2.4 QuickMUD C codebase to Python. It also describes how to migrate existing game data (rooms, characters, items, etc.) into JSON so the Python engine can consume it directly.

## System Inventory & Coverage Matrix
<!-- COVERAGE-START -->
| subsystem | status | evidence | tests |
|---|---|---|---|
| combat | present_wired | mud/combat/engine.py:9 | tests/test_combat.py |
| skills_spells | present_wired | mud/skills/registry.py:13 | tests/test_skill_registry.py |
| affects_saves | stub_or_partial | mud/models/constants.py:125-161; mud/models/character.py:100-129 | tests/test_affects.py |
| command_interpreter | present_wired | mud/commands/dispatcher.py:29-55 | tests/test_commands.py |
| socials | stub_or_partial | mud/models/social.py:27-52 | tests/test_socials.py |
| channels | present_wired | mud/commands/communication.py:8-55 | tests/test_communication.py |
| wiznet_imm | stub_or_partial | mud/wiznet.py:11-58 | tests/test_wiznet.py |
| world_loader | present_wired | mud/loaders/area_loader.py:1-64; mud/loaders/__init__.py:7-20 | tests/test_world.py; tests/test_area_loader.py |
| resets | present_wired | mud/spawning/reset_handler.py:14-40 | tests/test_spawning.py |
| weather | present_wired | mud/game_loop.py:59-68 | tests/test_game_loop.py |
| time_daynight | stub_or_partial | mud/time.py:1-48; mud/game_loop.py:67-85 | tests/test_time_daynight.py |
| movement_encumbrance | stub_or_partial | mud/world/movement.py:19-49 | tests/test_world.py |
| stats_position | present_wired | mud/models/constants.py:27-37 | tests/test_advancement.py |
| shops_economy | present_wired | mud/commands/shop.py:22-64 | tests/test_shops.py |
| boards_notes | present_wired | mud/notes.py:16-33 | tests/test_boards.py |
| help_system | stub_or_partial | mud/models/help.py:8-18 | — |
| mob_programs | present_wired | mud/mobprog.py:12-59 | tests/test_mobprog.py |
| npc_spec_funs | stub_or_partial | mud/models/mob.py:21 | — |
| game_update_loop | present_wired | mud/game_loop.py:65-70 | tests/test_game_loop.py |
| persistence | present_wired | mud/persistence.py:38-74 | tests/test_persistence.py |
| login_account_nanny | present_wired | mud/account/account_service.py:10-37 | tests/test_account_auth.py |
| networking_telnet | present_wired | mud/net/telnet_server.py:9-27 | tests/test_telnet_server.py |
| security_auth_bans | present_wired | mud/security/hash_utils.py:5-20 | tests/test_account_auth.py |
| logging_admin | stub_or_partial | mud/logging/agent_trace.py:5-9 | — |
| olc_builders | present_wired | mud/commands/build.py:4-17 | tests/test_building.py |
<!-- COVERAGE-END -->

## Next Actions (Aggregated P0s)
<!-- NEXT-ACTIONS-START -->
- logging_admin: Log admin commands to `log/admin.log` with timestamps
- logging_admin: Hook logging into admin command handlers
- npc_spec_funs: Build spec_fun registry and invoke during NPC updates
- npc_spec_funs: Load spec_fun names from mob JSON and execute functions
- affects_saves: Implement saving throw resolution using number_mm and c_div with ROM class/level tables
<!-- NEXT-ACTIONS-END -->

## Parity Gaps & Corrections
<!-- PARITY-GAPS-START -->
<!-- AUDITED: affects_saves, socials, wiznet_imm, time_daynight, movement_encumbrance, help_system, npc_spec_funs, logging_admin, world_loader -->

<!-- SUBSYSTEM: affects_saves START -->
### affects_saves — Parity Audit 2025-09-07
STATUS: completion:❌ implementation:partial correctness:unknown (confidence 0.62)
KEY RISKS: flags, RNG
TASKS:
- ✅ [P0] Enumerate all ROM affect flags via IntFlag — acceptance: enumeration matches merc.h bit values — done 2025-09-07
  EVIDENCE: mud/models/constants.py:L125-L158; tests/test_affects.py::test_affect_flag_values
- [P0] Implement saving throw resolution using number_mm and c_div with ROM class/level tables — acceptance: deterministic pass/fail test
  NEEDS CLARIFICATION: ROM saving throw tables and class mapping not yet defined
- ✅ [P0] Apply and remove affects through helpers — acceptance: unit test toggles multiple flags and updates stats — done 2025-09-08
  EVIDENCE: mud/models/character.py:L100-L129; tests/test_affects.py::test_apply_and_remove_affects_updates_stats
- [P1] Persist affects to character saves with correct bit widths — acceptance: save/load round trip preserves flags
- [P2] Achieve ≥80% test coverage for affects_saves — acceptance: coverage report ≥80%
NOTES:
- `Character.affected_by` and `saving_throw` fields lack mechanics (character.py:54,62)
- `AffectFlag` enumerates full ROM bitset (constants.py:125-158)
- Applied tiny fix: markers wrap `AffectFlag` enum only (constants.py:125-161)
- Helper methods update core stats when applying/removing affects (character.py:100-129; tests/test_affects.py:26-38)
- Saving throw tables absent; resolution not implemented
<!-- SUBSYSTEM: affects_saves END -->

<!-- SUBSYSTEM: socials START -->
### socials — Parity Audit 2025-09-06
STATUS: completion:❌ implementation:partial correctness:suspect (confidence 0.60)
KEY RISKS: file_formats, side_effects
TASKS:
- ✅ [P0] Wire social loader and command dispatcher — acceptance: `smile` command sends actor/room/victim messages — done 2025-09-08
  EVIDENCE: mud/commands/dispatcher.py:L87-L97; tests/test_socials.py::test_smile_command_sends_messages
- [P1] Convert `social.are` to JSON with fixed field widths — acceptance: golden JSON matches ROM text layout
- [P2] Add tests to reach ≥80% coverage for socials — acceptance: coverage report ≥80%
NOTES:
- `load_socials` reads JSON into registry (loaders/social_loader.py:1-16)
- Dispatcher falls back to socials when command not found (commands/dispatcher.py:87-97)
- `expand_placeholders` supports `$mself` pronouns (social.py:37-52)
- Applied tiny fix: refined `$mself` pronoun mapping for all sexes; added unit tests (social.py:37-52; tests/test_runtime_models.py:55-72)
- Applied tiny fix: added default-case `$mself` test (tests/test_runtime_models.py:73-79)
<!-- SUBSYSTEM: socials END -->

<!-- SUBSYSTEM: wiznet_imm START -->
### wiznet_imm — Parity Audit 2025-09-08
STATUS: completion:❌ implementation:partial correctness:unknown (confidence 0.86)
KEY RISKS: flags, side_effects
TASKS:
- ✅ [P0] Define wiznet flag bits via IntFlag — acceptance: enumeration matches ROM values — done 2025-09-08
  EVIDENCE: mud/wiznet.py:L11-L36; tests/test_wiznet.py::test_wiznet_flag_values
- ✅ [P0] Implement wiznet broadcast filtering — acceptance: immortal with WIZ_ON receives message; mortal does not — done 2025-09-08
  EVIDENCE: mud/wiznet.py:L43-L58; tests/test_wiznet.py::test_wiznet_broadcast_filtering
- ✅ [P0] Hook `wiznet` command into dispatcher — acceptance: pytest toggles WIZ_ON with `wiznet` command — done 2025-09-07
  EVIDENCE: mud/wiznet.py:L61-L74; tests/test_wiznet.py::test_wiznet_command_toggles_flag
- [P1] Persist wiznet subscriptions to player saves with bit widths — acceptance: save/load round trip retains flags
- [P2] Achieve ≥80% test coverage for wiznet — acceptance: coverage report ≥80%
NOTES:
- Added broadcast helper to filter subscribed immortals (wiznet.py:43-58)
- `Character.wiznet` stores wiznet flag bits (character.py:87)
- Command table registers `wiznet` command (commands/dispatcher.py:18-59)
- Help file documents wiznet usage despite missing code (area/help.are:1278-1286)
<!-- SUBSYSTEM: wiznet_imm END -->

<!-- SUBSYSTEM: world_loader START -->
### world_loader — Parity Audit 2025-09-06
STATUS: completion:❌ implementation:partial correctness:suspect (confidence 0.65)
KEY RISKS: file_formats, indexing
TASKS:
 - ✅ [P0] Parse `#AREADATA` builders/security/flags — acceptance: loader populates fields verified by test — done 2025-09-07
  EVIDENCE: mud/loaders/area_loader.py:L42-L57; tests/test_area_loader.py::test_areadata_parsing
- [P2] Achieve ≥80% test coverage for world_loader — acceptance: coverage report ≥80%
NOTES:
- Parser now reads `#AREADATA` builders, security, and flags (area_loader.py:42-57)
- Tests only verify movement/lookup, not area metadata
- Applied tiny fix: key `area_registry` by `min_vnum`
- Applied tiny fix: reject duplicate area vnums in `area_registry`; added regression test
- Applied tiny fix: enforce `$` sentinel in `area.lst`; test added
- Applied tiny fix: reordered imports in `tests/test_area_loader.py`
<!-- SUBSYSTEM: world_loader END -->

<!-- SUBSYSTEM: time_daynight START -->
### time_daynight — Parity Audit 2025-09-07
STATUS: completion:❌ implementation:absent correctness:fails (confidence 0.91)
KEY RISKS: tick_cadence
TASKS:
- ✅ [P0] Implement ROM `time_info` with hour/day/month/year and sun state — acceptance: unit test advances hour and triggers sunrise — done 2025-09-07
  EVIDENCE: mud/time.py:L8-L45; tests/test_time_daynight.py::test_time_tick_advances_hour_and_triggers_sunrise
- ✅ [P0] Broadcast sunrise/sunset messages to players — acceptance: pytest captures "The sun rises" on transition — done 2025-09-07
  EVIDENCE: mud/game_loop.py:L67-L76; tests/test_time_daynight.py::test_sunrise_broadcasts_to_all_characters
- ✅ [P0] Advance time at ROM tick cadence (4 pulses/hour) — acceptance: tick loop advances hour after 4 pulses — done 2025-09-07
  EVIDENCE: mud/game_loop.py:L73-L85; tests/test_time_daynight.py::test_time_tick_advances_hour_and_triggers_sunrise
- [P1] Persist `time_info` across reboot — acceptance: save/load retains current hour
- [P2] Achieve ≥80% test coverage for time_daynight — acceptance: coverage report ≥80%
NOTES:
- `time_tick` advances hour and broadcasts sunrise/sunset (game_loop.py:67-79)
- `TimeInfo` tracks hour/day/month/year and sunlight (time.py:8-48)
 - Tick cadence now advances hour every four pulses (game_loop.py:73-85)
<!-- SUBSYSTEM: time_daynight END -->

<!-- SUBSYSTEM: movement_encumbrance START -->
### movement_encumbrance — Parity Audit 2025-09-07
STATUS: completion:❌ implementation:partial correctness:unknown (confidence 0.55)
KEY RISKS: lag_wait, side_effects
TASKS:
- ✅ [P0] Enforce carry weight and number limits before movement — acceptance: overweight character cannot move — done 2025-09-07
  EVIDENCE: mud/world/movement.py:L19-L33; tests/test_world.py::test_overweight_character_cannot_move
- ✅ [P0] Update carry weight/number on object pickup, drop, and equip — acceptance: test verifies weight increments — done 2025-09-08
  EVIDENCE: mud/models/character.py:L92-L114; tests/test_encumbrance.py::test_carry_weight_updates_on_pickup_equip_drop
- [P1] Apply wait-state penalties when over limit — acceptance: overweight move adds ROM wait state
- [P2] Achieve ≥80% test coverage for movement_encumbrance — acceptance: coverage report ≥80%
NOTES:
- Movement now blocks when over weight/number limits (world/movement.py:19-33)
- `Character.carry_weight` and `carry_number` never update (character.py:60-61)
- Movement tests ignore encumbrance updates (tests/test_world.py:7-17)
<!-- SUBSYSTEM: movement_encumbrance END -->

<!-- SUBSYSTEM: help_system START -->
### help_system — Parity Audit 2025-09-08
STATUS: completion:❌ implementation:absent correctness:fails (confidence 0.70)
KEY RISKS: file_formats, indexing
TASKS:
- ✅ [P0] Load help entries from JSON and populate registry — acceptance: pytest loads `help.json` and finds `murder` topic — done 2025-09-08
  EVIDENCE: mud/loaders/help_loader.py:L1-L17; tests/test_help_system.py::test_load_help_file_populates_registry
- ✅ [P0] Wire `help` command into dispatcher — acceptance: test runs `help murder` and receives topic text — done 2025-09-08
  EVIDENCE: mud/commands/dispatcher.py:L18-L56; tests/test_help_system.py::test_help_command_returns_topic_text
- [P1] Preserve ROM help file widths in JSON conversion — acceptance: golden file matches `help.are`
- [P2] Achieve ≥80% test coverage for help_system — acceptance: coverage report ≥80%
NOTES:
- `HelpEntry` and `help_registry` placeholder exist without loader (help.py:8-28)
- Dispatcher lacks `help` command (commands/dispatcher.py:32-60)
- No `data/help.json` present for topics (data/)
- No tests exercise help lookup
<!-- SUBSYSTEM: help_system END -->

<!-- SUBSYSTEM: area_format_loader START -->
### area_format_loader — Parity Audit 2025-09-07
STATUS: completion:❌ implementation:partial correctness:suspect (confidence 0.65)
KEY RISKS: file_formats, flags, indexing
TASKS:
- [P0] Verify Midgaard conversion parity (counts & exits) — acceptance: ROOMS/MOBILES/OBJECTS/RESETS/SHOPS/SPECIALS counts match; exit flags/doors/keys verified; golden JSON added
- [P0] Enforce `area.lst` `$` sentinel and duplicate-entry rejection — acceptance: missing/duplicate entries raise errors; unit test asserts failures
- [P1] Preserve `#RESETS` command semantics — acceptance: reset loop reproduces ROM placements on tick; golden-driven test
- [P2] Coverage ≥80% for area_format_loader — acceptance: coverage report ≥80%
NOTES:
- C: `src/db.c:load_area()` handles `#AREADATA`, `#ROOMS`, `#RESETS`, sentinel `$`
- DOC: `doc/area.txt` sections for block layouts; `Rom2.4.doc` reset rules
- ARE: `areas/midgaard.are` as canonical fixture
- PY: `mud/scripts/convert_are_to_json.py`, `mud/loaders/area_loader.py` implement conversion/loading
<!-- SUBSYSTEM: area_format_loader END -->

<!-- SUBSYSTEM: player_save_format START -->
### player_save_format — Parity Audit 2025-09-07
STATUS: completion:❌ implementation:partial correctness:unknown (confidence 0.60)
KEY RISKS: flags, file_formats, side_effects
TASKS:
- [P0] Map `/player/*` fields to JSON preserving bit widths & field order — acceptance: S/L/H bitmasks round-trip; golden fixture player passes
- [P1] Reject malformed legacy saves with precise errors — acceptance: tests cover missing header/footer and bad widths
- [P2] Coverage ≥80% for player_save_format — acceptance: coverage report ≥80%
NOTES:
- C: `src/save.c:save_char_obj()/load_char_obj()` define record layout & bit packing
- DOC: `Rom2.4.doc` save layout notes (stats/flags)
- PLAYER: `/player/*` legacy files (choose sample fixture)
- PY: `mud/persistence.py` save/load; `mud/models/character_json.py` flag fields
<!-- SUBSYSTEM: player_save_format END -->

<!-- SUBSYSTEM: imc_chat START -->
### imc_chat — Parity Audit 2025-09-07
STATUS: completion:❌ implementation:absent correctness:unknown (confidence 0.55)
KEY RISKS: file_formats, side_effects, networking
TASKS:
- [P0] Stub IMC protocol reader/writer behind feature flag — acceptance: sample IMC frames parse/serialize; sockets not opened when disabled
- [P1] Wire no-op dispatcher integration (command visible, gated) — acceptance: help text present; command disabled unless `IMC_ENABLED=True`
- [P2] Coverage ≥80% for imc_chat — acceptance: coverage report ≥80%
NOTES:
- C: `imc/imc.c` framing & message flow
- DOC: any bundled IMC readme/spec in `/imc` (if present)
- PY: (absent) — add `mud/imc/*` module; guard with `IMC_ENABLED`
- Runtime: ensure zero side-effects when disabled
<!-- SUBSYSTEM: imc_chat END -->

<!-- SUBSYSTEM: help_system START -->
### help_system — Parity Audit 2025-09-07
STATUS: completion:❌ implementation:partial correctness:unknown (confidence 0.62)
KEY RISKS: file_formats, indexing
TASKS:
- [P0] Convert `help.are` to JSON respecting width/ordering — acceptance: golden JSON matches ROM layout
- [P0] Wire `help` command lookup & rendering — acceptance: `help murder` returns expected text; case/keyword matching per ROM
- [P2] Coverage ≥80% for help_system — acceptance: coverage report ≥80%
NOTES:
- C: `src/help.c` (or `db.c` help loader) and `interp.c` command behavior
- DOC: `doc/area.txt` help block format; `Rom2.4.doc` help conventions
- ARE: `areas/help.are` (or equivalent) as source
- PY: `mud/loaders/help_loader.py`, `mud/commands/help.py`, `data/help.json`
<!-- SUBSYSTEM: help_system END -->

<!-- SUBSYSTEM: socials START -->
### socials — Parity Audit 2025-09-07
STATUS: completion:❌ implementation:partial correctness:fails (confidence 0.58)
KEY RISKS: file_formats, side_effects
TASKS:
- [P0] Convert `social.are` to JSON per ROM width rules — acceptance: golden JSON matches ROM text layout
- [P0] Wire dispatcher & placeholder expansion — acceptance: `$n/$N/$mself` expansions validated for actor/room/victim lines
- [P2] Coverage ≥80% for socials — acceptance: coverage report ≥80%
NOTES:
- C: `src/socials.c` definitions; `interp.c` dispatch
- DOC: `doc/area.txt` social entry format
- ARE: `areas/social.are` as source
- PY: `mud/loaders/social_loader.py`, `mud/commands/socials.py`, `mud/models/social.py`
<!-- SUBSYSTEM: socials END -->


<!-- SUBSYSTEM: npc_spec_funs START -->
### npc_spec_funs — Parity Audit 2025-09-08
STATUS: completion:❌ implementation:absent correctness:fails (confidence 0.60)
KEY RISKS: flags, side_effects
TASKS:
- [P0] Build spec_fun registry and invoke during NPC updates — acceptance: unit test registers dummy spec and runs via update loop
- [P0] Load spec_fun names from mob JSON and execute functions — acceptance: pytest loads mob with spec_fun and function runs
- [P1] Port core ROM spec functions using number_mm RNG — acceptance: spec_cast_adept test matches expected number_percent sequence
- [P1] Persist spec_fun names across save/load — acceptance: round-trip retains spec_fun string
- [P2] Achieve ≥80% test coverage for npc_spec_funs — acceptance: coverage report ≥80%
NOTES:
- `spec_fun_registry` exists but never invoked (spec_funs.py:4-7)
- `MobIndex.spec_fun` field unused in game loop (mob.py:21)
- Game loop lacks spec_fun hook (game_loop.py:73-79)
<!-- SUBSYSTEM: npc_spec_funs END -->

<!-- SUBSYSTEM: logging_admin START -->
### logging_admin — Parity Audit 2025-09-08
STATUS: completion:❌ implementation:partial correctness:fails (confidence 0.55)
KEY RISKS: file_formats, side_effects
TASKS:
- [P0] Log admin commands to `log/admin.log` with timestamps — acceptance: invoking `ban` writes entry
- [P0] Hook logging into admin command handlers — acceptance: `wiznet` toggling logs action
- [P1] Rotate admin log daily with ROM naming convention — acceptance: midnight tick creates new file
- [P1] Achieve ≥80% test coverage for logging_admin — acceptance: coverage report ≥80%
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
