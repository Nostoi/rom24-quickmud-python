# Python Conversion Plan for QuickMUD

## Overview
This document outlines the steps needed to port the remaining ROM 2.4 QuickMUD C codebase to Python. It also describes how to migrate existing game data (rooms, characters, items, etc.) into JSON so the Python engine can consume it directly.

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
    - Added admin-only `@setroom`, `@setobj`, and `@setmob` commands to modify room data and mob/object prototypes with tests validating edits.
5.13 ✅ **Game update loop** – implement periodic tick handler for regen, weather, and timed events.
    - Added `update_tick` for regeneration, weather cycling, timed events, and area resets with tests.
5.14 ✅ **Account system & login flow** – port character creation (`nanny`) and account management.
    - Telnet connection now prompts for username/password and creates/selects characters.
    - Added tests exercising account creation and login flow.
5.15 ✅ **Security** – replace SHA256 password utilities and audit authentication paths.
    - Replaced custom PBKDF2 code with bcrypt hashing, updated seed data and tests, and verified login uses secure checks.

## 6. Testing and validation
6.1 ✅ Expand `pytest` suite to cover each subsystem as it is ported.
    - Tests now exercise world loading, command dispatch, combat, skills, advancement, shops, persistence, networking, communication, boards, mob programs, online creation, update loop, login flow, and security.
6.2 ✅ Add integration tests that run a small world, execute a scripted player session, and verify outputs.
    - Added scripted telnet session test covering login, movement, and chat.
6.3 ✅ Use CI to run tests and static analysis (ruff/flake8, mypy) on every commit.
    - GitHub workflow lints, type-checks, and tests core modules and their suites on each push or PR.
6.4 ✅ Measure code coverage and enforce minimum thresholds in CI.
    - CI runs pytest with coverage and fails if overall coverage drops below 80%.

## 7. Decommission C code
7.1 ✅ As Python features reach parity, remove the corresponding C files and build steps from `src/` and the makefiles.
    - Deleted the entire legacy `src/` directory and its makefiles, leaving Python as the sole codebase.
7.2 Update documentation to describe the new Python‑only architecture.
7.3 Ensure the Docker image and deployment scripts start the Python server exclusively.

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
