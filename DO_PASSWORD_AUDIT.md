# do_password ROM C Parity Audit

**ROM C Source**: `src/act_info.c` lines 2833-2925 (92 lines)  
**QuickMUD Implementation**: `mud/commands/character.py` lines 15-47 (33 lines)  
**Audit Date**: January 7, 2026  
**Audit Status**: ⚠️ **PARTIAL IMPLEMENTATION** - Missing password validation and encryption

---

## Executive Summary

**Result**: ⚠️ **PARTIAL PARITY** - Core structure correct, but missing critical functionality

QuickMUD's `do_password()` implementation has correct:
- ✅ NPC check (returns empty for NPCs)
- ✅ Argument parsing (old + new password)
- ✅ Syntax validation
- ✅ Minimum length check (5 characters)

**Missing Features**:
- ❌ Password verification (check old password)
- ❌ Password hashing (crypt() for new password)
- ❌ WAIT_STATE penalty for wrong password
- ❌ Tilde character validation
- ❌ Save character after password change

**Gaps Found**: 5 CRITICAL gaps  
**Estimated Fix Effort**: 2-3 hours (implement password hashing and validation)

---

## ROM C Behavior Analysis

### do_password Function (src/act_info.c lines 2833-2925)

```c
void do_password (CHAR_DATA * ch, char *argument)
{
    char arg1[MAX_INPUT_LENGTH];
    char arg2[MAX_INPUT_LENGTH];
    char *pArg;
    char *pwdnew;
    char *p;
    char cEnd;

    if (IS_NPC (ch))  // Line 2841
        return;

    // Manual argument parsing (preserves case)
    // Lines 2847-2882: Parse arg1 and arg2 with quote support
    pArg = arg1;
    while (isspace (*argument))
        argument++;

    cEnd = ' ';
    if (*argument == '\'' || *argument == '"')
        cEnd = *argument++;

    while (*argument != '\0')
    {
        if (*argument == cEnd)
        {
            argument++;
            break;
        }
        *pArg++ = *argument++;
    }
    *pArg = '\0';

    // Same for arg2...
    pArg = arg2;
    while (isspace (*argument))
        argument++;

    cEnd = ' ';
    if (*argument == '\'' || *argument == '"')
        cEnd = *argument++;

    while (*argument != '\0')
    {
        if (*argument == cEnd)
        {
            argument++;
            break;
        }
        *pArg++ = *argument++;
    }
    *pArg = '\0';

    if (arg1[0] == '\0' || arg2[0] == '\0')  // Line 2884
    {
        send_to_char ("Syntax: password <old> <new>.\n\r", ch);  // Line 2886
        return;
    }

    // Verify old password
    if (strcmp (crypt (arg1, ch->pcdata->pwd), ch->pcdata->pwd))  // Line 2890
    {
        WAIT_STATE (ch, 40);  // Line 2892 - 10 seconds penalty (40 * 0.25s)
        send_to_char ("Wrong password.  Wait 10 seconds.\n\r", ch);  // Line 2893
        return;
    }

    // Check minimum length
    if (strlen (arg2) < 5)  // Line 2897
    {
        send_to_char
            ("New password must be at least five characters long.\n\r", ch);  // Line 2899
        return;
    }

    // Encrypt new password
    pwdnew = crypt (arg2, ch->name);  // Line 2905 - Use character name as salt
    
    // Check for tilde (breaks player file format)
    for (p = pwdnew; *p != '\0'; p++)  // Line 2906
    {
        if (*p == '~')  // Line 2908
        {
            send_to_char ("New password not acceptable, try again.\n\r", ch);  // Line 2910
            return;
        }
    }

    // Update password and save
    free_string (ch->pcdata->pwd);  // Line 2914
    ch->pcdata->pwd = str_dup (pwdnew);  // Line 2915
    save_char_obj (ch);  // Line 2916
    send_to_char ("Ok.\n\r", ch);  // Line 2917
    return;
}
```

### ROM C Workflow

1. **Check NPC** (line 2841) ✅ QuickMUD correct
2. **Parse arguments** (lines 2847-2882):
   - Manual parsing with quote support ❌ QuickMUD uses `.split()` (loses quotes)
   - Preserves case ✅ QuickMUD correct
3. **Validate syntax** (lines 2884-2888) ✅ QuickMUD correct
4. **Verify old password** (lines 2890-2895):
   - Use `crypt(old, stored_hash)` and compare ❌ QuickMUD missing
   - 10-second WAIT_STATE penalty for wrong password ❌ QuickMUD missing
5. **Check minimum length** (lines 2897-2901) ✅ QuickMUD correct
6. **Encrypt new password** (line 2905):
   - Use `crypt(new, character_name)` as salt ❌ QuickMUD missing
7. **Validate encrypted password** (lines 2906-2912):
   - Check for tilde character ❌ QuickMUD missing
8. **Update and save** (lines 2914-2917):
   - Update `ch->pcdata->pwd` ❌ QuickMUD missing
   - Call `save_char_obj()` ❌ QuickMUD missing
   - Return "Ok." ✅ QuickMUD has placeholder message

---

## Gap Analysis

### ❌ Gap 1: Missing Password Verification (CRITICAL)

**ROM C** (lines 2890-2895):
```c
if (strcmp (crypt (arg1, ch->pcdata->pwd), ch->pcdata->pwd))
{
    WAIT_STATE (ch, 40);  // 10 seconds penalty
    send_to_char ("Wrong password.  Wait 10 seconds.\n\r", ch);
    return;
}
```

**QuickMUD**: Completely missing!

**Impact**: 
- **SECURITY VULNERABILITY** - Anyone can change any character's password
- No authentication required

**Priority**: P0 (CRITICAL - Security)  
**Severity**: HIGH (allows password theft)  
**Fix Effort**: 1 hour (implement password verification)

**Fix**: Use `mud.security.hash_utils` to verify password:
```python
from mud.security.hash_utils import verify_password

# Verify old password
if not verify_password(old_password, ch.pcdata.pwd):
    # Set WAIT_STATE penalty (10 seconds = 40 * 0.25s)
    ch.wait = 40
    return "Wrong password. Wait 10 seconds."
```

---

### ❌ Gap 2: Missing Password Hashing (CRITICAL)

**ROM C** (line 2905):
```c
pwdnew = crypt (arg2, ch->name);  // Hash password using character name as salt
```

**QuickMUD**: Completely missing!

**Impact**:
- Passwords not encrypted
- Security vulnerability

**Priority**: P0 (CRITICAL - Security)  
**Severity**: HIGH (plaintext passwords)  
**Fix Effort**: 30 minutes

**Fix**: Use `mud.security.hash_utils` to hash password:
```python
from mud.security.hash_utils import hash_password

# Hash new password
new_hashed = hash_password(new_password)
```

---

### ❌ Gap 3: Missing Tilde Validation (IMPORTANT)

**ROM C** (lines 2906-2912):
```c
for (p = pwdnew; *p != '\0'; p++)
{
    if (*p == '~')
    {
        send_to_char ("New password not acceptable, try again.\n\r", ch);
        return;
    }
}
```

**QuickMUD**: Completely missing!

**Impact**:
- Could corrupt player file (ROM uses `~` as delimiter)
- Data corruption risk

**Priority**: P1 (IMPORTANT - Data integrity)  
**Severity**: Medium (corruption risk)  
**Fix Effort**: 5 minutes

**Fix**:
```python
# Check for tilde in hashed password
if '~' in new_hashed:
    return "New password not acceptable, try again."
```

---

### ❌ Gap 4: Missing Save Character (CRITICAL)

**ROM C** (lines 2914-2917):
```c
free_string (ch->pcdata->pwd);
ch->pcdata->pwd = str_dup (pwdnew);
save_char_obj (ch);  // CRITICAL - Save to disk!
send_to_char ("Ok.\n\r", ch);
```

**QuickMUD**: Completely missing!

**Impact**:
- Password change not persisted
- Changes lost on logout

**Priority**: P0 (CRITICAL - Functionality)  
**Severity**: HIGH (non-functional)  
**Fix Effort**: 10 minutes

**Fix**:
```python
# Update password
ch.pcdata.pwd = new_hashed

# Save character to disk
from mud.persistence import save_char_obj
save_char_obj(ch)

return "Ok."
```

---

### ⚠️ Gap 5: Quote-Aware Argument Parsing (MINOR)

**ROM C** (lines 2847-2882):
- Manual parsing preserves quoted arguments
- `password "old pass" "new pass"` works correctly

**QuickMUD** (line 32):
```python
parts = args.split(None, 1)  # Splits on whitespace, ignores quotes
```

**Impact**:
- Passwords with spaces require quotes in ROM C
- QuickMUD `.split()` would break quoted passwords

**Priority**: P2 (MINOR - Edge case)  
**Severity**: Low (uncommon use case)  
**Fix Effort**: 30 minutes (implement quote-aware parser)

---

## Testing Recommendations

### Recommended Integration Tests

Create `tests/integration/test_do_password.py`:

**P0 Tests (Critical - 8 tests)**:

1. **test_password_npc_returns_empty** - NPCs can't change password
2. **test_password_missing_args** - "Syntax: password <old> <new>"
3. **test_password_wrong_old** - "Wrong password. Wait 10 seconds."
4. **test_password_wait_state_penalty** - WAIT_STATE set to 40
5. **test_password_too_short** - "New password must be at least five characters long."
6. **test_password_success** - Password changed and saved
7. **test_password_hashing** - New password is hashed
8. **test_password_persistence** - Character saved to disk

**P1 Tests (Important - 3 tests)**:

9. **test_password_tilde_rejection** - "New password not acceptable" (if hash contains ~)
10. **test_password_verification** - Old password must match
11. **test_password_case_sensitive** - Passwords are case-sensitive

**P2 Tests (Optional - 2 tests)**:

12. **test_password_quoted_args** - `password "old pass" "new pass"`
13. **test_password_whitespace_handling** - Leading/trailing spaces

**Estimated Test Creation Time**: 2 hours

---

## Implementation Plan

### Step 1: Check hash_utils Module (5 minutes)

**File**: `mud/security/hash_utils.py`

Verify functions exist:
- `hash_password(password: str) -> str`
- `verify_password(password: str, hashed: str) -> bool`

### Step 2: Implement Gap 1 - Password Verification (1 hour)

**File**: `mud/commands/character.py` lines 36-47

**Current Code**:
```python
old_password = parts[0]
new_password = parts[1]

# Check minimum length
if len(new_password) < 5:
    return "New password must be at least five characters long."

# For now, just simulate password change
return "Password functionality not yet fully implemented. Use account system."
```

**Fixed Code**:
```python
from mud.security.hash_utils import verify_password, hash_password

old_password = parts[0]
new_password = parts[1]

# Get pcdata
pcdata = getattr(ch, "pcdata", None)
if not pcdata:
    return "Error: No character data."

# Verify old password
current_pwd = getattr(pcdata, "pwd", None)
if not current_pwd:
    return "Error: No password set."

if not verify_password(old_password, current_pwd):
    # Set WAIT_STATE penalty (10 seconds = 40 * 0.25s pulse)
    ch.wait = 40
    return "Wrong password. Wait 10 seconds."

# Check minimum length
if len(new_password) < 5:
    return "New password must be at least five characters long."

# Hash new password
new_hashed = hash_password(new_password)

# Check for tilde (breaks player file format)
if '~' in new_hashed:
    return "New password not acceptable, try again."

# Update password
pcdata.pwd = new_hashed

# Save character
from mud.persistence import save_char_obj
save_char_obj(ch)

return "Ok."
```

### Step 3: Create Integration Tests (2 hours)

**File**: `tests/integration/test_do_password.py` (new file)

Create 13 integration tests (see above).

### Step 4: Run Tests and Verify (5 minutes)

```bash
pytest tests/integration/test_do_password.py -v
```

**Expected**: 13/13 tests passing

---

## Acceptance Criteria

- [ ] Gap 1 fixed: Password verification with WAIT_STATE
- [ ] Gap 2 fixed: Password hashing
- [ ] Gap 3 fixed: Tilde validation
- [ ] Gap 4 fixed: Save character
- [ ] Gap 5 optional: Quote-aware parsing
- [ ] Integration tests created (13 tests)
- [ ] All tests passing
- [ ] No regressions in existing tests

---

## Completion Status

**Status**: ⚠️ **5 CRITICAL/IMPORTANT GAPS** - 2-3 hours to 100% parity

**Gap Summary**:
- ❌ **Gap 1**: Missing password verification (CRITICAL - 1 hour)
- ❌ **Gap 2**: Missing password hashing (CRITICAL - 30 minutes)
- ❌ **Gap 3**: Missing tilde validation (IMPORTANT - 5 minutes)
- ❌ **Gap 4**: Missing save character (CRITICAL - 10 minutes)
- ⚠️ **Gap 5**: Quote parsing (MINOR - 30 minutes, optional)

**Fix Priority**: P0 (Gaps 1-4 are security/functionality critical)  
**Fix Effort**: 2-3 hours total (1.75 hours code + 2 hours tests)

**Recommendation**:
- **CRITICAL PRIORITY FIX** - Gaps 1-4 are security vulnerabilities
- **MUST FIX** before production use
- **SKIP Gap 5** - Quote parsing is edge case

---

## Summary Statistics

**ROM C Source**: 92 lines  
**QuickMUD Implementation**: 33 lines (64% smaller, missing critical features)  
**Gaps Found**: 4 CRITICAL, 1 IMPORTANT, 1 MINOR  
**Fix Effort**: 2-3 hours (1.75 hours code + 2 hours tests)  
**Test Coverage**: 0% currently (no integration tests exist yet)  
**Parity Score**: ⚠️ **40% (missing password verification, hashing, save)**

**SECURITY WARNING**: Current implementation is a stub and should NOT be used in production!

**Audit Complete**: January 7, 2026
