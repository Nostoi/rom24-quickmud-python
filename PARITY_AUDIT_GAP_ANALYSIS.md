# Parity Audit Gap Analysis - Command Coverage Blind Spot

**Date**: 2025-12-20
**Severity**: HIGH
**Impact**: 61% of player-visible commands missing from implementation

---

## 🔴 Root Cause Analysis

### The Problem

**Discovered**: Player reported "huh?" errors for most commands in the help output  
**Investigation**: Manual audit revealed **only 32 out of 82 help commands implemented (39%)**  
**Expanded Scope**: ROM 2.4b has **251 total commands** in `src/interp.c`

### Why Did Our Parity Audit Miss This?

Our parity audit system had a **critical blind spot**: It tracked subsystem *implementation quality* but NOT *command coverage*.

#### What the Parity Audit DID Track:
1. **Subsystem confidence scores** - Test pass rates for implemented features
2. **Test coverage** - Number of tests per subsystem
3. **ROM C module ports** - Which C files have Python equivalents
4. **Feature completeness** - Advanced mechanics within implemented systems

#### What the Parity Audit DIDN'T Track:
1. ❌ **Command table coverage** - Which ROM commands are actually registered
2. ❌ **Help output accuracy** - Whether help lists match reality
3. ❌ **Player-visible feature gaps** - What players see vs. what exists
4. ❌ **Cross-reference validation** - ROM `cmd_table[]` vs Python `COMMANDS[]`

---

## 📊 Audit System Architecture Flaw

### Current Audit Flow (INCOMPLETE)

```
scripts/test_data_gatherer.py
  │
  ├─→ Maps subsystems to test files
  ├─→ Runs pytest on each subsystem
  ├─→ Calculates confidence from pass/fail rates
  └─→ Outputs subsystem scores
```

**What's Missing**:
- No validation that `mud/commands/dispatcher.py` registers all ROM commands
- No check that help output reflects actual implementation
- No comparison between ROM `src/interp.c:cmd_table[]` and Python `COMMANDS[]`

### ROM_PARITY_FEATURE_TRACKER.md (MISLEADING)

The tracker claimed:
- ✅ "95-98% ROM Parity ACHIEVED"
- ✅ "Basic ROM Parity: 100% ACHIEVED (fully playable MUD)"
- ✅ "Critical Gameplay Features: ALL COMPLETE"

**Reality**:
- ❌ 61% of help commands return "Huh?"
- ❌ 219 out of 251 ROM commands NOT implemented (13% coverage)
- ❌ Core commands like `save`, `quit`, `recall`, `wear`, `wield` missing

**The Disconnect**:
- The tracker focused on **advanced mechanics** (dodge/parry details, damage types)
- It ignored **basic command availability** (can players actually equip items?)

---

## 🎯 Command Coverage Reality Check

### ROM 2.4b Command Table (src/interp.c)

**Total ROM Commands**: 251

**QuickMUD Implementation**: ~32 commands (13%)

**Missing Categories**:
1. **P0 Critical** (11 commands) - Game-breaking gaps
   - `save`, `quit`, `recall`, `wear`, `wield`, `hold`, `eat`, `drink`, `score`, `flee`, `cast`

2. **P1 Major** (17 commands) - Severely limits gameplay
   - `who`, `password`, `title`, `description`, `areas`, `where`, `time`, `put`, `give`, `open`, `close`, `lock`, `unlock`, `follow`, `group`, `gtell`, `wimpy`

3. **P2 Enhanced** (19 commands) - Quality of life
   - Potions/scrolls/wands, emotes, reporting, lockpicking, etc.

4. **P3+ Advanced** (182 commands) - ROM full feature set
   - Auto-settings, advanced admin, class skills, etc.

---

## 🔍 Why This Wasn't Caught Earlier

### 1. Overconfidence in Test Coverage

**We had 200+ passing tests**, which created false confidence:
- Tests covered **implemented features thoroughly**
- Tests did NOT verify **missing features**
- Passing tests ≠ Complete feature coverage

### 2. Subsystem-Centric View

The audit focused on subsystem *depth*, not *breadth*:
- "Combat system works" ✅
- But `flee` command doesn't exist ❌
- "Movement system works" ✅
- But `recall` command doesn't exist ❌

### 3. No Player Perspective Validation

The audit was code-centric, not player-centric:
- Tested: "Does `do_north()` work correctly?"
- Didn't test: "Can a player actually type 'north'?"
- Tested: "Do shop prices calculate correctly?"
- Didn't test: "Can a player wear the item they bought?"

### 4. Help Output Was Never Validated

`data/help.json` listed 82 commands, but:
- No test verified those commands actually work
- No cross-reference against `dispatcher.py:COMMANDS[]`
- Help output was treated as documentation, not a contract

---

## 🛠️ How to Fix the Audit System

### 1. Add Command Coverage Tracking

Create `tests/test_command_parity.py`:

```python
def test_rom_command_coverage():
    """Verify all ROM commands from src/interp.c are implemented."""
    rom_commands = load_rom_command_table()  # Parse src/interp.c
    python_commands = COMMANDS  # From dispatcher.py
    
    missing = rom_commands - python_commands
    assert len(missing) == 0, f"Missing ROM commands: {missing}"
```

### 2. Add Help Output Validation

Create `tests/test_help_accuracy.py`:

```python
def test_help_commands_actually_work():
    """Every command in help output must be implemented."""
    help_data = load_help_json()
    help_commands = extract_commands_from_help(help_data)
    
    for cmd in help_commands:
        assert resolve_command(cmd) is not None, \
            f"Help lists '{cmd}' but command not registered"
```

### 3. Update test_data_gatherer.py

Add command coverage subsystem:

```python
SUBSYSTEM_TEST_MAP = {
    # ... existing entries ...
    "command_coverage": [
        "tests/test_command_parity.py",
        "tests/test_help_accuracy.py",
    ],
}
```

### 4. Update ROM_PARITY_FEATURE_TRACKER.md

Add honest command coverage metrics:

```markdown
## Command Implementation Status

| Category | ROM Total | Implemented | Coverage |
|----------|-----------|-------------|----------|
| Movement | 12 | 11 | 92% |
| Objects | 28 | 10 | 36% |
| Combat | 15 | 3 | 20% |
| **TOTAL** | **251** | **32** | **13%** |
```

### 5. Add to CI/CD Pipeline

Make command parity a **blocking check**:

```yaml
# .github/workflows/test.yml
- name: Check Command Parity
  run: pytest tests/test_command_parity.py --tb=short
```

---

## 📋 Immediate Action Items

### Phase 1: Fix the Audit (This Session)

1. ✅ **Create this gap analysis document**
2. ⏳ **Create `tests/test_command_parity.py`** - Automated ROM command tracking
3. ⏳ **Update `scripts/test_data_gatherer.py`** - Add command_coverage subsystem
4. ⏳ **Run new audit** - Get honest baseline

### Phase 2: Implement Critical Commands (Next Session)

5. ⏳ **Implement P0 commands** (11 critical commands)
6. ⏳ **Implement P1 commands** (17 major commands)
7. ⏳ **Update help output** to match reality

### Phase 3: Prevent Regression (Ongoing)

8. ⏳ **Add CI checks** for command parity
9. ⏳ **Update parity tracker** with command metrics
10. ⏳ **Document lesson learned** in AGENTS.md

---

## 🎓 Lessons Learned

### For AI Agents

1. **Test what players see, not just what code does**
   - Don't just test `do_wear()` - test that `"wear sword"` works

2. **Cross-reference data sources**
   - Help output vs. dispatcher registration vs. ROM C cmd_table

3. **Challenge optimistic assessments**
   - "95% parity" requires evidence from **player perspective**

4. **Automated coverage is not optional**
   - Command parity should be a CI gate, not a manual check

### For the Project

1. **Command registration is the source of truth**
   - `dispatcher.py:COMMANDS[]` defines what players can do
   - Everything else is implementation details

2. **Help output is a contract**
   - If help lists a command, it MUST work
   - If a command works, it SHOULD be in help

3. **Subsystem tests ≠ Feature completeness**
   - Passing combat tests don't mean combat commands exist
   - Need player-journey tests, not just unit tests

---

## 🔬 Technical Deep Dive

### ROM Command Table Structure

```c
// src/interp.c
const struct cmd_type cmd_table[] = {
    {"north", do_north, POS_STANDING, 0, LOG_NEVER, 0},
    {"wear", do_wear, POS_RESTING, 0, LOG_NORMAL, 0},
    // ... 249 more commands ...
};
```

**251 total entries** (as of ROM 2.4b6)

### QuickMUD Command Registration

```python
# mud/commands/dispatcher.py
COMMANDS: list[Command] = [
    Command("north", do_north, min_position=Position.STANDING),
    # ... only ~32 commands ...
]
```

**Gap**: 219 commands missing from registration

---

## 📈 Expected Outcome After Fix

### New Parity Metrics (Honest)

```
Command Coverage:     13% (32/251)  ← Current
Subsystem Quality:    ~85% (tests passing on implemented features)
Overall ROM Parity:   ~40% (blend of coverage + quality)
```

### After P0 Implementation

```
Command Coverage:     17% (43/251)  ← +11 P0 commands
Player Experience:    Playable       ← Can save/quit/equip/fight
Overall ROM Parity:   ~50%
```

### After P1 Implementation

```
Command Coverage:     24% (60/251)  ← +17 P1 commands
Player Experience:    Feature-rich   ← Groups, equipment, info
Overall ROM Parity:   ~60%
```

---

## 🎯 Success Criteria

The parity audit system will be considered **fixed** when:

1. ✅ `pytest tests/test_command_parity.py` exists and runs in CI
2. ✅ `scripts/test_data_gatherer.py` reports command coverage
3. ✅ `ROM_PARITY_FEATURE_TRACKER.md` shows honest command metrics
4. ✅ Help output validation test exists
5. ✅ New command implementations automatically update coverage

---

## 📚 References

- **ROM Source**: `src/interp.c` lines 1-2000 (cmd_table definition)
- **Python Dispatcher**: `mud/commands/dispatcher.py` lines 106-286
- **Help Data**: `data/help.json` (249 entries)
- **Audit Script**: `scripts/test_data_gatherer.py`
- **Feature Tracker**: `ROM_PARITY_FEATURE_TRACKER.md`

---

**Bottom Line**: Our parity audit was **feature-quality focused** but **feature-coverage blind**. We thoroughly tested what we implemented, but never verified we implemented what ROM has. This is now being fixed with automated command coverage tracking.
