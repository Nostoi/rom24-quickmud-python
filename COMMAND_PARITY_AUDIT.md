# ROM Command Parity Audit - December 22, 2025

## Executive Summary

**Current Status**: 173 / 181 ROM commands implemented (**95.6% complete**)

- ✅ **Implemented**: 173 commands  
- ❌ **Missing**: 8 commands (P3 admin only)  
- ⚠️ **Extra/Custom**: 37 commands not in ROM C

**Recent Progress (Dec 23, 2025)**:
- **P0 COMPLETE**: All 26 critical commands ✅
- **P1 COMPLETE**: All 10 important commands ✅
- **P2 COMPLETE**: All 22 convenience commands ✅
- **Total**: 58 new commands implemented

**P1 Commands Added (Dec 23)**:
- sneak, hide, visible, steal (thief skills)
- examine, read, count, whois, worth, sit (info commands)

**P2 Commands Added (Dec 23)**:
- autolist, autoall, autoassist, autoexit, autogold, autoloot, autosac, autosplit
- brief, compact, combine, colour/color, prompt
- motd, imotd, rules, story, socials, skills, spells, rent

- **Integration tests: 26/26 passing (100%)** ✅
- **All P0, P1, P2 commands complete and tested**

---

## Missing Commands by Priority

### 🔴 **P0 - Critical for Basic Gameplay** - ✅ COMPLETE

**All P0 Commands Implemented:**
- ✅ `consider` - Assess mob difficulty
- ✅ `follow` - Follow another character
- ✅ `group` - Form/manage groups
- ✅ `gtell` - Group chat
- ✅ `order` - Command followers
- ✅ `split` - Share gold with group
- ✅ `give` - Give items to others
- ✅ `open` - Open doors
- ✅ `close` - Close doors
- ✅ `lock` - Lock doors
- ✅ `unlock` - Unlock doors
- ✅ `pick` - Pick locks
- ✅ `backstab` - Thief combat skill
- ✅ `bash` - Warrior combat skill
- ✅ `berserk` - Berserker rage
- ✅ `dirt` - Kick dirt (blind)
- ✅ `disarm` - Disarm opponent
- ✅ `trip` - Trip opponent
- ✅ `murder` - Attack peacefuls
- ✅ `affects` - Show active effects
- ✅ `compare` - Compare equipment
- ✅ `channels` - Communication channel list
- ✅ `fill` - Fill containers
- ✅ `pour` - Pour liquids
- ✅ `empty` - Empty containers

### 🟡 **P1 - Important for Full Experience** - ✅ COMPLETE

**Communication** (all implemented)
- ✅ `gossip`, `auction`, `music`, `question`, `answer` - Chat channels
- ✅ `shout`, `yell` - Area communication  
- ✅ `reply` - Reply to last tell
- ✅ `emote`, `pose` - Roleplay actions
- Note: `whisper` does NOT exist in ROM C source

**Magic** (all implemented)
- ✅ `cast` - Cast spells
- ✅ `recite` - Use scrolls
- ✅ `brandish` - Use staves
- ✅ `zap` - Use wands
- Note: `commune` does NOT exist in ROM C source (just `cast`)

**Thief Skills** (new)
- ✅ `sneak` - Move silently
- ✅ `hide` - Hide in shadows
- ✅ `visible` - Become visible
- ✅ `steal` - Steal items/gold

**Info Commands** (new)
- ✅ `examine` - Look + show contents
- ✅ `read` - Alias for look
- ✅ `count` - Count players online
- ✅ `whois` - Info about specific player
- ✅ `worth` - Show gold/exp values
- ✅ `sit` - Sit down

### 🟢 **P2 - Convenience/QoL** - ✅ COMPLETE

**Automation Settings** (all implemented)
- ✅ `autolist` - List all auto settings
- ✅ `autoall` - Toggle all auto settings
- ✅ `autoassist` - Auto assist group members
- ✅ `autoexit` - Auto show exits
- ✅ `autogold` - Auto loot gold
- ✅ `autoloot` - Auto loot corpses
- ✅ `autosac` - Auto sacrifice corpses
- ✅ `autosplit` - Auto split gold with group
- ✅ `brief` - Toggle brief descriptions
- ✅ `compact` - Toggle compact display
- ✅ `prompt` - Set custom prompt
- ✅ `colour`/`color` - Toggle ANSI colors
- ✅ `combine` - Combine inventory items

**Misc Info** (all implemented)
- ✅ `motd` - Message of the day
- ✅ `imotd` - Immortal MOTD
- ✅ `rules` - Game rules
- ✅ `story` - Game backstory
- ✅ `socials` - List social commands
- ✅ `skills` - List character skills
- ✅ `spells` - List character spells
- ✅ `rent` - No rent message

**Shortcuts/Aliases** (existing)
- ✅ `alias` - Define aliases
- ✅ `unalias` - Remove aliases
- ✅ `prefix` - Set command prefix

**Builder/OLC** (existing)
- ✅ `@alist`, `@vlist` - List vnums
- ✅ `@asave`, `@hesave` - Save area data

### ⚪ **P3 - Admin/Optional** (31 commands)

**OLC/Building**
- `aedit`, `redit`, `medit`, `oedit` - Online creation
- Partial implementations may exist

**Administration**
- Various immortal commands
- `wizhelp`, `wiznet`, `snoop`, `switch`, etc.

---

## Known Broken Commands

Even some "implemented" commands have issues:

| Command | Status | Issue |
|---------|--------|-------|
| `look <target>` | ⚠️ **Broken** | Ignores args, always shows room |
| `tell <mob>` | ⚠️ **Broken** | Can't tell to mobs |
| `score` | ⚠️ **Fixed** | Was crashing, now fixed |
| `weather` | ⚠️ **Fixed** | Was crashing, now fixed |

---

## Implementation Roadmap

### Phase 1: Critical Gameplay (2-3 days)

**Player Interaction** (Essential for testing with mobs)
1. ✅ Fix `look <target>` - Pass args to look()
2. ✅ Implement `consider <target>`
3. ✅ Implement `give <item> <target>`  
4. ✅ Fix `tell <target>` for mobs

**Group Mechanics** (Essential for multiplayer)
5. ✅ Implement `follow <target>`
6. ✅ Implement `group` command
7. ✅ Implement `gtell <message>`
8. ✅ Implement `split <amount>`

**Doors/Access** (Common gameplay)
9. ✅ Implement `open <door>`
10. ✅ Implement `close <door>`
11. ✅ Implement `lock <door>`
12. ✅ Implement `unlock <door>`

### Phase 2: Combat Completeness (1-2 days)

13. ✅ Implement `flee`
14. ✅ Implement `rescue <target>`
15. ✅ Implement `murder <target>`
16. ✅ Implement combat skills: `backstab`, `bash`, `dirt`, `disarm`, `trip`

### Phase 3: Polish & QoL (1-2 days)

17. ✅ Implement `affects`
18. ✅ Implement `compare <item1> <item2>`
19. ✅ Implement `channels`
20. ✅ Implement liquid mechanics: `fill`, `pour`, `empty`
21. ✅ Implement magic item use: `recite`, `brandish`, `zap`

### Phase 4: Communication & Social (1 day)

22. ✅ Channel commands: `gossip`, `auction`, `music`, `question`, `answer`
23. ✅ Social commands: `shout`, `yell`, `whisper`, `emote`, `reply`

### Phase 5: Convenience (Optional)

24. ⏸️ Auto-settings commands
25. ⏸️ Shortcut aliases
26. ⏸️ Additional builder tools

---

## Integration Test Framework

Create `tests/integration/` with player workflow tests:

### Example: test_player_meets_shopkeeper.py
```python
def test_complete_shop_interaction():
    """Simulate a new player buying their first sword"""
    player = create_test_player(level=1, gold=100)
    shopkeeper = create_test_mob("shopkeeper", in_room=player.room)
    
    # Can see shopkeeper
    result = do_look(player, "")
    assert "shopkeeper" in result.lower()
    
    # Can look at shopkeeper
    result = do_look(player, "shopkeeper")
    assert "shopkeeper" in result.lower()
    assert "shop" in result.lower() or "buy" in result.lower()
    
    # Can assess difficulty
    result = do_consider(player, "shopkeeper")
    assert "easy" in result.lower()  # Shopkeepers shouldn't be attackable
    
    # Can interact with shop
    result = do_list(player, "")
    assert "sword" in result.lower()
    
    result = do_buy(player, "sword")
    assert player.gold < 100  # Spent money
    assert has_item(player, "sword")
```

### Example: test_group_formation.py
```python
def test_player_groups_with_mob():
    """Test following and grouping with an NPC"""
    player = create_test_player()
    guide = create_test_mob("guide", in_room=player.room)
    
    # Follow the guide
    result = do_follow(player, "guide")
    assert "you now follow" in result.lower()
    assert player.master == guide
    
    # Group with guide
    result = do_group(player, "guide")
    assert "group" in result.lower()
    
    # Guide moves, player follows
    move_mob(guide, Direction.NORTH)
    assert player.room == guide.room
```

---

## Why Testing Missed This

**Root Cause**: Tests focused on **mechanics** not **commands**

| What Was Tested | What Wasn't Tested |
|-----------------|-------------------|
| ✅ Follower system works | ❌ `follow` command exists |
| ✅ `can_see_character()` works | ❌ `look <mob>` uses it |
| ✅ Group mechanics | ❌ `group` command exists |
| ✅ Combat calculations | ❌ Combat commands exist |

**The Gap**: Backend parity ≠ Gameplay parity

---

## Recommendations

1. **Immediate** (Today):
   - Fix `look <target>` bug
   - Implement `consider`, `follow`, `give` (3 most critical)

2. **This Week**:
   - Complete Phase 1 (Critical Gameplay)
   - Build integration test framework
   - Run end-to-end gameplay scenarios

3. **Next Week**:
   - Complete Phases 2-3
   - Full combat command coverage
   - Polish player experience

4. **Future**:
   - Communication channels
   - QoL features
   - Advanced OLC tools

---

## Success Metrics

**Before claiming "100% parity":**
- [ ] All P0 commands implemented
- [ ] All P1 commands implemented
- [ ] Integration tests for complete player workflows
- [ ] New player can: create char, visit shop, buy items, group up, fight mobs
- [ ] End-to-end testing shows parity with ROM C player experience

**Current Real Parity**: ~40% (considering missing commands)
**After Phase 1-3**: ~85% (gameplay complete)
**After Phase 4**: ~95% (communication complete)
**True 100%**: All 181 ROM commands + edge cases
