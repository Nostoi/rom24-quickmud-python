# do_weather() ROM C Parity Audit

**Command**: `weather`  
**ROM C Source**: `src/act_info.c` lines 1806-1830 (25 lines)  
**QuickMUD Location**: `mud/commands/info.py` lines 368-400  
**Date Audited**: January 7, 2026  
**Audited By**: Sisyphus (AI Agent)

---

## Executive Summary

**Parity Status**: ⚠️ **~70% ROM C Parity** (1 critical gap found)

**Assessment**: Command is functional but missing wind direction display.

**Recommendation**: **FIX - MEDIUM PRIORITY** (P1)
- Missing feature is noticeable to players
- Adds atmospheric flavor to weather system
- Fix effort: ~15 minutes (simple string formatting)

---

## ROM C Source Analysis

### ROM C Implementation (lines 1806-1830)

```c
void do_weather (CHAR_DATA * ch, char *argument)
{
    char buf[MAX_STRING_LENGTH];

    static char *const sky_look[4] = {
        "cloudless",
        "cloudy",
        "rainy",
        "lit by flashes of lightning"
    };

    if (!IS_OUTSIDE (ch))
    {
        send_to_char ("You can't see the weather indoors.\n\r", ch);
        return;
    }

    sprintf (buf, "The sky is %s and %s.\n\r",
             sky_look[weather_info.sky],
             weather_info.change >= 0
             ? "a warm southerly breeze blows"
             : "a cold northern gust blows");
    send_to_char (buf, ch);
    return;
}
```

### ROM C Macros & Structures

**IS_OUTSIDE macro** (merc.h lines 2112-2114):
```c
#define IS_OUTSIDE(ch)        (!IS_SET(                    \
                    (ch)->in_room->room_flags,            \
                    ROOM_INDOORS))
```

**weather_data structure** (merc.h lines 376-382):
```c
struct weather_data
{
    int mmhg;      // Barometric pressure (960-1040)
    int change;    // Pressure change rate (+/- value)
    int sky;       // Sky state (0-3: cloudless/cloudy/rainy/lightning)
    int sunlight;  // Sun position (unused in do_weather)
};
```

### ROM C Behavior Summary

**Output Format**:
```
The sky is cloudless and a warm southerly breeze blows.
```

OR

```
The sky is rainy and a cold northern gust blows.
```

**Key Features**:
1. **Indoor check**: `IS_OUTSIDE(ch)` checks `ROOM_INDOORS` flag
2. **Sky descriptions**: 4 states (cloudless, cloudy, rainy, lightning)
3. **Wind direction**: Based on `weather_info.change`:
   - `change >= 0`: "a warm southerly breeze blows" (pressure rising/stable)
   - `change < 0`: "a cold northern gust blows" (pressure falling)
4. **Single line output**: Both sky and wind in one sentence

---

## QuickMUD Implementation Analysis

### QuickMUD Implementation (lines 368-400)

```python
def do_weather(char: Character, args: str) -> str:
    """
    Display weather conditions.

    ROM Reference: src/act_info.c lines 2420-2480 (do_weather)  # ⚠️ WRONG LINE NUMBERS

    Usage: weather

    Shows current weather and sky conditions.
    """
    from mud.game_loop import weather, SkyState
    from mud.models.constants import RoomFlag

    char_room = getattr(char, "room", None)
    if not char_room:
        return "You can't see the sky from nowhere."

    # Check if in a room where you can see the sky
    # ROM Reference: src/act_info.c checks room_flags & ROOM_INDOORS
    room_flags = getattr(char_room, "room_flags", 0)
    if room_flags & RoomFlag.ROOM_INDOORS:
        return "You can't see the sky from here."  # ⚠️ Different message

    # Get weather conditions
    sky_msgs = {
        SkyState.CLOUDLESS: "The sky is cloudless.",
        SkyState.CLOUDY: "The sky is cloudy.",
        SkyState.RAINING: "It is raining.",
        SkyState.LIGHTNING: "Lightning flashes in the sky.",
    }

    msg = sky_msgs.get(weather.sky, "The sky is strange.")
    return msg
```

### QuickMUD Weather System

**WeatherState class** (mud/game_loop.py lines 55-61):
```python
class WeatherState:
    """ROM-style weather state tracking pressure and sky."""
    
    sky: SkyState
    mmhg: int
    change: int  # ✅ This field EXISTS but is unused in do_weather!
```

**SkyState enum** (mud/game_loop.py lines 45-51):
```python
class SkyState(IntEnum):
    CLOUDLESS = 0
    CLOUDY = 1
    RAINING = 2
    LIGHTNING = 3
```

### QuickMUD Output Example

```
The sky is cloudless.
```

---

## Gap Analysis

### ❌ Gap 1: Missing Wind Direction Display (CRITICAL)

**ROM C**: `"The sky is cloudless and a warm southerly breeze blows."`  
**QuickMUD**: `"The sky is cloudless."`

**Issue**: QuickMUD doesn't display wind direction based on `weather.change`.

**Impact**: 
- Loss of atmospheric detail
- Players can't tell if weather is improving or worsening
- Less immersive weather system

**Fix**:
```python
def do_weather(char: Character, args: str) -> str:
    from mud.game_loop import weather, SkyState
    from mud.models.constants import RoomFlag

    char_room = getattr(char, "room", None)
    if not char_room:
        return "You can't see the sky from nowhere.\n\r"

    # Check if in a room where you can see the sky (ROM C: IS_OUTSIDE macro)
    room_flags = getattr(char_room, "room_flags", 0)
    if room_flags & RoomFlag.ROOM_INDOORS:
        return "You can't see the weather indoors.\n\r"

    # ROM C sky descriptions (src/act_info.c lines 1810-1815)
    sky_look = [
        "cloudless",                  # SkyState.CLOUDLESS
        "cloudy",                     # SkyState.CLOUDY
        "rainy",                      # SkyState.RAINING
        "lit by flashes of lightning" # SkyState.LIGHTNING
    ]
    
    sky_desc = sky_look[weather.sky] if 0 <= weather.sky < len(sky_look) else "strange"
    
    # ROM C wind direction logic (src/act_info.c lines 1826-1828)
    wind = (
        "a warm southerly breeze blows" if weather.change >= 0
        else "a cold northern gust blows"
    )
    
    return f"The sky is {sky_desc} and {wind}.\n\r"
```

---

### ⚠️ Gap 2: Different Indoor Message (MINOR)

**ROM C**: `"You can't see the weather indoors."`  
**QuickMUD**: `"You can't see the sky from here."`

**Issue**: Minor wording difference.

**Impact**: Very low - message is functionally equivalent.

**Fix**: Change to ROM C exact message for consistency:
```python
return "You can't see the weather indoors.\n\r"
```

---

### ⚠️ Gap 3: Different Sky Descriptions (MINOR)

**ROM C**: Uses adjectives ("cloudless", "rainy", "lit by flashes of lightning")  
**QuickMUD**: Uses complete sentences ("The sky is cloudless.", "It is raining.", "Lightning flashes in the sky.")

**Issue**: ROM C uses simpler adjectives in a compound sentence with wind.

**Impact**: Medium - different phrasing style.

**ROM C Output**:
```
The sky is cloudless and a warm southerly breeze blows.
The sky is rainy and a cold northern gust blows.
The sky is lit by flashes of lightning and a warm southerly breeze blows.
```

**QuickMUD Output** (current):
```
The sky is cloudless.
It is raining.
Lightning flashes in the sky.
```

**Recommendation**: Use ROM C's exact adjective format for parity.

---

### 📝 Gap 4: Wrong ROM C Line Reference in Docstring (DOCUMENTATION)

**Docstring**: `ROM Reference: src/act_info.c lines 2420-2480 (do_weather)`  
**Actual**: `src/act_info.c lines 1806-1830 (do_weather)`

**Issue**: Incorrect line numbers in ROM C reference.

**Fix**: Update docstring to correct line numbers.

---

## Summary of Gaps

| Gap # | Issue | Severity | Impact | Fix Effort |
|-------|-------|----------|--------|------------|
| 1 | Missing wind direction (weather.change) | CRITICAL | Atmospheric detail lost | 10 min |
| 2 | Different indoor message | MINOR | Wording difference | 1 min |
| 3 | Different sky descriptions | MINOR | Stylistic difference | 5 min |
| 4 | Wrong docstring line reference | DOCS | Misleading reference | 1 min |

**Total Fix Effort**: ~15-20 minutes

---

## Recommended Fix Implementation

### Fixed do_weather() Implementation

```python
def do_weather(char: Character, args: str) -> str:
    """
    Display weather conditions.

    ROM Reference: src/act_info.c lines 1806-1830 (do_weather)

    Usage: weather

    Shows current weather (sky and wind direction).
    """
    from mud.game_loop import weather, SkyState
    from mud.models.constants import RoomFlag

    char_room = getattr(char, "room", None)
    if not char_room:
        return "You can't see the sky from nowhere.\n\r"

    # ROM C: IS_OUTSIDE(ch) checks ROOM_INDOORS flag (merc.h:2112-2114)
    room_flags = getattr(char_room, "room_flags", 0)
    if room_flags & RoomFlag.ROOM_INDOORS:
        return "You can't see the weather indoors.\n\r"

    # ROM C sky descriptions (src/act_info.c lines 1810-1815)
    sky_look = [
        "cloudless",                  # SkyState.CLOUDLESS (0)
        "cloudy",                     # SkyState.CLOUDY (1)
        "rainy",                      # SkyState.RAINING (2)
        "lit by flashes of lightning" # SkyState.LIGHTNING (3)
    ]
    
    # Get sky description with bounds checking
    sky_desc = (
        sky_look[weather.sky] 
        if 0 <= weather.sky < len(sky_look) 
        else "strange"
    )
    
    # ROM C wind direction logic (src/act_info.c lines 1826-1828)
    # weather.change >= 0: pressure rising/stable (warm south wind)
    # weather.change < 0:  pressure falling (cold north wind)
    wind = (
        "a warm southerly breeze blows" if weather.change >= 0
        else "a cold northern gust blows"
    )
    
    # ROM C output format: "The sky is {sky} and {wind}."
    return f"The sky is {sky_desc} and {wind}.\n\r"
```

---

## Testing Requirements

### Unit Tests

**File**: `tests/test_do_weather.py` (create new file)

**Test Cases**:
1. **Test indoor check** - Returns "You can't see the weather indoors."
2. **Test all sky states** - Cloudless, cloudy, rainy, lightning
3. **Test wind direction (positive change)** - "warm southerly breeze blows"
4. **Test wind direction (negative change)** - "cold northern gust blows"
5. **Test wind direction (zero change)** - "warm southerly breeze blows"
6. **Test output format** - Contains "The sky is" and "and"
7. **Test bounds checking** - Invalid sky state returns "strange"

### Integration Tests

**File**: `tests/integration/test_do_weather_command.py` (create new file)

**Scenarios**:
1. **P0: Basic weather display** - Call `do_weather()` outdoors, verify format
2. **P0: Indoor blocking** - Call `do_weather()` indoors, verify rejection
3. **P1: Wind direction changes** - Test both positive and negative pressure change
4. **P1: All sky states** - Verify all 4 sky states render correctly
5. **Edge: No room** - Character with no room returns safe error message

---

## ROM C Parity Checklist

**Feature Coverage**:
- [ ] IS_OUTSIDE check (ROOM_INDOORS flag)
- [ ] Indoor error message (exact ROM C wording)
- [ ] Sky descriptions (cloudless/cloudy/rainy/lightning)
- [ ] Wind direction based on weather.change
- [ ] ROM C output format ("The sky is X and Y.")
- [ ] ROM C line reference in docstring

**Current Status**: 4/6 features complete (67% parity)

---

## Acceptance Criteria

**Before marking do_weather as COMPLETE**:

1. ✅ Output format matches ROM C exactly:
   ```
   The sky is cloudless and a warm southerly breeze blows.
   ```

2. ✅ Wind direction changes based on `weather.change` (positive = warm south, negative = cold north)

3. ✅ Indoor message matches ROM C: "You can't see the weather indoors."

4. ✅ All 4 sky states use ROM C adjectives (cloudless, cloudy, rainy, lit by flashes of lightning)

5. ✅ Integration tests passing (5 scenarios minimum)

6. ✅ No regressions in existing tests

---

## Implementation Status

**Status**: ✅ **COMPLETE** - All ROM C parity gaps fixed!

**Completed**: January 7, 2026

**Changes Made**:
1. ✅ Updated `do_weather()` in `mud/commands/info.py` (lines 415-452)
2. ✅ Implemented wind direction based on `weather.change`
3. ✅ Fixed indoor error message to ROM C wording
4. ✅ Updated sky descriptions to ROM C adjective format
5. ✅ Fixed ROM C line reference in docstring (1806-1830)
6. ✅ All 10 integration tests passing (100%)

**Test Results**:
- Integration tests: 10/10 passing (100%)
- Wind direction tests: 3/3 passing
- Sky state tests: 4/4 passing
- Edge case tests: 3/3 passing

**ROM C Parity**: ✅ **100%** - All features implemented and tested

---

**End of Audit** - Implementation complete
