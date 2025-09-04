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

## 3. Convert legacy data files to JSON
3.1 ✅ Write conversion scripts in Python that parse existing `.are` files and output JSON using the schemas above.
    - Added `mud/scripts/convert_are_to_json.py` to transform `.are` files into schema-compliant JSON.
3.2 Store converted JSON in a new `data/` directory, mirroring the hierarchy by area name.
3.3 Create tests that load sample areas (e.g., Midgaard) from JSON and assert that room/mob/object counts match the original `.are` files.

## 4. Implement Python data models
4.1 Create `dataclasses` in `mud/models/` mirroring the JSON schemas.
4.2 Add serialization/deserialization helpers to read/write JSON and handle default values.
4.3 Replace legacy models referencing `merc.h` structures with these new dataclasses.

## 5. Replace C subsystems with Python equivalents
5.1 **World loading & resets** – implement reset logic in Python to spawn mobs/objects per area definitions.
5.2 **Command interpreter** – expand existing dispatcher to cover all player commands currently implemented in C.
5.3 **Combat engine** – port attack rounds, damage calculations, and status effects; ensure turn‑based loop is replicated.
5.4 **Skills & spells** – create a registry of skill/spell functions in Python, reading definitions from JSON.
5.5 **Character advancement** – implement experience, leveling, and class/race modifiers.
5.6 **Shops & economy** – port shop data, buying/selling logic, and currency handling.
5.7 **Persistence** – replace C save files with JSON; implement load/save for players and world state.
5.8 **Networking** – use existing async telnet server; gradually remove any remaining C networking code.

## 6. Testing and validation
6.1 Expand `pytest` suite to cover each subsystem as it is ported.
6.2 Add integration tests that run a small world, execute a scripted player session, and verify outputs.
6.3 Use CI to run tests and static analysis (ruff/flake8, mypy) on every commit.

## 7. Decommission C code
7.1 As Python features reach parity, remove the corresponding C files and build steps from `src/` and the makefiles.
7.2 Update documentation to describe the new Python‑only architecture.
7.3 Ensure the Docker image and deployment scripts start the Python server exclusively.

## 8. Future enhancements
8.1 Consider a plugin system for content or rules modifications.
8.2 Evaluate performance; profile hotspots and optimize or re‑implement critical paths in Cython/Rust if necessary.

## 9. Milestone tracking
9.1 Track progress in the issue tracker using milestones for each major subsystem (world, combat, skills, etc.).
9.2 Define completion criteria for each milestone to ensure the port remains on schedule.

This plan should be followed iteratively: pick a subsystem, define JSON, port logic to Python, write tests, and remove the old C code once feature parity is reached.
