# `ban.c` ROM Parity Audit

- **Status**: Phase 3 — gap identification complete; closures in progress
- **Date**: 2026-04-28
- **Source**: `src/ban.c` (ROM 2.4b6, 307 lines, 7 public functions)
- **Python primary**: `mud/security/bans.py`, `mud/commands/admin_commands.py:cmd_ban|cmd_permban|cmd_allow|cmd_banlist|_apply_ban|_render_ban_listing`

## Phase 1 — Function inventory

| ROM symbol | ROM lines | Python counterpart | Status |
|------------|-----------|--------------------|--------|
| `save_bans` | 43-69 | `mud/security/bans.py:save_bans_file` | ✅ AUDITED — only PERMANENT entries written, file deleted when none |
| `load_bans` | 71-102 | `mud/security/bans.py:load_bans_file` | ✅ AUDITED — letter-encoded flags parsed, only PERMANENT retained |
| `check_ban` | 104-132 | `mud/security/bans.py:is_host_banned` + `BanEntry.matches` | ⚠️ PARTIAL — see BAN-004 |
| `ban_site` | 135-254 | `mud/commands/admin_commands.py:_apply_ban` + `_render_ban_listing` | ⚠️ PARTIAL — see BAN-001..003 |
| `do_ban` | 256-259 | `mud/commands/admin_commands.py:cmd_ban` | ✅ AUDITED |
| `do_permban` | 261-264 | `mud/commands/admin_commands.py:cmd_permban` | ✅ AUDITED |
| `do_allow` | 266-307 | `mud/commands/admin_commands.py:cmd_allow` | ✅ AUDITED |

## Phase 2 — Verification highlights

### `_render_ban_listing` (ROM 157-174)

ROM format string: `"%-12s    %-3d  %-7s  %s\n\r"`. The `%-3d` is left-aligned (pads spaces on the right). Python uses `:3d` which is right-aligned. Visible difference for any level shorter than 3 digits (most). → **BAN-001**.

ROM type-text expression: `IS_SET(BAN_NEWBIES) ? "newbies" : IS_SET(BAN_PERMIT) ? "permit" : IS_SET(BAN_ALL) ? "all" : ""`. When none of the three flags is set, ROM emits the **empty string**. Python's `_render_ban_listing` defaults to `"all"` via `else: type_text = "all"`. → **BAN-002**.

### `_apply_ban` type-token parsing (ROM 180-191)

ROM uses `!str_prefix(arg2, "all")` etc. — accepts `arg2` when it is a **prefix of** `"all"`/`"newbies"`/`"permit"` (so `a`, `al`, `all`; `n`, `ne`, …, `newbies`; `p`, …, `permit`). Python uses `type_token.startswith("all")` — only matches when the argument **starts with** `"all"` (so `a` and `al` are rejected; `alloy`/`allowed` are accepted). → **BAN-003**.

### `check_ban` (ROM 104-132)

ROM matches an entry only if it has at least one of `BAN_PREFIX`/`BAN_SUFFIX`. An entry with neither bit set is silently skipped (ROM quirk: `ban foo.com` with no `*` makes an unmatchable entry). Python `BanEntry.matches` adds an exact-match fallback (`return candidate == self.pattern`). This makes Python match more strictly than ROM. → **BAN-004**.

### Other behavior verified parity-clean

- `save_bans_file` writes only `BanFlag.PERMANENT` entries and deletes the file when none remain (ROM 43-69).
- `load_bans_file` reads letter-encoded flag tokens (`A..F`) and discards entries without `PERMANENT` (ROM 71-102).
- Trust check on add (`That ban was set by a higher power.`) and remove (`You are not powerful enough to lift that ban.`) wired through `BanPermissionError` in `_ensure_can_modify`.
- `do_ban` → permanent=False, `do_permban` → permanent=True, `do_allow` returns `Site is not banned.`/`Ban on X lifted.` matching ROM strings.
- `_apply_ban` empty-stripped `core` returns `You have to ban SOMETHING.` (ROM 207-211).
- Listing header `"Banned sites  level  type     status"` matches ROM 157.

## Phase 3 — Gaps

| Gap ID | Severity | ROM C | Python | Description | Status |
|--------|----------|-------|--------|-------------|--------|
| `BAN-001` | IMPORTANT | `src/ban.c:164` | `mud/commands/admin_commands.py:_render_ban_listing` | Listing level column right-aligned (`:3d`) instead of ROM left-aligned (`%-3d`). | ✅ FIXED — switched to `:<3d`. Test: `tests/integration/test_ban_command_parity.py::test_banlist_level_column_left_aligned`. |
| `BAN-002` | IMPORTANT | `src/ban.c:166-168` | `mud/commands/admin_commands.py:_render_ban_listing` | Type-text fallback prints `"all"` when none of NEWBIES/PERMIT/ALL bits is set; ROM prints the empty string. | ✅ FIXED — chained ternary now mirrors ROM, falling through to `""`. Test: `test_banlist_type_text_empty_when_no_type_bits`. |
| `BAN-003` | IMPORTANT | `src/ban.c:180-191` | `mud/commands/admin_commands.py:_apply_ban` | Type-token abbreviation: ROM accepts prefixes of `all`/`newbies`/`permit` (so `a`, `n`, `p`); Python uses `startswith` so it rejects them. | ✅ FIXED — comparison flipped to `"all".startswith(type_token)` etc., mirroring ROM `!str_prefix(arg2, "all")`. Test: `test_apply_ban_accepts_single_letter_type_abbreviation`. |
| `BAN-004` | MINOR | `src/ban.c:104-132` | `mud/security/bans.py:BanEntry.matches` | `BanEntry.matches` adds exact-match fallback when neither PREFIX nor SUFFIX bit is set; ROM `check_ban` skips such entries. Python is stricter than ROM (more bans match). | 🔄 OPEN |

## Phase 4 — Closures

(Filled in as gaps land.)

## Phase 5 — Completion summary

(Filled in once all gaps closed.)
