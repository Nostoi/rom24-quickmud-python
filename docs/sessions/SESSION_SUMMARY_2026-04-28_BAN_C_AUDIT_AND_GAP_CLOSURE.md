# Session Summary — 2026-04-28 — `ban.c` parity audit & gap closure

## Scope

Audited `src/ban.c` (ROM 2.4b6, 7 public functions) against `mud/security/bans.py` and `mud/commands/admin_commands.py`. Produced `docs/parity/BAN_C_AUDIT.md`, identified 4 gaps (3 IMPORTANT + 1 MINOR), closed all four via the rom-gap-closer TDD flow. ban.c is now ✅ AUDITED at 100%.

## Outcomes

### `BAN-001` — ✅ FIXED
- **ROM C**: `src/ban.c:164` (`%-3d` left-aligned level column in `ban_site` listing)
- **Python**: `mud/commands/admin_commands.py:_render_ban_listing`
- **Fix**: Format spec changed from `:3d` (right-aligned) to `:<3d`.
- **Tests**: `test_banlist_level_column_left_aligned`

### `BAN-002` — ✅ FIXED
- **ROM C**: `src/ban.c:166-168` (chained ternary; `""` when none of NEWBIES/PERMIT/ALL set)
- **Python**: `mud/commands/admin_commands.py:_render_ban_listing`
- **Fix**: Replaced `else: type_text = "all"` with explicit `elif BAN_ALL` and `else: ""` fallback.
- **Tests**: `test_banlist_type_text_empty_when_no_type_bits`

### `BAN-003` — ✅ FIXED
- **ROM C**: `src/ban.c:180-191` (`!str_prefix(arg2, "all"/"newbies"/"permit")` — abbreviation accepted)
- **Python**: `mud/commands/admin_commands.py:_apply_ban`
- **Fix**: Comparison flipped to `"all".startswith(type_token)` etc., so single-letter abbreviations (`a`/`n`/`p`) now match per ROM. Empty token defaults to `BAN_ALL` per ROM 180.
- **Tests**: `test_apply_ban_accepts_single_letter_type_abbreviation`

### `BAN-004` — ✅ FIXED
- **ROM C**: `src/ban.c:104-132` (`check_ban` skips entries with neither PREFIX nor SUFFIX bit)
- **Python**: `mud/security/bans.py:BanEntry.matches`
- **Fix**: Removed exact-string fallback (`return candidate == self.pattern`). Pre-existing tests in `tests/test_bans.py` and `tests/test_account_auth.py` updated to use ROM-style `*host*` patterns so host-specific bans actually match under the corrected semantics.
- **Tests**: `test_check_ban_skips_entries_without_prefix_or_suffix`

## Files Modified

- `mud/commands/admin_commands.py` — listing alignment, type-text fallback, ROM-style abbreviation matching.
- `mud/security/bans.py` — `BanEntry.matches` no longer exact-match-falls-through.
- `tests/integration/test_ban_command_parity.py` — new file, 4 tests (one per BAN-NNN gap).
- `tests/test_bans.py` — updated to use `*example.org*` and `ABDF`-flagged file fixture (PREFIX+SUFFIX+ALL+PERMANENT).
- `tests/test_account_auth.py` — host-specific bans switched to `*host*` form (5 sites).
- `docs/parity/BAN_C_AUDIT.md` — created; all 4 gap rows ✅ FIXED.
- `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` — `ban.c` row flipped from ⚠️ Partial (50%) → ✅ AUDITED (100%).
- `CHANGELOG.md` — added Fixed entries for BAN-001..004.
- `pyproject.toml` — `2.6.19` → `2.6.20`.

## Test Status

- `pytest tests/integration/test_ban_command_parity.py tests/test_bans.py tests/integration/test_admin_commands.py tests/test_account_auth.py` — 77/77 passing.

## Next Steps

- Pick the next ⚠️ Partial / ❌ Not Audited file from `ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`. Candidates: deferred NANNY-008/009/010 (pet-on-login, title_table, CON_BREAK_CONNECT iteration), or another P2 file (OLC, recycle.c, save.c).
