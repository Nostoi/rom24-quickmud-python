# World Reset ROM Parity Test Report

**Date**: December 29, 2025  
**Status**: ✅ **Test Suite Complete** - 28 ROM parity tests added  
**Test Results**: 16 passing (57%), 12 failing (43%)  
**Outcome**: Tests successfully identify ROM C parity gaps in QuickMUD

---

## Summary

Added comprehensive ROM parity test suite for world reset system (`tests/test_db_resets_rom_parity.py`) covering all reset commands from ROM db.c. The test suite validates formula-level matching to ROM 2.4b6 C source code.

###Test Coverage (28 Tests Total)

#### M Reset - Mob Spawning (5 tests)
| Test | Status | ROM C Reference |
|------|--------|-----------------|
| `test_m_reset_global_limit` | ❌ FAIL | db.c:1691-1752 (line 1704) |
| `test_m_reset_room_limit` | ✅ PASS | db.c:1691-1752 (line 1720) |
| `test_m_reset_level_calculation` | ❌ FAIL | db.c:1691-1752 (line 1735) |
| `test_m_reset_infrared_in_dark_rooms` | ❌ FAIL | db.c:1691-1752 (line 1738) |
| `test_m_reset_pet_shop_flag` | ❌ FAIL | db.c:1691-1752 (line 1742) |

**M Reset Parity Gap Identified:**
- QuickMUD uses `_count_existing_mobs()` (counts world state)
- ROM C uses `pMobIndex->count` (maintained during spawn/despawn)
- **Root Cause**: `mud/spawning/reset_handler.py:413` should check `mob_registry[vnum].count` instead of `mob_counts`

#### O Reset - Object to Room (4 tests)
| Test | Status | ROM C Reference |
|------|--------|-----------------|
| `test_o_reset_room_presence_check` | ✅ PASS | db.c:1754-1786 (line 1762) |
| `test_o_reset_nplayer_check` | ✅ PASS | db.c:1754-1786 (line 1763) |
| `test_o_reset_level_fuzzing` | ✅ PASS | db.c:1754-1786 (line 1772) |
| `test_o_reset_cost_zeroing` | ✅ PASS | db.c:1754-1786 (line 1776) |

**O Reset: ✅ 100% PASS** - All formulas match ROM C exactly

#### P Reset - Put in Container (4 tests)
| Test | Status | ROM C Reference |
|------|--------|-----------------|
| `test_p_reset_limit_formula` | ✅ PASS | db.c:1788-1836 (line 1806) |
| `test_p_reset_arg4_count_formula` | ✅ PASS | db.c:1788-1836 (line 1807) |
| `test_p_reset_last_flag_always_true` | ✅ PASS | db.c:1788-1836 (line 1810) |
| `test_p_reset_container_lock_reset` | ✅ PASS | db.c:1788-1836 (line 1830) |

**P Reset: ✅ 100% PASS** - All formulas match ROM C exactly

#### G/E Reset - Give/Equip (7 tests)
| Test | Status | ROM C Reference |
|------|--------|-----------------|
| `test_ge_reset_shopkeeper_pill_formula` | ❌ FAIL | db.c:1838-1968 (line 1920) |
| `test_ge_reset_shopkeeper_wand_formula` | ❌ FAIL | db.c:1838-1968 (line 1927) |
| `test_ge_reset_shopkeeper_staff_formula` | ❌ FAIL | db.c:1838-1968 (line 1932) |
| `test_ge_reset_shopkeeper_armor_formula` | ❌ FAIL | db.c:1838-1968 (line 1939) |
| `test_ge_reset_shopkeeper_inventory_flag` | ❌ FAIL | db.c:1838-1968 (line 1960) |
| `test_ge_reset_non_shopkeeper_probability_check` | ❌ FAIL | db.c:1838-1968 (line 1941) |
| `test_ge_reset_lastmob_dependency` | ✅ PASS | db.c:1838-1968 (line 1847) |

**G/E Reset Parity Gaps Identified:**
- Shopkeeper level formula not implemented (ROM C lines 1920-1939)
- Shopkeeper inventory flag not implemented (ROM C line 1960)
- Non-shopkeeper probability not implemented (ROM C line 1941)

#### D Reset - Door States (2 tests)
| Test | Status | ROM C Reference |
|------|--------|-----------------|
| `test_d_reset_door_states` | ✅ PASS | db.c:1970-1971 |
| `test_d_reset_reverse_exit_sync` | ❌ FAIL | db.c:1970-1971 |

**D Reset Parity Gap Identified:**
- Reverse exit synchronization not implemented (both sides of door should update)

#### R Reset - Randomize Exits (1 test)
| Test | Status | ROM C Reference |
|------|--------|-----------------|
| `test_r_reset_fisher_yates_shuffle` | ✅ PASS | db.c:1973-1993 |

**R Reset: ✅ 100% PASS** - Fisher-Yates shuffle matches ROM C exactly

#### Area Update - Reset Scheduling (5 tests)
| Test | Status | ROM C Reference |
|------|--------|-----------------|
| `test_area_update_age_increment` | ✅ PASS | db.c:1602-1636 (line 1613) |
| `test_area_update_reset_condition` | ❌ FAIL | db.c:1602-1636 (line 1618) |
| `test_area_update_age_randomization` | ✅ PASS | db.c:1602-1636 (line 1625) |
| `test_area_update_mud_school_special` | ✅ PASS | db.c:1602-1636 (line 1629) |
| `test_area_update_empty_flag_logic` | ✅ PASS | db.c:1602-1636 (line 1619) |

**Area Update Parity Gap Identified:**
- Reset age condition formula doesn't exactly match ROM C (line 1618)

---

## Identified Parity Gaps (P0 Priority)

### 1. M Reset - Global Limit Check (CRITICAL)
**File**: `mud/spawning/reset_handler.py:413`  
**Issue**: Uses `mob_counts` (world state count) instead of `mob_registry[vnum].count` (ROM pMobIndex->count)  
**Fix Required**: 
```python
# Current (WRONG):
if global_limit > 0 and mob_counts.get(mob_vnum, 0) >= global_limit:

# Should be (ROM C parity):
if global_limit > 0 and getattr(mob_registry.get(mob_vnum), 'count', 0) >= global_limit:
```
**ROM C Reference**: `src/db.c:1704` - `if ( pMobIndex->count >= pReset->arg2 )`

### 2. M Reset - Mob Level Fuzzing
**File**: `mud/spawning/reset_handler.py` (M reset section)  
**Issue**: Doesn't apply level randomization formula  
**ROM C Reference**: `src/db.c:1735` - `pMob->level = URANGE(0, pMob->level - 2, LEVEL_HERO);`

### 3. M Reset - Infrared in Dark Rooms
**File**: `mud/spawning/reset_handler.py` (M reset section)  
**Issue**: Doesn't set `AFF_INFRARED` flag for mobs in dark rooms  
**ROM C Reference**: `src/db.c:1738` - `if ( room_is_dark(pMob->in_room) ) SET_BIT(pMob->affected_by, AFF_INFRARED);`

### 4. M Reset - Pet Shop Flag
**File**: `mud/spawning/reset_handler.py` (M reset section)  
**Issue**: Doesn't set `ACT_PET` flag based on room flags  
**ROM C Reference**: `src/db.c:1742` - `if ( IS_SET(pRoomIndex->room_flags, ROOM_PET_SHOP) ) SET_BIT(pMob->act, ACT_PET);`

### 5. G/E Reset - Shopkeeper Formulas (CRITICAL)
**File**: `mud/spawning/reset_handler.py` (G/E reset section)  
**Issue**: Doesn't apply shopkeeper-specific level formulas for pills/wands/staves/armor  
**ROM C Reference**: 
- Pills: `src/db.c:1920` - `pObj->value[0] = number_fuzzy( number_fuzzy( pLastMob->level / 4 + 2 ) );`
- Wands: `src/db.c:1927` - `pObj->value[0] = number_fuzzy( number_fuzzy( pLastMob->level / 2 + 6 ) );`
- Staves: `src/db.c:1932` - `pObj->value[0] = number_fuzzy( number_fuzzy( pLastMob->level / 2 + 10 ) );`
- Armor: `src/db.c:1939` - `pObj->value[0] = number_fuzzy( pLastMob->level / 5 + 3 );`

### 6. G/E Reset - Inventory Flag
**File**: `mud/spawning/reset_handler.py` (G/E reset section)  
**Issue**: Doesn't set `ITEM_INVENTORY` flag for shopkeeper items  
**ROM C Reference**: `src/db.c:1960` - `SET_BIT( pObj->extra_flags, ITEM_INVENTORY );`

### 7. D Reset - Reverse Exit Sync
**File**: `mud/spawning/reset_handler.py` (D reset section)  
**Issue**: Doesn't update reverse exit when setting door state  
**ROM C Reference**: `src/db.c:1970-1971` - Updates both `pexit->exit_info` and `pexit_rev->exit_info`

### 8. Area Update - Reset Age Condition
**File**: `mud/world/area_management.py` (area_update function)  
**Issue**: Reset age condition formula doesn't exactly match ROM C  
**ROM C Reference**: `src/db.c:1618` - `if ( ++pArea->age < 3 )`

---

## Test Validation

All tests include:
- ✅ Exact ROM C source line references in docstrings
- ✅ Detailed comments explaining ROM formulas
- ✅ Setup using real QuickMUD world state (`initialize_world`)
- ✅ Isolation (clear existing state before testing)
- ✅ Assertions on exact ROM C behavior

---

## Recommendations

### Immediate Actions (P0)

1. **Fix M Reset Global Limit** - Use `mob_registry[vnum].count` instead of `mob_counts`
2. **Implement Shopkeeper Formulas** - Add level calculations for pills/wands/staves/armor
3. **Add Shopkeeper Inventory Flag** - Set `ITEM_INVENTORY` on shopkeeper items
4. **Fix D Reset Reverse Sync** - Update both sides of door

### Future Enhancements (P1)

5. **Add M Reset Level Fuzzing** - Apply `URANGE(0, level - 2, LEVEL_HERO)` formula
6. **Add M Reset Infrared** - Set `AFF_INFRARED` for dark rooms
7. **Add M Reset Pet Shop** - Set `ACT_PET` based on room flags
8. **Fix Area Update Age** - Match exact ROM C reset age formula

### Testing Strategy

- Run `pytest tests/test_db_resets_rom_parity.py -v` after each fix
- Expected: Each fix should convert 1-6 failing tests to passing
- Goal: Achieve 28/28 passing tests (100% ROM parity)

---

## Files Modified

- **Created**: `tests/test_db_resets_rom_parity.py` (865 lines, 28 tests)
- **No production code changes** (tests only identify gaps, don't fix them)

---

## Conclusion

✅ **Test Suite Successfully Added**

The ROM parity test suite for world resets is complete and functional. The tests correctly identify 8 parity gaps in QuickMUD's reset system compared to ROM 2.4b6 C source code.

**Key Achievement**: Created formula-level verification tests that serve as:
1. **ROM Parity Certification** - Proves which formulas match ROM C exactly
2. **Regression Prevention** - Future changes won't break ROM parity
3. **Implementation Guide** - Each failing test shows exactly what ROM formula to implement

**Next Steps**: Use failing tests as implementation guide to achieve 100% ROM parity for world reset system.

---

**Test Suite File**: `tests/test_db_resets_rom_parity.py`  
**Test Count**: 28 ROM parity tests  
**Current Pass Rate**: 16/28 (57%)  
**Target Pass Rate**: 28/28 (100%) - achievable by implementing identified gaps
