# `alias.c` Audit — ROM 2.4b6 → QuickMUD-Python Parity

**Status:** ✅ AUDITED — all 5 gameplay-visible gaps closed (`ALIAS-001`..`005`)  
**Date:** 2026-04-28  
**ROM C:** `src/alias.c` (274 lines, 4 functions)  
**Python:** `mud/commands/alias_cmds.py`, `mud/commands/dispatcher.py`, `mud/commands/typo_guards.py`, `mud/rom_api.py`  
**Priority:** P2 (player command system, persistence-visible and UX-visible)

## Phase 1 — Function Inventory

| ROM C function | ROM lines | Python equivalent | Status |
|----------------|-----------|-------------------|--------|
| `substitute_alias` | `src/alias.c:41-99` | `mud/commands/dispatcher.py:847-881`, `mud/rom_api.py:281-295` | ✅ AUDITED |
| `do_alia` | `src/alias.c:97-100` | `mud/commands/typo_guards.py:60-62` | ✅ AUDITED |
| `do_alias` | `src/alias.c:102-220` | `mud/commands/alias_cmds.py:60-98` | ✅ AUDITED |
| `do_unalias` | `src/alias.c:224-274` | `mud/commands/alias_cmds.py:101-118` | ✅ AUDITED |

## Phase 2 — Line-by-line Verification

### `substitute_alias`

ROM `src/alias.c:49-67`:
- Applies the player's `prefix` before alias lookup, unless the command starts with `prefix`.
- Rejects overlong prefixed lines with `"Line to long, prefix not processed.\r\n"`.
- Bypasses alias substitution for `alias`, `una*`, and `prefix`.

ROM `src/alias.c:69-99`:
- Performs a **single** alias substitution pass.
- Lowercases the parsed head token via `one_argument`.
- Truncates oversized substitutions and warns with `"Alias substitution too long. Truncated.\r\n"`.

Python before closure:
- ❌ Recursively expanded alias chains.
- ❌ Had no prefix-length guard or substitution-length warning path.
- ❌ `mud.rom_api.substitute_alias()` returned the raw tuple from `_expand_aliases()` instead of the expanded string.

Python now:
- ✅ Performs one ROM-style substitution pass.
- ✅ Applies prefix warnings/truncation semantics in `process_command`.
- ✅ Returns just the expanded command string from `mud.rom_api.substitute_alias()`.

### `do_alia`

ROM `src/alias.c:97-100`:
- Returns `"I'm sorry, alias must be entered in full.\n\r"`.

Python before closure:
- ❌ Returned the generic typo-guard string `"If you want to ALIAS, spell it out."`

Python now:
- ✅ Uses the ROM-specific message text.

### `do_alias`

ROM `src/alias.c:112-220`:
- Lists aliases with the ROM header/body formatting.
- Lowercases alias names via `one_argument`.
- Treats `alias` and `una*` as reserved alias names.
- Forbids alias names containing spaces or quotes.
- Supports query mode (`alias <name>`).
- Blocks expansions whose first word prefixes `delete` or `prefix`.
- Redefines existing aliases in place and enforces `MAX_ALIAS == 5`.

Python before closure:
- ❌ Used non-ROM list/set messages.
- ❌ Had no query mode, alias-limit enforcement, or quote/name validation.
- ❌ Only blocked exact `alias`/`unalias`, not ROM `una*`.
- ❌ Allowed `delete`/`prefix` expansions.

Python now:
- ✅ Mirrors ROM messages, validation rules, query path, re-alias path, and alias limit.

### `do_unalias`

ROM `src/alias.c:236-274`:
- Prompts `"Unalias what?\n\r"` with no argument.
- Removes the alias and reports `"Alias removed.\n\r"`.
- Reports `"No alias of that name to remove.\n\r"` when absent.

Python before closure:
- ❌ Used usage/help text and different removal/failure messages.

Python now:
- ✅ Mirrors ROM prompts and removal messages.

## Phase 3 — Gaps

| ID | Severity | ROM C ref | Python ref | Description | Status |
|----|----------|-----------|------------|-------------|--------|
| `ALIAS-001` | IMPORTANT | `src/alias.c:97-100` | `mud/commands/typo_guards.py` (pre-fix) | `alia` returned a generic typo-guard string instead of the ROM `do_alia` message. | ✅ FIXED — `tests/integration/test_alias_command_parity.py::test_alias_command_uses_rom_messages_and_listing` |
| `ALIAS-002` | CRITICAL | `src/alias.c:112-220` | `mud/commands/alias_cmds.py` (pre-fix) | `do_alias` lacked ROM listing/query/redefinition/validation behavior and used non-ROM messages. | ✅ FIXED — `tests/integration/test_alias_command_parity.py::test_alias_command_uses_rom_messages_and_listing`, `tests/integration/test_alias_command_parity.py::test_alias_command_rejects_reserved_and_forbidden_expansions` |
| `ALIAS-003` | CRITICAL | `src/alias.c:69-99` | `mud/commands/dispatcher.py`, `mud/rom_api.py` (pre-fix) | Alias substitution recursively expanded chains, lacked warning/truncation parity, and `rom_api.substitute_alias()` returned the wrong shape. | ✅ FIXED — `tests/integration/test_alias_command_parity.py::test_alias_substitution_is_single_pass_like_rom` |
| `ALIAS-004` | IMPORTANT | `src/alias.c:236-274` | `mud/commands/alias_cmds.py` (pre-fix) | `do_unalias` used non-ROM prompt/removal/failure messages. | ✅ FIXED — `tests/integration/test_alias_command_parity.py::test_unalias_uses_rom_messages` |
| `ALIAS-005` | IMPORTANT | `src/alias.c:49-61,88-95` | `mud/commands/dispatcher.py` (pre-fix) | Prefix preprocessing skipped ROM line-length protection and used a non-ROM blocked-prefix set (`pref*` instead of full `prefix`). | ✅ FIXED — covered by `tests/test_commands.py::test_prefix_macro_prepends_to_commands` and focused alias suite |

## Phase 4 — Closures

### `ALIAS-001` — ✅ FIXED

- **Python:** `mud/commands/typo_guards.py:60-62`
- **ROM C:** `src/alias.c:97-100`
- **Fix:** Replaced the generic typo-guard text with the ROM `do_alia` message.
- **Tests:** `tests/integration/test_alias_command_parity.py::test_alias_command_uses_rom_messages_and_listing`

### `ALIAS-002` — ✅ FIXED

- **Python:** `mud/commands/alias_cmds.py:60-98`
- **ROM C:** `src/alias.c:112-220`
- **Fix:** Restored ROM alias listing/query/redefinition messages, reserved-word handling, quote/name validation, `delete`/`prefix` expansion guards, and `MAX_ALIAS` enforcement.
- **Tests:** `tests/integration/test_alias_command_parity.py::test_alias_command_uses_rom_messages_and_listing`, `tests/integration/test_alias_command_parity.py::test_alias_command_rejects_reserved_and_forbidden_expansions`

### `ALIAS-003` — ✅ FIXED

- **Python:** `mud/commands/dispatcher.py:847-881`, `mud/rom_api.py:281-295`
- **ROM C:** `src/alias.c:69-99`
- **Fix:** Changed alias substitution to a single pass, added truncation warnings, and fixed `mud.rom_api.substitute_alias()` to return the expanded string.
- **Tests:** `tests/integration/test_alias_command_parity.py::test_alias_substitution_is_single_pass_like_rom`

### `ALIAS-004` — ✅ FIXED

- **Python:** `mud/commands/alias_cmds.py:101-118`
- **ROM C:** `src/alias.c:236-274`
- **Fix:** Restored ROM `unalias` prompts and removal/failure messages.
- **Tests:** `tests/integration/test_alias_command_parity.py::test_unalias_uses_rom_messages`

### `ALIAS-005` — ✅ FIXED

- **Python:** `mud/commands/dispatcher.py:884-930`
- **ROM C:** `src/alias.c:49-61,88-95`
- **Fix:** Added ROM prefix-length warning handling and corrected the alias/prefix bypass set used before substitution.
- **Tests:** `tests/test_commands.py::test_prefix_macro_prepends_to_commands`

## Phase 5 — Completion

✅ `alias.c` is fully audited.

- Alias creation, lookup, substitution, and removal now mirror ROM-visible behavior.
- Alias expansion no longer recurses past one substitution.
- Prefix preprocessing now honors ROM line-length and bypass semantics.
- The `rom_api.substitute_alias()` compatibility helper now returns the expected expanded string.

Validation:
- `pytest tests/integration/test_alias_command_parity.py tests/test_alias_parity.py tests/test_commands.py::test_alias_create_expand_and_unalias tests/test_commands.py::test_alias_persists_in_save_load tests/test_commands.py::test_prefix_command_sets_changes_and_clears tests/test_commands.py::test_prefi_rejects_abbreviation tests/test_commands.py::test_prefix_macro_prepends_to_commands -q` — `23 passed`
