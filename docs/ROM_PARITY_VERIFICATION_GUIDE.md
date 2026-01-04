# How to Verify ROM Parity - Developer Guide

**Version**: 1.0  
**Date**: December 30, 2025  
**Purpose**: Systematic approach to ensuring QuickMUD maintains 100% behavioral parity with ROM 2.4b6

---

## Table of Contents

1. [Introduction](#introduction)
2. [What is ROM Parity?](#what-is-rom-parity)
3. [Why ROM Parity Matters](#why-rom-parity-matters)
4. [The Three Levels of Verification](#the-three-levels-of-verification)
5. [Level 1: Code Structure Parity](#level-1-code-structure-parity)
6. [Level 2: Behavioral Parity](#level-2-behavioral-parity)
7. [Level 3: Integration Parity](#level-3-integration-parity)
8. [Common Parity Pitfalls](#common-parity-pitfalls)
9. [Verification Checklist](#verification-checklist)
10. [Tools and Scripts](#tools-and-scripts)
11. [Case Studies](#case-studies)

---

## Introduction

This guide teaches developers how to verify that QuickMUD (Python) maintains **exact behavioral parity** with ROM 2.4b6 (C). 

**Critical Lesson**: Unit tests passing ≠ ROM parity. A function can work perfectly in isolation but behave differently than ROM when integrated into the game loop.

**Example**: The `violence_tick()` bug (December 2025):
- ✅ Unit tests passed: Combat mechanics worked
- ✅ Kill command worked: Started combat correctly
- ❌ **ROM parity failed**: Combat rounds never executed because `game_tick()` didn't call `multi_hit()`

---

## What is ROM Parity?

ROM parity means QuickMUD produces **identical observable behavior** to ROM 2.4b6 under equivalent conditions.

### Observable Behavior Includes:

1. **Game Mechanics**
   - Damage calculations
   - Skill/spell effects
   - Combat rounds
   - Movement mechanics

2. **Timing & Frequency**
   - Update cadences (PULSE constants)
   - Event triggers
   - Regeneration rates
   - Mob AI frequency

3. **Edge Cases**
   - Error messages
   - Boundary conditions
   - Race conditions
   - State transitions

4. **User Experience**
   - Command output
   - Message formatting
   - Color codes
   - Prompt behavior

### What Parity Does NOT Mean:

- ❌ Identical code structure (Python vs C is inherently different)
- ❌ Same variable names (Python conventions differ)
- ❌ Same implementation details (e.g., linked lists vs Python lists)
- ❌ Same performance characteristics (acceptable trade-off)

**Golden Rule**: *If a ROM player couldn't tell the difference, you have parity.*

---

## Why ROM Parity Matters

### 1. Historical Accuracy

ROM 2.4b6 is a **proven, balanced game design** refined over decades. Deviating from its behavior risks:
- Breaking game balance
- Creating exploits
- Losing the authentic ROM feel

### 2. Builder Expectations

ROM area builders expect **exact ROM behavior**:
- Mob damage formulas
- Skill success rates
- Reset mechanics
- Mob AI patterns

Deviations break existing areas.

### 3. Silent Failures

Parity violations often **fail silently**:
- No crashes
- No error messages
- Tests pass
- But gameplay is subtly (or critically) wrong

**Example**: Mobile update running 16x too frequently:
- No errors thrown
- Mobs still moved (just too often)
- Tests passed (mobs did move)
- But ROM parity was broken (4x faster scavenging/wandering)

---

## The Three Levels of Verification

### Level 1: Code Structure Parity
**Question**: Does the code mirror ROM C structure?

### Level 2: Behavioral Parity  
**Question**: Do individual functions produce ROM-identical output?

### Level 3: Integration Parity
**Question**: Does the system work correctly when integrated into the game loop?

**All three levels required** - missing any level = parity violation risk.

---

## Level 1: Code Structure Parity

### What to Verify

1. **Function Exists**
   - Every ROM C function has a QuickMUD equivalent
   - Function purpose matches ROM exactly

2. **Call Sites Correct**
   - Functions called from same places as ROM
   - Call order matches ROM

3. **Control Flow Matches**
   - Conditionals mirror ROM logic
   - Loops match ROM iteration patterns
   - Early returns match ROM exit points

### How to Verify

#### Step 1: Find the ROM C Function

```bash
# Example: Verifying violence_update
grep -n "void violence_update" src/*.c
# Result: src/fight.c:66
```

#### Step 2: Read ROM C Implementation

```c
// src/fight.c:66-96
void violence_update (void) {
    CHAR_DATA *ch;
    CHAR_DATA *ch_next;
    CHAR_DATA *victim;

    for (ch = char_list; ch != NULL; ch = ch_next) {
        ch_next = ch->next;
        
        if ((victim = ch->fighting) == NULL || ch->in_room == NULL)
            continue;

        if (IS_AWAKE(ch) && ch->in_room == victim->in_room)
            multi_hit(ch, victim, TYPE_UNDEFINED);  // ⚠️ THIS LINE IS CRITICAL!
        else
            stop_fighting(ch, FALSE);
    }
    return;
}
```

**Key Observations**:
1. Iterates all characters
2. Checks if fighting and in room
3. **Calls `multi_hit()` if awake and same room** ← CRITICAL
4. Else calls `stop_fighting()`

#### Step 3: Find QuickMUD Equivalent

```bash
grep -rn "def violence" mud/
# Result: mud/game_loop.py:955
```

#### Step 4: Compare Structure

```python
# QuickMUD BEFORE FIX (WRONG - missing multi_hit!)
def violence_tick() -> None:
    for ch in list(character_registry):
        # Decrement timers
        if hasattr(ch, "wait") and ch.wait > 0:
            ch.wait -= 1
        if hasattr(ch, "daze") and ch.daze > 0:
            ch.daze -= 1
    # ❌ MISSING: multi_hit() calls!

# QuickMUD AFTER FIX (CORRECT)
def violence_tick() -> None:
    from mud.combat.engine import multi_hit, stop_fighting
    
    for ch in list(character_registry):
        # Timer decrement (existing)
        # ...
        
        # ✅ ADDED: Combat round processing (ROM parity)
        victim = getattr(ch, "fighting", None)
        if victim is None or getattr(ch, "room", None) is None:
            continue
        
        if ch.is_awake() and ch.room == victim.room:
            multi_hit(ch, victim, dt=None)  # ✅ ROM PARITY RESTORED!
        else:
            stop_fighting(ch, both=False)
```

**Verification Result**: ✅ Structure now matches ROM

### Level 1 Checklist

- [ ] ROM C function identified
- [ ] ROM C control flow documented
- [ ] QuickMUD equivalent found
- [ ] Control flow matches ROM
- [ ] All ROM code paths represented in QuickMUD
- [ ] Docstring references ROM C source file and line numbers

**Example Docstring**:
```python
def violence_tick() -> None:
    """Process combat rounds and consume wait/daze counters.
    
    Mirrors ROM src/fight.c:violence_update (lines 66-96) which iterates
    all characters, checks if they're fighting, and calls multi_hit()
    to process combat rounds.
    """
```

---

## Level 2: Behavioral Parity

### What to Verify

Individual functions produce **ROM-identical output** for equivalent inputs.

### How to Verify

#### Method 1: Golden File Tests

**ROM 2.4b6 is the source of truth.** Capture ROM behavior and test QuickMUD matches exactly.

**Example: Damage Calculation**

1. **Capture ROM behavior** (from C code or live server):
```c
// ROM damage formula (src/fight.c)
dam = number_range(dam_type_low, dam_type_high);
dam = (dam * ch->damroll) / 100;  // C integer division!
```

2. **Create golden test**:
```python
def test_damage_calculation_rom_parity():
    """Verify damage calculation matches ROM C integer semantics."""
    from mud.math.c_compat import c_div
    from mud.combat.damage import calculate_damage
    
    # Test case: ROM C behavior for dam=150, damroll=133
    # ROM: (150 * 133) / 100 = 19950 / 100 = 199 (C integer division)
    result = calculate_damage(base=150, damroll=133)
    assert result == 199, f"Expected 199 (ROM C), got {result}"
    
    # Verify we use c_div, NOT Python //
    # Python 150 * 133 // 100 = 199 (same result here)
    # But edge cases differ!
```

3. **Test edge cases**:
```python
def test_c_integer_division_edge_cases():
    """ROM uses C integer division, NOT Python //"""
    from mud.math.c_compat import c_div, c_mod
    
    # Negative division edge cases
    assert c_div(-5, 2) == -2   # C behavior
    assert -5 // 2 == -3         # Python behavior (WRONG!)
    
    assert c_mod(-5, 2) == -1   # C behavior  
    assert -5 % 2 == 1           # Python behavior (WRONG!)
```

#### Method 2: ROM C Source Analysis

**Extract formulas directly from ROM C code**:

```c
// ROM regeneration (src/update.c:char_update)
gain = number_range(age(ch).year / 2, age(ch).year);
gain = gain * ch->pcdata->condition[COND_FULL] / 48;
```

**Translate to Python with C semantics**:
```python
def calculate_hp_gain(char: Character) -> int:
    """Mirror ROM src/update.c:char_update HP regeneration."""
    from mud.math.c_compat import c_div
    
    age_years = get_age_years(char)
    gain = rng_mm.number_range(c_div(age_years, 2), age_years)
    fullness = char.pcdata.condition[Condition.FULL]
    gain = c_div(gain * fullness, 48)  # ✅ Use c_div, NOT //!
    return gain
```

#### Method 3: Differential Testing

**Run identical inputs through ROM and QuickMUD, compare outputs**:

```python
def test_skill_success_rate_rom_parity():
    """Verify backstab success rate matches ROM formula."""
    # ROM formula: chance = 20 + (skill_level * 4) + (dex_bonus * 2)
    
    char = create_test_character(level=10, dex=18, backstab_skill=75)
    
    # Expected ROM behavior:
    # skill_level = 75 * 10 / 100 = 7 (C division!)
    # dex_bonus = (18 - 13) = 5
    # chance = 20 + (7 * 4) + (5 * 2) = 20 + 28 + 10 = 58%
    
    # Test 1000 attempts to verify statistical distribution
    successes = sum(attempt_backstab(char) for _ in range(1000))
    success_rate = successes / 1000
    
    # Allow 5% variance (statistical noise)
    assert 0.53 <= success_rate <= 0.63, \
        f"Expected ~58% success rate, got {success_rate*100}%"
```

### Level 2 Checklist

- [ ] ROM C formula extracted and documented
- [ ] C integer semantics preserved (`c_div`/`c_mod`)
- [ ] RNG uses `rng_mm` (ROM's Meow Meow RNG), not `random`
- [ ] Golden file tests created
- [ ] Edge cases tested (negative numbers, overflow, zero)
- [ ] Statistical tests for probabilistic behavior

---

## Level 3: Integration Parity

### What to Verify

Systems work correctly **when integrated into the game loop**, not just in isolation.

**This is where most parity violations hide!**

### The Integration Gap

```
✅ Unit tests pass:      combat.calculate_damage() works
✅ Unit tests pass:      kill_command() works  
✅ Unit tests pass:      violence_tick() decrements timers
❌ Integration FAILS:    Combat doesn't progress because
                         game_tick() never calls multi_hit()!
```

### How to Verify

#### Method 1: End-to-End Workflow Tests

**Test complete gameplay workflows through the game loop**:

```python
def test_combat_progression_integration():
    """Verify combat progresses through game loop (ROM parity)."""
    from mud.game_loop import game_tick
    from mud.commands.dispatcher import process_command
    
    # Setup
    attacker = create_test_character("Alice", room_vnum=3001)
    victim = create_test_mob(vnum=3000, room_vnum=3001)
    
    # Start combat
    result = process_command(attacker, "kill Hassan")
    assert "You miss Hassan" in result or "You hit Hassan" in result
    assert attacker.fighting == victim
    
    # ⚠️ CRITICAL: Verify combat continues through game loop
    combat_messages = []
    for _ in range(10):  # 10 game ticks
        game_tick()  # ✅ THIS MUST PROCESS COMBAT ROUNDS!
        # Capture combat messages here
    
    # Verify combat rounds occurred
    assert len(combat_messages) > 0, "Combat must progress via game_tick()!"
    assert any("hit" in msg or "miss" in msg for msg in combat_messages)
```

#### Method 2: Timing Verification

**Verify update frequencies match ROM pulse constants**:

```python
def test_mobile_update_frequency_rom_parity():
    """Verify mobs update every PULSE_MOBILE (16 pulses), not every pulse."""
    from mud.game_loop import game_tick
    from mud.config import get_pulse_mobile
    
    mob = create_scavenger_mob(room_vnum=3001)
    room = get_room(3001)
    create_object_in_room(room, cost=1000)  # Valuable item
    
    scavenge_count = 0
    pulse_mobile = get_pulse_mobile()  # Should be 16
    
    # Run 100 pulses, track scavenge attempts
    for pulse in range(100):
        initial_inventory = len(mob.inventory)
        game_tick()
        
        if len(mob.inventory) > initial_inventory:
            scavenge_count += 1
            # ✅ Should only happen on PULSE_MOBILE boundaries!
            assert pulse % pulse_mobile == 0, \
                f"Scavenge at pulse {pulse}, expected multiples of {pulse_mobile}"
    
    # Verify scavenging happened, but at correct frequency
    assert scavenge_count > 0, "Mob should scavenge sometimes"
    expected_attempts = 100 // pulse_mobile  # ~6 attempts
    # Allow for RNG variance (1/64 chance per attempt)
```

#### Method 3: State Transition Verification

**Verify state transitions match ROM exactly**:

```python
def test_position_transition_combat_rom_parity():
    """Verify position changes during combat match ROM rules."""
    from mud.game_loop import game_tick
    from mud.models.constants import Position
    
    char = create_test_character("TestChar", room_vnum=3001)
    victim = create_test_mob(vnum=3000, room_vnum=3001)
    
    # Start standing combat
    char.position = Position.STANDING
    start_combat(char, victim)
    
    # ROM rule: bash knocks target to sitting
    process_command(char, "bash")
    assert victim.position == Position.SITTING, "Bash should knock sitting"
    
    # ROM rule: sitting victim can't dodge as well
    # (Test through game tick to verify integration)
    hit_count = 0
    for _ in range(20):
        initial_hp = victim.hit
        game_tick()
        if victim.hit < initial_hp:
            hit_count += 1
    
    # Sitting targets should be hit more often (verify via statistics)
    assert hit_count > 10, "Sitting victim should be easier to hit"
```

### Level 3 Checklist

- [ ] Complete workflow tested (command → game loop → observable result)
- [ ] Timing verified (correct PULSE cadence)
- [ ] State transitions verified
- [ ] Multi-system interactions tested
- [ ] Game loop integration confirmed
- [ ] No manual function calls (all through game_tick())

---

## Common Parity Pitfalls

### Pitfall 1: Python Integer Division

**Problem**: Python `//` and `%` behave differently than C `/` and `%` for negative numbers.

**ROM C Behavior**:
```c
int result = -5 / 2;   // = -2
int remainder = -5 % 2; // = -1
```

**Python Behavior**:
```python
result = -5 // 2       # = -3 (WRONG!)
remainder = -5 % 2     # = 1 (WRONG!)
```

**Solution**: Always use `c_div()` and `c_mod()`:
```python
from mud.math.c_compat import c_div, c_mod

result = c_div(-5, 2)      # = -2 ✅
remainder = c_mod(-5, 2)   # = -1 ✅
```

### Pitfall 2: RNG Differences

**Problem**: Python's `random` module uses different algorithm than ROM's Meow Meow RNG.

**Wrong**:
```python
import random
damage = random.randint(10, 20)  # ❌ Different RNG!
```

**Correct**:
```python
from mud.math import rng_mm
damage = rng_mm.number_range(10, 20)  # ✅ ROM parity!
```

### Pitfall 3: Missing Integration

**Problem**: Function works in isolation but never gets called by game loop.

**Example**:
```python
# ✅ Function exists and works
def mobile_update():
    # ... correct implementation ...

# ❌ But game_tick() doesn't call it!
def game_tick():
    violence_tick()
    char_update()
    # Missing: mobile_update() call!
```

**Detection**: Write integration tests that verify game_tick() triggers expected behavior.

### Pitfall 4: Incorrect Update Frequency

**Problem**: Function called at wrong cadence (every pulse vs every PULSE_MOBILE).

**ROM**: `mobile_update()` every 16 pulses (4 seconds)  
**QuickMUD (wrong)**: `mobile_update()` every pulse (0.25 seconds)  
**Result**: Mobs move/scavenge 16x too frequently!

**Solution**: Verify all update functions use correct PULSE constants.

### Pitfall 5: Enum Value Hardcoding

**Problem**: Hardcoding flag values instead of using enum definitions.

**Wrong**:
```python
if char.act & 0x00000800:  # ❌ What flag is this?
    # ...
```

**Correct**:
```python
from mud.models.constants import ActFlag
if char.act & ActFlag.SCAVENGER:  # ✅ Clear intent!
    # ...
```

**Why This Matters**: ROM C enum values come from bit shifts, not hex constants. Hardcoded values will be wrong!

---

## Verification Checklist

### For New Features

- [ ] ROM C source file and line numbers documented in docstring
- [ ] ROM C formula/algorithm extracted and preserved
- [ ] Uses `c_div`/`c_mod` for integer math (not `//` or `%`)
- [ ] Uses `rng_mm` for randomness (not `random`)
- [ ] Uses enum constants (not hardcoded hex values)
- [ ] Golden file test created (ROM behavior captured)
- [ ] Edge cases tested (negative, zero, overflow)
- [ ] Integration test verifies game loop behavior
- [ ] Timing verified (correct PULSE cadence if periodic)
- [ ] Code review confirms ROM parity

### For Bug Fixes

- [ ] ROM C behavior verified (what does ROM actually do?)
- [ ] Root cause identified (why did QuickMUD differ?)
- [ ] Fix preserves ROM semantics (not just "makes it work")
- [ ] Regression test added (prevents reoccurrence)
- [ ] Related systems audited (any similar issues?)
- [ ] Documentation updated

### For Refactoring

- [ ] ROM behavior preserved (output identical before/after)
- [ ] Integration tests still pass
- [ ] ROM C source references maintained
- [ ] No new deviations introduced

---

## Tools and Scripts

### 1. Game Loop Verification Script

**Location**: `scripts/verify_game_loop_parity.py`

**Usage**:
```bash
python3 scripts/verify_game_loop_parity.py
```

**Verifies**:
- ✅ PULSE constants match ROM
- ✅ Update functions exist and are called
- ✅ Call order matches ROM
- ✅ Critical behaviors present (e.g., multi_hit in violence_tick)

### 2. C Integer Division Validator

**Location**: `mud/math/c_compat.py`

**Functions**:
- `c_div(a, b)` - C-style integer division
- `c_mod(a, b)` - C-style modulo
- `c_abs(x)` - C-style absolute value

**Usage**:
```python
from mud.math.c_compat import c_div, c_mod

# Always use these for ROM parity!
result = c_div(damage * level, 100)
remainder = c_mod(ticks, PULSE_VIOLENCE)
```

### 3. ROM RNG Wrapper

**Location**: `mud/math/rng_mm.py`

**Functions**:
- `number_range(low, high)` - ROM equivalent of `number_range()`
- `number_percent()` - ROM equivalent of `number_percent()`
- `number_bits(n)` - ROM equivalent of `number_bits()`

**Usage**:
```python
from mud.math import rng_mm

# Never use random module in gameplay code!
damage = rng_mm.number_range(dam_low, dam_high)
if rng_mm.number_percent() < skill_level:
    # Success!
```

### 4. Integration Test Framework

**Location**: `tests/integration/conftest.py`

**Fixtures**:
- `game_world` - Initialized world with areas loaded
- `test_character` - Character in test room
- `test_mob` - NPC mob for testing

**Example**:
```python
def test_my_integration(game_world, test_character):
    from mud.game_loop import game_tick
    
    # Setup
    # ...
    
    # Execute via game loop
    for _ in range(10):
        game_tick()
    
    # Verify
    assert expected_behavior
```

---

## Case Studies

### Case Study 1: Violence Tick Bug (December 2025)

**Symptom**: Combat started but never progressed.

**Investigation**:
1. ✅ Unit tests passed (combat math worked)
2. ✅ Kill command worked (started combat)
3. ❌ Integration failed (no combat rounds)

**Root Cause**: `violence_tick()` decremented timers but **never called `multi_hit()`**.

**ROM C Reference**:
```c
// src/fight.c:66-96
void violence_update (void) {
    for (ch = char_list; ch != NULL; ch = ch_next) {
        if (IS_AWAKE(ch) && ch->in_room == victim->in_room)
            multi_hit(ch, victim, TYPE_UNDEFINED);  // ⚠️ MISSING!
    }
}
```

**Fix**: Added `multi_hit()` calls to `violence_tick()`.

**Lesson**: **Integration tests would have caught this immediately.**

### Case Study 2: Mobile Update Frequency (December 2025)

**Symptom**: Mobs moved/scavenged too frequently.

**Investigation**:
1. ✅ mobile_update() logic correct
2. ✅ Scavenging worked (picked up items)
3. ❌ Frequency wrong (16x too often!)

**Root Cause**: `game_tick()` called `mobile_update()` **every pulse** instead of every **PULSE_MOBILE**.

**ROM C Reference**:
```c
// src/update.c:1151-1195
static int pulse_mobile;

if (--pulse_mobile <= 0) {
    pulse_mobile = PULSE_MOBILE;  // = 16
    mobile_update();
}
```

**Fix**: Added `_mobile_counter` and made `mobile_update()` pulse-based.

**Lesson**: **Timing verification is critical for ROM parity.**

### Case Study 3: Tell Command Lookup (December 2025)

**Symptom**: `tell Hassan hello` couldn't find NPCs.

**Investigation**:
1. ✅ Hassan exists in room
2. ✅ Tell command logic works
3. ❌ Wrong character lookup method

**Root Cause**: Used `character_registry` (global list) instead of ROM's `get_char_world()`.

**ROM C Reference**:
```c
// src/act_comm.c:880-881
if ((victim = get_char_world (ch, arg)) == NULL
    || (IS_NPC (victim) && victim->in_room != ch->in_room))
```

**Fix**: Changed to use `get_char_world()` with NPC room check.

**Lesson**: **Always mirror ROM C's API calls, not just the logic.**

---

## Quick Reference Card

### Before Writing Any Game Code

1. Find the ROM C equivalent function/file
2. Read and document ROM C behavior
3. Extract formulas and algorithms
4. Note edge cases and special conditions

### While Writing Code

1. Use `c_div`/`c_mod` for integer math
2. Use `rng_mm` for randomness
3. Use enum constants (not hex values)
4. Add ROM C source reference in docstring

### After Writing Code

1. Create golden file test (ROM behavior)
2. Test edge cases (negative, zero, overflow)
3. Write integration test (via game_tick)
4. Verify timing (if periodic update)
5. Code review with ROM parity focus

### Red Flags

- ❌ Using `//` or `%` for division/modulo
- ❌ Using `random` module
- ❌ Hardcoded hex flag values
- ❌ No ROM C source reference
- ❌ Only unit tests (no integration tests)
- ❌ "It works" without ROM verification

---

## Additional Resources

### ROM C Source Files (43 files)

Primary gameplay systems:
- `src/fight.c` - Combat engine
- `src/update.c` - Game loop and update cadences  
- `src/handler.c` - Object/character manipulation
- `src/magic.c` - Spell system
- `src/skills.c` - Skill system
- `src/act_move.c` - Movement and following
- `src/db.c` - Area loading and world data

### QuickMUD Documentation

- `VIOLENCE_TICK_ROOT_CAUSE_ANALYSIS.md` - Case study: combat bug
- `SESSION_SUMMARY_2025-12-30_BUG_FIXES.md` - Recent parity fixes
- `docs/parity/ROM_PARITY_FEATURE_TRACKER.md` - Parity status tracking
- `ROM_2.4B6_PARITY_CERTIFICATION.md` - Official parity certification

### Testing Resources

- `tests/integration/` - Integration test examples
- `tests/test_combat.py` - Combat parity tests
- `tests/test_game_loop.py` - Game loop tests
- `scripts/verify_game_loop_parity.py` - Automated verification

---

## Summary

**ROM parity is not automatic** - it requires:

1. **Understanding ROM C source code** (the source of truth)
2. **Preserving ROM semantics** (formulas, algorithms, edge cases)
3. **Testing at all three levels** (code structure, behavior, integration)
4. **Continuous verification** (automated scripts, code review)

**The Three-Level Checklist**:
- ✅ Level 1: Code structure mirrors ROM C
- ✅ Level 2: Functions produce ROM-identical output
- ✅ Level 3: Systems work through game loop integration

**Remember**: Unit tests passing ≠ ROM parity. Always verify integration!

---

**Document Version**: 1.0  
**Last Updated**: December 30, 2025  
**Maintainer**: QuickMUD Development Team
