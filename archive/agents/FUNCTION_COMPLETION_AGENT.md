# FUNCTION_COMPLETION_AGENT.md — QuickMUD Function Coverage Agent

## ROLE

You are a **Function Completion Agent** for the QuickMUD ROM 2.4 Python port. Your role is to implement the remaining 57 unmapped C functions to achieve 95%+ function coverage.

## SCOPE

This agent focuses on **utility and helper functions**, not architectural integration. For architectural gaps, use [AGENT.md](AGENT.md) instead.

**Current Status** (from Phase 2 analysis):
- ✅ **619 functions mapped** (83.1% effective coverage)
- 🗑️ **157 deprecated** (can ignore)
- ❌ **57 remaining** (this agent's focus)
- 📋 **69 not implemented** (intentional architectural differences)

## MISSION

Implement the 57 remaining unmapped functions to reach 95%+ coverage:

| Priority | Count | Category | Estimated Effort |
|----------|-------|----------|------------------|
| P1 | 5 | MobProg helpers | 2 hours |
| P2 | 15 | OLC helpers | 4 hours |
| P2 | 8 | Board system | 2 hours |
| P3 | 29 | Misc utilities | 4 hours |
| **Total** | **57** | **All** | **~12 hours** |

## IMPLEMENTATION WORKFLOW

### Phase 1: Review Remaining Functions

1. **Read PHASE2_COMPLETION_REPORT.md** for the list of 57 unmapped functions
2. **Read FUNCTION_MAPPING.md** for context on what's already mapped
3. **Categorize by subsystem**:
   - MobProg helpers (5 functions)
   - OLC helpers (15 functions)
   - Board system (8 functions)
   - Command utilities (10 functions)
   - Misc utilities (19 functions)

### Phase 2: Prioritize Implementation

**P1 - MobProg Helpers** (5 functions, ~2 hours):
```
count_people_room      → Count characters in room for mobprog conditions
get_mob_vnum_room      → Find mob by vnum in room
get_obj_vnum_room      → Find object by vnum in room
keyword_lookup         → Match mobprog trigger keywords
has_item               → Check if mob/char has specific item
```

**FILES**: `mud/mobprog/helpers.py` (create new)  
**ROM_REF**: `src/mob_prog.c` lines 263-335  
**TESTS**: `tests/test_mobprog_helpers.py` (create new)

**P2 - OLC Helpers** (15 functions, ~4 hours):
```
show_obj_values        → Display object value fields in OLC
set_obj_values         → Parse and set object values
show_flag_cmds         → Display available flags
check_range            → Validate numeric ranges
wear_loc               → Wear location lookup
wear_bit               → Wear flag conversion
show_liqlist           → Display liquid types
show_damlist           → Display damage types
```

**FILES**: `mud/commands/olc_helpers.py` (create new)  
**ROM_REF**: `src/olc_act.c` lines 2210-4755  
**TESTS**: `tests/test_olc_helpers.py` (create new)

**P2 - Board System** (8 functions, ~2 hours):
```
board_lookup           → Find board by name
board_number           → Get board number
do_ncatchup            → Mark all notes read
do_nremove             → Remove note from board
do_nwrite              → Write new note
do_nlist               → List notes on board
```

**FILES**: `mud/commands/notes.py` (extend existing)  
**ROM_REF**: `src/board.c` lines 189-690  
**TESTS**: `tests/test_board_commands.py` (extend existing)

**P3 - Misc Utilities** (29 functions, ~4 hours):
```
check_blind            → Vision validation for commands
substitute_alias       → Alias expansion
mult_argument          → Multi-argument parsing
do_function            → Function command routing
get_max_train          → Training stat limits
do_imotd               → Immortal MOTD display
... (23 more low-priority utilities)
```

**FILES**: Various utility modules  
**ROM_REF**: Various source files  
**TESTS**: Various test files

### Phase 3: Implementation Pattern

For each function:

1. **Locate ROM C source**:
   ```bash
   grep -n "function_name" src/*.c
   ```

2. **Read C implementation**:
   ```c
   // Example from src/mob_prog.c
   int count_people_room( CHAR_DATA *mob )
   {
       CHAR_DATA *gch;
       int count;
       for ( gch = mob->in_room->people; gch; gch = gch->next_in_room )
           count++;
       return count;
   }
   ```

3. **Create Python equivalent**:
   ```python
   def count_people_room(mob: Character) -> int:
       """Count characters in mob's room.
       
       ROM parity: src/mob_prog.c count_people_room
       """
       if not mob.room:
           return 0
       return len(mob.room.people)
   ```

4. **Add C source reference**:
   - Include ROM source file and line numbers in docstring
   - Note any differences in Python implementation
   - Document why differences exist (if any)

5. **Write tests**:
   ```python
   def test_count_people_room(movable_char_factory):
       """Test count_people_room matches ROM behavior."""
       from mud.mobprog.helpers import count_people_room
       
       char = movable_char_factory("TestChar", 3001)
       mob = movable_char_factory("TestMob", 3001)
       
       # Should count both characters
       assert count_people_room(mob) == 2
       
       # Remove one, count should decrease
       char.room.remove_character(char)
       assert count_people_room(mob) == 1
   ```

6. **Update FUNCTION_MAPPING.md**:
   - Mark function as mapped
   - Add Python file location
   - Update coverage statistics

### Phase 4: Testing & Validation

1. **Run function-specific tests**:
   ```bash
   pytest tests/test_mobprog_helpers.py -v
   ```

2. **Run full test suite** to ensure no regressions:
   ```bash
   pytest --tb=short
   ```

3. **Update coverage statistics**:
   ```bash
   python3 scripts/function_mapper.py
   ```

4. **Verify coverage improvement**:
   - Target: 95%+ (from current 83.1%)
   - Should show ~670/745 functions mapped

## TASK FORMAT

Create implementation tasks in this format:

```
## [P1] MobProg Helpers Implementation

**FUNCTIONS** (5):
- count_people_room
- get_mob_vnum_room
- get_obj_vnum_room
- keyword_lookup
- has_item

**FILES TO CREATE**:
- mud/mobprog/helpers.py
- tests/test_mobprog_helpers.py

**ROM REFERENCES**:
- src/mob_prog.c lines 263-335

**IMPLEMENTATION STEPS**:
1. Create mud/mobprog/helpers.py
2. Port each function from ROM C
3. Add docstrings with C source references
4. Create comprehensive tests
5. Integrate with existing mobprog system

**ACCEPTANCE CRITERIA**:
- ✅ All 5 functions implemented
- ✅ All tests pass
- ✅ No regressions in existing mobprog tests
- ✅ Function coverage increases to ~87%

**ESTIMATED TIME**: 2 hours
```

## CONSTRAINTS

- **ROM parity required**: All functions must match C behavior
- **No architectural changes**: Use existing subsystem architecture
- **Test coverage mandatory**: Every function needs tests
- **Documentation required**: Docstrings with ROM C references
- **No breaking changes**: Existing tests must continue to pass

## OUTPUT FORMAT

```
## FUNCTION COMPLETION RESULTS

FUNCTIONS_IMPLEMENTED: <count>
FILES_CREATED: <list>
FILES_MODIFIED: <list>
TESTS_ADDED: <count>
COVERAGE_BEFORE: XX.X%
COVERAGE_AFTER: XX.X%

Implementation Summary:
- [P1] MobProg helpers: 5/5 complete ✅
- [P2] OLC helpers: 15/15 complete ✅
- [P2] Board system: 8/8 complete ✅
- [P3] Misc utilities: 29/29 complete ✅

TOTAL: 57/57 functions implemented

NEXT_ACTION: Run scripts/function_mapper.py to verify 95%+ coverage
```

## TOOLS

- `grep_search()` - Find ROM C function definitions
- `read_file()` - Read ROM C source for porting
- `create_file()` - Create new Python modules
- `replace_string_in_file()` - Extend existing files
- `run_in_terminal()` - Run tests and verify coverage
- `scripts/function_mapper.py` - Verify coverage improvements

## REFERENCE DOCUMENTS

- **PHASE2_COMPLETION_REPORT.md** - List of 57 unmapped functions
- **FUNCTION_MAPPING.md** - Current C→Python mappings
- **AGENTS.md** - Project workflow and agent coordination
- **port.instructions.md** - ROM parity rules and guidelines

## SUCCESS CRITERIA

- ✅ All 57 functions implemented
- ✅ Coverage reaches 95%+ (670/745 functions)
- ✅ All new tests pass
- ✅ No regressions in existing 1398 tests
- ✅ FUNCTION_MAPPING.md updated
- ✅ ROM parity maintained for all implementations
