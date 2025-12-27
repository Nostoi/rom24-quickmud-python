# MobProg Parity Completion Plan

**Goal**: Achieve 100% ROM C parity for MobProg system  
**Current Status**: 97% complete (50/50 unit tests passing, 3/7 integration tests passing)  
**Estimated Total Time**: 4-6 hours

---

## P0: Critical Integration Fixes (2-3 hours)

### Task 1: Hook mp_give_trigger in do_give command ⏱️ 30 min
**File**: `mud/commands/give.py`  
**Issue**: GIVE trigger not firing when players give items to mobs  
**Fix**: Add `mp_give_trigger(target, char, obj)` call after successful give  
**Test**: `test_quest_completion_workflow` should pass  
**ROM Ref**: `src/act_obj.c:1523-1567` (do_give calls mp_give_trigger)

### Task 2: Hook mp_hprct_trigger in combat system ⏱️ 45 min
**File**: `mud/combat/engine.py`  
**Issue**: HPRCT (HP percent) trigger not firing during combat  
**Fix**: Call `mp_hprct_trigger(mob, attacker)` after damage calculation  
**Test**: `test_mob_casts_spell_at_low_health` should pass  
**ROM Ref**: `src/fight.c:1094-1136` (damage calls mp_hprct_trigger)

### Task 3: Hook mp_death_trigger on character death ⏱️ 30 min
**File**: `mud/combat/engine.py` or `mud/combat/death.py`  
**Issue**: DEATH trigger not firing when mobs die  
**Fix**: Call `mp_death_trigger(killer, mob)` before mob cleanup  
**Test**: `test_mob_death_curse` should pass  
**ROM Ref**: `src/fight.c:1136-1180` (raw_kill calls mp_death_trigger)

### Task 4: Enable speech trigger cascading ⏱️ 45 min
**File**: `mud/commands/communication.py`  
**Issue**: Mobs don't hear other mobs speak (no SPEECH trigger cascade)  
**Fix**: Call `mp_speech_trigger(text, mob, speaker)` for all mobs in room  
**Test**: `test_guard_chain_reaction` should pass  
**ROM Ref**: `src/act_comm.c:567-623` (do_say triggers speech progs)

**P0 Success Criteria**:
- ✅ All 7 integration tests passing
- ✅ No regressions in 50 unit tests
- ✅ Manual testing confirms triggers fire in gameplay

---

## P1: Validation and Verification (1-2 hours)

### Task 5: Run area file validation ⏱️ 30 min
**Action**: Execute validation script on all stock ROM areas  
**Command**: `python3 scripts/validate_mobprogs.py area/*.are --verbose --test-execute`  
**Output**: Save to `mobprog_validation_report.txt`  
**Success**: No errors, all programs parse and execute without crashes

### Task 6: Test with real area files ⏱️ 45 min
**Action**: Load stock areas and manually test MobProgs  
**Areas to test**:
- Midgaard (if has progs)
- Limbo
- School
**Test scenarios**:
- Quest-giving NPCs
- Aggressive mobs with GREET triggers
- Shop keepers with SPEECH triggers

### Task 7: Update documentation ⏱️ 15 min
**Files to update**:
- `../parity/ROM_PARITY_FEATURE_TRACKER.md` - Update MobProg section to 100%
- `PROJECT_COMPLETION_STATUS.md` - Update mob_programs confidence to 1.00
- `MOBPROG_TESTING_SUMMARY.md` - Mark all tests passing

**P1 Success Criteria**:
- ✅ All stock ROM areas validate cleanly
- ✅ Manual testing confirms real-world MobProgs work
- ✅ Documentation reflects 100% parity

---

## P2: Advanced Testing (1-2 hours) - OPTIONAL

### Task 8: Performance benchmarking ⏱️ 45 min
**Action**: Test MobProg performance with many active programs  
**Scenarios**:
- 100+ mobs with active programs in same area
- Complex nested conditionals (deep if/else chains)
- Rapid trigger firing (combat spam)
**Metrics**: Trigger evaluation time, memory usage

### Task 9: Edge case testing ⏱️ 30 min
**Scenarios**:
- Malformed program code (syntax errors)
- Invalid trigger types
- Circular mpcall references
- Empty/null arguments to mob commands
**Expected**: Graceful error handling, no crashes

### Task 10: Differential testing setup ⏱️ 45 min
**Action**: Create framework for comparing Python vs ROM C output  
**Files**: `scripts/test_mobprog_differential.sh`  
**Note**: Requires ROM C environment (may skip if not available)

**P2 Success Criteria**:
- ✅ Performance acceptable for production
- ✅ Edge cases handled gracefully
- ✅ Differential testing framework ready (optional)

---

## Execution Order

### Phase 1: Integration Fixes (P0)
1. Fix do_give trigger hook
2. Fix combat HP trigger hook  
3. Fix death trigger hook
4. Fix speech cascade
5. Run all tests: `pytest tests/test_mobprog*.py tests/integration/test_mobprog_scenarios.py -v`
6. Verify 57/57 tests passing

### Phase 2: Validation (P1)
7. Run area validation script
8. Manual testing with real areas
9. Update documentation

### Phase 3: Advanced Testing (P2) - Optional
10. Performance benchmarks
11. Edge case testing
12. Differential testing setup

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Integration changes break existing gameplay | High | Run full test suite after each change |
| Trigger hookups cause performance issues | Medium | Benchmark before/after, optimize if needed |
| Area files have unknown MobProg patterns | Low | Validation script catches parse errors |
| No ROM C environment for differential testing | Low | P2 optional, can skip |

---

## Rollback Plan

If integration changes cause issues:
1. Revert specific commit
2. Re-run test suite to confirm stable state
3. Debug issue in isolation
4. Re-apply fix with additional tests

---

## Success Definition

**100% ROM C MobProg Parity Achieved When**:
- ✅ All 50 unit tests passing (already done)
- ✅ All 7 integration tests passing (4 fixes needed)
- ✅ All stock ROM areas validate without errors
- ✅ Manual gameplay testing confirms triggers fire correctly
- ✅ Documentation updated to reflect 100% status

**Deliverables**:
- Fixed trigger hookups in game commands
- Validation report for all area files
- Updated parity tracking documents
- Integration tests demonstrating complete workflows

---

## Time Tracking

| Phase | Estimated | Actual | Status |
|-------|-----------|--------|--------|
| P0: Integration Fixes | 2-3 hours | - | Pending |
| P1: Validation | 1-2 hours | - | Pending |
| P2: Advanced Testing | 1-2 hours | - | Optional |
| **Total** | **4-7 hours** | - | - |

---

**Start Time**: 2025-12-26  
**Target Completion**: Same day (autonomous execution)
