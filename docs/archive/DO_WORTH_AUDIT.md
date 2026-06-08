# do_worth ROM C Parity Audit

**ROM C Source**: `src/act_info.c` lines 1453-1474 (22 lines)  
**QuickMUD Implementation**: `mud/commands/info_extended.py` lines 228-249 (22 lines)  
**Audit Date**: January 7, 2026  
**Audit Status**: ⚠️ **1 IMPORTANT GAP FOUND** - Simplified exp_per_level formula

---

## Executive Summary

**Result**: ⚠️ **PARTIAL PARITY - 1 Important Gap**

QuickMUD's `do_worth()` command correctly implements the display logic, but uses a **simplified exp_per_level formula** that doesn't match ROM C's complex calculation. This affects exp-to-level display accuracy.

**Gaps Found**: 0 CRITICAL, 1 IMPORTANT, 0 MINOR  
**Estimated Fix Effort**: 1-2 hours (implement correct exp_per_level formula)

---

## ROM C Behavior Analysis

### do_worth Function (src/act_info.c lines 1453-1474)

```c
void do_worth (CHAR_DATA * ch, char *argument)
{
    char buf[MAX_STRING_LENGTH];

    if (IS_NPC (ch))  // Line 1457
    {
        sprintf (buf, "You have %ld gold and %ld silver.\n\r",
                 ch->gold, ch->silver);
        send_to_char (buf, ch);
        return;
    }

    sprintf (buf,  // Line 1465
             "You have %ld gold, %ld silver, and %d experience (%d exp to level).\n\r",
             ch->gold, ch->silver, ch->exp,
             (ch->level + 1) * exp_per_level (ch,
                                              ch->pcdata->points) - ch->exp);

    send_to_char (buf, ch);

    return;
}
```

### exp_per_level Function (src/skills.c lines 639-672)

**CRITICAL**: ROM C uses a complex formula based on race/class multipliers and creation points!

```c
int exp_per_level (CHAR_DATA * ch, int points)
{
    int expl, inc;

    if (IS_NPC (ch))  // Line 643
        return 1000;

    expl = 1000;  // Line 646
    inc = 500;

    if (points < 40)  // Line 649 - Base case for standard characters
        return 1000 * (pc_race_table[ch->race].class_mult[ch->class] ?
                       pc_race_table[ch->race].class_mult[ch->class] /
                       100 : 1);

    /* processing */
    points -= 40;  // Line 655

    while (points > 9)  // Line 657 - Complex escalating formula
    {
        expl += inc;
        points -= 10;
        if (points > 9)
        {
            expl += inc;
            inc *= 2;  // Doubling increment!
            points -= 10;
        }
    }

    expl += points * inc / 10;  // Line 669 - Final adjustment

    return expl * pc_race_table[ch->race].class_mult[ch->class] / 100;  // Line 671 - Apply class mult
}
```

**ROM C Formula Explained**:
1. **NPC**: Always 1000 exp/level
2. **PC with points < 40**: `1000 * class_mult / 100` (race/class modifier)
3. **PC with points ≥ 40**: Complex escalating formula:
   - Start: `expl = 1000`, `inc = 500`
   - Every 10 points over 40: Add `inc`, then double `inc`
   - Final: Multiply by race/class multiplier (`class_mult / 100`)

**Example Calculation** (Human Warrior, 60 creation points):
- Points = 60, Race = Human, Class = Warrior
- `points < 40`? NO, so continue
- `points -= 40` → points = 20
- Iteration 1: expl = 1500 (1000+500), points = 10, inc = 500
- Iteration 2: expl = 2000 (1500+500), inc = 1000, points = 0
- Final: `expl * class_mult / 100` = `2000 * 100 / 100` = **2000 exp/level**

---

## QuickMUD Implementation Analysis

### do_worth (mud/commands/info_extended.py lines 228-249)

```python
def do_worth(char: Character, args: str) -> str:
    """
    Show character's monetary worth and experience.

    ROM Reference: src/act_info.c do_worth (lines 1453-1472)
    """
    gold = getattr(char, "gold", 0)  # Line 234
    silver = getattr(char, "silver", 0)

    is_npc = getattr(char, "is_npc", False)  # Line 237

    if is_npc:  # Line 239
        return f"You have {gold} gold and {silver} silver."

    exp = getattr(char, "exp", 0)  # Line 242
    level = getattr(char, "level", 1)

    # Calculate exp to next level
    exp_per_lvl = _exp_per_level(char)  # Line 246
    exp_to_level = (level + 1) * exp_per_lvl - exp

    return f"You have {gold} gold, {silver} silver, and {exp} experience ({exp_to_level} exp to level)."
```

### _exp_per_level (mud/commands/info_extended.py lines 327-335)

**⚠️ SIMPLIFIED FORMULA** - Does not match ROM C!

```python
def _exp_per_level(char: Character) -> int:
    """Calculate experience per level."""
    # Base 1000 exp per level, modified by creation points
    pcdata = getattr(char, "pcdata", None)  # Line 330
    if pcdata:
        points = getattr(pcdata, "points", 40)
        base = 1000
        return base + points * 10  # ⚠️ WRONG! Should use ROM C escalating formula
    return 1000
```

**Problem**: QuickMUD uses `base + points * 10` instead of ROM C's complex escalating formula with class/race multipliers!

---

## Gap Analysis

### ✅ Correctly Implemented Features

| Feature | ROM C | QuickMUD | Status |
|---------|-------|----------|--------|
| NPC gold/silver display | ✅ Line 1457-1462 | ✅ Line 239-240 | ✅ PERFECT |
| PC gold/silver/exp display | ✅ Line 1465-1471 | ✅ Line 242-249 | ✅ PERFECT |
| Exp to level calculation | ✅ `(level+1)*exp_per_level - exp` | ✅ Line 247 | ✅ PERFECT |
| Message format (NPC) | `"You have %ld gold and %ld silver.\n\r"` | `"You have {gold} gold and {silver} silver."` | ✅ PERFECT |
| Message format (PC) | `"You have %ld gold, %ld silver, and %d experience (%d exp to level).\n\r"` | Matches | ✅ PERFECT |

### ⚠️ Gap 1: Simplified exp_per_level Formula (IMPORTANT)

**ROM C Formula** (src/skills.c lines 639-672):
- Complex escalating formula with race/class multipliers
- Different behavior for `points < 40` vs `points ≥ 40`
- Exponentially increasing exp requirements for optimized characters

**QuickMUD Formula** (info_extended.py lines 327-335):
- Simplified linear formula: `1000 + points * 10`
- No race/class multipliers
- No escalating calculation for high creation points

**Impact**:
- **Incorrect exp-to-level display** for characters with non-standard creation points
- **Example Discrepancy**:
  - Character with 60 creation points (Human Warrior):
    - **ROM C**: 2000 exp/level (after complex calculation)
    - **QuickMUD**: 1200 exp/level (1000 + 60*10 = 1600? NO, see below)

**Wait, let me recalculate QuickMUD's formula**:
- `points = 60`
- `base + points * 10 = 1000 + 60*10 = 1000 + 600 = 1600`

**Comparison** (60 creation points):
- **ROM C**: ~2000 exp/level (with class mult)
- **QuickMUD**: 1600 exp/level
- **Difference**: -400 exp/level (-20% error!)

**Priority**: IMPORTANT (P1)  
**Severity**: Medium (affects character progression display, not gameplay)  
**Fix Effort**: 1-2 hours (implement correct ROM C formula)

---

## Detailed Gap Analysis

### Gap 1: Implement Correct exp_per_level Formula

**File**: `mud/commands/info_extended.py`  
**Location**: Lines 327-335 (`_exp_per_level`)

**Current Code** (WRONG):
```python
def _exp_per_level(char: Character) -> int:
    """Calculate experience per level."""
    # Base 1000 exp per level, modified by creation points
    pcdata = getattr(char, "pcdata", None)
    if pcdata:
        points = getattr(pcdata, "points", 40)
        base = 1000
        return base + points * 10  # ⚠️ SIMPLIFIED
    return 1000
```

**Correct ROM C Implementation** (NEEDED):
```python
def _exp_per_level(char: Character) -> int:
    """
    Calculate experience per level.
    
    ROM Reference: src/skills.c exp_per_level (lines 639-672)
    """
    # NPCs always get 1000 exp/level
    is_npc = getattr(char, "is_npc", False)
    if is_npc:
        return 1000
    
    # Get pcdata and creation points
    pcdata = getattr(char, "pcdata", None)
    if not pcdata:
        return 1000
    
    points = getattr(pcdata, "points", 40)
    
    # Get race and class for multiplier lookup
    race = getattr(char, "race", None)
    char_class = getattr(char, "char_class", None)
    
    # Get class multiplier from race table
    # TODO: Implement pc_race_table lookup
    # For now, use default multiplier of 100 (1.0x)
    class_mult = 100
    if race and char_class:
        # class_mult = pc_race_table[race].class_mult[char_class]
        pass
    
    # Base case: points < 40 (standard character creation)
    if points < 40:
        return 1000 * (class_mult // 100 if class_mult else 1)
    
    # Complex escalating formula for optimized characters (points >= 40)
    expl = 1000
    inc = 500
    points -= 40
    
    while points > 9:
        expl += inc
        points -= 10
        if points > 9:
            expl += inc
            inc *= 2  # Double the increment
            points -= 10
    
    # Final fractional points
    expl += points * inc // 10
    
    # Apply class multiplier
    return expl * class_mult // 100
```

**Dependencies**:
- Need `pc_race_table` data structure with `class_mult` values
- Check if this exists in QuickMUD's race/class system
- If not, may need to add race/class multipliers to data models

**Verification**:
1. Test with standard character (40 points) → 1000 exp/level
2. Test with optimized character (60 points) → ~2000 exp/level
3. Test with different race/class combinations
4. Compare with ROM C calculations

---

## Testing Recommendations

### Recommended Integration Tests

Create `tests/integration/test_do_worth.py`:

```python
def test_worth_npc_shows_gold_silver():
    """Test worth command for NPCs shows only gold/silver."""
    mob = create_mob(gold=100, silver=50, is_npc=True)
    result = do_worth(mob, "")
    assert "You have 100 gold and 50 silver" in result
    assert "experience" not in result.lower()

def test_worth_pc_shows_gold_silver_exp():
    """Test worth command for PCs shows gold/silver/exp."""
    char = create_char(gold=100, silver=50, exp=5000, level=10)
    result = do_worth(char, "")
    assert "100 gold" in result
    assert "50 silver" in result
    assert "5000 experience" in result
    assert "exp to level" in result.lower()

def test_worth_exp_to_level_calculation():
    """Test exp-to-level calculation is correct."""
    char = create_char(exp=5000, level=10)
    # Assuming 1000 exp/level: (10+1)*1000 - 5000 = 11000 - 5000 = 6000
    result = do_worth(char, "")
    assert "6000 exp to level" in result or "(6000 exp" in result

def test_worth_exp_per_level_standard_character():
    """Test exp_per_level for standard character (40 points)."""
    char = create_char(level=1, points=40)
    exp_per_lvl = _exp_per_level(char)
    assert exp_per_lvl == 1000  # Base case

def test_worth_exp_per_level_optimized_character():
    """Test exp_per_level for optimized character (60 points)."""
    char = create_char(level=1, points=60, race="human", char_class="warrior")
    exp_per_lvl = _exp_per_level(char)
    # ROM C calculation for 60 points (human warrior):
    # expl=1000, inc=500, points=20
    # Iter 1: expl=1500, points=10
    # Iter 2: expl=2000, inc=1000, points=0
    # Result: 2000 * 100/100 = 2000
    assert exp_per_lvl == 2000  # Complex escalating formula

def test_worth_exp_per_level_with_class_multiplier():
    """Test exp_per_level applies class multiplier."""
    # Example: Elf Mage might have class_mult=120 (20% more exp needed)
    char = create_char(level=1, points=40, race="elf", char_class="mage")
    exp_per_lvl = _exp_per_level(char)
    # Expected: 1000 * 120/100 = 1200
    # (once class_mult lookup is implemented)
```

**Estimated Test Creation Time**: 1 hour

---

## Implementation Plan

### Step 1: Verify Race/Class Data Structures (15 minutes)

Check if QuickMUD has `pc_race_table` equivalent with `class_mult` values:
```bash
grep -r "class_mult" mud/
grep -r "pc_race_table" mud/
```

If missing, need to:
1. Add `class_mult` field to race data
2. Populate class multipliers from ROM C `pc_race_table` (src/tables.c)

### Step 2: Implement Correct exp_per_level Formula (30 minutes)

Replace simplified formula with ROM C escalating formula (see code above).

### Step 3: Create Integration Tests (1 hour)

Write 6 integration tests to verify:
1. NPC worth display
2. PC worth display
3. Exp-to-level calculation
4. Standard character (40 points) → 1000 exp/level
5. Optimized character (60 points) → 2000 exp/level
6. Class multiplier application

### Step 4: Verification (15 minutes)

1. Run integration tests
2. Manually test in-game with different characters
3. Compare with ROM C calculations

**Total Estimated Time**: 2 hours

---

## Acceptance Criteria

- [ ] `_exp_per_level()` implements ROM C formula correctly
- [ ] Race/class multipliers (`class_mult`) integrated
- [ ] Standard character (40 points) returns 1000 exp/level
- [ ] Optimized character (60 points) returns ~2000 exp/level
- [ ] Integration tests created (6 tests)
- [ ] All tests passing
- [ ] No regressions in existing tests

---

## Completion Status

**Status**: ⚠️ **PARTIAL PARITY** - 1 Important Gap

**Completed**:
- [x] do_worth message format (100% ROM C parity)
- [x] NPC vs PC handling (100% ROM C parity)
- [x] Exp-to-level calculation formula (100% ROM C parity)

**Remaining**:
- [ ] Fix exp_per_level formula (simplified → ROM C complex formula)
- [ ] Add race/class multiplier support (if missing)
- [ ] Create integration tests (6 tests)
- [ ] Verify with ROM C calculations

---

## Recommendation

**Status**: ⚠️ **NEEDS FIX** - Simplified exp_per_level formula

**Priority**: P1 (IMPORTANT)  
**Severity**: Medium (incorrect exp display, not game-breaking)  
**User Impact**: Players see incorrect "exp to level" values  
**Fix Effort**: 1-2 hours

**Next Steps**:
1. **Optional**: Fix exp_per_level formula (1-2 hours)
2. **Move to next audit**: Audit `do_affects()` (more critical for gameplay)
3. **Update ACT_INFO_C_AUDIT.md**: Mark do_worth as "partial parity - needs exp_per_level fix"

**Recommendation**: 
- **Defer fix** (P2 priority) - Incorrect exp display is not game-breaking
- **Continue auditing** - Focus on do_affects (affects display is more critical)
- **Document gap** - Add to ROM_C_SUBSYSTEM_AUDIT_TRACKER.md as known issue

---

## Summary Statistics

**ROM C Source**: 22 lines (do_worth) + 34 lines (exp_per_level) = 56 lines total  
**QuickMUD Implementation**: 22 lines (do_worth) + 9 lines (_exp_per_level) = 31 lines  
**Gaps Found**: 0 CRITICAL, 1 IMPORTANT, 0 MINOR  
**Fix Effort**: 1-2 hours  
**Test Coverage**: 0% (no integration tests yet, recommended)  
**Parity Score**: ⚠️ **75% (do_worth perfect, exp_per_level simplified)**

**Audit Complete**: January 7, 2026
