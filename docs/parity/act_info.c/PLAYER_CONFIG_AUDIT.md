# act_info.c Player Config Commands - ROM C Parity Audit

**Audit Date**: January 7, 2026  
**ROM C Source**: `src/act_info.c` lines 972-1035  
**QuickMUD Source**: `mud/commands/player_config.py` lines 17-92  
**Auditor**: AI Agent (Batch 2 of 6)

---

## Executive Summary

**Status**: ✅ **EXCELLENT ROM C PARITY** (3/3 commands complete)

**Commands Audited**: 3 player configuration commands  
**Gaps Found**: 0 critical, 0 minor  
**Integration Tests**: 9/9 passing (100%)

This audit verifies QuickMUD's player configuration commands (`do_noloot`, `do_nofollow`, `do_nosummon`) against the ROM 2.4b6 C source implementation. All three commands demonstrate **excellent ROM C parity** with proper flag operations, messages, and special behaviors (nofollow stops followers, nosummon handles NPCs).

---

## Commands Audited

### 1. do_noloot() - Toggle Corpse Looting Permission

**ROM C Source**: `src/act_info.c` lines 972-987 (16 lines)  
**QuickMUD Source**: `mud/commands/player_config.py` lines 17-35 (19 lines)  
**Status**: ✅ **100% ROM C Parity**

#### ROM C Implementation
```c
void do_noloot (CHAR_DATA * ch, char *argument)
{
    if (IS_NPC (ch))
        return;

    if (IS_SET (ch->act, PLR_CANLOOT))
    {
        send_to_char ("Your corpse is now safe from thieves.\n\r", ch);
        REMOVE_BIT (ch->act, PLR_CANLOOT);
    }
    else
    {
        send_to_char ("Your corpse may now be looted.\n\r", ch);
        SET_BIT (ch->act, PLR_CANLOOT);
    }
}
```

#### QuickMUD Implementation
```python
def do_noloot(char: Character, args: str) -> str:
    """
    Toggle whether others can loot your corpse.
    
    ROM Reference: src/act_info.c do_noloot (lines 972-986)
    
    Usage: noloot
    """
    if getattr(char, "is_npc", False):
        return ""
    
    act_flags = getattr(char, "act", 0)
    
    if act_flags & PLR_CANLOOT:
        char.act = act_flags & ~PLR_CANLOOT
        return "Your corpse is now safe from thieves."
    else:
        char.act = act_flags | PLR_CANLOOT
        return "Your corpse may now be looted."
```

#### Parity Analysis

| Aspect | ROM C | QuickMUD | Match? |
|--------|-------|----------|--------|
| **NPC Check** | `IS_NPC(ch)` returns | `is_npc` check returns `""` | ✅ YES |
| **Flag Check** | `IS_SET(ch->act, PLR_CANLOOT)` | `act_flags & PLR_CANLOOT` | ✅ YES |
| **Toggle OFF** | `REMOVE_BIT(ch->act, PLR_CANLOOT)` | `act_flags & ~PLR_CANLOOT` | ✅ YES |
| **Toggle ON** | `SET_BIT(ch->act, PLR_CANLOOT)` | `act_flags | PLR_CANLOOT` | ✅ YES |
| **Message (OFF)** | "Your corpse is now safe from thieves.\n\r" | "Your corpse is now safe from thieves." | ✅ YES* |
| **Message (ON)** | "Your corpse may now be looted.\n\r" | "Your corpse may now be looted." | ✅ YES* |

*Messages match (newline formatting handled by output layer)

**Flag Definition Verification**:
```python
# ROM C (merc.h): #define PLR_CANLOOT (P)
# QuickMUD (constants.py:414): CANLOOT = 1 << 15  # (P) = 0x00008000
# QuickMUD (player_config.py:12): PLR_CANLOOT = 0x00008000
```
✅ Flag bit matches ROM C exactly (bit 15 = 0x8000)

**Gaps**: None

---

### 2. do_nofollow() - Toggle Follower Permission

**ROM C Source**: `src/act_info.c` lines 989-1005 (17 lines)  
**QuickMUD Source**: `mud/commands/player_config.py` lines 38-60 (23 lines)  
**Status**: ✅ **100% ROM C Parity**

#### ROM C Implementation
```c
void do_nofollow (CHAR_DATA * ch, char *argument)
{
    if (IS_NPC (ch))
        return;

    if (IS_SET (ch->act, PLR_NOFOLLOW))
    {
        send_to_char ("You now accept followers.\n\r", ch);
        REMOVE_BIT (ch->act, PLR_NOFOLLOW);
    }
    else
    {
        send_to_char ("You no longer accept followers.\n\r", ch);
        SET_BIT (ch->act, PLR_NOFOLLOW);
        die_follower (ch);
    }
}
```

#### QuickMUD Implementation
```python
def do_nofollow(char: Character, args: str) -> str:
    """
    Toggle whether others can follow you.
    
    ROM Reference: src/act_info.c do_nofollow (lines 989-1004)
    
    Usage: nofollow
    
    Note: Enabling nofollow also stops all current followers.
    """
    if getattr(char, "is_npc", False):
        return ""
    
    act_flags = getattr(char, "act", 0)
    
    if act_flags & PLR_NOFOLLOW:
        char.act = act_flags & ~PLR_NOFOLLOW
        return "You now accept followers."
    else:
        char.act = act_flags | PLR_NOFOLLOW
        # Stop all followers
        _die_follower(char)
        return "You no longer accept followers."
```

#### Parity Analysis

| Aspect | ROM C | QuickMUD | Match? |
|--------|-------|----------|--------|
| **NPC Check** | `IS_NPC(ch)` returns | `is_npc` check returns `""` | ✅ YES |
| **Flag Check** | `IS_SET(ch->act, PLR_NOFOLLOW)` | `act_flags & PLR_NOFOLLOW` | ✅ YES |
| **Toggle OFF** | `REMOVE_BIT(ch->act, PLR_NOFOLLOW)` | `act_flags & ~PLR_NOFOLLOW` | ✅ YES |
| **Toggle ON** | `SET_BIT(ch->act, PLR_NOFOLLOW)` | `act_flags | PLR_NOFOLLOW` | ✅ YES |
| **Stop Followers** | `die_follower(ch)` | `_die_follower(char)` | ✅ YES |
| **Message (OFF)** | "You now accept followers.\n\r" | "You now accept followers." | ✅ YES* |
| **Message (ON)** | "You no longer accept followers.\n\r" | "You no longer accept followers." | ✅ YES* |

*Messages match (newline formatting handled by output layer)

**Flag Definition Verification**:
```python
# ROM C (merc.h): #define PLR_NOFOLLOW (R)
# QuickMUD (constants.py:416): NOFOLLOW = 1 << 17  # (R) = 0x00020000
# QuickMUD (player_config.py:14): PLR_NOFOLLOW = 0x00020000
```
✅ Flag bit matches ROM C exactly (bit 17 = 0x20000)

**Helper Function Verification**:
- QuickMUD implements `_die_follower()` at lines 171-192
- Calls `_stop_follower()` for each follower (lines 195-216)
- Removes `AffectFlag.CHARM` and clears `master`/`leader` fields
- Matches ROM C `die_follower()` and `stop_follower()` behavior

**Gaps**: None

---

### 3. do_nosummon() - Toggle Summon Immunity

**ROM C Source**: `src/act_info.c` lines 1007-1035 (29 lines)  
**QuickMUD Source**: `mud/commands/player_config.py` lines 63-92 (30 lines)  
**Status**: ✅ **100% ROM C Parity**

#### ROM C Implementation
```c
void do_nosummon (CHAR_DATA * ch, char *argument)
{
    if (IS_NPC (ch))
    {
        if (IS_SET (ch->imm_flags, IMM_SUMMON))
        {
            send_to_char ("You are no longer immune to summon.\n\r", ch);
            REMOVE_BIT (ch->imm_flags, IMM_SUMMON);
        }
        else
        {
            send_to_char ("You are now immune to summoning.\n\r", ch);
            SET_BIT (ch->imm_flags, IMM_SUMMON);
        }
    }
    else
    {
        if (IS_SET (ch->act, PLR_NOSUMMON))
        {
            send_to_char ("You are no longer immune to summon.\n\r", ch);
            REMOVE_BIT (ch->act, PLR_NOSUMMON);
        }
        else
        {
            send_to_char ("You are now immune to summoning.\n\r", ch);
            SET_BIT (ch->act, PLR_NOSUMMON);
        }
    }
}
```

#### QuickMUD Implementation
```python
def do_nosummon(char: Character, args: str) -> str:
    """
    Toggle whether you can be summoned.
    
    ROM Reference: src/act_info.c do_nosummon (lines 1007-1030)
    
    Usage: nosummon
    """
    is_npc = getattr(char, "is_npc", False)
    
    if is_npc:
        # NPCs use imm_flags
        imm_flags = getattr(char, "imm_flags", 0)
        IMM_SUMMON = 0x00000010
        
        if imm_flags & IMM_SUMMON:
            char.imm_flags = imm_flags & ~IMM_SUMMON
            return "You are no longer immune to summon."
        else:
            char.imm_flags = imm_flags | IMM_SUMMON
            return "You are now immune to summoning."
    else:
        act_flags = getattr(char, "act", 0)
        
        if act_flags & PLR_NOSUMMON:
            char.act = act_flags & ~PLR_NOSUMMON
            return "You are no longer immune to summon."
        else:
            char.act = act_flags | PLR_NOSUMMON
            return "You are now immune to summoning."
```

#### Parity Analysis

| Aspect | ROM C | QuickMUD | Match? |
|--------|-------|----------|--------|
| **NPC Check** | `IS_NPC(ch)` branches | `is_npc` check branches | ✅ YES |
| **NPC Flag Check** | `IS_SET(ch->imm_flags, IMM_SUMMON)` | `imm_flags & IMM_SUMMON` | ✅ YES |
| **NPC Toggle OFF** | `REMOVE_BIT(ch->imm_flags, IMM_SUMMON)` | `imm_flags & ~IMM_SUMMON` | ✅ YES |
| **NPC Toggle ON** | `SET_BIT(ch->imm_flags, IMM_SUMMON)` | `imm_flags | IMM_SUMMON` | ✅ YES |
| **PC Flag Check** | `IS_SET(ch->act, PLR_NOSUMMON)` | `act_flags & PLR_NOSUMMON` | ✅ YES |
| **PC Toggle OFF** | `REMOVE_BIT(ch->act, PLR_NOSUMMON)` | `act_flags & ~PLR_NOSUMMON` | ✅ YES |
| **PC Toggle ON** | `SET_BIT(ch->act, PLR_NOSUMMON)` | `act_flags | PLR_NOSUMMON` | ✅ YES |
| **NPC Message (OFF)** | "You are no longer immune to summon.\n\r" | "You are no longer immune to summon." | ✅ YES* |
| **NPC Message (ON)** | "You are now immune to summoning.\n\r" | "You are now immune to summoning." | ✅ YES* |
| **PC Message (OFF)** | "You are no longer immune to summon.\n\r" | "You are no longer immune to summon." | ✅ YES* |
| **PC Message (ON)** | "You are now immune to summoning.\n\r" | "You are now immune to summoning." | ✅ YES* |

*Messages match (newline formatting handled by output layer)

**Flag Definition Verification**:
```python
# ROM C (merc.h): #define PLR_NOSUMMON (Q)
# QuickMUD (constants.py:415): NOSUMMON = 1 << 16  # (Q) = 0x00010000
# QuickMUD (player_config.py:13): PLR_NOSUMMON = 0x00010000

# ROM C (merc.h): #define IMM_SUMMON (E)
# QuickMUD (player_config.py:76): IMM_SUMMON = 0x00000010  # bit 4
```
✅ Flag bits match ROM C exactly

**Special Behavior**:
- ✅ NPCs use `imm_flags` field (immunity flags)
- ✅ Players use `act` field (player flags)
- ✅ Both have same toggle logic (just different flag locations)

**Gaps**: None

---

## Summary of Findings

### Overall Statistics

| Metric | Count |
|--------|-------|
| **Commands Audited** | 3 |
| **Total ROM C Lines** | 64 (lines 972-1035) |
| **Total QuickMUD Lines** | 76 (lines 17-92) |
| **Critical Gaps** | 0 |
| **Minor Gaps** | 0 |
| **Excellent Parity** | 3/3 (100%) |

### Gap Analysis

**Critical Gaps (P0)**: 0  
**Minor Gaps (P1)**: 0  
**Cosmetic Differences (P2)**: 0

### Implementation Quality Assessment

**Strengths**:
1. ✅ All NPC checks return empty string (matches ROM C void return)
2. ✅ Flag bit operations match ROM C exactly (`&`, `|`, `&~`)
3. ✅ Messages match ROM C 100% (all 8 messages verified)
4. ✅ Special behavior implemented correctly:
   - `do_nofollow` calls `_die_follower()` to stop followers
   - `do_nosummon` handles NPC vs player flags correctly
5. ✅ Defensive programming with `getattr(char, "act", 0)` fallbacks
6. ✅ Proper use of hardcoded flag values (consistent with constants.py)
7. ✅ Clear ROM C source references in docstrings
8. ✅ Helper functions (`_die_follower`, `_stop_follower`) implement ROM C behavior

**Flag Definitions Verified**:
- `PLR_CANLOOT = 0x00008000` (bit 15) ✅ matches ROM C `(P)`
- `PLR_NOSUMMON = 0x00010000` (bit 16) ✅ matches ROM C `(Q)`
- `PLR_NOFOLLOW = 0x00020000` (bit 17) ✅ matches ROM C `(R)`
- `IMM_SUMMON = 0x00000010` (bit 4) ✅ matches ROM C `(E)`

**Weaknesses**: None identified

---

## Integration Test Coverage

**Test File**: `tests/integration/test_player_config.py`  
**Total Tests**: 9  
**Passing**: 9/9 (100%)

### Test Breakdown

#### do_noloot Tests (3 tests)
1. ✅ `test_noloot_npc_returns_empty()` - NPCs can't toggle loot permission
2. ✅ `test_noloot_toggle_on()` - Enable corpse looting (PLR_CANLOOT set)
3. ✅ `test_noloot_toggle_off()` - Disable corpse looting (PLR_CANLOOT clear)

#### do_nofollow Tests (3 tests)
4. ✅ `test_nofollow_npc_returns_empty()` - NPCs can't toggle follower permission
5. ✅ `test_nofollow_toggle_on()` - Enable nofollow + stop followers
6. ✅ `test_nofollow_toggle_off()` - Disable nofollow (accept followers)

#### do_nosummon Tests (3 tests)
7. ✅ `test_nosummon_player_toggle_on()` - Player enables summon immunity
8. ✅ `test_nosummon_player_toggle_off()` - Player disables summon immunity
9. ✅ `test_nosummon_npc_toggle()` - NPC uses imm_flags (not act flags)

### Test Patterns Used

**NPC Check Pattern**:
```python
def test_command_npc_returns_empty(test_npc):
    """NPCs can't use command (ROM C line X-Y)."""
    output = do_command(test_npc, "")
    assert output == ""
```

**Player Toggle Pattern**:
```python
def test_command_toggle_on(test_char):
    """Command toggles from OFF to ON (ROM C line X-Y)."""
    assert not (test_char.act & PlayerFlag.FLAG)
    output = do_command(test_char, "")
    assert "expected message" in output.lower()
    assert test_char.act & PlayerFlag.FLAG
```

**NPC Special Behavior Pattern** (nosummon):
```python
def test_nosummon_npc_toggle(test_npc):
    """NPCs use imm_flags not act flags (ROM C line 1007-1021)."""
    assert not (test_npc.imm_flags & IMM_SUMMON)
    output = do_nosummon(test_npc, "")
    assert "immune to summoning" in output.lower()
    assert test_npc.imm_flags & IMM_SUMMON
```

---

## Recommendations

### For QuickMUD Developers

1. ✅ **No changes needed** - All 3 commands have excellent ROM C parity
2. ✅ **Integration tests complete** - 9/9 tests passing
3. ✅ **Flag definitions verified** - All 4 flags match ROM C exactly
4. ✅ **Helper functions verified** - `_die_follower()` and `_stop_follower()` match ROM C

### For Future Audits

1. **Reuse test patterns** - The 3 test patterns used here work well:
   - NPC rejection test
   - Player toggle ON test
   - Player toggle OFF test
   - Special behavior test (when applicable)

2. **Verify flag definitions** - Always check `constants.py` and hardcoded values against ROM C `merc.h`

3. **Check special behaviors** - Some commands have side effects (like nofollow stopping followers)

---

## Files Verified

### ROM C Source Files
- ✅ `src/act_info.c` (lines 972-1035) - 3 commands
- ✅ `src/merc.h` (flag definitions) - verified via constants.py

### QuickMUD Source Files
- ✅ `mud/commands/player_config.py` (lines 17-92) - 3 commands
- ✅ `mud/commands/player_config.py` (lines 171-216) - helper functions
- ✅ `mud/models/constants.py` (lines 403-423) - PlayerFlag definitions

### Integration Test Files
- ✅ `tests/integration/test_player_config.py` (9 tests, 100% passing)

---

## Conclusion

**All 3 player config commands demonstrate EXCELLENT ROM C parity.**

**No gaps found. No implementation needed. Ready for next batch.**

---

## Appendix: Flag Bit Verification

### PlayerFlag Enum (constants.py lines 403-423)
```python
class PlayerFlag(IntFlag):
    """Player-specific act flags (merc.h PLR_* bitmasks)."""
    
    IS_NPC = 1 << 0  # (A)
    AUTOASSIST = 1 << 2  # (C)
    AUTOEXIT = 1 << 3  # (D)
    AUTOLOOT = 1 << 4  # (E)
    AUTOSAC = 1 << 5  # (F)
    AUTOGOLD = 1 << 6  # (G)
    AUTOSPLIT = 1 << 7  # (H)
    HOLYLIGHT = 1 << 13  # (N)
    CANLOOT = 1 << 15  # (P) = 0x00008000 ✅
    NOSUMMON = 1 << 16  # (Q) = 0x00010000 ✅
    NOFOLLOW = 1 << 17  # (R) = 0x00020000 ✅
    COLOUR = 1 << 19  # (T)
    PERMIT = 1 << 20  # (U)
    LOG = 1 << 22  # (W)
    DENY = 1 << 23  # (X)
    FREEZE = 1 << 24  # (Y)
    THIEF = 1 << 25  # (Z)
    KILLER = 1 << 26  # (aa)
```

### ROM C merc.h Flag Definitions
```c
#define PLR_CANLOOT     (P)  // bit 15 = 0x00008000
#define PLR_NOSUMMON    (Q)  // bit 16 = 0x00010000
#define PLR_NOFOLLOW    (R)  // bit 17 = 0x00020000
```

✅ All 3 flags verified correct

---

**End of Audit**
