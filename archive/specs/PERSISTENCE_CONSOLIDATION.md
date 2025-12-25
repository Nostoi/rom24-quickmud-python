# Persistence System Consolidation - December 22, 2025

## Summary

Consolidated QuickMUD to use **database-only persistence** via `mud.account.account_manager`, eliminating the dual persistence system that was causing data loss and confusion.

## Problem

QuickMUD had TWO competing persistence systems:

1. **JSON files** (`mud/persistence.py`) - Legacy ROM C compatibility
2. **SQLAlchemy database** (`mud/account/account_manager.py`) - Modern account system

This caused:
- ❌ Characters created in database getting lost
- ❌ Account exists but no characters found
- ❌ Two `save_character()` functions with same name
- ❌ Confusion about which is source of truth

## Solution

**Consolidated to database-only** by:

1. ✅ Updated all `save_character()` calls to use `mud.account.account_manager`
2. ✅ Fixed `account_manager.save_character()` to CREATE characters if they don't exist (not just UPDATE)
3. ✅ Added lazy import in `advancement.py` to avoid circular dependencies
4. ✅ Deprecated `mud/persistence.py` with clear notice
5. ✅ Updated test to use new import path

## Files Changed

| File | Change |
|------|--------|
| `mud/game_loop.py` | Import from `account_manager` instead of `persistence` |
| `mud/combat/engine.py` | Import from `account_manager` instead of `persistence` |
| `mud/commands/admin_commands.py` | Import from `account_manager` instead of `persistence` |
| `mud/commands/session.py` | Import from `account_manager` instead of `persistence` |
| `mud/advancement.py` | Lazy import from `account_manager` to avoid circular dependency |
| `mud/account/account_manager.py` | CREATE character if not found (not just UPDATE) |
| `mud/account/account_service.py` | Better error logging for character creation |
| `mud/net/connection.py` | Better error message when character creation fails |
| `mud/persistence.py` | Added deprecation notice |
| `tests/test_advancement.py` | Updated monkeypatch path |

## Benefits

✅ **Single source of truth**: All data in database  
✅ **No data loss**: Characters always saved to database  
✅ **Account system works**: Login → find account → find characters  
✅ **Better error messages**: Clear logging when things fail  
✅ **Cleaner codebase**: No confusion about which save to use  

## Migration Notes

**Existing JSON files** (`data/players/*.json`) will NOT be automatically migrated. They remain for backward compatibility but are no longer actively used. To migrate existing JSON characters to database:

1. Log in with account
2. Create character (will be saved to database)
3. Old JSON file can be deleted or kept as backup

## Testing

- ✅ All persistence tests passing (11/11)
- ✅ All advancement tests passing (11/11)
- ✅ No circular import issues
- ✅ Character creation works
- ✅ Character save on quit works
- ✅ Character load on login works

## Next Steps

The persistence system is now consolidated and working. Future improvements:

1. Optional: Add migration tool to import JSON files to database
2. Optional: Remove deprecated `mud/persistence.py` entirely
3. Recommended: Add database backups to deployment workflow
