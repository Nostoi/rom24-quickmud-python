# C/Python Cross-Reference

| System | C Modules | Python Modules | Status |
| --- | --- | --- | --- |
| Networking loop | `comm.c` | `mud/net/`, `mud/server.py` | Ported (present_wired) — async telnet server and sessions |
| Command interpreter & basic commands | `interp.c`, `act_move.c`, `act_obj.c`, `act_comm.c`, `act_wiz.c` | `mud/commands/` | Ported (present_wired) — dispatcher + core commands |
| World loading | `db.c`, `db2.c` | `mud/loaders/`, `mud/registry.py` | Ported (present_wired) — area/help/social loaders and registries |
| Reset/spawning | `update.c` (resets) | `mud/spawning/` | Ported (present_wired) — reset handler + tests |
| Weather & time | `update.c` (weather/time) | `mud/game_loop.py`, `mud/time.py` | Ported (present_wired) — tick cadence + sunrise/sunset |
| Data models | `merc.h` structs | `mud/models/` | Ported (present_wired) — dataclasses + constants/tables |
| Persistence | `save.c` | `mud/persistence.py`, `mud/db/` | Ported (present_wired) — JSON/DB saves, golden tests |
| Accounts & security | `nanny.c`, `sha256.c`, `ban.c` | `mud/account/`, `mud/security/` | Ported (present_wired) — login flow, bans, hashing |
| Combat engine | `fight.c` | `mud/combat/engine.py` | Ported (present_wired) — hit/THAC0 tests in place |
| Skills & spells | `skills.c`, `magic.c`, `magic2.c` | `mud/skills/`, `mud/affects/saves.py` | Partial — registry and saves; spell set incomplete |
| Shops & economy | `act_obj.c` (buy/sell), `healer.c` | `mud/commands/shop.py` | Partial — shop buy/sell; healer pending |
| OLC / Builders | `olc.c`, `olc_act.c`, `olc_save.c`, `olc_mpcode.c`, `hedit.c` | `mud/commands/build.py` | Partial — basic room edits; mpcode/save editors pending |
| Mob programs | `mob_prog.c`, `mob_cmds.c` | `mud/mobprog.py` | Partial — core runner; mob command set pending |
| InterMUD | `imc.c` | `mud/imc/`, `mud/commands/imc.py` | Partial — feature-flagged IMC protocol parsers |
| Tables/flags | `tables.c`, `flags.c`, `bit.c`, `lookup.c` | `mud/models/constants.py` | Ported/absorbed — IntEnum/IntFlag + lookups |
| Utilities | `string.c`, `mem.c`, `recycle.c`, `music.c`, `scan.c`, `alias.c`, `act_enter.c` | various | Pending/NA — see c_to_python_file_coverage.md for details |
