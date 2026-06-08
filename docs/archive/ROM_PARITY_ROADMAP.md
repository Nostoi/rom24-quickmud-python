# 100% ROM Parity Roadmap

**Goal**: Achieve complete ROM 2.4b parity with QuickMUD Python port  
**Current Status**: ~85-90% ROM parity  
**Target**: 100% ROM parity  
**Timeline**: 2-4 weeks  
**Created**: 2025-12-28  

---

## 📊 Current State Summary

Based on comprehensive audit (2025-12-28):

| Subsystem | Current Parity | Status |
|-----------|----------------|--------|
| Mob Programs | 100% | ✅ COMPLETE |
| Movement/Encumbrance | 100% | ✅ COMPLETE |
| Object Commands | 100% | ✅ All 25 commands |
| Shop Economy | 95% | ✅ Nearly complete |
| Object System (overall) | 85-90% | ⚠️ 5 features missing |
| Combat | 75% (est) | ⚠️ Needs audit |
| Skills/Spells | 80% (est) | ⚠️ Needs audit |
| World Reset | 75% (est) | ⚠️ Needs audit |

**Overall**: ~85-90% ROM parity

---

## 🎯 PHASE 1: Complete Object System (5-6 days)

**Goal**: Object system 85% → 100%

### Task 1: Dual Wield Support (1 day) - P1

**ROM C Reference**: `src/act_obj.c:1320+`

**What to implement**:
- `wield <weapon>` - Primary weapon
- `wield <weapon> second` - Secondary weapon (dual wield)
- Two-handed weapon check (blocks dual wield)
- Dual wield skill requirement check
- Off-hand attack penalty

**Files to modify**:
- `mud/commands/equipment.py` - Update `do_wield()`
- `mud/models/constants.py` - Add `WearLocation.WIELD_OFF` if missing
- `mud/combat/engine.py` - Off-hand attack in combat

**Tests to add**:
- `tests/test_player_equipment.py` - Add dual wield tests
- Test two-handed weapon blocks dual wield
- Test skill requirement checks

**Acceptance**:
- [ ] `wield sword second` works
- [ ] Two-handed weapons block dual wield
- [ ] Off-hand attacks in combat
- [ ] All tests pass

---

### Task 2: Container Weight/Count Limits (1 day) - P1

**ROM C Reference**: `src/act_obj.c:400-430`

**What to implement**:
- Container max weight capacity (value[0])
- Container max item count limit (value[3])
- `put` command rejects when over limit
- Proper error messages

**Files to modify**:
- `mud/commands/obj_manipulation.py` - Update `do_put()`
- Add weight/count checks before putting

**ROM C logic**:
```c
// act_obj.c:400-430
if (get_obj_weight(obj) + get_obj_weight(container) > container->value[0])
    send_to_char("It won't fit.\n\r", ch);
```

**Tests to add**:
- `tests/test_containers.py` (new file)
- Test weight limit enforcement
- Test item count limit enforcement
- Test proper error messages

**Acceptance**:
- [ ] Container rejects items over weight limit
- [ ] Container rejects items over count limit
- [ ] Error messages match ROM
- [ ] All tests pass

---

### Task 3: Corpse Looting Permissions (1 day) - P1

**ROM C Reference**: `src/act_obj.c:61-89 (can_loot)`

**What to implement**:
```c
bool can_loot(CHAR_DATA *ch, OBJ_DATA *obj) {
    // Immortals can loot anything
    // No owner = lootable
    // Owner offline = lootable
    // Player is owner = lootable
    // Owner has PLR_CANLOOT = lootable
    // Same group = lootable
    // Otherwise = not lootable
}
```

**Files to modify**:
- `mud/commands/inventory.py` - Add `can_loot()` function
- `mud/commands/inventory.py` - Call in `do_get()` before taking from corpse
- `mud/models/constants.py` - Verify `PlayerFlag.CANLOOT` exists

**Tests to add**:
- `tests/test_combat_death.py` - Add corpse looting permission tests
- Test owner can loot own corpse
- Test group can loot group member corpse
- Test non-group cannot loot corpse
- Test PLR_CANLOOT flag allows looting
- Test immortal can loot anything

**Acceptance**:
- [ ] `can_loot()` function implemented
- [ ] Called in `do_get()` for corpses
- [ ] Group looting works
- [ ] Non-group looting blocked
- [ ] All tests pass

---

### Task 4: Class/Alignment Equipment Restrictions (2 days) - P1

**ROM C Reference**: `src/act_obj.c:1080-1100`

**What to implement**:
- Class restrictions (WARRIOR_ONLY, MAGE_ONLY, etc.)
- Alignment restrictions (ANTI_GOOD, ANTI_EVIL, ANTI_NEUTRAL)
- Level restrictions (already implemented)
- Cursed item removal prevention

**ROM C extra flags**:
```c
#define ITEM_ANTI_GOOD    (I)  // Can't be used by good
#define ITEM_ANTI_EVIL    (J)  // Can't be used by evil
#define ITEM_ANTI_NEUTRAL (K)  // Can't be used by neutral
#define ITEM_NOREMOVE     (L)  // Cursed, can't remove
```

**Files to modify**:
- `mud/commands/equipment.py` - Add class/alignment checks in `do_wear()`, `do_wield()`
- `mud/commands/obj_manipulation.py` - Add cursed check in `do_remove()`
- `mud/models/constants.py` - Add missing `ExtraFlag` enums if needed

**Tests to add**:
- `tests/test_player_equipment.py` - Add restriction tests
- Test class restriction enforcement
- Test alignment restriction enforcement
- Test cursed item cannot be removed
- Test proper error messages

**Acceptance**:
- [ ] Class restrictions enforced
- [ ] Alignment restrictions enforced
- [ ] Cursed items can't be removed
- [ ] Error messages match ROM
- [ ] All tests pass

---

### Task 5: Shop Charisma Price Modifiers (1 day) - P2

**ROM C Reference**: `src/act_obj.c:2290-2310 (get_cost)`

**What to implement**:
```c
// ROM charisma price modifier
int get_cost(CHAR_DATA *keeper, OBJ_DATA *obj, bool fBuy) {
    int cost = obj->cost;
    int charisma = get_curr_stat(ch, STAT_CHA);
    
    if (fBuy) {
        cost = cost * (100 + (25 - charisma)) / 100;  // Higher CHA = lower buy price
    } else {
        cost = cost * charisma / 100;  // Higher CHA = higher sell price
    }
    
    return cost;
}
```

**Files to modify**:
- `mud/commands/shop.py` - Update `do_buy()` and `do_sell()`
- Add charisma-based price calculation

**Tests to add**:
- `tests/test_shops.py` - Add charisma price tests
- Test high charisma lowers buy price
- Test low charisma raises buy price
- Test high charisma raises sell price
- Test low charisma lowers sell price

**Acceptance**:
- [ ] Buy prices affected by charisma
- [ ] Sell prices affected by charisma
- [ ] Formula matches ROM C
- [ ] All tests pass

---

## 📈 PHASE 1 Summary

**Timeline**: 5-6 days  
**Result**: Object system 100% ROM parity  
**Test Coverage**: +50 new tests  

**After Phase 1**:
- ✅ Object System: 100%
- ✅ Shop Economy: 100%
- ✅ Equipment System: 100%
- ✅ Container System: 100%

---

## 🔍 PHASE 2: Audit Remaining Subsystems (3-5 days)

**Goal**: Identify true parity status (like we did for objects)

### Audit 1: Combat System (1-2 days)

**Current Claim**: 75% complete  
**Expected Reality**: Likely 80-85% (based on object pattern)

**Audit Method**:
1. List all ROM combat commands (`src/fight.c`, `src/act_wiz.c`)
2. Find Python implementations
3. Count tests (`tests/test_combat*.py`)
4. Identify actual gaps

**Commands to verify**:
- `kill`, `murder`, `flee`, `rescue`, `bash`, `kick`, `trip`
- `disarm`, `dirt`, `backstab`, `circle`, `berserk`

**Deliverable**: `COMBAT_PARITY_AUDIT_RESULTS.md`

---

### Audit 2: Skills/Spells System (1-2 days)

**Current Claim**: 80% complete  
**Expected Reality**: Likely 85-90%

**Audit Method**:
1. List all ROM skills/spells (`src/magic.c`, `src/skills.c`)
2. Verify handlers in `mud/skills/handlers.py`
3. Count tests (`tests/test_skills*.py`)
4. Check practice/improvement system

**Already Known Complete**:
- ✅ 134 skill/spell handlers (0 stubs)
- ✅ Practice-based learning system

**Deliverable**: `SKILLS_PARITY_AUDIT_RESULTS.md`

---

### Audit 3: World Reset System (1 day)

**Current Claim**: 75% complete  
**Expected Reality**: Unknown

**Audit Method**:
1. List all ROM reset types (`src/db.c:1602-1900`)
2. Verify implementations in `mud/spawning/reset_handler.py`
3. Count tests (`tests/test_area_loader.py`, `tests/test_reset*.py`)
4. Check reset dependencies

**Deliverable**: `RESET_PARITY_AUDIT_RESULTS.md`

---

## 🎯 PHASE 3: Implement Remaining Features (1-2 weeks)

**Based on Phase 2 audit results**

**Estimated work** (conservative):
- Combat gaps: 3-5 days
- Skills/Spells gaps: 2-3 days
- World Reset gaps: 2-3 days
- Polish/testing: 2-3 days

**Total**: 9-14 days (2 weeks)

---

## 📊 Success Metrics

### Phase 1 Complete When:
- [ ] All 5 object tasks implemented
- [ ] All new tests passing
- [ ] `pytest tests/` shows 0 regressions
- [ ] Object parity = 100%

### Phase 2 Complete When:
- [ ] 3 audit documents created
- [ ] Accurate parity percentages for Combat/Skills/Reset
- [ ] Prioritized task list for Phase 3

### Phase 3 Complete When:
- [ ] All identified gaps implemented
- [ ] All subsystems ≥95% ROM parity
- [ ] Full test suite passing
- [ ] Documentation updated

### 100% ROM Parity Achieved When:
- [ ] All ROM 2.4b commands implemented
- [ ] All ROM 2.4b features implemented
- [ ] Behavioral equivalence verified
- [ ] Test coverage ≥90%
- [ ] Integration tests passing

---

## 🚀 Next Steps

**Starting now**:
1. Implement Task 1: Dual Wield Support
2. Then Task 2: Container Limits
3. Then Task 3: Corpse Looting
4. Then Task 4: Equipment Restrictions
5. Then Task 5: Charisma Modifiers

**After Phase 1 (5-6 days)**:
6. Audit Combat System
7. Audit Skills/Spells System
8. Audit World Reset System

**After Phase 2 (8-11 days total)**:
9. Implement Combat gaps
10. Implement Skills gaps
11. Implement Reset gaps

**Target completion**: 3-4 weeks from today

---

## 📝 Progress Tracking

This roadmap will be updated as tasks complete. See individual task todos for real-time status.

**Last Updated**: 2025-12-28  
**Current Phase**: Planning → Ready to start Phase 1
