# C/Python Cross-Reference

| System | C Modules | Python Modules | Status |
| --- | --- | --- | --- |
| Networking loop | `comm.c` | `mud/net/`, `mud/server.py` | Python telnet server mirrors network loop; C loop still used in legacy engine |
| Command interpreter & basic commands | `interp.c`, `act_move.c`, `act_obj.c`, `act_comm.c`, `act_wiz.c` | `mud/commands/` | Python dispatcher covers movement, communication, inventory, admin |
| World loading | `db.c`, `db2.c` | `mud/loaders/`, `mud/registry.py` | Python loaders parse areas into world registry; C loader still serves legacy runtime |
| Reset/spawning | `update.c` (resets) | `mud/spawning/` | Python spawning handles tests; C update loop still authoritative |
| Data models | `merc.h` structs | `mud/models/` | Dataclasses mirror C structures but are not yet integrated |
| Persistence | `save.c` | `mud/db/` | Python uses SQLAlchemy for accounts and inventories; C still saves characters |
| Accounts & security | `nanny.c`, `sha256.c` | `mud/account/`, `mud/security/` | Python handles account creation and hashing; login flow incomplete |
| Combat engine | `fight.c` | – | Not yet ported |
| Skills & spells | `skills.c`, `magic.c`, `magic2.c` | – | Not yet ported |
| Shops & economy | `healer.c`, shop logic in other files | – | Not yet ported |
| OLC / Builders | `olc.c`, `olc_act.c`, `olc_save.c`, `olc_mpcode.c` | – | Not yet ported |
| Mob programs | `mob_prog.c`, `mob_cmds.c` | – | Not yet ported |
| InterMUD | `imc.c` | – | Not yet ported |

