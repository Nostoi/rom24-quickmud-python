# Command Implementation Status Report

**Generated**: 2025-12-20
**Total Commands in Help**: 82
**Implemented**: 32 (39%)
**Missing**: 50 (61%)

## Executive Summary

Based on the help output shown to players, QuickMUD has implemented **32 out of 82** core ROM commands (39% complete). The majority of missing commands are in the OBJECTS category (18/28 missing) and INFORMATION/COMMUNICATION category (18/25 missing).

---

## Category Breakdown

### ✅ MOVEMENT (11/12 implemented - 92%)

| Command | Status | Notes |
|---------|--------|-------|
| north | ✅ Implemented | Directional movement |
| south | ✅ Implemented | Directional movement |
| east | ✅ Implemented | Directional movement |
| west | ✅ Implemented | Directional movement |
| up | ✅ Implemented | Directional movement |
| down | ✅ Implemented | Directional movement |
| exits | ✅ Implemented | Show available exits |
| **recall** | ❌ **MISSING** | Return to temple |
| sleep | ✅ Implemented | Change position to sleeping |
| wake | ✅ Implemented | Wake up from sleep |
| rest | ✅ Implemented | Change position to resting |
| stand | ✅ Implemented | Change position to standing |

**Priority**: Implement `recall` (P0 - core movement feature)

---

### ⚠️ OBJECTS (10/28 implemented - 36%)

| Command | Status | Notes |
|---------|--------|-------|
| get | ✅ Implemented | Pick up objects |
| **put** | ❌ **MISSING** | Put object in container |
| drop | ✅ Implemented | Drop object |
| **give** | ❌ **MISSING** | Give object to character |
| **sacrifice** | ❌ **MISSING** | Sacrifice object to gods |
| **wear** | ❌ **MISSING** | Wear equipment |
| **wield** | ❌ **MISSING** | Wield weapon |
| **hold** | ❌ **MISSING** | Hold item |
| **recite** | ❌ **MISSING** | Recite scroll |
| **quaff** | ❌ **MISSING** | Drink potion |
| **zap** | ❌ **MISSING** | Use wand |
| **brandish** | ❌ **MISSING** | Use staff |
| **lock** | ❌ **MISSING** | Lock door/container |
| **unlock** | ❌ **MISSING** | Unlock door/container |
| **open** | ❌ **MISSING** | Open door/container |
| **close** | ❌ **MISSING** | Close door/container |
| **pick** | ❌ **MISSING** | Pick lock |
| inventory | ✅ Implemented | Show inventory |
| equipment | ✅ Implemented | Show worn equipment |
| look | ✅ Implemented | Look at room/object/character |
| **compare** | ❌ **MISSING** | Compare equipment stats |
| **eat** | ❌ **MISSING** | Consume food |
| **drink** | ❌ **MISSING** | Drink from fountain/container |
| **fill** | ❌ **MISSING** | Fill drink container |
| list | ✅ Implemented | List shop inventory |
| buy | ✅ Implemented | Buy from shop |
| sell | ✅ Implemented | Sell to shop |
| value | ✅ Implemented | Get shop appraisal |

**Priority Commands**:
- P0: `wear`, `wield`, `hold` (core equipment system)
- P0: `eat`, `drink` (survival mechanics)
- P1: `put`, `give` (object manipulation)
- P1: `open`, `close`, `lock`, `unlock` (door/container interaction)
- P2: `recite`, `quaff`, `zap`, `brandish` (magic item usage)
- P2: `compare`, `sacrifice`, `pick`, `fill` (utility)

---

### ❌ GROUP (0/4 implemented - 0%)

| Command | Status | Notes |
|---------|--------|-------|
| **follow** | ❌ **MISSING** | Follow another character |
| **group** | ❌ **MISSING** | Manage group |
| **gtell** | ❌ **MISSING** | Group chat |
| **split** | ❌ **MISSING** | Split gold among group |

**Priority**: All P1 (core multiplayer feature)

---

### ⚠️ INFORMATION/COMMUNICATION (7/25 implemented - 28%)

| Command | Status | Notes |
|---------|--------|-------|
| help | ✅ Implemented | Show help topics |
| **credits** | ❌ **MISSING** | Show ROM credits |
| commands | ✅ Implemented | List available commands |
| **areas** | ❌ **MISSING** | List available areas |
| **report** | ❌ **MISSING** | Report stats to group |
| **score** | ❌ **MISSING** | Show character sheet |
| **time** | ❌ **MISSING** | Show game time |
| **weather** | ❌ **MISSING** | Show weather |
| **where** | ❌ **MISSING** | Show area character list |
| **who** | ❌ **MISSING** | Show player list (note: @who exists for admins) |
| **description** | ❌ **MISSING** | Set character description |
| **password** | ❌ **MISSING** | Change password |
| **title** | ❌ **MISSING** | Set character title |
| **bug** | ❌ **MISSING** | Report bug |
| **idea** | ❌ **MISSING** | Submit idea |
| **typo** | ❌ **MISSING** | Report typo |
| gossip | ✅ Implemented | Gossip channel |
| **cgossip** | ❌ **MISSING** | Colored gossip |
| say | ✅ Implemented | Say to room |
| shout | ✅ Implemented | Shout to area |
| tell | ✅ Implemented | Private message |
| **yell** | ❌ **MISSING** | Yell to adjacent rooms |
| **emote** | ❌ **MISSING** | Custom emote |
| **pose** | ❌ **MISSING** | Pose (alias for emote) |
| note | ✅ Implemented | Note/board system |

**Priority Commands**:
- P0: `score` (essential character info)
- P0: `who` (player-visible version)
- P1: `password`, `title`, `description` (character customization)
- P1: `areas`, `where`, `time` (world info)
- P2: `report`, `emote`, `pose`, `yell` (enhanced communication)
- P2: `bug`, `idea`, `typo` (player feedback)
- P3: `credits`, `weather`, `cgossip` (nice-to-have)

---

### ⚠️ COMBAT (3/8 implemented - 38%)

| Command | Status | Notes |
|---------|--------|-------|
| kill | ✅ Implemented | Initiate combat |
| **flee** | ❌ **MISSING** | Flee from combat |
| kick | ✅ Implemented | Kick attack |
| rescue | ✅ Implemented | Rescue group member |
| **disarm** | ❌ **MISSING** | Disarm opponent |
| **backstab** | ❌ **MISSING** | Thief backstab attack |
| **cast** | ❌ **MISSING** | Cast spell |
| **wimpy** | ❌ **MISSING** | Set auto-flee threshold |

**Priority Commands**:
- P0: `flee` (essential combat escape)
- P0: `cast` (essential for casters)
- P1: `wimpy` (quality of life)
- P2: `backstab`, `disarm` (class-specific skills)

---

### ⚠️ OTHER (2/5 implemented - 40%)

| Command | Status | Notes |
|---------|--------|-------|
| **!** | ❌ **MISSING** | Repeat last command |
| **save** | ❌ **MISSING** | Save character |
| **quit** | ❌ **MISSING** | Quit game |
| practice | ✅ Implemented | Practice skills |
| train | ✅ Implemented | Train stats |

**Priority Commands**:
- P0: `save` (critical - data persistence)
- P0: `quit` (critical - graceful disconnect)
- P2: `!` (convenience)

---

## Implementation Priority Matrix

### P0 - Critical (Breaks Core Gameplay) - 11 Commands
1. **save** - Cannot persist character
2. **quit** - Cannot exit gracefully
3. **recall** - Cannot return to safety
4. **wear** - Cannot equip armor
5. **wield** - Cannot equip weapons
6. **hold** - Cannot use held items
7. **eat** - Cannot consume food
8. **drink** - Cannot consume beverages
9. **score** - Cannot view character stats
10. **flee** - Cannot escape combat
11. **cast** - Cannot use magic

### P1 - Major Features (Significantly Impacts Gameplay) - 16 Commands
1. **who** - Player list visibility
2. **password** - Account security
3. **title** - Character customization
4. **description** - Character customization
5. **areas** - World information
6. **where** - Player location finding
7. **time** - Game time
8. **put** - Container management
9. **give** - Trading items
10. **open** - Access containers/doors
11. **close** - Close containers/doors
12. **lock** - Secure containers/doors
13. **unlock** - Unlock containers/doors
14. **follow** - Group mechanics
15. **group** - Group management
16. **gtell** - Group communication
17. **wimpy** - Auto-flee

### P2 - Enhanced Features (Nice to Have) - 19 Commands
1. **split** - Group gold sharing
2. **report** - Group status reporting
3. **recite** - Scroll usage
4. **quaff** - Potion usage
5. **zap** - Wand usage
6. **brandish** - Staff usage
7. **compare** - Equipment comparison
8. **sacrifice** - Item disposal
9. **pick** - Lockpicking
10. **fill** - Container filling
11. **backstab** - Thief skill
12. **disarm** - Combat skill
13. **emote** - Custom emotes
14. **pose** - Custom poses
15. **yell** - Area yelling
16. **bug** - Bug reporting
17. **idea** - Idea submission
18. **typo** - Typo reporting
19. **!** - Command repeat

### P3 - Polish (Optional) - 4 Commands
1. **credits** - ROM attribution
2. **weather** - Atmospheric
3. **cgossip** - Colored chat

---

## Recommendations

### Phase 1: Core Gameplay Restoration (P0 - 11 commands)
Implement the 11 critical commands that break core gameplay. Without these, the game is essentially unplayable:
- Session management: `save`, `quit`
- Equipment: `wear`, `wield`, `hold`
- Survival: `eat`, `drink`
- Navigation: `recall`
- Information: `score`
- Combat: `flee`, `cast`

**Estimated Effort**: 2-3 days
**Impact**: Makes game playable

### Phase 2: Major Features (P1 - 17 commands)
Add major features that significantly impact player experience:
- Social: `who`, `password`, `title`, `description`
- World info: `areas`, `where`, `time`
- Objects: `put`, `give`, `open`, `close`, `lock`, `unlock`
- Groups: `follow`, `group`, `gtell`
- Combat: `wimpy`

**Estimated Effort**: 3-4 days
**Impact**: Makes game feature-complete for basic multiplayer

### Phase 3: Enhanced Features (P2 - 19 commands)
Round out gameplay with quality-of-life and class-specific features.

**Estimated Effort**: 4-5 days
**Impact**: Full ROM feature parity

### Phase 4: Polish (P3 - 4 commands)
Optional atmospheric and attribution features.

**Estimated Effort**: 1 day
**Impact**: 100% help output compliance

---

## ROM C Source References

Commands should be implemented referencing these ROM 2.4b6 source files:
- **Movement**: `src/act_move.c` (lines 1-1800)
- **Objects**: `src/act_obj.c` (lines 1-2500)
- **Information**: `src/act_info.c` (lines 1-3500)
- **Communication**: `src/act_comm.c` (lines 1-1200)
- **Combat**: `src/fight.c` (lines 1-2000)
- **Magic**: `src/magic.c` (lines 1-2200)

---

## Next Steps

1. ✅ **Create this status report** - COMPLETE
2. **Update ROM_PARITY_FEATURE_TRACKER.md** with command gaps
3. **Implement P0 commands** (11 critical commands)
4. **Run full test suite** after each command
5. **Update help output** to reflect actual available commands
6. **Continue with P1, P2, P3** as time permits

---

## Testing Strategy

For each implemented command:
1. Add unit tests in `tests/test_commands.py` or category-specific file
2. Test position requirements (sleeping/resting/standing/fighting)
3. Test error cases (invalid arguments, missing targets, etc.)
4. Test ROM parity with golden files from ROM 2.4b6 behavior
5. Run full test suite to catch regressions

---

## Notes

- **Admin commands** (`@who`, `@teleport`, etc.) are separate and mostly complete
- **Social commands** (100+ emotes) work via the social system, not the command dispatcher
- **IMC commands** (inter-MUD communication) are separate from core ROM commands
- Some commands may be partially implemented but not registered in the dispatcher
