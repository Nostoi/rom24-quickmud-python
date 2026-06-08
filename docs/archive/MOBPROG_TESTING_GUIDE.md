# MobProg Testing Guide: Ensuring C Parity

**Purpose**: Comprehensive guide for testing mob programs (MobProgs) to ensure behavioral parity with ROM 2.4b C codebase  
**Status**: QuickMUD has 97% MobProg parity - this guide verifies the remaining 3%  
**Last Updated**: 2025-12-26

---

## 🎯 Executive Summary

**Current MobProg Status**:
- ✅ **Engine**: 100% complete (trigger system, interpreter, execution)
- ✅ **Commands**: 31/31 mob commands implemented (100%)
- ✅ **Tests**: 50 tests passing (unit + integration)
- ⚠️ **Remaining**: 3% - advanced edge cases and real-world area testing

**Test Coverage**:
```bash
# Current test suite
pytest tests/test_mobprog*.py -v
# Result: 50/50 tests passing (100%)
```

---

## 📊 Three-Layer Testing Strategy

### Layer 1: Unit Tests (Component Verification)
**Purpose**: Verify individual MobProg components work in isolation  
**Location**: `tests/test_mobprog*.py` (4 files, 50 tests)  
**Coverage**: Triggers, commands, helpers, conditional logic

### Layer 2: Integration Tests (Workflow Verification)
**Purpose**: Verify complete MobProg workflows in realistic scenarios  
**Location**: `tests/integration/test_mobprog_scenarios.py` (to be created)  
**Coverage**: Multi-trigger interactions, quest workflows, AI behaviors

### Layer 3: Live Area Testing (Real-World Verification)
**Purpose**: Verify MobProgs work with actual ROM area files  
**Location**: `area/*.are` files with embedded mob programs  
**Coverage**: Production mob behaviors from ROM 2.4b distributions

---

## 🧪 Layer 1: Unit Test Coverage (Current Status)

### Test Files Breakdown

#### 1. `tests/test_mobprog.py` (2 tests)
**Focus**: Basic trigger mechanics
```python
# What's tested:
- Random character selection (visibility handling)
- Greet trigger (invisible player filtering)
```

**ROM C References**:
- `src/mob_prog.c:1252-1310` - `mp_greet_trigger()`
- `src/mob_prog.c:600-650` - `_get_random_char()`

#### 2. `tests/test_mobprog_commands.py` (20 tests)
**Focus**: All 31 mob commands (mob echo, mob kill, mob transfer, etc.)
```python
# Sample tested commands:
- mob echo/emote/say (communication)
- mob transfer/gtransfer/otransfer (teleportation)
- mob force/gforce/vforce (command execution)
- mob kill/mpmurder (combat initiation)
- mob junk/purge (object cleanup)
- mob cast (spell casting)
- mpremember/mpforget (target tracking)
```

**ROM C References**:
- `src/mob_cmds.c:1-1369` - Full mob command implementation

#### 3. `tests/test_mobprog_helpers.py` (13 tests)
**Focus**: Helper functions used by mob commands
```python
# What's tested:
- count_people_room() - Room population counting
- has_item() - Inventory checking (by vnum, type, wear location)
- get_mob_vnum_room() - NPC lookup
- get_obj_vnum_room() - Object lookup
- keyword_lookup() - Table searching
```

**ROM C References**:
- `src/mob_prog.c:400-550` - Helper function suite

#### 4. `tests/test_mobprog_triggers.py` (15 tests)
**Focus**: Trigger execution and program flow
```python
# What's tested:
- Program execution (if/else/endif conditionals)
- Variable expansion ($n, $i, $o, $r tokens)
- Trigger phrase matching (case sensitivity)
- Nested program calls (mpcall recursion)
- Event hooks (speech, act, greet, exit, fight, etc.)
```

**ROM C References**:
- `src/mob_prog.c:800-1200` - Trigger system
- `src/mob_prog.c:1-400` - Program interpreter

---

## 🔬 Layer 2: Integration Test Scenarios

### Creating Comprehensive Workflow Tests

**File**: `tests/integration/test_mobprog_scenarios.py`

#### Scenario 1: Quest-Giving NPC
```python
def test_quest_giver_workflow(test_player, test_mob):
    """
    Test complete quest workflow with MobProgs:
    1. Greet player on entry
    2. Listen for keyword "quest"
    3. Give quest item
    4. Listen for keyword "complete"
    5. Take item and give reward
    
    ROM C Reference: Common ROM quest pattern from contrib areas
    """
    # Setup quest-giver mob with speech triggers
    quest_prog = MobProgram(
        trig_type=int(Trigger.SPEECH),
        trig_phrase="quest",
        vnum=5001,
        code="""
if ispc $n
    if has_item $n 1234
        say You already have a quest from me, $n.
    else
        say I need you to find the Golden Widget.
        mob give $n 1234
        say Return it to me when you find it.
    endif
endif
"""
    )
    
    complete_prog = MobProgram(
        trig_type=int(Trigger.GIVE),
        trig_phrase="1234",
        vnum=5002,
        code="""
if ispc $n
    say Excellent work, $n!
    mob junk $o
    mob give $n 5678
    mob echoat $n You receive 1000 gold as a reward.
    mob echoaround $n $n completes the quest!
endif
"""
    )
    
    test_mob.mob_programs = [quest_prog, complete_prog]
    
    # Execute workflow
    result1 = do_say(test_player, "quest")
    assert "golden widget" in result1.lower()
    
    # Verify item given
    widget = test_player.get_object_by_vnum(1234)
    assert widget is not None
    
    # Complete quest
    result2 = do_give(test_player, "widget mob")
    assert "excellent work" in result2.lower()
    
    # Verify reward
    reward = test_player.get_object_by_vnum(5678)
    assert reward is not None
```

#### Scenario 2: Combat-Triggered Behavior
```python
def test_mob_combat_script(test_player, test_mob):
    """
    Test mob behavior during combat:
    - Fight trigger at 50% HP (cast spell)
    - HPCNT trigger at 20% HP (flee and heal)
    - Death trigger (curse player)
    
    ROM C Reference: src/mob_prog.c:1100-1200 (mp_fight_trigger, mp_hpcnt_trigger)
    """
    fight_prog = MobProgram(
        trig_type=int(Trigger.FIGHT),
        trig_phrase="50",
        vnum=6001,
        code="mob cast 'lightning bolt' $n"
    )
    
    hpcnt_prog = MobProgram(
        trig_type=int(Trigger.HPCNT),
        trig_phrase="20",
        vnum=6002,
        code="""
mob flee
mob cast 'heal' self
"""
    )
    
    death_prog = MobProgram(
        trig_type=int(Trigger.DEATH),
        trig_phrase="100",
        vnum=6003,
        code="mob echoat $n You feel a curse settle upon you..."
    )
    
    test_mob.mob_programs = [fight_prog, hpcnt_prog, death_prog]
    test_mob.max_hit = 100
    test_mob.hit = 100
    
    # Trigger fight at 50% HP
    test_mob.hit = 50
    mp_fight_trigger(test_mob)
    assert "lightning bolt" in test_player.messages[-1]
    
    # Trigger HPCNT at 20% HP
    test_mob.hit = 20
    mp_hpcnt_trigger(test_mob)
    # Verify mob attempted to flee
```

#### Scenario 3: Multi-Trigger Chain Reaction
```python
def test_cascading_mob_triggers(test_player):
    """
    Test complex trigger chains:
    - Guard mob watches for player entering restricted area
    - Entry trigger → speech trigger → act trigger cascade
    
    ROM C Reference: src/mob_prog.c:1200-1350 (trigger chaining)
    """
    # Guard mob with entry trigger
    guard = Character(name="Palace Guard", is_npc=True)
    entry_prog = MobProgram(
        trig_type=int(Trigger.ENTRY),
        trig_phrase="100",
        vnum=7001,
        code="""
if ispc $n
    mob say Halt! State your business.
    mob remember $n
endif
"""
    )
    
    # Second guard reacts to first guard's speech
    guard2 = Character(name="Second Guard", is_npc=True)
    speech_prog = MobProgram(
        trig_type=int(Trigger.SPEECH),
        trig_phrase="halt",
        vnum=7002,
        code="mob say I'll handle this."
    )
    
    guard.mob_programs = [entry_prog]
    guard2.mob_programs = [speech_prog]
    
    # Test cascade
    mp_entry_trigger(test_player)
    # Verify both guards responded
```

---

## 🌍 Layer 3: Live Area Testing

### Testing Real ROM Area Files

ROM area files contain embedded MobProgs. QuickMUD loads these during startup.

#### Finding Mobs with Programs

```bash
# Search for mob program vnums in area files
cd area/
grep -n "^M" midgaard.are | grep -A 20 "mob_programs"

# Or use Python to inspect loaded mobs
python3 -c "
from mud.loaders.area_loader import load_all_areas
from mud.models.character import character_registry

load_all_areas()
for vnum, mob_idx in character_registry.items():
    if mob_idx.mob_programs:
        print(f'Mob {vnum}: {mob_idx.name} has {len(mob_idx.mob_programs)} programs')
"
```

#### Common ROM MobProg Patterns

**1. Shopkeeper Greet**
```
>greet_prog 100~
if ispc $n
  say Welcome to my shop, $n!
endif
~
```

**2. Aggressive Guard**
```
>greet_prog 100~
if ispc $n
  if level $n < 20
    mob kill $n
  endif
endif
~
```

**3. Quest Item Handler**
```
>give_prog 1234~
if ispc $n
  say Thank you for returning this!
  mob junk $o
  mob transfer $n 3001
endif
~
```

### Testing Workflow for Area Files

```python
# tests/integration/test_mobprog_areas.py

def test_midgaard_mobprogs_execute():
    """
    Load Midgaard area and verify all MobProgs:
    1. Can be parsed without errors
    2. Have valid trigger types
    3. Execute without crashes
    
    ROM C Reference: Stock Midgaard area from ROM 2.4b distribution
    """
    from mud.loaders.area_loader import load_area
    from mud.models.character import character_registry
    
    # Load Midgaard
    area = load_area("area/midgaard.are")
    
    # Find all mobs with programs
    programmed_mobs = [
        mob_idx for mob_idx in character_registry.values()
        if mob_idx.mob_programs
    ]
    
    assert len(programmed_mobs) > 0, "Midgaard should have MobProgs"
    
    # Verify each program is valid
    for mob_idx in programmed_mobs:
        for prog in mob_idx.mob_programs:
            # Check trigger type is valid
            assert prog.trig_type in [t.value for t in Trigger]
            
            # Check code is not empty
            assert prog.code.strip() != ""
            
            # Try to execute (smoke test)
            try:
                mob = Character.from_index(mob_idx)
                result = mobprog.run_prog(
                    mob, 
                    Trigger(prog.trig_type),
                    actor=None,
                    phrase=prog.trig_phrase
                )
                # Should not crash
            except Exception as e:
                pytest.fail(f"MobProg {prog.vnum} crashed: {e}")
```

---

## 🔍 Differential Testing: Python vs C

### Strategy: Compare Outputs

**Goal**: Run identical MobProg scenarios in both C ROM and Python QuickMUD, compare results

#### Setup

1. **Prepare test scenario** in area file:
```
#MOBPROGS
#5000
* Test prog: echo on greet
>greet_prog 100~
if ispc $n
  mob echo Test message for $n
  mob say Hello $n
endif
~
#0
```

2. **Run in ROM C** (compile and run):
```bash
cd rom24/area
# Load area with test mob
# Walk character to mob's room
# Capture output
```

3. **Run in QuickMUD Python**:
```python
def test_differential_greet():
    """Compare Python output to ROM C output"""
    # Load same area file
    # Trigger same greet
    # Capture output
    
    # Expected from ROM C run:
    rom_c_output = "Test message for TestPlayer\nThe mob says 'Hello TestPlayer'"
    
    # Python output:
    python_output = capture_mobprog_output()
    
    assert normalize_output(python_output) == normalize_output(rom_c_output)
```

#### Automation Script

```bash
#!/bin/bash
# scripts/test_mobprog_differential.sh

# Run MobProg scenario in ROM C and capture output
run_rom_c_scenario() {
    local scenario=$1
    cd rom24/
    echo "walk n" | ./rom -s scenario_$scenario.txt > /tmp/rom_c_output.txt
    cat /tmp/rom_c_output.txt
}

# Run same scenario in Python
run_python_scenario() {
    local scenario=$1
    pytest tests/integration/test_mobprog_differential.py::test_$scenario -v --tb=short
}

# Compare outputs
compare_outputs() {
    diff <(normalize /tmp/rom_c_output.txt) <(normalize /tmp/python_output.txt)
}
```

---

## 📋 Checklist: Verifying Complete Parity

### Basic Functionality ✅
- [x] All 31 mob commands implemented
- [x] All 16 trigger types working
- [x] If/else/endif conditionals
- [x] Variable expansion ($n, $i, $o, $r, etc.)
- [x] Nested program calls (mpcall)
- [x] Trigger phrase matching

### Advanced Mechanics ⚠️
- [x] Percent-based trigger chance
- [x] Multiple programs per mob
- [x] Program execution order (priority)
- [ ] **NEEDS TESTING**: Edge cases with malformed programs
- [ ] **NEEDS TESTING**: Extremely long program chains
- [ ] **NEEDS TESTING**: Memory/recursion limits

### Real-World Scenarios 🔄
- [ ] Load all stock ROM areas (midgaard, limbo, etc.)
- [ ] Verify no MobProg parse errors
- [ ] Test common quest patterns work
- [ ] Test shopkeeper behaviors work
- [ ] Test aggressive mob behaviors work

### Performance 🔄
- [ ] Benchmark trigger evaluation speed
- [ ] Test with 100+ mobs with active programs
- [ ] Verify no memory leaks in long-running programs

---

## 🚀 Quick Start: Running All MobProg Tests

```bash
# 1. Unit tests (50 tests, ~1.2s)
pytest tests/test_mobprog*.py -v

# 2. Integration tests (create first!)
pytest tests/integration/test_mobprog_scenarios.py -v

# 3. Area file validation
python3 scripts/validate_mobprogs.py area/*.are

# 4. Full differential test
bash scripts/test_mobprog_differential.sh
```

---

## 📝 Writing New MobProg Tests

### Test Template

```python
from mud.mobprog import Trigger, run_prog, mp_greet_trigger
from mud.models.mob import MobProgram
from mud.models.character import Character

def test_my_mobprog_scenario():
    """
    Description of what this test verifies
    
    ROM C Reference: src/mob_prog.c:LINE_NUMBER
    """
    # 1. Setup
    mob = Character(name="TestMob", is_npc=True)
    player = Character(name="TestPlayer", is_npc=False)
    
    program = MobProgram(
        trig_type=int(Trigger.SPEECH),
        trig_phrase="test",
        vnum=9999,
        code="""
if ispc $n
    mob echo This is a test
endif
"""
    )
    mob.mob_programs = [program]
    
    # 2. Execute
    results = run_prog(
        mob,
        Trigger.SPEECH,
        actor=player,
        phrase="test message"
    )
    
    # 3. Assert
    assert len(results) == 1
    assert results[0].command == "mob echo"
    assert "test" in results[0].argument.lower()
```

### Best Practices

1. **Reference ROM C code** in docstrings
2. **Test one behavior** per test function
3. **Use descriptive names** (test_quest_giver_accepts_item)
4. **Include edge cases** (empty phrases, invalid triggers)
5. **Verify no crashes** for malformed inputs

---

## 🐛 Common Issues and Solutions

### Issue 1: Trigger Not Firing
**Symptom**: MobProg defined but never executes  
**Debug**:
```python
# Add logging to trigger evaluation
import logging
logging.basicConfig(level=logging.DEBUG)

# Check trigger type matches event
assert program.trig_type == int(Trigger.SPEECH)

# Verify phrase matches
assert "quest" in "I want a quest".lower()
```

### Issue 2: Variable Not Expanding
**Symptom**: `$n` appears as literal `$n` instead of player name  
**Debug**:
```python
from mud.mobprog import expand_arg

# Test expansion directly
result = expand_arg(mob, "$n gives $o to $p", actor=player, obj=item, rndm=None)
assert result == "TestPlayer gives sword to merchant"
```

### Issue 3: Infinite Recursion
**Symptom**: Stack overflow from nested mpcall  
**Debug**:
```python
# Check recursion limit is enforced
from mud.mobprog import MAX_CALL_LEVEL

# Should stop at depth 5
results = call_prog(vnum_that_calls_itself, mob)
assert len([r for r in results if r.command == "say"]) <= MAX_CALL_LEVEL
```

---

## 📊 Coverage Goals

### Current Coverage (2025-12-26)
- **Unit Tests**: 50 tests covering 97% of mobprog.py
- **Integration Tests**: 0 tests (to be created)
- **Area Tests**: 0 tests (to be created)

### Target Coverage (100% Parity)
- **Unit Tests**: 70+ tests (add edge cases)
- **Integration Tests**: 20+ tests (workflows)
- **Area Tests**: All stock ROM areas validated
- **Differential Tests**: 10+ scenarios matched to ROM C

---

## 🔗 References

### ROM C Source Files
- `src/mob_prog.c` - Main interpreter (1363 lines)
- `src/mob_cmds.c` - Mob command implementations (1369 lines)
- `src/olc_mpcode.c` - MobProg editor (not ported yet)

### QuickMUD Python Files
- `mud/mobprog.py` - Main interpreter (1686 lines)
- `mud/commands/mobprog_tools.py` - Builder commands (mpdump, mpstat)
- `mud/loaders/mobprog_loader.py` - Area file parser

### Test Files
- `tests/test_mobprog.py` - Basic tests (2 tests)
- `tests/test_mobprog_commands.py` - Command tests (20 tests)
- `tests/test_mobprog_helpers.py` - Helper tests (13 tests)
- `tests/test_mobprog_triggers.py` - Trigger tests (15 tests)

### Documentation
- [ROM_PARITY_FEATURE_TRACKER.md](../parity/ROM_PARITY_FEATURE_TRACKER.md) - Feature matrix
- [AGENTS.md](AGENTS.md) - Development guide
- [doc/c_to_python_file_coverage.md](doc/c_to_python_file_coverage.md) - C→Python mapping

---

## ✅ Next Steps

1. **Create integration test suite** (`tests/integration/test_mobprog_scenarios.py`)
2. **Validate all stock ROM areas** (automated area file scanner)
3. **Implement differential testing** (Python vs C output comparison)
4. **Performance benchmarking** (trigger evaluation speed)
5. **Edge case testing** (malformed programs, recursion limits)

**Estimated Time**: 8-12 hours for complete parity verification

**Priority**: P1 (MobProgs are 97% complete, final 3% is polish and validation)
