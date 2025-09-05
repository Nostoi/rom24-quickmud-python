# C/Python Cross-Reference

The legacy `src/` directory has been removed; C module names below are kept for
historical reference only.

| System | C Modules | Python Modules | Status |
| --- | --- | --- | --- |
| Networking loop | – | `mud/net/`, `mud/server.py` | Python telnet server handles login, prompts, and ANSI |
| Command interpreter & basic commands | `interp.c`, `act_move.c`, `act_obj.c`, `act_wiz.c` | `mud/commands/` | Python dispatcher covers movement, communication (say/tell/shout with channel mute/ban), inventory, admin; supports abbreviations & permission checks |
| World loading | `db.c`, `db2.c` | `mud/loaders/`, `mud/registry.py` | Python loaders parse areas into world registry; legacy C loader removed |
| Reset/spawning | `update.c` (resets) | `mud/spawning/` | Python scheduler clears and repopulates areas; legacy C reset code removed |
| Game update loop | `update.c` | `mud/update.py` | Python tick handler regenerates resources, advances weather, runs timed events, and calls area resets |
| Data models | `merc.h` structs | `mud/models/` | Reset logic now uses schema dataclasses instead of `merc.h` structs; runtime dataclasses added for shops, skills, helps, socials |
| Persistence | `save.c` | `mud/persistence.py`, `mud/db/` | Characters saved to JSON with atomic file replacement |
| Accounts & security | `sha256.c` | `mud/account/`, `mud/security/`, `mud/net/connection.py` | Python handles account creation, bcrypt hashing, and login flow |
| Combat engine | `fight.c` | `mud/combat/` | Python engine resolves hit/miss rolls and death cleanup |
| Skills & spells | `skills.c`, `magic.c`, `magic2.c` | `mud/skills/` | JSON-driven registry dispatches skill handlers |
| Character advancement | `update.c`, `act_info.c` | `mud/advancement.py`, `mud/commands/advancement.py` | Python handles experience, leveling, practice, and training |
| Shops & economy | `healer.c`, shop logic in other files | `mud/commands/shop.py`, `mud/loaders/shop_loader.py` | Python lists, buys, and sells items using profit margins |
| Message boards & notes | `board.c` | `mud/notes.py`, `mud/commands/notes.py` | Notes persisted to JSON and accessed via Python commands |
| OLC / Builders | `olc.c`, `olc_act.c`, `olc_save.c`, `olc_mpcode.c` | `mud/commands/olc.py` | Admin in-game editing commands |
| Mob programs | `mob_prog.c`, `mob_cmds.c` | `mud/mobprog.py` | Basic trigger handling and interpreter |
| InterMUD | `imc.c` | – | Not yet ported; legacy IMC code removed |

