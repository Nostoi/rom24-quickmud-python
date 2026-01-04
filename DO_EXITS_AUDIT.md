# do_exits ROM C Parity Audit

**Date**: January 6, 2026  
**Auditor**: AI Agent (Sisyphus)  
**ROM C Source**: `src/act_info.c` lines 1393-1451 (59 lines)  
**QuickMUD Implementation**: `mud/commands/inspection.py` lines 133-141 (9 lines)

---

## Executive Summary

**Status**: ⚠️ **CRITICAL GAPS FOUND** - QuickMUD implementation missing 90% of ROM C features

**Parity Score**: **10%** (1/10 ROM C features implemented)

**Priority**: **P1 (Important)** - Essential for player navigation experience

**Recommendation**: **IMMEDIATE IMPLEMENTATION REQUIRED**

QuickMUD's do_exits is a minimal stub that only lists exit directions. ROM C do_exits provides:
- Auto-exit mode (compact format)
- Door status checking (closed doors hidden)
- Room visibility checks (darkness, permissions)
- Immortal extras (room vnums, sector types)
- Detailed room names per exit
- Proper message formatting

---

## ROM C Feature Analysis (10 features)

### Feature 1: Blindness Check ❌ MISSING

**ROM C** (line 1401):
```c
if (!check_blind (ch))
    return;
```

**QuickMUD**: NO IMPLEMENTATION

**Gap**: Blind characters should see "You can't see a thing!" (from check_blind)

**Impact**: CRITICAL - Blind players can see exits (breaks ROM parity)

**Fix Required**: Add `check_blind()` call at start

---

### Feature 2: Auto-Exit Mode ❌ MISSING

**ROM C** (lines 1403-1405, 1425-1431, 1445-1446):
```c
fAuto = !str_cmp (argument, "auto");

if (fAuto)
{
    strcat (buf, " ");
    strcat (buf, dir_name[door]);
}

if (fAuto)
    strcat (buf, "]{x\n\r");
```

**QuickMUD**: NO IMPLEMENTATION

**Gap**: `exits auto` should show compact format: `[Exits: north south east]`

**Impact**: CRITICAL - Players cannot use auto-exit mode (common ROM feature)

**Fix Required**: Detect `args == "auto"` and format as `{o[Exits: <dirs>]{x\n\r`

---

### Feature 3: Immortal Room Vnum Display ❌ MISSING

**ROM C** (lines 1407-1408, 1422-1423):
```c
if (IS_IMMORTAL (ch))
    sprintf (buf, "Obvious exits from room %d:\n\r", ch->in_room->vnum);
else
    sprintf (buf, "Obvious exits:\n\r");

// Later:
if (IS_IMMORTAL (ch))
    sprintf (buf + strlen (buf), " (room %d)\n\r", pexit->u1.to_room->vnum);
```

**QuickMUD**: NO IMPLEMENTATION

**Gap**: Immortals should see:
- Header: `Obvious exits from room 3001:`
- Per exit: `North - Midgaard Temple Square (room 3001)`

**Impact**: HIGH - Immortals cannot see room vnums (critical for building/debugging)

**Fix Required**: Check immortal status and add vnum display

---

### Feature 4: Door Closed Check ❌ MISSING

**ROM C** (lines 1414-1416):
```c
if ((pexit = ch->in_room->exit[door]) != NULL
    && pexit->u1.to_room != NULL
    && can_see_room (ch, pexit->u1.to_room)
    && !IS_SET (pexit->exit_info, EX_CLOSED))  // ← CRITICAL
```

**QuickMUD**: NO IMPLEMENTATION

**Gap**: Closed doors should be HIDDEN from exit list

**Impact**: CRITICAL - Players can see exits through closed doors (breaks immersion)

**Fix Required**: Check `EX_CLOSED` flag (bit 0 in exit_info)

---

### Feature 5: can_see_room Visibility Check ❌ MISSING

**ROM C** (line 1415):
```c
&& can_see_room (ch, pexit->u1.to_room)
```

**QuickMUD**: NO IMPLEMENTATION

**Gap**: Exit should be hidden if:
- Target room is dark (and char lacks dark vision)
- Target room has permission restrictions (IMP_ONLY, GODS_ONLY, etc.)
- Target room has clan restrictions

**Impact**: HIGH - Players can see exits to forbidden/dark rooms

**Fix Required**: Call `can_see_room(char, exit.to_room)` before displaying

**Note**: QuickMUD already has `mud.world.vision.can_see_room()` - just needs integration

---

### Feature 6: Detailed Room Names ❌ MISSING

**ROM C** (lines 1417-1421):
```c
sprintf (buf + strlen (buf), "%-5s - %s",
         capitalize (dir_name[door]),
         room_is_dark (pexit->u1.to_room)
         ? "Too dark to tell" : pexit->u1.to_room->name);
```

**QuickMUD**: NO IMPLEMENTATION

**Gap**: Non-auto mode should show:
```
North - Midgaard Temple Square
South - Too dark to tell
East  - Main Street
```

**Impact**: CRITICAL - Players cannot see where exits lead (core navigation feature)

**Fix Required**: Display room names (or "Too dark to tell" if dark)

---

### Feature 7: room_is_dark Check ❌ MISSING

**ROM C** (lines 1419-1420):
```c
room_is_dark (pexit->u1.to_room)
? "Too dark to tell" : pexit->u1.to_room->name
```

**QuickMUD**: NO IMPLEMENTATION

**Gap**: Dark rooms should show "Too dark to tell" instead of room name

**Impact**: MEDIUM - Players see room names through darkness

**Fix Required**: Call `room_is_dark(exit.to_room)` before displaying name

**Note**: QuickMUD already has `mud.world.vision.room_is_dark()` - just needs integration

---

### Feature 8: Direction Name Capitalization ❌ MISSING

**ROM C** (line 1418):
```c
capitalize (dir_name[door])
```

**QuickMUD**: PARTIAL (lowercase only)

**Gap**: Directions should be capitalized: `North`, `South`, `East`, `West`, `Up`, `Down`

**Impact**: LOW - Cosmetic formatting issue

**Fix Required**: Capitalize direction names in non-auto mode

---

### Feature 9: Proper "None" Message ✅ IMPLEMENTED

**ROM C** (line 1443):
```c
if (!found)
    strcat (buf, fAuto ? " none" : "None.\n\r");
```

**QuickMUD** (line 137-140):
```python
if not dirs:
    return "Obvious exits: none."
```

**Status**: ✅ CORRECT (non-auto mode message matches)

**Note**: Auto mode message still needed (`[Exits: none]`)

---

### Feature 10: Exit Direction Iteration (6 directions) ✅ IMPLEMENTED

**ROM C** (line 1413):
```c
for (door = 0; door <= 5; door++)
```

**QuickMUD** (line 138):
```python
for i, ex in enumerate(room.exits)
```

**Status**: ✅ CORRECT (iterates all 6 directions: N, E, S, W, U, D)

---

## Gap Summary

| Category | ROM C Features | QuickMUD | Gaps |
|----------|----------------|----------|------|
| **Critical** | 5 | 0 | 5 |
| **High** | 2 | 0 | 2 |
| **Medium** | 1 | 0 | 1 |
| **Low** | 1 | 0 | 1 |
| **Working** | 1 | 1 | 0 |
| **TOTAL** | **10** | **1** | **9** |

---

## Critical Gaps (P0 - Blocking Basic Functionality)

### Gap 1: No Blindness Check
- **Impact**: Blind players can see exits
- **Effort**: 5 minutes
- **Fix**: Add `check_blind(char)` call

### Gap 2: No Auto-Exit Mode
- **Impact**: `exits auto` command broken
- **Effort**: 30 minutes
- **Fix**: Detect `args == "auto"` and format as `{o[Exits: north south]{x`

### Gap 3: No Closed Door Check
- **Impact**: Players see exits through closed doors
- **Effort**: 15 minutes
- **Fix**: Check `exit.exit_info & EX_CLOSED`

### Gap 4: No Room Names Display
- **Impact**: Players don't know where exits lead
- **Effort**: 30 minutes
- **Fix**: Display `exit.to_room.name` per direction

### Gap 5: No can_see_room Check
- **Impact**: Players see exits to forbidden/dark rooms
- **Effort**: 10 minutes
- **Fix**: Call `can_see_room(char, exit.to_room)`

---

## High Priority Gaps (P1 - Important Features)

### Gap 6: No Immortal Room Vnum Display
- **Impact**: Immortals cannot see room vnums (critical for building)
- **Effort**: 20 minutes
- **Fix**: Check `char.is_immortal()` and add vnum display

### Gap 7: No room_is_dark Check
- **Impact**: Players see room names through darkness
- **Effort**: 10 minutes
- **Fix**: Call `room_is_dark(exit.to_room)` and show "Too dark to tell"

---

## Medium Priority Gaps (P2 - Polish)

### Gap 8: Direction Capitalization
- **Impact**: Cosmetic - lowercase "north" instead of "North"
- **Effort**: 5 minutes
- **Fix**: Use `direction.capitalize()` in non-auto mode

---

## Implementation Plan

### Phase 1: Critical Fixes (1 hour)
1. Add `check_blind()` call (5 min)
2. Implement auto-exit mode (30 min)
3. Add closed door check (15 min)
4. Add room names display (30 min)
5. Add can_see_room check (10 min)

### Phase 2: High Priority (30 min)
6. Add immortal vnum display (20 min)
7. Add room_is_dark check (10 min)

### Phase 3: Polish (5 min)
8. Capitalize direction names (5 min)

**Total Estimated Time**: 1 hour 35 minutes

---

## ROM C Source Reference

**File**: `src/act_info.c`  
**Lines**: 1393-1451 (59 lines)

```c
void do_exits (CHAR_DATA * ch, char *argument)
{
    extern char *const dir_name[];
    char buf[MAX_STRING_LENGTH];
    EXIT_DATA *pexit;
    bool found;
    bool fAuto;
    int door;

    fAuto = !str_cmp (argument, "auto");

    if (!check_blind (ch))
        return;

    if (fAuto)
        sprintf (buf, "{o[Exits:");
    else if (IS_IMMORTAL (ch))
        sprintf (buf, "Obvious exits from room %d:\n\r", ch->in_room->vnum);
    else
        sprintf (buf, "Obvious exits:\n\r");

    found = FALSE;
    for (door = 0; door <= 5; door++)
    {
        if ((pexit = ch->in_room->exit[door]) != NULL
            && pexit->u1.to_room != NULL
            && can_see_room (ch, pexit->u1.to_room)
            && !IS_SET (pexit->exit_info, EX_CLOSED))
        {
            found = TRUE;
            if (fAuto)
            {
                strcat (buf, " ");
                strcat (buf, dir_name[door]);
            }
            else
            {
                sprintf (buf + strlen (buf), "%-5s - %s",
                         capitalize (dir_name[door]),
                         room_is_dark (pexit->u1.to_room)
                         ? "Too dark to tell" : pexit->u1.to_room->name);
                if (IS_IMMORTAL (ch))
                    sprintf (buf + strlen (buf),
                             " (room %d)\n\r", pexit->u1.to_room->vnum);
                else
                    sprintf (buf + strlen (buf), "\n\r");
            }
        }
    }

    if (!found)
        strcat (buf, fAuto ? " none" : "None.\n\r");

    if (fAuto)
        strcat (buf, "]{x\n\r");

    send_to_char (buf, ch);
    return;
}
```

---

## QuickMUD Current Implementation

**File**: `mud/commands/inspection.py`  
**Lines**: 133-141 (9 lines)

```python
def do_exits(char: Character, args: str = "") -> str:
    """List obvious exits from the current room (ROM-style)."""
    room = char.room
    if not room or not getattr(room, "exits", None):
        return "Obvious exits: none."
    dirs = [dir_names[type(list(dir_names.keys())[0])(i)] for i, ex in enumerate(room.exits) if ex]
    if not dirs:
        return "Obvious exits: none."
    return f"Obvious exits: {' '.join(dirs)}."
```

**Analysis**: Minimal stub - only lists direction names, no visibility checks, no auto mode, no room names.

---

## QuickMUD Helper Functions Available

QuickMUD already has these ROM C equivalent functions:

| ROM C Function | QuickMUD Equivalent | Location |
|----------------|---------------------|----------|
| `check_blind()` | `rom_api.check_blind()` | `mud/rom_api.py:265` |
| `can_see_room()` | `vision.can_see_room()` | `mud/world/vision.py:242` |
| `room_is_dark()` | `vision.room_is_dark()` | `mud/world/vision.py:221` |
| `IS_IMMORTAL()` | `char.is_immortal()` | `mud/models/character.py` |
| `capitalize()` | `str.capitalize()` | Python builtin |

**No new helper functions needed** - just integration work!

---

## Data Model Requirements

### Exit Data Structure

QuickMUD uses `mud.models.exit.Exit`:

```python
@dataclass
class Exit:
    to_room: Optional[Room]
    exit_info: int  # Bitfield: EX_CLOSED (bit 0), EX_LOCKED (bit 1), etc.
    key_vnum: int
    keyword: str
    description: str
```

### Exit Flags (from ROM C merc.h)

```c
#define EX_ISDOOR    (A)  // Bit 0 (1)   - Door exists
#define EX_CLOSED    (B)  // Bit 1 (2)   - Door is closed
#define EX_LOCKED    (C)  // Bit 2 (4)   - Door is locked
#define EX_PICKPROOF (F)  // Bit 5 (32)  - Lock cannot be picked
#define EX_NOPASS    (G)  // Bit 6 (64)  - Cannot pass through
#define EX_EASY      (H)  // Bit 7 (128) - Easy to pick
#define EX_HARD      (I)  // Bit 8 (256) - Hard to pick
#define EX_INFURIATING (J) // Bit 9 (512) - Very hard to pick
#define EX_NOCLOSE   (K)  // Bit 10 (1024) - Cannot close
#define EX_NOLOCK    (L)  // Bit 11 (2048) - Cannot lock
```

**For do_exits, we only care about bit 1 (EX_CLOSED = 2)**

---

## Expected Output Examples

### Mortal Player (Non-Auto Mode)

```
> exits
Obvious exits:
North - Midgaard Temple Square
East  - Main Street
South - Dark Alley
```

### Mortal Player (Auto Mode)

```
> exits auto
{o[Exits: north east south]{x
```

### Immortal (Non-Auto Mode)

```
> exits
Obvious exits from room 3001:
North - Midgaard Temple Square (room 3001)
East  - Main Street (room 3002)
South - Too dark to tell (room 3010)
```

### Immortal (Auto Mode)

```
> exits auto
{o[Exits: north east south]{x
```

### No Exits

```
> exits
Obvious exits:
None.
```

### No Exits (Auto Mode)

```
> exits auto
{o[Exits: none]{x
```

### Blind Player

```
> exits
You can't see a thing!
```

### Closed Door (Hidden)

**Room Setup**: North exit has closed door

```
> exits
Obvious exits:
East  - Main Street
South - Dark Alley
```

(North exit is HIDDEN because door is closed)

---

## Acceptance Criteria

✅ **do_exits is complete when:**

1. Blind players see "You can't see a thing!" (check_blind integration)
2. `exits auto` shows compact format: `{o[Exits: north south]{x`
3. Closed doors are hidden from exit list
4. Non-auto mode shows room names per direction
5. Dark rooms show "Too dark to tell" instead of name
6. Exits to forbidden rooms are hidden (can_see_room check)
7. Immortals see room vnums in header and per exit
8. Direction names are capitalized in non-auto mode
9. Integration tests verify all above behaviors
10. All tests passing (no regressions)

---

## Test Plan (Next Phase)

Create `tests/integration/test_do_exits_command.py` with:

**P0 Tests (Critical - 5 tests)**:
1. `test_exits_shows_available_exits` - Basic exit listing with room names
2. `test_exits_closed_door_hidden` - Closed doors not shown
3. `test_exits_auto_mode` - Compact format `[Exits: north south]`
4. `test_exits_blind_check` - Blind players see nothing
5. `test_exits_no_exits_message` - "None" when no exits

**P1 Tests (Important - 4 tests)**:
6. `test_exits_immortal_room_vnums` - Immortals see vnums
7. `test_exits_dark_room_message` - "Too dark to tell" for dark rooms
8. `test_exits_can_see_room_check` - Forbidden rooms hidden
9. `test_exits_direction_capitalization` - "North" not "north"

**Edge Cases (3 tests)**:
10. `test_exits_auto_mode_no_exits` - `[Exits: none]`
11. `test_exits_all_six_directions` - N, E, S, W, U, D all work
12. `test_exits_mixed_open_closed` - Only open doors shown

**Total**: 12 integration tests

---

## Conclusion

**QuickMUD's do_exits is a minimal stub missing 90% of ROM C features.**

**Critical gaps**:
- No blindness check (blind players can see)
- No auto-exit mode (common ROM feature broken)
- No closed door check (players see through doors)
- No room names (players don't know where exits lead)
- No visibility checks (players see forbidden rooms)

**Recommendation**: IMMEDIATE IMPLEMENTATION REQUIRED (Priority P1)

**Estimated effort**: 1 hour 35 minutes total

**Impact**: Core navigation command - essential for player experience

---

**Next Steps**: Fix gaps in `mud/commands/inspection.py` following implementation plan above.
