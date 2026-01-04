# do_where() ROM C Parity Audit

**Command**: `where [target]`  
**ROM C Source**: `src/act_info.c` lines 2407-2467 (61 lines)  
**QuickMUD Location**: `mud/commands/info.py` lines 267-311  
**Date Audited**: January 7, 2026  
**Audited By**: Sisyphus (AI Agent)

---

## Executive Summary

**Parity Status**: ⚠️ **~50% ROM C Parity** (5 critical gaps found)

**Assessment**: Command is **INCOMPLETE** - only implements one of two modes.

**ROM C has TWO modes**:
1. **`where` (no args)**: Show all players in same area ✅ QuickMUD implements this
2. **`where <target>` (with args)**: Search for specific mob/player ❌ QuickMUD MISSING

**Recommendation**: **FIX - HIGH PRIORITY** (P1)
- Missing functionality (target search mode)
- Missing visibility checks (private rooms, ROOM_NOWHERE, hide/sneak affects)
- Missing ownership checks (is_room_owner, room_is_private)
- Fix effort: ~1-2 hours (implement target search mode + visibility checks)

---

## ROM C Source Analysis

### ROM C Implementation (lines 2407-2467)

```c
void do_where (CHAR_DATA * ch, char *argument)
{
    char buf[MAX_STRING_LENGTH];
    char arg[MAX_INPUT_LENGTH];
    CHAR_DATA *victim;
    DESCRIPTOR_DATA *d;
    bool found;

    one_argument (argument, arg);

    // MODE 1: No arguments - show players in area
    if (arg[0] == '\0')
    {
        send_to_char ("Players near you:\n\r", ch);
        found = FALSE;
        for (d = descriptor_list; d; d = d->next)
        {
            if (d->connected == CON_PLAYING
                && (victim = d->character) != NULL && !IS_NPC (victim)
                && victim->in_room != NULL
                && !IS_SET (victim->in_room->room_flags, ROOM_NOWHERE)
                && (is_room_owner (ch, victim->in_room)
                    || !room_is_private (victim->in_room))
                && victim->in_room->area == ch->in_room->area
                && can_see (ch, victim))
            {
                found = TRUE;
                sprintf (buf, "%-28s %s\n\r",
                         victim->name, victim->name->in_room->name);
                send_to_char (buf, ch);
            }
        }
        if (!found)
            send_to_char ("None\n\r", ch);
    }
    // MODE 2: With argument - search for specific target
    else
    {
        found = FALSE;
        for (victim = char_list; victim != NULL; victim = victim->next)
        {
            if (victim->in_room != NULL
                && victim->in_room->area == ch->in_room->area
                && !IS_AFFECTED (victim, AFF_HIDE)
                && !IS_AFFECTED (victim, AFF_SNEAK)
                && can_see (ch, victim) && is_name (arg, victim->name))
            {
                found = TRUE;
                sprintf (buf, "%-28s %s\n\r",
                         PERS (victim, ch), victim->in_room->name);
                send_to_char (buf, ch);
                break;  // Only show first match
            }
        }
        if (!found)
            act ("You didn't find any $T.", ch, NULL, arg, TO_CHAR);
    }

    return;
}
```

### ROM C Behavior Summary

**Mode 1: `where` (no arguments)**
- Header: `"Players near you:\n\r"`
- Filters:
  - Connected players only (CON_PLAYING)
  - Not NPCs (!IS_NPC)
  - Has valid room (in_room != NULL)
  - Not in ROOM_NOWHERE rooms
  - Private room checks (is_room_owner OR !room_is_private)
  - Same area as viewer
  - Visible to viewer (can_see)
- Format: `"%-28s %s\n\r"` (name, room name)
- Empty: `"None\n\r"`

**Mode 2: `where <target>` (with argument)**
- Searches: char_list (ALL characters, including mobs)
- Filters:
  - Has valid room (in_room != NULL)
  - Same area as viewer
  - Not hiding (!AFF_HIDE)
  - Not sneaking (!AFF_SNEAK)
  - Visible to viewer (can_see)
  - Name matches argument (is_name)
- Format: `"%-28s %s\n\r"` (PERS name, room name)
- Breaks after first match (shows only ONE result)
- Not found: `"You didn't find any {target}."`

**Key Features**:
1. **Two distinct modes** based on argument presence
2. **Private room filtering** (mode 1 only)
3. **ROOM_NOWHERE filtering** (mode 1 only)
4. **Hide/sneak filtering** (mode 2 only)
5. **PERS() name formatting** (mode 2 uses PERS, mode 1 uses raw name)
6. **First match only** (mode 2 breaks after finding first target)

---

## QuickMUD Implementation Analysis

### QuickMUD Implementation (lines 267-311)

```python
def do_where(char: Character, args: str) -> str:
    """
    Show players in current area.

    ROM Reference: src/act_info.c lines 2200-2280 (do_where)  # ⚠️ WRONG LINE NUMBERS

    Usage: where

    Lists all players in the same area as you.
    """
    from mud.net.session import SESSIONS

    char_room = getattr(char, "room", None)
    if not char_room:
        return "You are nowhere!"

    char_area_vnum = getattr(getattr(char_room, "area", None), "vnum", None)
    if char_area_vnum is None:
        return "You are in an unknown area."

    lines = [f"Players near you in {getattr(getattr(char_room, 'area', None), 'name', 'this area')}:"]
    # ⚠️ Extra header info (area name) not in ROM C

    found = False
    for sess in SESSIONS.values():
        ch = sess.character  # ⚠️ Variable name shadows outer 'char'
        if not ch:
            continue

        room = getattr(ch, "room", None)
        if not room:
            continue

        area = getattr(room, "area", None)
        area_vnum = getattr(area, "vnum", None)

        if area_vnum == char_area_vnum:
            name = getattr(ch, "name", "Unknown")
            room_name = getattr(room, "name", "somewhere")
            lines.append(f"  {name:28s} {room_name}")
            # ⚠️ No visibility checks (can_see, private rooms, ROOM_NOWHERE)
            # ⚠️ No NPC filtering (!IS_NPC check missing)
            # ⚠️ Indented with 2 spaces (ROM C has no indent)
            found = True

    if not found:
        lines.append("  None")  # ⚠️ Indented (ROM C: "None\n\r" not indented)

    return ROM_NEWLINE.join(lines) + ROM_NEWLINE
```

### QuickMUD Output Example

```
Players near you in Midgaard:
  Gandalf                      The Temple of Midgaard
  Bilbo                        Midgaard Market Square
  None
```

vs ROM C output:

```
Players near you:
Gandalf                      The Temple of Midgaard
Bilbo                        Midgaard Market Square
None
```

---

## Gap Analysis

### ❌ Gap 1: Missing Target Search Mode (CRITICAL)

**ROM C**: `where <target>` searches for specific mob/player  
**QuickMUD**: Ignores arguments entirely (only implements no-arg mode)

**Issue**: QuickMUD doesn't implement the second mode at all!

**Example Missing Functionality**:
```
> where guard
City Guard                   Midgaard Market Square
```

**Impact**: 
- Players can't search for specific mobs
- Missing major functionality
- Command is incomplete

**Fix Required**: Implement full target search logic:
```python
def do_where(char: Character, args: str) -> str:
    from mud.net.session import SESSIONS
    from mud.world.char_find import is_name
    from mud.world.vision import can_see
    from mud.models.constants import AffectFlag
    
    # Parse argument
    arg = args.strip()
    
    char_room = getattr(char, "room", None)
    if not char_room:
        return "You are nowhere!\n\r"
    
    char_area = getattr(char_room, "area", None)
    if not char_area:
        return "You are in an unknown area.\n\r"
    
    # MODE 2: Search for specific target
    if arg:
        # Search char_list for matching character in same area
        from mud.models.registries import character_registry
        
        for victim in character_registry.values():
            victim_room = getattr(victim, "room", None)
            if not victim_room:
                continue
            
            victim_area = getattr(victim_room, "area", None)
            if victim_area != char_area:
                continue
            
            # ROM C filters (mode 2)
            if is_affected(victim, AffectFlag.HIDE):
                continue
            if is_affected(victim, AffectFlag.SNEAK):
                continue
            if not can_see(char, victim):
                continue
            if not is_name(arg, victim.name):
                continue
            
            # Found! (show first match only)
            victim_name = pers(victim, char)  # PERS() formatting
            room_name = getattr(victim_room, "name", "somewhere")
            return f"{victim_name:28s} {room_name}\n\r"
        
        # Not found
        return f"You didn't find any {arg}.\n\r"
    
    # MODE 1: Show all players in area (existing logic)
    ...
```

---

### ❌ Gap 2: Missing Visibility Checks (CRITICAL)

**ROM C Mode 1 Filters**:
```c
!IS_SET(victim->in_room->room_flags, ROOM_NOWHERE)  // Not in ROOM_NOWHERE
(is_room_owner(ch, victim->in_room) || !room_is_private(victim->in_room))  // Private room check
can_see(ch, victim)  // Visibility check
```

**QuickMUD**: NO visibility checks at all!

**Issue**: QuickMUD shows ALL players in area, including:
- Players in private rooms you don't own
- Players in ROOM_NOWHERE rooms
- Players you can't see (invisible, dark, etc.)

**Impact**: Privacy violation, shows invisible players

**Fix Required**: Add visibility filters to mode 1

---

### ❌ Gap 3: Missing NPC Filter (IMPORTANT)

**ROM C**: `!IS_NPC(victim)` check in mode 1  
**QuickMUD**: No NPC filtering

**Issue**: If NPCs were in SESSIONS (they're not currently), they would show up.

**Impact**: Low (NPCs aren't in SESSIONS currently, but missing for correctness)

**Fix**: Add NPC check

---

### ❌ Gap 4: Wrong Header Format (MINOR)

**ROM C**: `"Players near you:\n\r"`  
**QuickMUD**: `"Players near you in {area_name}:"`

**Issue**: QuickMUD adds extra area name info not in ROM C.

**Impact**: Minor formatting difference, but might be useful?

**Fix**: Remove area name from header for ROM C parity

---

### ❌ Gap 5: Wrong Indent Formatting (COSMETIC)

**ROM C**: No indentation  
```
Players near you:
Gandalf                      The Temple of Midgaard
None
```

**QuickMUD**: 2-space indentation
```
Players near you in Midgaard:
  Gandalf                    The Temple of Midgaard
  None
```

**Issue**: Different formatting style.

**Impact**: Very minor cosmetic difference.

**Fix**: Remove 2-space indent

---

### 📝 Gap 6: Wrong ROM C Line Reference (DOCUMENTATION)

**Docstring**: `ROM Reference: src/act_info.c lines 2200-2280 (do_where)`  
**Actual**: `src/act_info.c lines 2407-2467 (do_where)`

**Issue**: Incorrect line numbers.

**Fix**: Update docstring.

---

### 📝 Gap 7: Variable Name Shadowing (CODE QUALITY)

**Issue**: Loop variable `ch` shadows function parameter `char`.

**Line 291**: `ch = sess.character`

**Impact**: Confusing code, potential bugs.

**Fix**: Rename loop variable to `victim` (matching ROM C):
```python
for sess in SESSIONS.values():
    victim = sess.character
    if not victim:
        continue
    ...
```

---

## Summary of Gaps

| Gap # | Issue | Severity | Impact | Fix Effort |
|-------|-------|----------|--------|------------|
| 1 | Missing target search mode (where <target>) | CRITICAL | Major missing functionality | 45 min |
| 2 | Missing visibility checks (can_see, private, ROOM_NOWHERE) | CRITICAL | Privacy/visibility bugs | 30 min |
| 3 | Missing NPC filter (!IS_NPC) | IMPORTANT | Potential bug if NPCs in sessions | 5 min |
| 4 | Wrong header format (extra area name) | MINOR | Formatting difference | 2 min |
| 5 | Wrong indent formatting (2-space indent) | COSMETIC | Visual difference | 2 min |
| 6 | Wrong docstring line reference | DOCS | Misleading reference | 1 min |
| 7 | Variable name shadowing (`ch` vs `char`) | CODE QUALITY | Confusing code | 2 min |

**Total Fix Effort**: ~1.5 hours

---

## Recommended Fix Implementation

### Fixed do_where() Implementation

```python
def do_where(char: Character, args: str) -> str:
    """
    Show players in current area, or search for specific character.

    ROM Reference: src/act_info.c lines 2407-2467 (do_where)

    Usage: 
        where           - Show all players in your area
        where <target>  - Search for specific character/mob in your area
    """
    from mud.net.session import SESSIONS
    from mud.world.char_find import is_name
    from mud.world.vision import can_see, pers
    from mud.models.constants import AffectFlag, RoomFlag
    from mud.models.registries import character_registry
    
    # Get character's room and area
    char_room = getattr(char, "room", None)
    if not char_room:
        return "You are nowhere!\n\r"
    
    char_area = getattr(char_room, "area", None)
    if not char_area:
        return "You are in an unknown area.\n\r"
    
    # Parse argument (ROM C: one_argument)
    arg = args.strip()
    
    # MODE 2: Search for specific target (ROM C lines 2443-2463)
    if arg:
        found = False
        
        # Search char_list (all characters including mobs)
        for victim in character_registry.values():
            victim_room = getattr(victim, "room", None)
            if not victim_room:
                continue
            
            victim_area = getattr(victim_room, "area", None)
            
            # ROM C filters for mode 2
            if victim_area != char_area:
                continue
            if is_affected(victim, AffectFlag.HIDE):
                continue
            if is_affected(victim, AffectFlag.SNEAK):
                continue
            if not can_see(char, victim):
                continue
            if not is_name(arg, victim.name):
                continue
            
            # Found! Show first match only (ROM C breaks after first)
            victim_name = pers(victim, char)  # PERS() formatting
            room_name = getattr(victim_room, "name", "somewhere")
            return f"{victim_name:<28s} {room_name}\n\r"
        
        # Not found (ROM C: act("You didn't find any $T.", ...))
        return f"You didn't find any {arg}.\n\r"
    
    # MODE 1: Show all players in area (ROM C lines 2416-2440)
    lines = ["Players near you:"]  # ROM C header (no area name)
    found = False
    
    for sess in SESSIONS.values():
        victim = sess.character  # Renamed from 'ch' to avoid shadowing
        if not victim:
            continue
        
        # ROM C: d->connected == CON_PLAYING check (implicit via SESSIONS)
        # ROM C: !IS_NPC check
        if getattr(victim, "is_npc", False):
            continue
        
        victim_room = getattr(victim, "room", None)
        if not victim_room:
            continue
        
        victim_area = getattr(victim_room, "area", None)
        
        # ROM C filters for mode 1
        # 1. Same area check
        if victim_area != char_area:
            continue
        
        # 2. ROOM_NOWHERE check
        room_flags = getattr(victim_room, "room_flags", 0)
        if room_flags & RoomFlag.ROOM_NOWHERE:
            continue
        
        # 3. Private room check (is_room_owner OR !room_is_private)
        if is_room_private(victim_room) and not is_room_owner(char, victim_room):
            continue
        
        # 4. Visibility check
        if not can_see(char, victim):
            continue
        
        # Passed all filters - add to output
        victim_name = getattr(victim, "name", "Unknown")
        room_name = getattr(victim_room, "name", "somewhere")
        lines.append(f"{victim_name:<28s} {room_name}")  # No indent (ROM C format)
        found = True
    
    if not found:
        lines.append("None")  # No indent (ROM C format)
    
    return "\n\r".join(lines) + "\n\r"
```

### Helper Functions Needed

**May need to implement** (if not already in codebase):

1. `is_affected(char, flag)` - Check if character has affect flag
2. `is_name(arg, name_list)` - Check if arg matches any name in list
3. `pers(victim, viewer)` - Get name as viewer sees it (ROM C PERS macro)
4. `is_room_private(room)` - Check if room is private (ROM C room_is_private)
5. `is_room_owner(char, room)` - Check if char owns room (ROM C is_room_owner)

---

## Testing Requirements

### Unit Tests

**File**: `tests/test_do_where.py` (create new file)

**Test Cases**:

**Mode 1 (No Arguments)**:
1. **Test basic player list** - Show players in same area
2. **Test empty area** - Show "None" when no other players
3. **Test ROOM_NOWHERE filtering** - Don't show players in ROOM_NOWHERE rooms
4. **Test private room filtering** - Don't show players in private rooms unless owner
5. **Test visibility** - Don't show invisible players
6. **Test NPC filtering** - Don't show NPCs (only players)
7. **Test different areas** - Don't show players in other areas

**Mode 2 (With Argument)**:
8. **Test target search (player)** - Find specific player by name
9. **Test target search (mob)** - Find specific mob by name
10. **Test hide filtering** - Don't find hidden characters
11. **Test sneak filtering** - Don't find sneaking characters
12. **Test visibility** - Don't find invisible characters
13. **Test first match only** - Only show first match (not all)
14. **Test not found** - Return "You didn't find any {target}."
15. **Test area filtering** - Don't find targets in other areas

### Integration Tests

**File**: `tests/integration/test_do_where_command.py` (create new file)

**Scenarios**:
1. **P0: Basic player listing** - Multiple players in area, verify list
2. **P0: Target search (mob)** - Search for mob by name
3. **P0: Target search (player)** - Search for player by name
4. **P1: Private room filtering** - Verify private rooms hidden
5. **P1: Visibility checks** - Verify invisible players hidden
6. **P1: Hide/sneak filtering** - Verify hidden/sneaking targets not found
7. **Edge: Empty area** - No other players shows "None"
8. **Edge: Target not found** - Search for non-existent target
9. **Edge: Multi-area** - Players in different areas don't show

---

## ROM C Parity Checklist

**Feature Coverage**:
- [ ] Mode 1: Show all players in area (no arguments)
  - [ ] ROM C header format ("Players near you:")
  - [ ] NPC filtering (!IS_NPC)
  - [ ] ROOM_NOWHERE filtering
  - [ ] Private room filtering (is_room_owner / room_is_private)
  - [ ] Visibility check (can_see)
  - [ ] Same area check
  - [ ] "None" when empty (no indent)
  - [ ] No 2-space indent on output
- [ ] Mode 2: Search for specific target (with argument)
  - [ ] Search char_list (all characters including mobs)
  - [ ] AFF_HIDE filtering
  - [ ] AFF_SNEAK filtering
  - [ ] Visibility check (can_see)
  - [ ] Same area check
  - [ ] Name matching (is_name)
  - [ ] PERS() name formatting
  - [ ] First match only (break after finding)
  - [ ] "You didn't find any {target}." message
- [ ] ROM C line reference in docstring

**Current Status**: 2/20 features complete (10% parity)

---

## Acceptance Criteria

**Before marking do_where as COMPLETE**:

1. ✅ Mode 1 (no args) shows all players in area with correct filters
2. ✅ Mode 2 (with args) searches for specific target (player or mob)
3. ✅ Private room filtering works (ROM C logic)
4. ✅ ROOM_NOWHERE filtering works
5. ✅ Hide/sneak filtering works (mode 2)
6. ✅ Visibility checks work (can_see)
7. ✅ NPC filtering works (mode 1 only shows players)
8. ✅ PERS() name formatting in mode 2
9. ✅ First match only in mode 2 (doesn't show all matches)
10. ✅ Output format matches ROM C (no area name, no indent)
11. ✅ Integration tests passing (9 scenarios minimum)
12. ✅ No regressions in existing tests

---

## Implementation Status

**Status**: ⏳ **NOT STARTED** - Gaps documented, major rewrite needed

**Complexity**: HIGH - Missing entire mode 2, needs helper functions

**Next Steps**:
1. Verify helper functions exist (is_affected, is_name, pers, is_room_private, is_room_owner, can_see)
2. Rewrite do_where() with both modes
3. Add all ROM C visibility filters
4. Create unit tests (15 test cases)
5. Create integration tests (9 scenarios)
6. Run tests and verify all pass
7. Update `ACT_INFO_C_AUDIT.md` to mark do_where as complete

**Estimated Time**: 2-3 hours total (1.5 hours implementation + 1 hour tests + 30 min helper functions)

---

**End of Audit** - Ready for implementation (after helper function verification)
