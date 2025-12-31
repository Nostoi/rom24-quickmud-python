# Saves & Immunity ROM Parity Test Completion Report

**Date**: December 30, 2025  
**Status**: ✅ **COMPLETE** - 29/29 tests passing (100%)  
**ROM C Sources**: `magic.c:215-254`, `handler.c:213-320`

---

## Summary

Added comprehensive ROM C parity tests for save formulas and immunity mechanics, completing the optional ROM C parity test enhancement work for core magic resistance systems.

---

## Tests Created

### File: `tests/test_saves_rom_parity.py` (29 tests)

#### 1. `saves_spell()` Mechanics (9 tests) - ROM `magic.c:215-239`

**Base Formula**: `save = 50 + (victim->level - level) * 5 - victim->saving_throw * 2`

**Tests**:
1. ✅ `test_saves_spell_base_formula` - Verifies base save calculation
2. ✅ `test_saves_spell_berserk_bonus` - `+victim->level / 2` when BERSERK (C integer division)
3. ✅ `test_saves_spell_immune_auto_success` - Immune characters always save
4. ✅ `test_saves_spell_resistant_bonus` - Resistant adds +2 to save
5. ✅ `test_saves_spell_vulnerable_penalty` - Vulnerable subtracts -2 from save
6. ✅ `test_saves_spell_fmana_class_reduction` - Mage/Cleric: `save = 9 * save / 10`
7. ✅ `test_saves_spell_non_fmana_class_no_reduction` - Warrior/Thief: no reduction
8. ✅ `test_saves_spell_clamped_to_5_95` - Save clamped to 5-95% range
9. ✅ `test_saves_spell_npc_no_fmana_reduction` - NPCs never get fMana reduction

**Key Implementation Detail**: 
- `movable_char_factory` defaults to `ch_class = 0` (Mage), which triggers fMana reduction
- Tests requiring baseline behavior use `char.ch_class = 3` (Warrior) to disable this

#### 2. `check_immune()` Mechanics (8 tests) - ROM `handler.c:213-320`

**Global Immunity Flags**:
- `IMM_WEAPON` - Immune to all weapon damage
- `RES_WEAPON` - Resistant to all weapon damage (+2 save)
- `VULN_WEAPON` - Vulnerable to all weapon damage (-2 save)
- `IMM_MAGIC` - Immune to all magic damage
- `RES_MAGIC` - Resistant to all magic damage
- `VULN_MAGIC` - Vulnerable to all magic damage

**Specific Damage Type Flags**:
- 17 damage types: `none`, `bash`, `pierce`, `slash`, `fire`, `cold`, `lightning`, `acid`, `poison`, `negative`, `holy`, `energy`, `mental`, `disease`, `drowning`, `light`, `other`, `harm`, `charm`, `sound`
- Specific flags override global flags

**Tests**:
1. ✅ `test_check_immune_weapon_global_immune` - Global weapon immunity
2. ✅ `test_check_immune_weapon_global_resistant` - Global weapon resistance
3. ✅ `test_check_immune_weapon_global_vulnerable` - Global weapon vulnerability
4. ✅ `test_check_immune_magic_global_immune` - Global magic immunity
5. ✅ `test_check_immune_specific_overrides_global` - Specific flags override global
6. ✅ `test_check_immune_vuln_downgrades_immunity` - IMM+VULN=RES, RES+VULN=NORMAL
7. ✅ `test_check_immune_all_damage_types_mapped` - All 17 damage types work
8. ✅ `test_check_immune_none_returns_minus_one` - Returns -1 for NORMAL immunity

#### 3. `saves_dispel()` Mechanics (3 tests) - ROM `magic.c:243-254`

**Base Formula**: `save = 50 + (spell_level - dis_level) * 5`

**Permanent Effect Bonus**: `spell_level += 5` when `duration == -1`

**Tests**:
1. ✅ `test_saves_dispel_base_formula` - Verifies base save calculation
2. ✅ `test_saves_dispel_permanent_effect_bonus` - Permanent effects harder to dispel
3. ✅ `test_saves_dispel_clamped_to_5_95` - Save clamped to 5-95% range

#### 4. `check_dispel()` Mechanics (4 tests) - ROM `magic.c:258-282`

**Behavior**:
- Failed save: Removes affect completely
- Successful save: Reduces `affect.level` by 1
- Returns `False` if not affected by spell

**Tests**:
1. ✅ `test_check_dispel_removes_on_failed_save` - Failed save removes affect
2. ✅ `test_check_dispel_reduces_level_on_successful_save` - Successful save reduces level
3. ✅ `test_check_dispel_returns_false_if_not_affected` - Returns False if no affect
4. ✅ `test_check_dispel_permanent_effect_harder_to_remove` - Permanent effects get +5 to save

#### 5. Integration Tests (5 tests)

**Tests**:
1. ✅ `test_immune_character_never_takes_damage` - Immune + saves_spell = always save
2. ✅ `test_vulnerable_resistant_cancel_out` - VULN + RES = NORMAL
3. ✅ `test_mage_class_gets_better_saves` - fMana reduction: `9 * save / 10`
4. ✅ `test_level_difference_matters` - Higher victim level = better saves
5. ✅ `test_saving_throw_stat_matters` - Higher saving_throw = better saves

---

## ROM C Parity Verification

### saves_spell() - ROM `magic.c:215-239`

**ROM C Implementation**:
```c
bool saves_spell (int level, CHAR_DATA * victim, int dam_type)
{
    int save;

    save = 50 + (victim->level - level) * 5 - victim->saving_throw * 2;
    if (IS_AFFECTED (victim, AFF_BERSERK))
        save += victim->level / 2;

    switch (check_immune (victim, dam_type))
    {
        case IS_IMMUNE:
            return TRUE;
        case IS_RESISTANT:
            save += 2;
            break;
        case IS_VULNERABLE:
            save -= 2;
            break;
    }

    if (!IS_NPC (victim) && class_table[victim->class].fMana)
        save = 9 * save / 10;
    save = URANGE (5, save, 95);
    return number_percent () < save;
}
```

**QuickMUD Implementation**: `mud/affects/saves.py:saves_spell()`

✅ **Exact parity verified** - All formulas match ROM C behavior

### saves_dispel() - ROM `magic.c:243-254`

**ROM C Implementation**:
```c
bool saves_dispel (int dis_level, int spell_level, int duration)
{
    int save;

    if (duration == -1)
        spell_level += 5;
    /* very hard to dispel permanent effects */

    save = 50 + (spell_level - dis_level) * 5;
    save = URANGE (5, save, 95);
    return number_percent () < save;
}
```

**QuickMUD Implementation**: `mud/affects/saves.py:saves_dispel()`

✅ **Exact parity verified** - Permanent effect bonus and formula match ROM C

### check_immune() - ROM `handler.c:213-320`

**ROM C Implementation**: Complex switch statement with global/specific flag resolution

**QuickMUD Implementation**: `mud/affects/saves.py:check_immune()`

✅ **Exact parity verified** - All global and specific immunity flags work correctly

---

## Test Execution Results

```bash
$ pytest tests/test_saves_rom_parity.py -v
=============================== 29 passed in 0.41s ===============================
```

**All 108 ROM C Parity Tests (This Session)**:
```bash
$ pytest tests/test_saves_rom_parity.py tests/test_char_update_rom_parity.py tests/test_obj_update_rom_parity.py tests/test_handler_affects_rom_parity.py -v
=============================== 108 passed in 3.19s ===============================
```

---

## Coverage Summary

### ROM C Files Tested (This Session)

| File | Lines Tested | Tests | Status |
|------|--------------|-------|--------|
| `magic.c` | 215-254 | 16 tests | ✅ Complete |
| `handler.c` | 213-320 | 13 tests | ✅ Complete |

### Optional ROM C Parity Test Progress

**From `ROM_C_PARITY_TEST_GAP_ANALYSIS.md`**:

| Task | C File | Tests | Status |
|------|--------|-------|--------|
| #5 Character Update (update.c) | `update.c:378-560` | 30 tests | ✅ Complete (Dec 29) |
| #6 Object Update (update.c) | `update.c:563-705` | 22 tests | ✅ Complete (Dec 29) |
| #7-8 Affect Mechanics (handler.c) | `handler.c:2049-2222` | 27 tests | ✅ Complete (Dec 29) |
| #9-10 Saves/Immunity (magic.c, handler.c) | `magic.c:215-254`, `handler.c:213-320` | 29 tests | ✅ **Complete (Dec 30)** |

**Total**: 108 tests added for core mechanics formula verification

---

## Key Implementation Insights

### 1. Character Class Defaults

**Issue**: `movable_char_factory` creates characters with `ch_class = 0` (Mage) by default, which triggers the fMana save reduction formula.

**Solution**: Tests requiring baseline behavior explicitly set `char.ch_class = 3` (Warrior) to disable fMana reduction.

**Code Pattern**:
```python
def test_saves_spell_base_formula(self, movable_char_factory, monkeypatch):
    from mud.utils import rng_mm
    char = movable_char_factory("Test", 3001)
    char.ch_class = 3  # Warrior (no fMana reduction)
    # ... rest of test
```

### 2. RNG Mocking Pattern

**Correct Approach** (using pytest `monkeypatch`):
```python
def test_example(self, movable_char_factory, monkeypatch):
    from mud.utils import rng_mm
    char = movable_char_factory("Test", 3001)
    
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 34)
    result = saves_spell(15, char, int(DamageType.FIRE))
```

**Why It Works**: `saves.py` imports `from mud.utils import rng_mm` and calls `rng_mm.number_percent()`, so monkeypatching the attribute works correctly.

### 3. Immunity Downgrade Behavior

**ROM C Logic** (from `handler.c`):
```c
if (IS_SET(victim->imm_flags, bit) && IS_SET(victim->vuln_flags, bit))
    return IS_RESISTANT;  // IMM + VULN = RES
if (IS_SET(victim->res_flags, bit) && IS_SET(victim->vuln_flags, bit))
    return IS_NORMAL;     // RES + VULN = NORMAL
```

**Test Verification**:
```python
def test_check_immune_vuln_downgrades_immunity(self, movable_char_factory):
    char = movable_char_factory("Test", 3001)
    char.imm_flags = int(DefenseBit.IMM_FIRE)
    char.vuln_flags = int(DefenseBit.VULN_FIRE)
    
    result = check_immune(char, int(DamageType.FIRE))
    assert result == 1  # IS_RESISTANT
```

---

## Files Modified

### Created
- `tests/test_saves_rom_parity.py` - 29 tests for save formulas and immunity

### Modified (Context)
- `mud/affects/saves.py` - Implementation verified against ROM C sources
- `mud/models/character.py` - Character class constants used in tests
- `mud/models/constants.py` - DamageType, DefenseBit enums used in tests

---

## Next Steps (Optional)

From `ROM_C_PARITY_TEST_GAP_ANALYSIS.md`:

### Remaining P0 Tasks (Optional Quality Enhancements)

**Task #11**: Reset Execution Tests (OPTIONAL)
- **Target**: ROM `reset.c:160-350`
- **Estimated**: ~25 tests, 2-3 hours
- **Priority**: P0 (important for world reset correctness)

**Task #12**: Save/Load Integrity Tests (OPTIONAL)
- **Target**: ROM `save.c:43-800`
- **Estimated**: ~30 tests, 2-3 hours
- **Priority**: P1 (important for long-term MUD operation)

**Task #14-15**: Documentation Updates
- Update `ROM_2.4B6_PARITY_CERTIFICATION.md` with new test counts
- Update `docs/parity/ROM_PARITY_FEATURE_TRACKER.md`

---

## Success Criteria

- [x] Test `saves_spell()` base formula (ROM magic.c:215-239)
- [x] Test immunity/resistance/vulnerability (ROM handler.c:213-320)
- [x] Test `saves_dispel()` formula (ROM magic.c:243-254)
- [x] Test `check_dispel()` mechanics (ROM magic.c:258-282)
- [x] Integration tests combining saves/immunity/damage
- [x] All 29 tests passing with ROM C parity verified
- [x] No regressions in full test suite (2488 tests total)

---

## Test Suite Statistics

**Total Tests**: 2488 tests (December 30, 2025)

**ROM C Parity Tests (This Session)**:
- `test_saves_rom_parity.py`: 29 tests (saves/immunity)
- `test_char_update_rom_parity.py`: 30 tests (character regeneration)
- `test_obj_update_rom_parity.py`: 22 tests (object timers/decay)
- `test_handler_affects_rom_parity.py`: 27 tests (affect mechanics)
- **Total**: 108 tests added for core mechanics formula verification

**Overall ROM Parity Coverage**:
- Spell tests: 375 tests (100% coverage - all 97 spells)
- Skill tests: 254+ tests (100% coverage - all 37 skills)
- Combat tests: 104 tests (100% coverage - all 8 combat skills)
- Core mechanics: 108 tests (NEW - saves, regeneration, affects, timers)
- **Total ROM parity tests**: 841+ tests

---

## Conclusion

✅ **Saves & immunity ROM parity tests complete!**

- **29 tests** added for save formulas and immunity mechanics
- **100% ROM C parity** verified against `magic.c` and `handler.c`
- **All tests passing** (29/29 in file, 108/108 this session, 2488 total)
- **No regressions** in full test suite

These tests provide formula-level verification for ROM's magic resistance system, ensuring QuickMUD's save calculations and immunity mechanics match ROM 2.4b6 exactly.
