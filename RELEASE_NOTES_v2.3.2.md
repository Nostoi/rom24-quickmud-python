# Release Notes - QuickMUD v2.3.2

**Release Date:** December 27, 2025  
**Status:** Stable  
**Priority:** Minor Update - Test Coverage & Bug Fixes

---

## 🎉 Highlights

- ✅ **+64 new player character tests** (Phase 1 Priority 1 complete)
- ✅ **183 total player tests** (65.4% of planned ROM character parity coverage)
- ✅ **Critical equipment system bugs fixed**
- ✅ **ROM 2.4b parity verified** for equipment, stats, and combat attributes

---

## 📊 Test Coverage Improvements

### New Test Suites (64 tests)

#### 1. Equipment System Tests (29 tests) - `test_player_equipment.py`
- ✅ Wear/Remove/Wield mechanics (12 tests)
- ✅ Equipment slot management (8 tests)
- ✅ Encumbrance & carry limits (9 tests)

**Covers:** All 19 equipment slots, wear flags, encumbrance calculation, container weight

#### 2. Character Stats Tests (20 tests) - `test_player_stats.py`
- ✅ Permanent stat array (perm_stat) (7 tests)
- ✅ Modified stat array (mod_stat) (7 tests)
- ✅ Stat bounds & clamping (0-25 ROM range) (6 tests)

**Covers:** get_curr_stat() calculation, stat persistence, temporary bonuses/penalties

#### 3. Combat Attributes Tests (15 tests) - `test_player_combat_attributes.py`
- ✅ Hitroll (to-hit bonus) (5 tests)
- ✅ Damroll (damage bonus) (5 tests)
- ✅ Armor Class (4 AC types) (5 tests)

**Covers:** Combat attribute defaults, accumulation, per-character independence

### Test Suite Status
- **Total Tests:** 1726 tests
- **Player Tests:** 183 tests (up from 119)
- **Phase 1 P1 Coverage:** 86/75 tests (114.7% complete ✅)

---

## 🐛 Bug Fixes

### Equipment System Fixes

1. **Fixed WearFlag vs WearLocation enum confusion**
   - **Issue:** Equipment commands were mixing WearFlag (what can be worn) with WearLocation (where it's worn)
   - **Fix:** `_get_wear_location()` now correctly maps WearFlag bits to WearLocation slots
   - **Files:** `mud/commands/equipment.py`

2. **Fixed item_type string vs enum comparison**
   - **Issue:** Object stores `item_type` as string, but code compared to enum directly
   - **Fix:** Convert string to int before comparison in `do_wear()`, `do_wield()`, `do_hold()`
   - **Impact:** Wielding weapons, wearing armor now works correctly

3. **Fixed equipment dictionary field name mismatch**
   - **Issue:** `get_obj_wear()` used `char.equipped` instead of `char.equipment`
   - **Fix:** Updated to use correct field name
   - **Files:** `mud/world/obj_find.py`
   - **Impact:** `remove` command now finds equipped items

4. **Fixed inventory field name mismatch**
   - **Issue:** `_remove_obj()` used `char.carrying` instead of `char.inventory`
   - **Fix:** Updated to use correct field name, added equipment dict removal
   - **Files:** `mud/commands/obj_manipulation.py`
   - **Impact:** Removed items now return to inventory correctly

---

## 🔧 Technical Changes

### Modified Files

**Equipment System:**
- `mud/commands/equipment.py` - WearFlag/WearLocation fixes, item_type handling
- `mud/world/obj_find.py` - Equipment field name fix
- `mud/commands/obj_manipulation.py` - Inventory field name fix, equipment removal

**Test Files (New):**
- `tests/test_player_equipment.py` - 29 equipment tests
- `tests/test_player_stats.py` - 20 stat tests
- `tests/test_player_combat_attributes.py` - 15 combat attribute tests

**Documentation:**
- `CHARACTER_TEST_PLAN.md` - Updated with Phase 1 completion status
- `RELEASE_NOTES_v2.3.2.md` - This file

---

## 📈 ROM Parity Status

### Equipment System: ✅ 100% Tested
- ✅ Wear/Remove/Wield commands
- ✅ All 19 equipment slots (finger, neck, body, head, legs, feet, hands, arms, shield, about, waist, wrist, wield, hold, light, float)
- ✅ Encumbrance calculation (weight + count limits)
- ✅ Multi-slot support (2 rings, 2 neck items, 2 bracelets)

### Character Stats: ✅ 100% Tested
- ✅ perm_stat array (permanent character stats)
- ✅ mod_stat array (temporary spell/equipment bonuses)
- ✅ get_curr_stat() calculation (perm + mod, clamped 0-25)
- ✅ Stat enum indexing (STR, INT, WIS, DEX, CON)

### Combat Attributes: ✅ 100% Tested
- ✅ hitroll (to-hit bonus)
- ✅ damroll (damage bonus)
- ✅ armor array (AC_PIERCE, AC_BASH, AC_SLASH, AC_EXOTIC)

---

## 🎯 Next Steps (Phase 2)

**Priority 2 Tests (Planned):**
- Character creation flow (race/class selection, stat rolling)
- Affect flags system (blind, invisible, detect_magic, sanctuary, etc.)
- Skills & spells integration

**Timeline:** Phase 2 implementation planned for Q1 2026

---

## 📚 Documentation

- [CHARACTER_TEST_PLAN.md](CHARACTER_TEST_PLAN.md) - Complete test coverage roadmap
- [AGENTS.md](AGENTS.md) - AI agent development workflows
- [README.md](README.md) - Project overview

---

## ⚠️ Breaking Changes

None. This release is fully backward compatible.

---

## 🙏 Acknowledgments

- Original ROM 2.4b by Russ Taylor and the ROM consortium
- Test coverage improvements by AI-assisted development
- Equipment system bug reports from integration testing

---

**Full Changelog:** https://github.com/Nostoi/rom24-quickmud-python/compare/v2.3.1...v2.3.2
