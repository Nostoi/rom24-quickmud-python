# Python Module Inventory

## Core modules in `mud/`

| Module | Purpose | C Feature Equivalent |
| --- | --- | --- |
| `net/` & `server.py` | Async telnet server, ANSI color translation, connection handling | replaces `comm.c` and `nanny.c` |
| `commands/` | Command dispatcher and basic commands (movement, inventory, communication with channels, admin, shops) | `interp.c`, `act_move.c`, `act_obj.c`, `act_comm.c`, `act_wiz.c`, shop code |
| `world/` | World state management, movement helpers, look | `act_move.c`, `act_info.c` |
| `loaders/` | Parse legacy area files into Python objects | `db.c`, `db2.c` |
| `spawning/` | Reset handling and spawning of mobs/objects | `update.c` resets |
| `update.py` | Periodic tick handler for regen, weather, events, and resets | `update.c` |
| `combat/` | Basic melee resolution and combat helpers | `fight.c` |
| `skills/` | Skill registry and spell handlers | `skills.c`, `magic.c` |
| `advancement.py` | Experience gain, leveling, practice/train | `update.c`, `act_info.c` |
| `models/` | Dataclasses mirroring MUD structures (rooms, mobs, objects, characters, skills, shops) | `merc.h` structs |
| `registry.py` | Global registries for rooms, mobs, objects, areas | `db.c` tables |
| `persistence.py` | JSON save/load for characters and world | `save.c` |
| `notes.py` | Message boards and note handling with JSON persistence | `board.c` |
| `mobprog.py` | Mob program triggers and interpreter | `mob_prog.c` |
| `db/` | SQLAlchemy models and persistence helpers | `save.c`, database portions of `db.c` |
| `account/` & `security/` | Account management, login flow, bcrypt password hashing | `sha256.c` |
| `network/` | Websocket server (new functionality) | – |

- `schemas/skill.schema.json` formalizes skill and spell metadata for use with `SkillJson`.
- `schemas/help.schema.json` captures help entry text and levels for `HelpJson`.
- `schemas/social.schema.json` defines social command messages for `SocialJson`.
- `schemas/board.schema.json` and `schemas/note.schema.json` describe persistent
  message boards and their notes.

## Tests in `tests/`

| Test Module | Feature Verified |
| --- | --- |
| `test_world.py` | Movement and room descriptions |
| `test_commands.py` | Command processing sequence |
| `test_admin_commands.py` | Wizard/admin commands |
| `test_spawning.py` | Reset spawning logic |
| `test_load_midgaard.py` | Area file loading |
| `test_account_auth.py` | Account creation and authentication |
| `test_hash_utils.py` | bcrypt password hashing |
| `test_inventory_persistence.py` | Saving/loading inventories |
| `test_agent_interface.py` | AI agent command interface |
| `test_model_instantiation.py` | Dataclass construction |
| `test_are_conversion.py` | `.are` to JSON conversion produces valid schema |
| `test_schema_validation.py` | JSON schemas remain valid |
| `test_area_counts.py` | Area JSON preserves room/mob/object counts |
| `test_combat.py` | Basic melee hit/miss and death handling |
| `test_skills.py` | Skill registry, mana costs, and failure rates |
| `test_advancement.py` | Level gains, practice, and training |
| `test_shops.py` | Shop listing and transactions |
| `test_telnet_server.py` | Telnet look command and multi-connection chat |
| `test_ansi.py` | ROM color tokens translate to ANSI |
| `test_mobprog.py` | Mob program trigger handling |
| `test_update_loop.py` | Game tick regeneration, weather cycling, timed events, and resets |
| `test_login_flow.py` | Account login and character creation via telnet |
