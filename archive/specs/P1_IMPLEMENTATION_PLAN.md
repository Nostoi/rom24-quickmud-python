# P1 Command Implementation Plan - Next Session

**Status**: Ready to implement  
**Commands**: 38 total  
**Estimated Effort**: 3-4 hours  
**Goal**: PLAYABLE → FEATURE-RICH  

---

## 📊 Current Status (End of Previous Session)

### What's Complete ✅
- ✅ All 11 P0 critical commands implemented and working
- ✅ Parity audit system fixed with automated tracking
- ✅ Command coverage: 27.7% (74/267 ROM commands)
- ✅ Help commands working: 52.4% (43/82)
- ✅ Game status: **PLAYABLE**

### What's Needed for Feature-Rich ⏳
- ⏳ 38 P1 commands remaining
- ⏳ Command coverage target: ~42% (112/267)
- ⏳ Help commands target: ~98% (81/82)
- ⏳ Game status target: **FEATURE-RICH**

---

## 🎯 P1 Commands to Implement (38 Total)

### Batch 1: Information Commands (7 commands)
**Priority**: HIGH - Players need visibility into game state

| Command | ROM Reference | Purpose |
|---------|---------------|---------|
| `who` | `act_info.c:2016-2100` | List online players |
| `areas` | `act_info.c:220-280` | List available areas |
| `where` | `act_info.c:2200-2280` | Show players in current area |
| `time` | `act_info.c:2350-2400` | Display game time |
| `weather` | `act_info.c:2420-2480` | Display weather |
| `credits` | `act_info.c:150-200` | ROM attribution |
| `report` | `act_comm.c:800-850` | Report status to group/room |

**File**: Add to existing `mud/commands/info.py`  
**Estimated Time**: 30 minutes

### Batch 2: Character Customization (3 commands)
**Priority**: HIGH - Essential for player identity

| Command | ROM Reference | Purpose |
|---------|---------------|---------|
| `password` | `nanny.c:500-600` | Change password |
| `title` | `act_comm.c:900-950` | Set character title |
| `description` | `act_comm.c:1000-1100` | Set character description |

**File**: Create new `mud/commands/character.py`  
**Estimated Time**: 20 minutes

### Batch 3: Object Manipulation (6 commands)
**Priority**: HIGH - Core object interaction

| Command | ROM Reference | Purpose |
|---------|---------------|---------|
| `put` | `act_obj.c:600-700` | Put object in container |
| `give` | `act_obj.c:800-900` | Give object to character |
| `open` | `act_obj.c:1600-1700` | Open door/container |
| `close` | `act_obj.c:1700-1800` | Close door/container |
| `lock` | `act_obj.c:1800-1900` | Lock door/container |
| `unlock` | `act_obj.c:1900-2000` | Unlock door/container |

**File**: Add to existing `mud/commands/inventory.py` OR create `mud/commands/objects.py`  
**Estimated Time**: 45 minutes

### Batch 4: Object Utilities (4 commands)
**Priority**: MEDIUM - Quality of life features

| Command | ROM Reference | Purpose |
|---------|---------------|---------|
| `fill` | `act_obj.c:500-600` | Fill drink container |
| `compare` | `act_obj.c:2100-2200` | Compare equipment stats |
| `sacrifice` | `act_obj.c:2200-2300` | Sacrifice object for gold |
| `pick` | `act_obj.c:2000-2100` | Pick lock (thief skill) |

**File**: Extend `mud/commands/consumption.py` OR create `mud/commands/object_utils.py`  
**Estimated Time**: 30 minutes

### Batch 5: Magic Items (4 commands)
**Priority**: MEDIUM - Magic system completeness

| Command | ROM Reference | Purpose |
|---------|---------------|---------|
| `brandish` | `act_obj.c:100-200` | Use staff |
| `quaff` | `act_obj.c:200-300` | Drink potion |
| `recite` | `act_obj.c:300-400` | Recite scroll |
| `zap` | `act_obj.c:400-500` | Use wand |

**File**: Create new `mud/commands/magic_items.py`  
**Estimated Time**: 40 minutes

### Batch 6: Group Commands (4 commands)
**Priority**: HIGH - Multiplayer essential

| Command | ROM Reference | Purpose |
|---------|---------------|---------|
| `follow` | `act_move.c:600-700` | Follow character |
| `group` | `act_info.c:1200-1400` | Manage group |
| `gtell` | `act_comm.c:600-650` | Group chat |
| `split` | `act_obj.c:2400-2500` | Split gold among group |

**File**: Create new `mud/commands/group.py`  
**Estimated Time**: 45 minutes

### Batch 7: Communication (4 commands)
**Priority**: MEDIUM - Enhanced social interaction

| Command | ROM Reference | Purpose |
|---------|---------------|---------|
| `emote` | `act_comm.c:400-450` | Custom emote |
| `pose` | `act_comm.c:450-500` | Pose (alias for emote) |
| `yell` | `act_comm.c:500-550` | Yell to adjacent rooms |
| `cgossip` | `act_comm.c:700-750` | Colored gossip |

**File**: Add to existing `mud/commands/communication.py`  
**Estimated Time**: 25 minutes

### Batch 8: Combat Skills (3 commands)
**Priority**: HIGH - Combat depth

| Command | ROM Reference | Purpose |
|---------|---------------|---------|
| `backstab` | `fight.c:500-600` | Thief backstab (ALREADY EXISTS - just check) |
| `disarm` | `fight.c:600-700` | Disarm opponent |
| `wimpy` | `fight.c:900-950` | Set auto-flee threshold |

**File**: Add to existing `mud/commands/combat.py`  
**Estimated Time**: 20 minutes (backstab already exists)

### Batch 9: Feedback Commands (3 commands)
**Priority**: LOW - Player feedback system

| Command | ROM Reference | Purpose |
|---------|---------------|---------|
| `bug` | `act_info.c:100-120` | Report bug |
| `idea` | `act_info.c:120-140` | Submit idea |
| `typo` | `act_info.c:140-160` | Report typo |

**File**: Create new `mud/commands/feedback.py`  
**Estimated Time**: 15 minutes

---

## 📝 Implementation Checklist

### For Each Batch:

1. **Create/Update Command File**
   - [ ] Add ROM C source references in docstrings
   - [ ] Implement command functions with ROM parity
   - [ ] Use defensive programming (getattr, try/except)
   - [ ] Match ROM error messages
   - [ ] Enforce position requirements

2. **Register Commands**
   - [ ] Import functions in `dispatcher.py`
   - [ ] Add Command() entries with proper settings
   - [ ] Set min_position, log_level, aliases

3. **Verify**
   - [ ] Run `pytest tests/test_command_parity.py::test_critical_command_coverage`
   - [ ] Run `pytest tests/test_command_parity.py::test_help_command_coverage`
   - [ ] Verify command registration count increases

---

## 🎯 Success Criteria

### When All P1 Commands Are Complete:

| Metric | Before P1 | After P1 Target | Change |
|--------|-----------|-----------------|--------|
| **Total Commands** | 95 | 133 | +38 |
| **ROM Coverage** | 27.7% (74/267) | 42% (112/267) | +14.3% |
| **Help Commands** | 52.4% (43/82) | 98.8% (81/82) | +46.4% |
| **Game Status** | PLAYABLE | **FEATURE-RICH** | ✅ |

### Test Results Expected:
```bash
✅ test_critical_command_coverage - PASSING
✅ test_help_command_coverage - PASSING (0 or 1 missing)
✅ test_rom_command_coverage_metric - 42%+
```

---

## 🚀 Implementation Strategy

### Recommended Order:

1. **Start with HIGH priority batches** (Information, Character, Object Manipulation, Group, Combat)
2. **Quick wins first** (Feedback - 15 min)
3. **Save complex for last** (Magic Items - requires spell integration)

### Time Allocation:

| Time Block | Batches | Commands |
|------------|---------|----------|
| **Hour 1** | Info (7) + Character (3) + Feedback (3) | 13 commands |
| **Hour 2** | Object Manipulation (6) + Utilities (4) | 10 commands |
| **Hour 3** | Group (4) + Communication (4) | 8 commands |
| **Hour 4** | Combat (3) + Magic Items (4) + Testing | 7 commands |

**Total**: ~4 hours for complete P1 implementation

---

## 📋 Existing Code to Leverage

### Check These First (May Already Exist):

1. **`backstab`** - Check `mud/commands/combat.py` (likely already implemented)
2. **`who`** - Check if admin `@who` can be adapted
3. **Group mechanics** - Check if any group code exists in models
4. **Magic item handlers** - Check `mud/skills/handlers.py` for scroll/potion/wand/staff logic

### Reusable Patterns:

- **Object finding**: Copy from `_find_obj_inventory()` in equipment.py
- **Room messaging**: Copy from flee/recall implementations
- **Position checking**: Pattern from all P0 commands
- **Error handling**: Defensive programming from session.py

---

## 🔧 Code Templates

### Template 1: Simple Info Command
```python
def do_commandname(ch: Character, args: str) -> str:
    """
    Brief description.
    
    ROM Reference: src/file.c lines X-Y (do_commandname)
    """
    try:
        # Implementation
        return "Success message"
    except Exception as e:
        return f"Error: {e}"
```

### Template 2: Object Manipulation Command
```python
def do_commandname(ch: Character, args: str) -> str:
    """
    Description.
    
    ROM Reference: src/act_obj.c lines X-Y
    """
    args = args.strip()
    if not args:
        return "Command what?"
    
    # Check position
    if ch.position < Position.RESTING:
        return "You can't do that right now."
    
    # Find object
    obj = _find_obj_inventory(ch, args)
    if not obj:
        return "You don't have that."
    
    # Execute action
    return "Action completed."
```

### Template 3: Communication Command
```python
def do_commandname(ch: Character, args: str) -> str:
    """
    Description.
    
    ROM Reference: src/act_comm.c lines X-Y
    """
    args = args.strip()
    if not args:
        return "Command what?"
    
    # Send to room/area/world
    room = getattr(ch, 'room', None)
    if room:
        for other in getattr(room, 'characters', []):
            if other != ch:
                try:
                    desc = getattr(other, 'desc', None)
                    if desc and hasattr(desc, 'send'):
                        desc.send(f"Message from {ch.name}")
                except Exception:
                    pass
    
    return "You message."
```

---

## 📚 Reference Files

### ROM C Sources (in src/):
- `act_info.c` - who, areas, where, time, weather, credits, bug, idea, typo
- `act_comm.c` - report, title, description, emote, pose, yell, cgossip, gtell
- `act_obj.c` - put, give, open, close, lock, unlock, fill, compare, sacrifice, pick, brandish, quaff, recite, zap, split
- `act_move.c` - follow
- `fight.c` - disarm, wimpy
- `nanny.c` - password

### Python Implementation Files:
- `mud/commands/info.py` - Extend with new info commands
- `mud/commands/communication.py` - Extend with emote, pose, yell, cgossip
- `mud/commands/combat.py` - Check for backstab, add disarm, wimpy
- `mud/commands/inventory.py` - May extend with object manipulation
- `mud/commands/dispatcher.py` - Register all new commands

---

## ✅ Final Checklist

Before completing P1 session:

- [ ] All 38 commands implemented
- [ ] All commands registered in dispatcher
- [ ] `test_help_command_coverage` PASSING or 1 missing
- [ ] ROM coverage ≥42%
- [ ] Help coverage ≥98%
- [ ] No regressions in existing tests
- [ ] Documentation updated
- [ ] Session summary written

---

**Status**: Ready to implement in next session  
**Estimated Duration**: 3-4 hours  
**Expected Outcome**: Game becomes FEATURE-RICH with full multiplayer, group mechanics, object interaction, and communication systems.
