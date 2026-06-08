# do_time() ROM C Parity Audit

**Command**: `time`  
**ROM C Source**: `src/act_info.c` lines 1771-1804 (34 lines)  
**QuickMUD Location**: `mud/commands/info.py` lines 314-365  
**Date Audited**: January 7, 2026  
**Audited By**: Sisyphus (AI Agent)

---

## Executive Summary

**Parity Status**: ⚠️ **~50% ROM C Parity** (5 critical gaps found)

**Assessment**: Command is functional but has significant output format differences and missing features:
- ❌ Wrong time format ("12 PM" vs "12 o'clock pm")
- ❌ Incorrect ordinal suffix logic (11th shows as "11st")
- ❌ Missing boot time and system time display
- ❌ Extra year field not in ROM C output
- ❌ Wrong AM/PM capitalization

**Recommendation**: **FIX - HIGH PRIORITY** (P1)  
- Players use this command frequently
- Output format is visibly wrong (uppercase AM/PM, no "o'clock")
- Ordinal suffix bug is embarrassing (11st, 12nd, 13rd)
- Fix effort: ~1 hour (straightforward string formatting)

---

## ROM C Source Analysis

### ROM C Implementation (lines 1771-1804)

```c
void do_time (CHAR_DATA * ch, char *argument)
{
    extern char str_boot_time[];
    char buf[MAX_STRING_LENGTH];
    char *suf;
    int day;

    day = time_info.day + 1;

    // Ordinal suffix logic
    if (day > 4 && day < 20)
        suf = "th";
    else if (day % 10 == 1)
        suf = "st";
    else if (day % 10 == 2)
        suf = "nd";
    else if (day % 10 == 3)
        suf = "rd";
    else
        suf = "th";

    sprintf (buf,
             "It is %d o'clock %s, Day of %s, %d%s the Month of %s.\n\r",
             (time_info.hour % 12 == 0) ? 12 : time_info.hour % 12,
             time_info.hour >= 12 ? "pm" : "am",
             day_name[day % 7], day, suf, month_name[time_info.month]);
    send_to_char (buf, ch);
    sprintf (buf, "ROM started up at %s\n\rThe system time is %s.\n\r",
             str_boot_time, (char *) ctime (&current_time));

    send_to_char (buf, ch);
    return;
}
```

### ROM C Constants (lines 1759-1769)

```c
char *const day_name[] = {
    "the Moon", "the Bull", "Deception", "Thunder", "Freedom",
    "the Great Gods", "the Sun"
};

char *const month_name[] = {
    "Winter", "the Winter Wolf", "the Frost Giant", "the Old Forces",
    "the Grand Struggle", "the Spring", "Nature", "Futility", "the Dragon",
    "the Sun", "the Heat", "the Battle", "the Dark Shades", "the Shadows",
    "the Long Shadows", "the Ancient Darkness", "the Great Evil"
};
```

### ROM C Behavior Summary

**Output Format** (2 lines):
```
It is 3 o'clock pm, Day of the Moon, 15th the Month of Winter.
ROM started up at Mon Dec 30 14:22:15 2025
The system time is Tue Jan  7 00:45:32 2026.
```

**Key Features**:
1. **Time format**: `"{hour} o'clock {am/pm}"` (lowercase am/pm)
2. **12-hour conversion**: `hour % 12 == 0 ? 12 : hour % 12`
3. **Ordinal suffix**: Special logic for 11-13 (always "th"), then check last digit
4. **Day names**: 7 day cycle (the Moon, the Bull, Deception, Thunder, Freedom, the Great Gods, the Sun)
5. **Month names**: 17 month names (Winter through the Great Evil)
6. **Boot time**: Shows when server started (str_boot_time)
7. **System time**: Shows real-world current time (ctime(&current_time))
8. **No year**: Year is NOT displayed in ROM C output

---

## QuickMUD Implementation Analysis

### QuickMUD Implementation (lines 314-365)

```python
def do_time(char: Character, args: str) -> str:
    """
    Display game time.

    ROM Reference: src/act_info.c lines 2350-2400 (do_time)  # ⚠️ WRONG LINE NUMBERS

    Usage: time

    Shows the current game time and date.
    """
    from mud.time import time_info

    # ROM month names
    month_names = [
        "Winter",
        "the Winter Wolf",
        "the Frost Giant",
        "the Old Forces",
        "the Grand Struggle",
        "the Spring",
        "Nature",
        "Futility",
        "the Dragon",
        "the Sun",
        "the Heat",
        "the Battle",
        "the Dark Shades",
        "the Shadows",
        "the Long Shadows",
        "the Ancient Darkness",
        "the Great Evil",
    ]

    # Get time info
    hour = time_info.hour
    day = time_info.day + 1  # ROM days are 1-based for display
    month = time_info.month
    year = time_info.year

    # Convert hour to 12-hour format
    if hour == 0:
        time_str = "12 AM"
    elif hour < 12:
        time_str = f"{hour} AM"
    elif hour == 12:
        time_str = "12 PM"
    else:
        time_str = f"{hour - 12} PM"

    month_name = month_names[month] if 0 <= month < len(month_names) else "Unknown"

    return f"It is {time_str}, Day of the {['Moon', 'Bull', 'Deception', 'Thunder', 'Freedom', 'Great Gods', 'Sun'][day % 7]}, {day}{['th', 'st', 'nd', 'rd', 'th'][min(day % 10, 4)]} the Month of {month_name}, {year} A.D."
```

### QuickMUD Output Example

```
It is 3 PM, Day of the Moon, 15th the Month of Winter, 1234 A.D.
```

---

## Gap Analysis

### ❌ Gap 1: Wrong Time Format (CRITICAL)

**ROM C**: `"3 o'clock pm"`  
**QuickMUD**: `"3 PM"`

**Issue**: Missing "o'clock" and wrong capitalization.

**Fix**:
```python
# ROM C: (time_info.hour % 12 == 0) ? 12 : time_info.hour % 12
display_hour = 12 if hour % 12 == 0 else hour % 12
am_pm = "pm" if hour >= 12 else "am"
time_str = f"{display_hour} o'clock {am_pm}"
```

---

### ❌ Gap 2: Incorrect Ordinal Suffix Logic (CRITICAL BUG)

**ROM C Logic**:
```c
if (day > 4 && day < 20)
    suf = "th";          // 5-19 always use "th" (catches 11, 12, 13)
else if (day % 10 == 1)
    suf = "st";          // 1, 21, 31
else if (day % 10 == 2)
    suf = "nd";          // 2, 22, 32
else if (day % 10 == 3)
    suf = "rd";          // 3, 23, 33
else
    suf = "th";          // Everything else
```

**QuickMUD Logic**:
```python
day_suffix = ['th', 'st', 'nd', 'rd', 'th'][min(day % 10, 4)]
```

**Bug Examples**:
| Day | ROM C | QuickMUD | Correct? |
|-----|-------|----------|----------|
| 11  | 11th  | 11st     | ❌ WRONG |
| 12  | 12th  | 12nd     | ❌ WRONG |
| 13  | 13th  | 13rd     | ❌ WRONG |
| 14  | 14th  | 14th     | ✅       |
| 21  | 21st  | 21st     | ✅       |
| 22  | 22nd  | 22nd     | ✅       |

**Issue**: QuickMUD's `min(day % 10, 4)` doesn't handle the 11-13 special case.

**Fix**:
```python
# ROM C ordinal suffix logic (exact port)
if 5 <= day <= 19:
    suffix = "th"
elif day % 10 == 1:
    suffix = "st"
elif day % 10 == 2:
    suffix = "nd"
elif day % 10 == 3:
    suffix = "rd"
else:
    suffix = "th"
```

---

### ❌ Gap 3: Missing Boot Time Display (IMPORTANT)

**ROM C**:
```c
sprintf (buf, "ROM started up at %s\n\rThe system time is %s.\n\r",
         str_boot_time, (char *) ctime (&current_time));
send_to_char (buf, ch);
```

**QuickMUD**: Missing entirely.

**Issue**: ROM C shows two additional lines:
- When the MUD server started (boot time)
- Current real-world system time

**Impact**: Players can't see server uptime or correlate game time to real time.

**Fix Approach**:
1. Add `server_boot_time` to `mud/game_loop.py` or `mud/time.py`
2. Set on server startup (e.g., `datetime.now().strftime("%c")`)
3. Display in do_time output

**Example Implementation**:
```python
import time as time_module
from datetime import datetime

# In mud/game_loop.py or mud/time.py
server_boot_time = datetime.now().strftime("%c")  # Set once on server start

# In do_time()
lines = []
lines.append(f"It is {time_str}, Day of {day_name}, {day}{suffix} the Month of {month_name}.")
lines.append(f"ROM started up at {server_boot_time}")
lines.append(f"The system time is {time_module.ctime(time_module.time())}.")
return "\n\r".join(lines) + "\n\r"
```

---

### ❌ Gap 4: Extra Year Field Not in ROM C (MINOR)

**ROM C**: No year in output  
**QuickMUD**: `", {year} A.D."`

**Issue**: QuickMUD adds a year field that ROM C doesn't display.

**Impact**: Minor formatting difference.

**Fix**: Remove `, {year} A.D.` from output string.

---

### ❌ Gap 5: Wrong Day Name Format (MINOR)

**ROM C day_name[]**:
```c
"the Moon", "the Bull", "Deception", "Thunder", "Freedom",
"the Great Gods", "the Sun"
```

**QuickMUD inline array**:
```python
['Moon', 'Bull', 'Deception', 'Thunder', 'Freedom', 'Great Gods', 'Sun']
```

**Issue**: QuickMUD is missing "the" prefix for "Moon", "Bull", "Great Gods", and "Sun".

**Impact**: Output says "Day of the Moon" vs "Day of Moon" (wait, ROM C uses "Day of %s" so it would be "Day of the Moon" in ROM too - QuickMUD is missing "the" in array).

**Wait, let me re-check**: ROM C format string is `"Day of %s"` and day_name has `"the Moon"`, so output is `"Day of the Moon"`. QuickMUD uses `f"Day of the {day_name}"` with `"Moon"`, so output is `"Day of the Moon"`. Actually QuickMUD's "the" is in the format string, not the array.

**Verdict**: Actually CORRECT - QuickMUD adds "the" in format string, ROM C includes it in array. Net result is the same.

**Update**: Actually, ROM C day_name[1] = "the Bull", but ROM format is "Day of %s" so output is "Day of the Bull". QuickMUD has "Bull" but adds "the" in f-string, so "Day of the Bull". So output matches!

**Correction**: This is NOT a gap - different implementation but same output.

---

### ❌ Gap 6: Wrong ROM C Line Reference in Docstring (DOCUMENTATION)

**Docstring**: `ROM Reference: src/act_info.c lines 2350-2400 (do_time)`  
**Actual**: `src/act_info.c lines 1771-1804 (do_time)`

**Issue**: Incorrect line numbers in ROM C reference.

**Fix**: Update docstring to correct line numbers.

---

## Summary of Gaps

| Gap # | Issue | Severity | Impact | Fix Effort |
|-------|-------|----------|--------|------------|
| 1 | Missing "o'clock" and wrong AM/PM case | CRITICAL | Very visible, non-ROM output | 5 min |
| 2 | Ordinal suffix bug (11st, 12nd, 13rd) | CRITICAL | Embarrassing bug, wrong grammar | 10 min |
| 3 | Missing boot time and system time | IMPORTANT | Can't see server uptime | 30 min |
| 4 | Extra year field | MINOR | Non-ROM output format | 2 min |
| 5 | ~~Wrong day name format~~ | N/A | Actually correct | N/A |
| 6 | Wrong docstring line reference | DOCS | Misleading reference | 1 min |

**Total Fix Effort**: ~50 minutes

---

## Recommended Fix Implementation

### Fixed do_time() Implementation

```python
def do_time(char: Character, args: str) -> str:
    """
    Display game time.

    ROM Reference: src/act_info.c lines 1771-1804 (do_time)

    Usage: time

    Shows the current game time, boot time, and system time.
    """
    import time as time_module
    from mud.time import time_info, server_boot_time  # Add server_boot_time

    # ROM day names (src/act_info.c lines 1759-1762)
    day_names = [
        "the Moon", "the Bull", "Deception", "Thunder", "Freedom",
        "the Great Gods", "the Sun"
    ]

    # ROM month names (src/act_info.c lines 1764-1769)
    month_names = [
        "Winter", "the Winter Wolf", "the Frost Giant", "the Old Forces",
        "the Grand Struggle", "the Spring", "Nature", "Futility", "the Dragon",
        "the Sun", "the Heat", "the Battle", "the Dark Shades", "the Shadows",
        "the Long Shadows", "the Ancient Darkness", "the Great Evil",
    ]

    # Get time info
    hour = time_info.hour
    day = time_info.day + 1  # ROM days are 1-based for display
    month = time_info.month

    # Convert hour to 12-hour format (ROM C: hour % 12 == 0 ? 12 : hour % 12)
    display_hour = 12 if hour % 12 == 0 else hour % 12
    am_pm = "pm" if hour >= 12 else "am"

    # ROM C ordinal suffix logic (src/act_info.c lines 1780-1789)
    if 5 <= day <= 19:
        suffix = "th"
    elif day % 10 == 1:
        suffix = "st"
    elif day % 10 == 2:
        suffix = "nd"
    elif day % 10 == 3:
        suffix = "rd"
    else:
        suffix = "th"

    # Get day and month names with bounds checking
    day_name = day_names[day % 7] if day % 7 < len(day_names) else "Unknown"
    month_name = month_names[month] if 0 <= month < len(month_names) else "Unknown"

    # Build ROM C output format (src/act_info.c lines 1791-1799)
    lines = []
    lines.append(
        f"It is {display_hour} o'clock {am_pm}, Day of {day_name}, "
        f"{day}{suffix} the Month of {month_name}."
    )
    lines.append(f"ROM started up at {server_boot_time}")
    lines.append(f"The system time is {time_module.ctime(time_module.time())}.")

    return "\n\r".join(lines) + "\n\r"
```

### Required Changes to mud/time.py

```python
from datetime import datetime

# Add server boot time tracking (set once on import)
server_boot_time = datetime.now().strftime("%c")  # e.g., "Mon Dec 30 14:22:15 2025"
```

---

## Testing Requirements

### Unit Tests

**File**: `tests/test_do_time.py` (create new file)

**Test Cases**:
1. **Test ordinal suffixes** (1st, 2nd, 3rd, 4th, 11th, 12th, 13th, 21st, 22nd, 31st)
2. **Test 12-hour conversion** (0h → 12 am, 12h → 12 pm, 13h → 1 pm)
3. **Test day name cycling** (day 0-6 map to 7 day names)
4. **Test month name cycling** (month 0-16 map to 17 month names)
5. **Test output format** (has "o'clock", lowercase "am/pm", newline format)
6. **Test boot time presence** (output contains "ROM started up at")
7. **Test system time presence** (output contains "The system time is")

### Integration Tests

**File**: `tests/integration/test_do_time_command.py` (create new file)

**Scenarios**:
1. **P0: Basic time display** - Call `do_time()` and verify output format
2. **P0: Ordinal suffix correctness** - Test days 11, 12, 13 specifically
3. **P1: Boot time display** - Verify server uptime is shown
4. **P1: System time display** - Verify real-world time is shown
5. **Edge: Midnight** - Test hour = 0 shows "12 o'clock am"
6. **Edge: Noon** - Test hour = 12 shows "12 o'clock pm"

---

## ROM C Parity Checklist

**Feature Coverage**:
- [ ] 12-hour time format with "o'clock"
- [ ] Lowercase "am/pm" (not "AM/PM")
- [ ] Correct ordinal suffix logic (handles 11-13)
- [ ] Day name cycling (7 day names)
- [ ] Month name cycling (17 month names)
- [ ] Boot time display ("ROM started up at...")
- [ ] System time display ("The system time is...")
- [ ] No year field in output
- [ ] ROM C line reference in docstring

**Current Status**: 2/9 features complete (22% parity)

---

## Acceptance Criteria

**Before marking do_time as COMPLETE**:

1. ✅ Output format matches ROM C exactly:
   ```
   It is 3 o'clock pm, Day of the Moon, 15th the Month of Winter.
   ROM started up at Mon Dec 30 14:22:15 2025
   The system time is Tue Jan  7 00:45:32 2026.
   ```

2. ✅ Ordinal suffix logic passes all test cases (1st, 11th, 21st, etc.)

3. ✅ Boot time and system time are displayed

4. ✅ Integration tests passing (6 scenarios minimum)

5. ✅ No regressions in existing tests

---

## Implementation Status

**Status**: ⏳ **NOT STARTED** - Gaps documented, fix ready to implement

**Next Steps**:
1. Add `server_boot_time` to `mud/time.py`
2. Rewrite `do_time()` in `mud/commands/info.py` using fixed implementation above
3. Create unit tests in `tests/test_do_time.py`
4. Create integration tests in `tests/integration/test_do_time_command.py`
5. Run tests and verify all pass
6. Update `ACT_INFO_C_AUDIT.md` to mark do_time as complete

**Estimated Time**: 1 hour total (30 min implementation + 30 min tests)

---

**End of Audit** - Ready for implementation
