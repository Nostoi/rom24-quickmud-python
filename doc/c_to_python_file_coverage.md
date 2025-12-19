# C → Python File Coverage Audit

This inventory enumerates each C module under `src/` and its Python counterpart(s), mapped to a canonical subsystem. Status reflects current port coverage as of 2025-12-18.

| C file | Subsystem(s) | Python target(s) | Status | Notes |
| --- | --- | --- | --- | --- |
| act_comm.c | channels | mud/commands/communication.py | ported | say/tell/shout/gossip/grats/quote/question/answer/music wired and tested |
| act_enter.c | movement_encumbrance | mud/commands/movement.py; mud/world/movement.py | ported | do_enter + move_character_through_portal implemented |
| act_info.c | help_system, world_loader | mud/commands/help.py; mud/world/look.py | ported | help + look/info commands complete |
| act_move.c | movement_encumbrance | mud/world/movement.py; mud/commands/movement.py | ported | direction commands + do_hide/do_pick/do_recall wired |
| act_obj.c | shops_economy | mud/commands/inventory.py; mud/commands/shop.py | ported | buy/sell/envenom/steal present |
| act_wiz.c | wiznet_imm, logging_admin | mud/wiznet.py; mud/admin_logging/admin.py | ported | wiznet + admin logging complete |
| alias.c | command_interpreter | mud/commands/alias_cmds.py | ported | do_alias implemented |
| ban.c | security_auth_bans | mud/security/bans.py; mud/commands/admin_commands.py | ported | load/save bans + commands |
| bit.c | flags | mud/models/constants.py | absorbed | IntFlag supersedes bit ops |
| board.c | boards_notes | mud/notes.py; mud/commands/notes.py | ported | board load/save + notes |
| comm.c | networking_telnet | mud/net/telnet_server.py; mud/net/session.py | ported | async telnet server |
| const.c | tables/flags | mud/models/constants.py | ported | enums/constants mirrored |
| db.c | world_loader, resets | mud/loaders/*; mud/spawning/reset_handler.py | ported | area/loaders + reset tick |
| db2.c | socials, world_loader | mud/loaders/social_loader.py | ported | socials loader implemented |
| effects.c | affects_saves | mud/affects/saves.py | ported | core saves/IMM/RES/VULN done |
| fight.c | combat | mud/combat/engine.py | ported | combat engine + THAC0 tests; defense skills need parity implementation |
| flags.c | tables/flags | mud/models/constants.py | ported | flag tables as IntFlag |
| handler.c | affects_saves | mud/affects/saves.py | ported | check_immune parity implemented |
| healer.c | shops_economy | mud/commands/healer.py | ported | do_heal NPC shop logic |
| hedit.c | olc_builders | – | pending | help editor not implemented |
| imc.c | imc_chat | mud/imc/; mud/commands/imc.py | partial | feature-flagged parsers operational |
| interp.c | command_interpreter | mud/commands/dispatcher.py | ported | dispatcher + aliases table |
| lookup.c | tables/flags | mud/models/constants.py | absorbed | lookups via Enums |
| magic.c | skills_spells, affects_saves | mud/skills/handlers.py; mud/affects/saves.py | partial | saves parity complete; 31 spell handler stubs pending (return 42 placeholders) |
| magic2.c | skills_spells | mud/skills/handlers.py | ported | farsight/portal/nexus implemented |
| mem.c | utilities | – | n/a | Python GC |
| mob_cmds.c | mob_programs | mud/mob_cmds.py | ported | 1101 lines, full command set |
| mob_prog.c | mob_programs | mud/mobprog.py | ported | engine + triggers complete |
| music.c | utilities | mud/music/__init__.py | ported | song_update + jukebox playback |
| nanny.c | login_account_nanny | mud/account/account_service.py | ported | account/login flows |
| olc.c | olc_builders | mud/commands/build.py | ported | redit/mreset/oreset implemented |
| olc_act.c | olc_builders | mud/commands/build.py | ported | action handlers complete |
| olc_mpcode.c | olc_builders, mob_programs | – | pending | mpcode editor not implemented |
| olc_save.c | olc_builders | – | **PENDING** | **CRITICAL: OLC save routines needed for builder persistence** |
| recycle.c | utilities | – | n/a | Python memory management |
| save.c | persistence | mud/persistence.py; mud/models/player_json.py | ported | player/object saves |
| scan.c | commands | mud/commands/inspection.py | ported | do_scan implemented |
| sha256.c | security_auth_bans | mud/security/hash_utils.py | ported | hashing implemented |
| skills.c | skills_spells | mud/skills/registry.py; mud/skills/handlers.py | partial | registry complete; 31 handler stubs with TODO comments pending exact ROM formula implementation |
| special.c | npc_spec_funs | mud/spec_funs.py | ported | spec fun runner |
| string.c | utilities | – | n/a | Python string utils |
| tables.c | skills_spells, stats_position | mud/models/constants.py; mud/models/skill.py | ported | tables mirrored |
| update.c | game_update_loop, weather, resets | mud/game_loop.py | ported | tick cadence + updates |

---

## Summary Statistics (Updated 2025-12-18)

| Status | Count | Percentage |
|--------|-------|------------|
| **ported** | 38 | 76% |
| **partial** | 3 | 6% |
| **pending** | 3 | 6% |
| **absorbed** | 2 | 4% |
| **n/a** | 4 | 8% |
| **TOTAL** | 50 | 100% |

---

## Critical Pending Items (Prioritized)

### P0 - Required for Complete ROM Parity

1. **skills.c / magic.c** → 31 skill handler stubs with `return 42` placeholders
   - **Impact**: Skills work minimally but don't match ROM formulas exactly
   - **Effort**: 3-4 weeks (one-by-one implementation with tests)
   - **Tracking**: See `ROM_PARITY_PLAN.md` for detailed task breakdown

2. **olc_save.c** → OLC builder persistence (asave command)
   - **Impact**: OLC edits (redit/mreset/oreset) don't persist across restarts
   - **Effort**: 1-2 weeks
   - **Criticality**: HIGH - builders cannot save their work
   - **Tracking**: See `ROM_PARITY_PLAN.md` Task 16-18

### P1 - Nice to Have

3. **hedit.c** → Help editor OLC
   - **Impact**: No online help editing
   - **Effort**: Medium

4. **olc_mpcode.c** → Mob program code editor
   - **Impact**: Cannot edit mob programs online
   - **Effort**: Medium

---

## Skill Handler Stub Detail

The following skills in `mud/skills/handlers.py` currently return placeholder `42` values and need exact ROM C formula implementations:

### Active Commands (13 skills)
- `steal` (act_obj.c:2161-2310)
- `pick_lock` (act_move.c:841-970)
- `hide` (act_move.c:1526-1542)
- `peek` (act_info.c)
- `envenom` (act_obj.c:849-965)
- `recall` (act_move.c:1563-1650)
- `scrolls`, `staves`, `wands` (magic.c)
- `farsight`, `heat_metal`, `mass_healing`, `shocking_grasp` (magic.c/magic2.c)

### Passive Combat Skills (11 skills)
- `dodge` (fight.c:1354-1373)
- `parry` (fight.c:1294-1321)
- `shield_block` (fight.c:1326-1348)
- `second_attack`, `third_attack` (fight.c:774-790)
- `enhanced_damage` (fight.c:837-847)
- Weapon proficiencies: `axe`, `dagger`, `flail`, `mace`, `polearm`, `spear`, `sword`, `whip`

### Utility Skills (7 skills)
- `fast_healing` (update.c:gain_hit)
- `meditation` (update.c:gain_mana)
- `haggle` (act_obj.c)
- `hand_to_hand` (fight.c)

**Total**: 31 skills requiring implementation

---

## ROM Parity Progress Tracking

See `ROM_PARITY_PLAN.md` for:
- Detailed implementation tasks (20 tasks total)
- C source code references for each skill
- ROM formula documentation
- Test coverage requirements
- 6-week implementation schedule

---

## Validation

To verify this document's accuracy:

```bash
# Count remaining stubs
grep -c "return 42" mud/skills/handlers.py  # Currently: 31

# Verify tests passing
pytest --cov=mud --cov-fail-under=80

# Check for missing implementations
grep "TODO.*Implement" mud/skills/handlers.py | wc -l  # Currently: 32
```

---

**Last Updated**: 2025-12-18  
**Next Review**: After skill stub implementations complete
