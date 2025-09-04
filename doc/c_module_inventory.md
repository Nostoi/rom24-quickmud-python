# C Module Inventory

| Module | Responsibility |
| --- | --- |
| act_comm.c | Player communication commands (say, shout, channels) |
| act_enter.c | Enter and exit actions, gate commands |
| act_info.c | Information commands like look, score, help |
| act_move.c | Movement commands (north, south, flee) |
| act_obj.c | Object interactions: get, drop, wear |
| act_wiz.c | Administrative and wizard commands |
| alias.c | Player command aliases |
| ban.c | Site and player banning |
| bit.c | Bit and flag manipulation helpers |
| board.c | In-game message boards and notes |
| comm.c | Network I/O and main game loop |
| const.c | Global constant tables |
| db.c | World database loading, area resets |
| db2.c | Additional world loading helpers |
| effects.c | Status effect utilities |
| fight.c | Combat engine and damage resolution |
| flags.c | Flag table definitions |
| handler.c | Character and object handler functions |
| healer.c | NPC healer shop logic |
| hedit.c | Help-file editor for OLC |
| imc.c | InterMUD communication subsystem |
| interp.c | Command interpreter dispatch |
| lookup.c | Lookup utilities for tables and flags |
| magic.c | Core spell implementations |
| magic2.c | Extended spell implementations |
| mem.c | Custom memory management |
| mob_cmds.c | Mob command interpreter |
| mob_prog.c | Mobile program scripting engine |
| music.c | Song and music support |
| nanny.c | Connection and login state machine |
| olc.c | On-line creation core |
| olc_act.c | OLC action handlers |
| olc_mpcode.c | OLC mob program code editor |
| olc_save.c | OLC save routines |
| recycle.c | Object recycle/free lists |
| save.c | Player and object persistence |
| scan.c | Scan command implementation |
| sha256.c | SHA-256 hashing implementation |
| skills.c | Skill table and skill-specific code |
| special.c | Special procedure handlers for mobiles/objects |
| string.c | String utilities and buffer management |
| tables.c | Skill, spell, and other constant tables |
| update.c | Periodic updates and area resets |
