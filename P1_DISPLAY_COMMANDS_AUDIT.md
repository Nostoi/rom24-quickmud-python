# P1 Display Commands Quick Audit Summary

**Date**: January 7, 2026  
**Commands**: do_affects, do_inventory, do_equipment  
**Status**: ⚠️ **SIMPLIFIED IMPLEMENTATIONS** - Functional but not ROM C parity

---

## Summary

These three commands are **implemented and functional** but use **simplified QuickMUD patterns** rather than exact ROM C parity. They work for gameplay but don't match ROM C line-by-line.

### do_affects (lines 1714-1769)

**ROM C Implementation**:
- Uses `ch->affected` linked list of AFFECT_DATA structs
- Shows spell name from `skill_table[paf->type].name`
- For level >= 20: shows modifier details (`modifies STR by +3`)
- For level >= 20: shows duration (`for 5 hours` or `permanently`)
- Groups consecutive identical spell types

**QuickMUD Implementation** (`mud/commands/affects.py`):
- Uses `spell_effects` dict (not linked list)
- Shows spell names and durations
- **MISSING**: Level-based detail filtering (level >= 20 check)
- **MISSING**: Modifier details (location + value)
- **MISSING**: Grouping of consecutive identical spells
- **EXTRA**: Shows hunger/thirst (not in ROM C)
- **EXTRA**: Shows affected_by bitvector flags

**ROM C Parity**: ❌ **~40%** - Basic functionality works, but missing key features

**Gaps**:
1. No level-based filtering (level >= 20 for details)
2. No modifier display (`modifies CON by -2`)
3. No affect_loc_name() mapping
4. Different data structure (dict vs linked list)
5. No consecutive spell grouping

**Recommendation**: **Low priority** - Command works for gameplay. Full parity requires rewriting affect system.

---

### do_inventory (lines 2254-2261)

**ROM C Implementation**:
```c
send_to_char ("You are carrying:\n\r", ch);
show_list_to_char (ch->carrying, ch, TRUE, TRUE);
```

**QuickMUD Implementation** (`mud/commands/inventory.py` lines 176-179):
```python
if not char.inventory:
    return "You are carrying nothing."
return "You are carrying: " + ", ".join(obj.short_descr or obj.name or "object" for obj in char.inventory)
```

**ROM C Parity**: ❌ **20%** - Completely different output format

**Gaps**:
1. No `show_list_to_char()` call - uses simple join()
2. Output format: `"sword, shield, potion"` vs ROM's detailed list with line breaks
3. Missing visual detail formatting
4. Missing object condition/flags display

**ROM C Output Example**:
```
You are carrying:
  a steel sword
  a wooden shield
  a red potion
```

**QuickMUD Output Example**:
```
You are carrying: a steel sword, a wooden shield, a red potion
```

**Recommendation**: **Medium priority** - Output is usable but not ROM-like. Would need `show_list_to_char()` helper implementation.

---

### do_equipment (lines 2263-2295)

**ROM C Implementation**:
- Loops through `MAX_WEAR` slots
- Calls `get_eq_char(ch, iWear)` for each slot
- Uses `where_name[iWear]` for slot labels
- Calls `format_obj_to_char(obj, ch, TRUE)` for object display
- Shows "something." if `can_see_obj()` fails
- Shows "Nothing." if no equipment

**QuickMUD Implementation** (`mud/commands/inventory.py` lines 182-222):
- Loops through `char.equipment` dict
- Uses hardcoded `slot_names` dict
- Simple `obj.short_descr` or `obj.name`
- **MISSING**: `can_see_obj()` visibility check
- **MISSING**: `format_obj_to_char()` detailed formatting

**ROM C Parity**: ❌ **60%** - Correct structure, missing helper functions

**Gaps**:
1. No `can_see_obj()` check (invisibility/blindness)
2. No `format_obj_to_char()` call (loses condition/enchantment display)
3. Simplified object name display

**Recommendation**: **Medium priority** - Structure is correct, just needs helper function calls.

---

## Overall Assessment

| Command | ROM C Parity | Priority | Effort | Functional? |
|---------|--------------|----------|--------|-------------|
| do_affects | ~40% | Low | High | ✅ Yes |
| do_inventory | ~20% | Medium | Medium | ✅ Yes |
| do_equipment | ~60% | Medium | Low | ✅ Yes |

**All three commands are functional** - players can use them without errors. However, they don't match ROM C output format or feature completeness.

**Recommended Action**: 
1. **Skip detailed parity work** on these for now (low ROI)
2. **Mark as "functional but simplified"** in audit
3. **Move to higher-value P1 commands** (do_time, do_weather, do_where, do_consider)
4. **Return to these later** if time permits (P2 priority)

**Why Skip?**
- All three require helper functions (`show_list_to_char`, `format_obj_to_char`, `affect_loc_name`)
- Helper functions are complex (30-100 lines each in ROM C)
- Low player impact (commands work, just different formatting)
- Better to spend time on commands with actual bugs/gaps

---

## Next Steps

Move to **P1 Batch 3**: do_time, do_weather, do_where, do_consider

These are likely to be simpler standalone commands without complex helper dependencies.
