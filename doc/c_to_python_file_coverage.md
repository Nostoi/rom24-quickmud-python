# C → Python File Coverage Audit

This inventory enumerates each C module under `src/` and its Python counterpart(s), mapped to a canonical subsystem. Status reflects current port coverage. Update idempotently when modules change.

| C file | Subsystem(s) | Python target(s) | Status | Notes |
| --- | --- | --- | --- | --- |
| act_comm.c | channels | mud/commands/communication.py | ported | say/tell/shout wired and tested |
| act_enter.c | movement_encumbrance | – | pending | enter/leave/portal flows not implemented |
| act_info.c | help_system, world_loader | mud/commands/help.py; mud/world/look.py | partial | help ported; look/info split |
| act_move.c | movement_encumbrance | mud/world/movement.py; mud/commands/movement.py | ported | direction commands wired |
| act_obj.c | shops_economy | mud/commands/inventory.py; mud/commands/shop.py | partial | buy/sell present; full obj ops ongoing |
| act_wiz.c | wiznet_imm, logging_admin | mud/wiznet.py; mud/logging/admin.py | ported | wiznet + admin logging |
| alias.c | command_interpreter | – | pending | user-defined aliases unimplemented |
| ban.c | security_auth_bans | mud/security/bans.py; mud/commands/admin_commands.py | ported | load/save bans + commands |
| bit.c | flags | mud/models/constants.py | absorbed | IntFlag supersedes bit ops |
| board.c | boards_notes | mud/notes.py; mud/commands/notes.py | ported | board load/save + notes |
| comm.c | networking_telnet | mud/net/telnet_server.py; mud/net/session.py | ported | async telnet server |
| const.c | tables/flags | mud/models/constants.py | ported | enums/constants mirrored |
| db.c | world_loader, resets | mud/loaders/*; mud/spawning/reset_handler.py | ported | area/loaders + reset tick |
| db2.c | socials, world_loader | mud/loaders/social_loader.py | ported | socials loader implemented |
| effects.c | affects_saves | mud/affects/saves.py | partial | core saves/IMM/RES/VULN done |
| fight.c | combat | mud/combat/engine.py | ported | combat engine + THAC0 tests |
| flags.c | tables/flags | mud/models/constants.py | ported | flag tables as IntFlag |
| handler.c | affects_saves | mud/affects/saves.py | partial | check_immune parity implemented |
| healer.c | shops_economy | – | pending | healer NPC shop logic TBD |
| hedit.c | olc_builders | – | pending | help editor not implemented |
| imc.c | imc_chat | mud/imc/; mud/commands/imc.py | partial | feature-flagged parsers |
| interp.c | command_interpreter | mud/commands/dispatcher.py | ported | dispatcher + aliases table |
| lookup.c | tables/flags | mud/models/constants.py | absorbed | lookups via Enums |
| magic.c | skills_spells, affects_saves | mud/skills/; mud/affects/saves.py | partial | saves parity; spells partial |
| magic2.c | skills_spells | – | pending | extended spells |
| mem.c | utilities | – | n/a | Python GC |
| mob_cmds.c | mob_programs | – | pending | mob command interpreter |
| mob_prog.c | mob_programs | mud/mobprog.py | partial | engine present; command set pending |
| music.c | utilities | – | pending | songs/music not ported |
| nanny.c | login_account_nanny | mud/account/account_service.py | ported | account/login flows |
| olc.c | olc_builders | mud/commands/build.py | partial | basic redit; save/mpcode pending |
| olc_act.c | olc_builders | mud/commands/build.py | partial | action handlers subset |
| olc_mpcode.c | olc_builders, mob_programs | – | pending | mpcode editor |
| olc_save.c | olc_builders | – | pending | OLC save routines |
| recycle.c | utilities | – | n/a | Python memory management |
| save.c | persistence | mud/persistence.py; mud/models/player_json.py | ported | player/object saves |
| scan.c | commands | – | pending | scan command |
| sha256.c | security_auth_bans | mud/security/hash_utils.py | ported | hashing implemented |
| skills.c | skills_spells | mud/skills/registry.py; mud/skills/handlers.py | ported | registry + handlers |
| special.c | npc_spec_funs | mud/spec_funs.py | ported | spec fun runner |
| string.c | utilities | – | n/a | Python string utils |
| tables.c | skills_spells, stats_position | mud/models/constants.py; mud/models/skill.py | ported | tables mirrored |
| update.c | game_update_loop, weather, resets | mud/game_loop.py | ported | tick cadence + updates |

