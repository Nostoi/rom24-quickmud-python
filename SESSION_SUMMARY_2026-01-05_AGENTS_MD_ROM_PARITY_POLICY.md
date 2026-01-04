# Session Summary: AGENTS.md ROM Parity Policy Update

**Date**: January 5, 2026  
**Session Duration**: ~30 minutes  
**Focus**: Update AGENTS.md to enforce strict ROM parity policy

---

## 🎉 Major Achievement

**✅ AGENTS.md Updated with Mandatory ROM Parity Policy!**

- Added strict "NO DEFERRING IMPLEMENTATION" policy at top of file
- Identified current ROM parity violations (effects.c, save.c)
- Updated ROM C Audit Workflow to require integration tests
- Created todo list for critical parity work (8 tasks)

---

## What We Accomplished

### 1. Added Mandatory ROM Parity Policy Section

**File Modified**: `AGENTS.md`  
**Section Added**: Lines 1-60 (new "MANDATORY ROM PARITY POLICY" section)

#### Policy Highlights

**🚨 Core Principles**:
1. **NO DEFERRING IMPLEMENTATION** - When ROM C functions discovered missing, implement immediately
2. **INTEGRATION TESTS ARE MANDATORY** - Every new function requires integration tests
3. **AUDIT COMPLETION CRITERIA** - 100% implementation + tests required before moving on
4. **PRIORITY OVERRIDE** - ROM parity gaps are ALWAYS P0 (CRITICAL)

**Current Violations Identified**:
- ❌ **effects.c**: 5/5 functions are stubs (marked P2 - WRONG!)
- ❌ **save.c**: 2/8 functions missing (marked P2 - WRONG!)

---

### 2. Updated START HERE Section

**Changes Made**: Lines 27-153 (complete rewrite)

**Before**: "Current Priority: Integration Test Coverage (1-2 days)"  
**After**: "🚨 CRITICAL ROM PARITY GAPS IDENTIFIED - MUST FIX FIRST"

#### New Priority Structure

**Priority 1: effects.c Full Implementation** (P0 - CRITICAL, 5-8 days)
- Status: 5/5 functions are stubs only (NO ROM C behavior!)
- Impact: Environmental damage system completely non-functional
- Required: Implement full ROM C behavior + integration tests
- File: `tests/integration/test_environmental_effects.py`

**Priority 2: save.c Pet Persistence** (P0 - CRITICAL, 1-2 days)
- Status: 2/8 functions missing (fwrite_pet, fread_pet)
- Impact: Charmed mobs lost on logout
- Required: Implement pet save/load + integration tests
- File: `tests/integration/test_pet_persistence.py`

**Priority 3: Next ROM C Audit** (AFTER fixing above gaps)
- Only proceed after effects.c and save.c are 100% complete
- Recommended: act_info.c, act_comm.c, or act_move.c

---

### 3. Updated Current Work Focus Section

**Changes Made**: Lines 181-213

**Status Changes**:
```markdown
# Before:
- ✅ save.c - 75% complete (6/8 functions, pet save P2)
- ✅ effects.c - 100% mapped (5/5 stubs, implementation P2)

# After:
- ⚠️ save.c - 75% complete (6/8 functions, 2 functions MISSING - P0!)
- ⚠️ effects.c - 0% implemented (5/5 stubs only - P0!)
```

**Next Priority Work**:
1. effects.c full implementation (P0 - CRITICAL, 5-8 days)
2. save.c pet persistence (P0 - CRITICAL, 1-2 days)
3. Next ROM C audit (AFTER fixing above)

---

### 4. Updated ROM C Audit Workflow

**Changes Made**: Lines 277-310 (Phase 3-5 rewritten)

#### Key Changes

**Phase 3: Implementation** (Day 4-5)
- ❌ OLD: "Use stubs with TODO for complex integrations"
- ✅ NEW: "NEVER use stubs or TODO comments - implement full ROM C behavior"
- ✅ NEW: "🚨 CRITICAL: Create integration tests for ALL new functions"

**Phase 4: Integration Tests** (Day 6-7) - **NEW MANDATORY PHASE**
- Added explicit integration test phase (previously missing)
- Requirements:
  - ✅ Test complete workflows (not just function calls)
  - ✅ Verify ROM C formulas and probability calculations
  - ✅ Test edge cases and error conditions
  - ✅ Verify messages/output match ROM behavior
  - ✅ Use `game_tick()` integration where applicable

**Phase 5: Completion** (Day 8)
- Added "Verify integration tests passing (100%)" to success criteria

---

### 5. Created Todo List for Critical Work

**Todo Items**: 8 total (4 high, 3 medium, 1 low)

**High Priority** (Implementation + Tests):
1. ⏳ Implement effects.c full ROM C behavior (5 functions)
2. ⏳ Create integration tests for effects.c
3. ⏳ Implement save.c pet persistence (fwrite_pet, fread_pet)
4. ⏳ Create integration tests for pet persistence

**Medium Priority** (Documentation):
5. ⏳ Update EFFECTS_C_AUDIT.md to 100% complete
6. ⏳ Update SAVE_C_AUDIT.md to 100% complete
7. ⏳ Update ROM_C_SUBSYSTEM_AUDIT_TRACKER.md

**Low Priority**:
8. ⏳ Create session summary for completion

---

## Rationale: Why This Policy Is Critical

### Problem Statement

**Previous Approach** (WRONG):
- Audits marked functions as "P2 - Optional" if they seemed non-critical
- Implementation was deferred to "later" (which never comes)
- Integration tests were treated as optional follow-up work
- ROM parity violations accumulated silently

**Examples of Violations**:
1. **effects.c**: All 5 functions exist as stubs, marked "P2 deferred"
   - Impact: Environmental damage system doesn't work
   - Reality: Core ROM feature, NOT optional!

2. **save.c**: Pet persistence missing, marked "P2 deferred"
   - Impact: Charmed mobs lost on logout
   - Reality: Core ROM gameplay feature, NOT optional!

### New Approach (CORRECT)

**Strict Policy**:
1. ✅ Audit discovers gap → Implement immediately (no deferring)
2. ✅ Implementation → Integration tests created (not deferred)
3. ✅ Tests passing → Mark audit complete
4. ✅ Audit complete → Move to next file

**Benefits**:
- No silent ROM parity violations
- Integration tests catch behavioral differences early
- Clear completion criteria (can't mark 75% as "done")
- Prevents technical debt accumulation

---

## Impact on Project

### Current Status

**Before This Update**:
- save.c marked "75% complete" (but 2 functions missing)
- effects.c marked "100% audit complete" (but 0% implemented)
- Next work: "Create integration tests" (optional)

**After This Update**:
- save.c marked "75% - P0 CRITICAL GAP" (2 functions MUST be implemented)
- effects.c marked "0% implemented - P0 CRITICAL GAP" (stubs not acceptable)
- Next work: "Fix ROM parity violations" (mandatory)

### Work Scope

**Estimated Effort**:
1. effects.c implementation: 3-4 days (5 functions)
2. effects.c integration tests: 2-3 days (comprehensive scenarios)
3. save.c pet persistence: 1 day (2 functions)
4. save.c pet tests: 1 day (save/load workflows)

**Total**: 7-9 days to fix ROM parity violations

**Alternative (OLD APPROACH)**: Mark as "P2" and never implement = silent parity violations forever

---

## Files Modified

### 1. AGENTS.md (lines 1-310 modified)

**Sections Added**:
- "🚨 MANDATORY ROM PARITY POLICY" (lines 1-60)
- Updated "🚀 START HERE" section (lines 27-153)

**Sections Modified**:
- "Current Work Focus" (lines 181-213)
- "ROM C Audit Workflow" (lines 251-310)

**Sections Unchanged**:
- Previous Completions
- Command Parity Status
- Autonomous Mode
- Task Tracking
- Code Style Guidelines

### 2. Todo List Created

**File**: In-memory todo list (via todowrite tool)  
**Items**: 8 tasks (4 high, 3 medium, 1 low)

---

## Commands Run This Session

```bash
# No bash commands run (documentation update only)
```

---

## Next Steps

### Immediate Actions

**User Decision Required**:
- Start effects.c full implementation? (P0 - CRITICAL, 5-8 days)
- Start save.c pet persistence? (P0 - CRITICAL, 1-2 days)
- Both in parallel? (7-9 days total)

**Recommended Order**:
1. save.c pet persistence (1-2 days) - Smaller scope, easier to complete
2. effects.c full implementation (5-8 days) - Larger scope, more complex

### Long-Term Impact

**ROM C Audit Process**:
- All future audits will follow strict policy
- No more "P2 deferring" of missing functions
- Integration tests mandatory for all implementations
- Clear completion criteria (100% or bust)

**Quality Assurance**:
- ROM parity violations caught immediately
- Behavioral differences verified with integration tests
- Technical debt prevented from accumulating

---

## Success Metrics

✅ **Policy Established**:
1. ✅ "NO DEFERRING IMPLEMENTATION" policy documented
2. ✅ Integration test requirements made explicit
3. ✅ Current violations identified (effects.c, save.c)
4. ✅ Priority override for ROM parity gaps (P0 CRITICAL)

✅ **Documentation Updated**:
1. ✅ AGENTS.md reflects strict ROM parity policy
2. ✅ START HERE section prioritizes parity violations
3. ✅ ROM C Audit Workflow includes mandatory integration tests
4. ✅ Todo list created for critical work

⏳ **Implementation Pending**:
1. ⏳ effects.c full implementation (5-8 days)
2. ⏳ save.c pet persistence (1-2 days)
3. ⏳ Integration tests for both (3-4 days)

---

## Context for Next Session

### What Just Changed

**AGENTS.md Policy**:
- ROM parity gaps are now P0 CRITICAL (not P2 optional)
- Integration tests are mandatory (not deferred)
- 100% completion required before moving to next file

**Current Violations**:
- effects.c: 5/5 stubs → Must implement full ROM C behavior
- save.c: 6/8 functions → Must implement remaining 2 functions

### Recommended Starting Point

**Option 1: save.c Pet Persistence** (1-2 days, easier)
- Implement `fwrite_pet()` and `fread_pet()`
- Create integration tests for pet save/load
- Update SAVE_C_AUDIT.md to 100% (8/8 functions)

**Option 2: effects.c Full Implementation** (5-8 days, harder)
- Implement 5 environmental effect functions
- Create integration tests for object destruction
- Update EFFECTS_C_AUDIT.md to 100% (5/5 implemented)

**Option 3: Both in Parallel** (delegate to specialized agents)
- Frontend-UI-UX for effects.c (visual/gameplay)
- General agent for save.c (data persistence)

---

## Critical Files for Reference

### Documentation (Updated This Session)
- ✅ `AGENTS.md` - Development guide (UPDATED - lines 1-310)

### Audit Documents (Need Updates)
- `docs/parity/EFFECTS_C_AUDIT.md` - effects.c audit (needs 100% update)
- `docs/parity/SAVE_C_AUDIT.md` - save.c audit (needs 8/8 functions update)
- `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` - Overall tracker (needs status updates)

### ROM C Source Files
- `src/effects.c` - ROM C source (615 lines, 5 functions)
- `src/save.c` - ROM C source (2,020 lines, 8 functions)

### QuickMUD Implementation
- `mud/magic/effects.py` - Current stubs (needs full implementation)
- `mud/persistence.py` - Current save/load (needs pet functions)

---

## Session Summary

**What We Did**: Updated AGENTS.md to enforce strict ROM parity policy

**Why It Matters**: Prevents silent ROM parity violations from accumulating

**What's Next**: Implement effects.c and save.c to fix current violations

**Estimated Effort**: 7-9 days to complete both (or 1-2 days for save.c only)

**Priority**: P0 CRITICAL - Must fix before continuing ROM C audits

---

**Session Status**: ✅ **100% COMPLETE**  
**Next Major Work**: Choose effects.c or save.c implementation  
**Policy Impact**: All future audits must achieve 100% parity + integration tests

**Ready to start ROM parity fixes!** 🚀
