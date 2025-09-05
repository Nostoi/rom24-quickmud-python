# C/Python Cross-Reference

| System | C Modules | Python Modules | Status |
| --- | --- | --- | --- |
| Networking loop | `comm.c` | `mud/net/`, `mud/server.py` | Python telnet server mirrors network loop; C loop still used in legacy engine |
| Command interpreter & basic commands | `interp.c`, `act_move.c`, `act_obj.c`, `act_comm.c`, `act_wiz.c` | `mud/commands/` | Python dispatcher covers movement, communication, inventory, admin; supports abbreviations & permission checks |
| World loading | `db.c`, `db2.c` | `mud/loaders/`, `mud/registry.py` | Python loaders parse areas into world registry; C loader still serves legacy runtime |
| Reset/spawning | `update.c` (resets) | `mud/spawning/` | Python scheduler clears and repopulates areas; C update loop unused in tests |
| Data models | `merc.h` structs | `mud/models/` | Reset logic now uses schema dataclasses instead of `merc.h` structs; runtime dataclasses added for shops, skills, helps, socials |
| Persistence | `save.c` | `mud/persistence.py`, `mud/db/` | Characters saved to JSON with atomic file replacement |
| Accounts & security | `nanny.c`, `sha256.c` | `mud/account/`, `mud/security/` | Python handles account creation and hashing; login flow incomplete |
| Combat engine | `fight.c` | `mud/combat/` | Python engine resolves hit/miss rolls and death cleanup |
| Skills & spells | `skills.c`, `magic.c`, `magic2.c` | `mud/skills/` | JSON-driven registry dispatches skill handlers |
| Character advancement | `update.c`, `act_info.c` | `mud/advancement.py`, `mud/commands/advancement.py` | Python handles experience, leveling, practice, and training |
| Shops & economy | `healer.c`, shop logic in other files | `mud/commands/shop.py`, `mud/loaders/shop_loader.py` | Python lists, buys, and sells items using profit margins |
| OLC / Builders | `olc.c`, `olc_act.c`, `olc_save.c`, `olc_mpcode.c` | – | Not yet ported |
| Mob programs | `mob_prog.c`, `mob_cmds.c` | – | Not yet ported |
| InterMUD | `imc.c` | – | Not yet ported |

