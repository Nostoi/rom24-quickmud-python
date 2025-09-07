# Python Module Inventory

## Core modules in `mud/`

| Module | Purpose | C Feature Equivalent |
| --- | --- | --- |
| `net/` & `server.py` | Async telnet server and connection handling | `comm.c` network loop |
| `commands/` | Command dispatcher and basic commands (movement, inventory, communication, admin) | `interp.c`, `act_move.c`, `act_obj.c`, `act_comm.c`, `act_wiz.c` |
| `world/` | World state management, movement helpers, look | `act_move.c`, `act_info.c` |
| `loaders/` | Parse legacy area files into Python objects | `db.c`, `db2.c` |
| `spawning/` | Reset handling and spawning of mobs/objects | `update.c` resets |
| `models/` | Dataclasses mirroring MUD structures (rooms, mobs, objects, characters, skills, shops) | `merc.h` structs |
| `registry.py` | Global registries for rooms, mobs, objects, areas | `db.c` tables |
| `db/` | SQLAlchemy models and persistence helpers | `save.c`, database portions of `db.c` |
| `account/` & `security/` | Account management and password hashing | `nanny.c`, `sha256.c` |
| `network/` | Websocket server (new functionality) | – |

- `schemas/skill.schema.json` formalizes skill and spell metadata for use with `SkillJson`.
- `schemas/help.schema.json` captures help entry text and levels for `HelpJson`.
- `schemas/social.schema.json` defines social command messages for `SocialJson`.

## Tests in `tests/`

| Test Module | Feature Verified |
| --- | --- |
| `test_world.py` | Movement and room descriptions |
| `test_commands.py` | Command processing sequence |
| `test_admin_commands.py` | Wizard/admin commands |
| `test_spawning.py` | Reset spawning logic |
| `test_load_midgaard.py` | Area file loading |
| `test_account_auth.py` | Account creation and authentication |
| `test_inventory_persistence.py` | Saving/loading inventories |
| `test_agent_interface.py` | AI agent command interface |
| `test_model_instantiation.py` | Dataclass construction |
| `test_are_conversion.py` | `.are` to JSON conversion produces valid schema |
| `test_schema_validation.py` | JSON schemas remain valid |
| `test_area_counts.py` | Area JSON preserves room/mob/object counts |