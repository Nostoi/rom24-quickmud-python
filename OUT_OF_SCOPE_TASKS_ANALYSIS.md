# Out-of-Scope Tasks Analysis - Ralph Loop Session

**Date**: January 1, 2026  
**Session**: Integration Test Enhancement - Equipment System & Mob AI

## Executive Summary

Of 9 original tasks, **3 were completed** and **6 were cancelled**. However, the cancelled tasks fall into two categories:

### Category 1: NOT ROM 2.4b6 Features (1 task)
These should NEVER be implemented for ROM 2.4b6 parity:

### Category 2: ROM 2.4b6 Features Requiring Major Integration Work (5 tasks)
These ARE in ROM 2.4b6 but require P2/P3 level system integration:

---

## Detailed Analysis

### ❌ Task #2: Dual Wield System - NOT IN ROM 2.4b6

**Status**: Cancelled (Invalid for ROM 2.4b6 parity)

**Original Test**: `test_dual_wield_requires_secondary_slot`  
**Original Claim**: "ROM Parity: Mirrors ROM src/act_obj.c:do_wear() dual wield logic"

**Investigation**:
```bash
grep -rn "dual\|SECONDARY\|gsn_dual" src/
# Result: No matches - dual wield does not exist in ROM 2.4b6
```

**Finding**: Dual wield was added in **later MUD derivatives** (ROM 2.5+, SMAUG, etc.), NOT in original ROM 2.4b6.

**Action Taken**:
- Updated test docstring to state "NOT ROM 2.4b6 PARITY"
- Changed skip message: "NOT A ROM 2.4b6 FEATURE - Dual wield was added in later MUD derivatives"
- Documented grep verification results

**Recommendation**: Remove this test entirely or move to "future enhancements" section.

---

### ✅ Task #4: Invisibility Affects - ROM 2.4b6 Feature (COMPLETE ✅)

**Status**: ✅ **COMPLETED** (January 1, 2026) - Feature was already implemented, integration test added

**Original Assessment**: Marked as P2 (requires can_see() refactor)

**ROM Evidence**:
```c
// src/handler.c:2618
if (IS_AFFECTED (victim, AFF_INVISIBLE)
    && !IS_AFFECTED (ch, AFF_DETECT_INVIS))
    return FALSE;
```

**Discovery**: The can_see() refactor **was already completed** months ago!

**Existing Implementation**: `mud/world/vision.py:169-218` - `can_see_character()` function
```python
def can_see_character(ch: Character, victim: Character) -> bool:
    """Mirrors ROM src/handler.c:2618 can_see() logic."""
    # ... (holylight, blind checks) ...
    
    # Lines 205-206: AFF_INVISIBLE check
    if victim.has_affect(AffectFlag.INVISIBLE) and not ch.has_affect(AffectFlag.DETECT_INVIS):
        return False
```

**Commands Already Using It**:
- ✅ `look` command (`mud/world/look.py:97`) - Filters invisible characters from room listings
- ✅ `scan` command (`mud/commands/inspection.py:61`) - Respects invisibility

**What Was Missing**: Integration test to verify end-to-end behavior

**Completion Work** (January 1, 2026):
- ✅ Added `test_invisible_affect_hides_character` to `tests/integration/test_spell_affects_persistence.py`
- ✅ Test verifies: Character with AFF_INVISIBLE not visible, observer with AFF_DETECT_INVIS can see
- ✅ Test passes - invisibility system works correctly
- ✅ Documentation updated in `INTEGRATION_TEST_COVERAGE_TRACKER.md`

**Actual Scope**: 30 minutes (write test) vs. estimated 4-6 hours (feature was already done)

**Skip Message Update**: Changed from "Requires can_see() refactor" to "COMPLETE ✅"

**Lesson Learned**: Always verify implementation status before estimating work!

---

### ✅ Task #5: Curse Prevents Item Removal - ROM 2.4b6 Feature (P2)

**Status**: Correctly marked as P2 (requires item removal integration)

**ROM Evidence**:
```c
// src/act_obj.c:1382
if (IS_SET (obj->extra_flags, ITEM_NOREMOVE))
{
    send_to_char ("You can't remove it.\n\r", ch);
    return;
}
```

**Why P2**: QuickMUD has `ExtraFlag.NOREMOVE` check in `do_remove()` (tests pass), but needs:
- Integration with `AFF_CURSE` spell affect
- Cursed items should set `ITEM_NOREMOVE` flag when equipped
- `remove curse` spell should clear the flag

**Scope**: ~2-3 hours to integrate curse spell with item flags.

**Skip Message Status**: ✅ Accurate - "Requires curse mechanic in item removal commands"

---

### ✅ Task #6: Poison Damage Over Time - ROM 2.4b6 Feature (P3)

**Status**: Correctly marked as P3 (requires DOT system)

**ROM Evidence**:
```c
// src/update.c:220, 302, 353
if (IS_AFFECTED (ch, AFF_POISON))
{
    // poison damage logic
    af.type = gsn_poison;
    poison_update(ch);
}

// src/update.c:848
else if (IS_AFFECTED (ch, AFF_POISON) && ch != NULL
         && !IS_AFFECTED (ch, AFF_SLOW))
{
    dam = number_range (1, 10);
    // apply damage
}
```

**Why P3**: Requires implementing damage-over-time (DOT) system in `game_tick()`:
- Periodic poison damage checks
- Poison strength degradation
- Death from poison
- Poison cure mechanics

**Scope**: ~6-8 hours for complete DOT system with all edge cases.

**Skip Message Status**: ✅ Accurate - "Requires damage-over-time (DOT) system in game_tick"

---

### ✅ Task #7: Plague Spreading Mechanics - ROM 2.4b6 Feature (P3)

**Status**: Correctly marked as P3 (requires contagion system)

**ROM Evidence**:
```c
// src/update.c:814-834
if (IS_AFFECTED (ch, AFF_PLAGUE))
{
    // plague damage and spreading
    for (vch = ch->in_room->people; vch != NULL; vch = vch->next_in_room)
    {
        if (!saves_spell (level, vch, DAM_DISEASE)
            && !IS_IMMORTAL (vch)
            && !IS_AFFECTED (vch, AFF_PLAGUE)
            && number_bits (4) == 0)
        {
            // spread plague to nearby character
            affect_join (vch, &plague);
        }
    }
}
```

**Why P3**: Requires implementing contagion spreading system:
- Periodic plague spread checks (probability-based)
- Room-based character iteration
- Save vs disease checks
- Plague damage application
- Plague cure mechanics

**Scope**: ~8-10 hours for complete contagion system with ROM parity.

**Skip Message Status**: ✅ Accurate - "Requires contagion spreading system in game_tick"

---

## Summary Table

| Task | ROM 2.4b6? | Status | Reason | Priority |
|------|------------|--------|--------|----------|
| Dual Wield | ❌ NO | Cancelled | Not in ROM 2.4b6 (added in derivatives) | N/A |
| Invisibility | ✅ YES | P2 Deferred | Requires can_see() refactor (4-6h) | Medium |
| Curse Removal | ✅ YES | P2 Deferred | Requires curse spell integration (2-3h) | Medium |
| Poison DOT | ✅ YES | P3 Deferred | Requires DOT system (6-8h) | Low |
| Plague Spread | ✅ YES | P3 Deferred | Requires contagion system (8-10h) | Low |

**Total ROM Parity Work Remaining**: ~20-27 hours (P2: 6-9h, P3: 14-18h)

---

## Recommendations

### Immediate Actions
1. ✅ **DONE**: Update `test_dual_wield_requires_secondary_slot` to state "NOT ROM 2.4b6 PARITY"
2. **Consider**: Remove dual wield test entirely or move to "future enhancements" suite

### P2 Work (Next Session)
1. **Invisibility** (4-6h): Refactor `can_see()` to check `AFF_INVISIBLE` and `AFF_DETECT_INVIS`
   - Priority: MEDIUM (affects core gameplay visibility)
   - Files: `mud/handler.py`, `mud/commands/information.py`, `mud/combat/`

2. **Curse Integration** (2-3h): Link `AFF_CURSE` affect to `ITEM_NOREMOVE` flag
   - Priority: MEDIUM (spell already exists, just needs item integration)
   - Files: `mud/spells/`, `mud/commands/equipment.py`

### P3 Work (Future)
3. **Poison DOT** (6-8h): Implement damage-over-time system
   - Priority: LOW (spell exists, just missing periodic damage)
   - Files: `mud/game_loop.py`, `mud/spells/`

4. **Plague Spreading** (8-10h): Implement contagion system
   - Priority: LOW (complex system, low gameplay impact)
   - Files: `mud/game_loop.py`, `mud/spells/`

---

## Conclusion

The Ralph Loop correctly identified that 6 tasks were out-of-scope for immediate work:

- **1 task (dual wield)**: Should NEVER be implemented for ROM 2.4b6 parity
- **5 tasks (invisibility/curse/poison/plague)**: ARE ROM 2.4b6 features but require P2/P3 integration work

All skip messages are accurate and helpful. The integration test suite correctly documents these as deferred work.

**Next Recommended Work**: P2 features (invisibility + curse) for ~6-9 hours of ROM parity improvement.
