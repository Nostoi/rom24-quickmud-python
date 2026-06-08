# do_equipment ROM C Parity Audit

**Command**: `equipment` (alias: `eq`)  
**ROM C Source**: `src/act_info.c` lines 2263-2295  
**QuickMUD Source**: `mud/commands/inventory.py` lines 292-332  
**Date**: January 7, 2026  
**Status**: 🔄 **AUDITING IN PROGRESS**

---

## ROM C Reference Implementation

```c
void do_equipment (CHAR_DATA * ch, char *argument)
{
    OBJ_DATA *obj;
    int iWear;
    bool found;

    send_to_char ("You are using:\n\r", ch);
    found = FALSE;
    for (iWear = 0; iWear < MAX_WEAR; iWear++)
    {
        if ((obj = get_eq_char (ch, iWear)) == NULL)
            continue;

        send_to_char (where_name[iWear], ch);
        if (can_see_obj (ch, obj))
        {
            send_to_char (format_obj_to_char (obj, ch, TRUE), ch);
            send_to_char ("\n\r", ch);
        }
        else
        {
            send_to_char ("something.\n\r", ch);
        }
        found = TRUE;
    }

    if (!found)
        send_to_char ("Nothing.\n\r", ch);

    return;
}
```

**ROM Reference**: `src/act_info.c` lines 2263-2295

### ROM C Constants

**where_name array** (`src/act_info.c` lines 48-67):
```c
char *const where_name[] = {
    "<used as light>     ",
    "<worn on finger>    ",
    "<worn on finger>    ",
    "<worn around neck>  ",
    "<worn around neck>  ",
    "<worn on torso>     ",
    "<worn on head>      ",
    "<worn on legs>      ",
    "<worn on feet>      ",
    "<worn on hands>     ",
    "<worn on arms>      ",
    "<worn as shield>    ",
    "<worn about body>   ",
    "<worn about waist>  ",
    "<worn around wrist> ",
    "<worn around wrist> ",
    "<wielded>           ",
    "<held>              ",
    "<floating nearby>   ",
};
```

**MAX_WEAR** (`src/merc.h` line 1356): `#define MAX_WEAR 19`

### ROM C Behavioral Features

1. **Header Message** (line 2268): `"You are using:\n\r"` on separate line
2. **Iterates All Slots** (lines 2270-2289): Loops through 0 to MAX_WEAR (19 slots)
3. **Slot Name Display** (line 2276): Shows where_name[iWear] before object
4. **Visibility Check** (line 2277): Uses `can_see_obj(ch, obj)` for filtering
5. **Invisible Object** (line 2283): Shows `"something.\n\r"` for invisible equipment
6. **Empty Message** (line 2291): Shows `"Nothing.\n\r"` when no equipment worn
7. **Format Function** (line 2279): Uses `format_obj_to_char(obj, ch, TRUE)` for object display

---

## QuickMUD Implementation

```python
def do_equipment(char: Character, args: str = "") -> str:
    """
    Show equipment worn by character.

    ROM Reference: src/act_info.c:do_equipment (lines 451-489)
    """
    from mud.models.constants import WearLocation

    # ROM slot names mapping (src/act_info.c:451-489)
    slot_names = {
        int(WearLocation.LIGHT): "<used as light>",
        int(WearLocation.FINGER_L): "<worn on finger>",
        int(WearLocation.FINGER_R): "<worn on finger>",
        int(WearLocation.NECK_1): "<worn around neck>",
        int(WearLocation.NECK_2): "<worn around neck>",
        int(WearLocation.BODY): "<worn on torso>",
        int(WearLocation.HEAD): "<worn on head>",
        int(WearLocation.LEGS): "<worn on legs>",
        int(WearLocation.FEET): "<worn on feet>",
        int(WearLocation.HANDS): "<worn on hands>",
        int(WearLocation.ARMS): "<worn on arms>",
        int(WearLocation.SHIELD): "<worn as shield>",
        int(WearLocation.ABOUT): "<worn about body>",
        int(WearLocation.WAIST): "<worn about waist>",
        int(WearLocation.WRIST_L): "<worn around wrist>",
        int(WearLocation.WRIST_R): "<worn around wrist>",
        int(WearLocation.WIELD): "<wielded>",
        int(WearLocation.HOLD): "<held>",
        int(WearLocation.FLOAT): "<floating nearby>",
    }

    if not char.equipment:
        return "You are wearing nothing."

    parts = []
    for slot, obj in char.equipment.items():
        slot_name = slot_names.get(slot, f"<slot {slot}>")
        obj_name = obj.short_descr or obj.name or "object"
        parts.append(f"{slot_name:20} {obj_name}")

    return "You are using:\n" + "\n".join(parts)
```

**QuickMUD Source**: `mud/commands/inventory.py` lines 292-332

---

## Gap Analysis

### Gap 1: Missing Slot Name Padding (MINOR)

**ROM C Behavior**:
```
<used as light>      a bright lantern
<worn on finger>     a gold ring
```

**QuickMUD Behavior**:
```
<used as light>      a bright lantern
<worn on finger>     a gold ring
```

**Status**: ✅ **NO GAP** - QuickMUD uses `:20` format (20-char padding) which matches ROM C

---

### Gap 2: Missing Visibility Filtering (CRITICAL)

**ROM C Behavior** (lines 2277-2284):
```c
if (can_see_obj (ch, obj))
{
    send_to_char (format_obj_to_char (obj, ch, TRUE), ch);
    send_to_char ("\n\r", ch);
}
else
{
    send_to_char ("something.\n\r", ch);
}
```

**QuickMUD Behavior**:
```python
obj_name = obj.short_descr or obj.name or "object"
parts.append(f"{slot_name:20} {obj_name}")
```

**Impact**: 
- Invisible equipment always shows object name
- Should show "something." for invisible objects
- No `can_see_obj()` check

**Priority**: **P0 - CRITICAL**

---

### Gap 3: Wrong Empty Message (MINOR)

**ROM C Behavior**:
```
You are using:
Nothing.
```

**QuickMUD Behavior**:
```
You are wearing nothing.
```

**Impact**: 
- Message doesn't match ROM C format
- Missing header line ("You are using:")
- Says "wearing" instead of "Nothing."

**Priority**: **P1 - IMPORTANT**

---

### Gap 4: Missing Slot Order Iteration (MINOR)

**ROM C Behavior** (lines 2270-2272):
```c
for (iWear = 0; iWear < MAX_WEAR; iWear++)
{
    if ((obj = get_eq_char (ch, iWear)) == NULL)
        continue;
```

**QuickMUD Behavior**:
```python
for slot, obj in char.equipment.items():
```

**Impact**: 
- QuickMUD iterates dict keys (insertion order in Python 3.7+)
- ROM C iterates 0-18 sequentially
- May show equipment in different order

**Priority**: **P2 - NICE TO HAVE** (Python 3.7+ dicts are ordered, likely matches ROM)

---

## Priority Classification

### P0 - CRITICAL (Must Fix for ROM Parity):
1. ❌ **Gap 2**: Visibility filtering (`can_see_obj` check and "something." for invisible)

### P1 - IMPORTANT (Should Fix):
2. ❌ **Gap 3**: Empty message format ("Nothing.\n" vs "You are wearing nothing.")

### P2 - OPTIONAL (Nice to Have):
3. ⚠️ **Gap 4**: Slot order iteration (likely OK in practice)

---

## Recommended Fixes

### Fix 1: Add Visibility Filtering

```python
from mud.world.vision import can_see_object

for slot, obj in char.equipment.items():
    slot_name = slot_names.get(slot, f"<slot {slot}>")
    
    if can_see_object(char, obj):
        obj_name = obj.short_descr or obj.name or "object"
    else:
        obj_name = "something."
    
    parts.append(f"{slot_name:20} {obj_name}")
```

### Fix 2: Update Empty Message

```python
if not char.equipment:
    return "You are using:\nNothing.\n"
```

### Fix 3: Iterate Slots in ROM Order (Optional)

```python
from mud.models.constants import WearLocation

for i_wear in range(19):  # 0 to MAX_WEAR-1 (19 slots)
    obj = char.equipment.get(i_wear)
    if obj is None:
        continue
    
    slot_name = slot_names.get(i_wear, f"<slot {i_wear}>")
    # ... rest of logic
```

---

## Expected Output Examples

### Example 1: Normal Equipment (Visible)

**Input**: Player wearing ring, sword, shield

**Expected Output**:
```
You are using:
<worn on finger>     a gold ring
<wielded>            a steel sword
<worn as shield>     a wooden shield
```

### Example 2: Equipment with Invisible Item

**Input**: Player wearing invisible cloak

**Expected Output**:
```
You are using:
<worn about body>    something.
```

### Example 3: No Equipment

**Expected Output**:
```
You are using:
Nothing.
```

---

## Integration Test Requirements

### P0 Tests (Critical):
1. ⏳ Header on separate line ("You are using:\n")
2. ⏳ Visible equipment shows object name
3. ⏳ Invisible equipment shows "something."
4. ⏳ Multiple equipment items display correctly
5. ⏳ Empty equipment shows "Nothing."

### P1 Tests (Important):
6. ⏳ All 19 slot names display correctly
7. ⏳ Equipment in correct slot order
8. ⏳ Long object names don't break formatting

### P2 Tests (Optional):
9. ⏳ Mixed visible/invisible equipment
10. ⏳ All slots filled (19 items)

---

## Success Criteria

- [ ] All P0 gaps fixed (visibility filtering)
- [ ] All P1 gaps fixed (empty message)
- [ ] Integration tests created (8+ tests)
- [ ] All integration tests passing
- [ ] No regressions in existing tests

---

## Notes

- ROM C `format_obj_to_char()` likely adds additional formatting (investigate if needed)
- QuickMUD slot names match ROM C where_name array ✅
- ROM C uses 20-character padding for slot names (matches QuickMUD `:20` format) ✅

---

## Next Steps

1. ⏳ Add `can_see_object()` check for visibility filtering
2. ⏳ Add "something." for invisible equipment
3. ⏳ Update empty message format
4. ⏳ Create comprehensive integration tests
5. ⏳ Verify all tests pass
6. ⏳ Update ACT_INFO_C_AUDIT.md with completion status
