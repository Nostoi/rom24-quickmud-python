# do_who Comprehensive Audit

**ROM C Location**: `src/act_info.c` lines 2016-2226 (211 lines)  
**QuickMUD Location**: `mud/commands/info.py` lines 77-115 (39 lines)  
**Audit Date**: January 6, 2026  
**Status**: 🚨 **CRITICAL GAPS IDENTIFIED** - ~90% ROM functionality missing

---

## Summary

**Current Implementation**: ⚠️ **10% ROM C parity** - Basic player listing only  
**Gaps Identified**: 11 major features missing  
**Priority**: **P0 CRITICAL** - This is the most-used information command  
**Estimated Fix Time**: 3-4 hours (complete rewrite required)

---

## ROM C Features vs QuickMUD Implementation

### 1. Argument Parsing ❌ **MISSING ENTIRELY**

**ROM C** (lines 2037-2128):
```c
// Supports multiple argument types:
// - Level range: "who 10 20" (players level 10-20)
// - Class filter: "who warrior" (only warriors)
// - Race filter: "who elf" (only elves)
// - Clan filter: "who mystara" (only clan members)
// - Immortals: "who immortals" (only immortals)
```

**QuickMUD**: No argument parsing at all (args parameter ignored)

**Impact**: Players cannot filter WHO list by level, class, race, or clan  
**Fix Required**: Full argument parser with class_lookup, race_lookup, clan_lookup  
**Estimated Time**: 1 hour

---

### 2. Level Range Filtering ❌ **MISSING**

**ROM C** (lines 2048-2057, 2156-2157):
```c
if (is_number(arg)) {
    switch (++nNumber) {
        case 1: iLevelLower = atoi(arg); break;
        case 2: iLevelUpper = atoi(arg); break;
    }
}
// Later in filtering:
if (wch->level < iLevelLower || wch->level > iLevelUpper)
    continue;
```

**QuickMUD**: Shows all levels (no filtering)

**Impact**: Cannot do "who 40 50" to see high-level players  
**Fix Required**: Parse numeric arguments, filter by level range  
**Estimated Time**: 15 minutes

---

### 3. Class Filtering ❌ **MISSING**

**ROM C** (lines 2075-2079, 2159):
```c
iClass = class_lookup(arg);
if (iClass != -1) {
    fClassRestrict = TRUE;
    rgfClass[iClass] = TRUE;
}
// Later: if (fClassRestrict && !rgfClass[wch->class]) continue;
```

**QuickMUD**: No class filtering

**Impact**: Cannot do "who warrior" or "who mage"  
**Fix Required**: Implement class_lookup, maintain class filter bitmask  
**Estimated Time**: 20 minutes

---

### 4. Race Filtering ❌ **MISSING**

**ROM C** (lines 2081-2092, 2160):
```c
iRace = race_lookup(arg);
if (iRace == 0 || iRace >= MAX_PC_RACE) {
    // Try clan lookup
} else {
    fRaceRestrict = TRUE;
    rgfRace[iRace] = TRUE;
}
// Later: if (fRaceRestrict && !rgfRace[wch->race]) continue;
```

**QuickMUD**: No race filtering

**Impact**: Cannot do "who human" or "who elf"  
**Fix Required**: Implement race_lookup, maintain race filter bitmask  
**Estimated Time**: 20 minutes

---

### 5. Clan Filtering ❌ **MISSING**

**ROM C** (lines 2100-2106, 2161-2162):
```c
iClan = clan_lookup(arg);
if (iClan) {
    fClanRestrict = TRUE;
    rgfClan[iClan] = TRUE;
}
// Later: if (fClan && !is_clan(wch)) continue;
// Later: if (fClanRestrict && !rgfClan[wch->clan]) continue;
```

**QuickMUD**: No clan system at all

**Impact**: Cannot filter by clan membership  
**Fix Required**: Implement clan_lookup (if clans exist), or stub for now  
**Estimated Time**: 10 minutes (stub) or 1+ hour (full clan system)  
**Priority**: P2 (clans are optional ROM feature)

---

### 6. Immortals-Only Filter ❌ **MISSING**

**ROM C** (lines 2069-2071, 2158):
```c
if (!str_prefix(arg, "immortals")) {
    fImmortalOnly = TRUE;
}
// Later: if (fImmortalOnly && wch->level < LEVEL_IMMORTAL) continue;
```

**QuickMUD**: Shows all players regardless of level

**Impact**: Cannot do "who immortals" to see online staff  
**Fix Required**: Parse "immortals" keyword, filter by LEVEL_IMMORTAL  
**Estimated Time**: 10 minutes

---

### 7. Immortal Rank Display ❌ **MISSING**

**ROM C** (lines 2168-2195):
```c
class = class_table[wch->class].who_name;
switch (wch->level) {
    case MAX_LEVEL - 0: class = "IMP"; break;  // Level 60
    case MAX_LEVEL - 1: class = "CRE"; break;  // Level 59
    case MAX_LEVEL - 2: class = "SUP"; break;  // Level 58
    case MAX_LEVEL - 3: class = "DEI"; break;  // Level 57
    case MAX_LEVEL - 4: class = "GOD"; break;  // Level 56
    case MAX_LEVEL - 5: class = "IMM"; break;  // Level 55
    case MAX_LEVEL - 6: class = "DEM"; break;  // Level 54
    case MAX_LEVEL - 7: class = "ANG"; break;  // Level 53
    case MAX_LEVEL - 8: class = "AVA"; break;  // Level 52
}
```

**QuickMUD**: No immortal rank display

**Impact**: Immortals show as regular classes (confusing)  
**Fix Required**: Implement immortal rank lookup based on level  
**Estimated Time**: 15 minutes

---

### 8. Race WHO Name Display ❌ **MISSING**

**ROM C** (line 2204):
```c
wch->race < MAX_PC_RACE ? pc_race_table[wch->race].who_name : "     "
```

**QuickMUD**: No race display in WHO list

**Impact**: Players cannot see other players' races  
**Fix Required**: Look up race WHO name from race table  
**Estimated Time**: 10 minutes

---

### 9. Class WHO Name Display ❌ **MISSING**

**ROM C** (line 2200):
```c
class = class_table[wch->class].who_name;
```

**QuickMUD**: No class display in WHO list

**Impact**: Players cannot see other players' classes  
**Fix Required**: Look up class WHO name from class table  
**Estimated Time**: 10 minutes

---

### 10. Status Flags Display ❌ **MISSING**

**ROM C** (lines 2206-2210):
```c
sprintf(buf, "[%2d %6s %s] %s%s%s%s%s%s%s%s\n\r",
    wch->level,
    race_who_name,
    class_who_name,
    wch->incog_level >= LEVEL_HERO ? "(Incog) " : "",
    wch->invis_level >= LEVEL_HERO ? "(Wizi) " : "",
    clan_table[wch->clan].who_name,
    IS_SET(wch->comm, COMM_AFK) ? "[AFK] " : "",
    IS_SET(wch->act, PLR_KILLER) ? "(KILLER) " : "",
    IS_SET(wch->act, PLR_THIEF) ? "(THIEF) " : "",
    wch->name,
    wch->pcdata->title);
```

**QuickMUD**: No status flags shown

**Missing Flags**:
- (Incog) - Incognito immortal
- (Wizi) - Wizard invisible
- [Clan tag] - Clan affiliation
- [AFK] - Away from keyboard
- (KILLER) - Player killer flag
- (THIEF) - Thief flag

**Impact**: Players have no idea about other players' status  
**Fix Required**: Check all flags and build prefix string  
**Estimated Time**: 20 minutes

---

### 11. Proper Output Formatting ❌ **WRONG FORMAT**

**ROM C Format**:
```
[Lv Race   Class] (Flags) ClanTag [AFK] (KILLER) (THIEF) Name Title
```

**Example**:
```
[50 Human  War  ] Gandalf the Grey Wizard
[52 Elf    Mag  ] (Wizi) Elrond the Wise
[60 Drow   IMP  ] <Mystara> [AFK] Lloth the Spider Queen
```

**QuickMUD Current Format**:
```
[Lv] Name Title
```

**Example**:
```
[50] Gandalf the Grey Wizard
[52] Elrond the Wise
[60] Lloth the Spider Queen
```

**Impact**: WHO list is much less informative than ROM  
**Fix Required**: Complete format rewrite  
**Estimated Time**: 30 minutes

---

## Gap Summary

| Category | Gaps | Priority | Estimated Fix Time |
|----------|------|----------|-------------------|
| Argument Parsing | 1 | P0 | 1 hour |
| Level Filtering | 1 | P0 | 15 mins |
| Class Filtering | 1 | P0 | 20 mins |
| Race Filtering | 1 | P0 | 20 mins |
| Clan Filtering | 1 | P2 | 10 mins (stub) |
| Immortals Filter | 1 | P1 | 10 mins |
| Immortal Ranks | 1 | P0 | 15 mins |
| Race WHO Name | 1 | P0 | 10 mins |
| Class WHO Name | 1 | P0 | 10 mins |
| Status Flags | 1 | P1 | 20 mins |
| Output Format | 1 | P0 | 30 mins |

**Total P0 Gaps**: 7  
**Total P1 Gaps**: 2  
**Total P2 Gaps**: 2  
**Total Fix Time**: 3-4 hours

---

## Recommended Approach

### Phase 1: Argument Parsing (1 hour)
1. Parse level range (two numeric arguments)
2. Parse class filter (class_lookup)
3. Parse race filter (race_lookup)
4. Parse "immortals" keyword
5. Parse clan filter (stub for now)

### Phase 2: Display Logic (1.5 hours)
1. Implement immortal rank lookup
2. Implement race WHO name lookup
3. Implement class WHO name lookup
4. Implement status flags (Incog, Wizi, AFK, KILLER, THIEF)
5. Implement clan WHO name (stub)

### Phase 3: Output Formatting (30 mins)
1. Rewrite format string to match ROM C
2. Add proper spacing/alignment
3. Test with various character types

### Phase 4: Integration & Testing (1 hour)
1. Test all argument combinations
2. Test with immortals, mortals, AFK players
3. Test edge cases (no players, all filtered out)
4. Create integration tests

---

## Priority Decision

**Question**: Should we fix do_who now (3-4 hours) or move to do_help (simpler)?

**Recommendation**: **Fix do_who first** because:
1. It's the most frequently used command (players use "who" constantly)
2. Current implementation is embarrassingly incomplete (10% ROM parity)
3. It's a P0 command (critical functionality)
4. The gaps are straightforward to fix (no complex logic)

**Alternative**: If time is limited, fix P0 gaps only (2 hours) and defer P1/P2 to later.

---

## Next Steps

1. ✅ Complete this audit
2. **Decision needed**: Fix do_who now or move to do_help?
3. If fixing do_who: Implement Phase 1-4 above
4. Update ACT_INFO_C_AUDIT.md with findings
5. Create session summary when complete

---

**Audit Complete - Awaiting Decision on Next Steps**
