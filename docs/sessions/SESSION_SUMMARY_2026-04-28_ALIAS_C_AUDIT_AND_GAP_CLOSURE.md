# Session Summary — 2026-04-28 — `alias.c` Audit and Gap Closure

## Scope

Picked the next remaining P2 file after `healer.c`: `alias.c`. The Python
port had the rough alias feature in place, but ROM-visible behavior still
diverged in several places: the `alia` typo guard, `alias` list/set/query
messages, validation rules, `unalias` messaging, recursive alias expansion,
and prefix-length handling before alias substitution. Audited `src/alias.c`
end-to-end, identified five gameplay-visible gaps, and closed all five with
focused parity coverage.

## Outcomes

### `ALIAS-001` — ✅ FIXED

- **Python**: `mud/commands/typo_guards.py`
- **ROM C**: `src/alias.c:97-100`
- **Gap**: `alia` returned a generic typo-guard string instead of ROM’s exact `do_alia` message.
- **Fix**: Restored `"I'm sorry, alias must be entered in full.\n\r"`.
- **Tests**: `tests/integration/test_alias_command_parity.py::test_alias_command_uses_rom_messages_and_listing` — passing.

### `ALIAS-002` — ✅ FIXED

- **Python**: `mud/commands/alias_cmds.py`
- **ROM C**: `src/alias.c:112-220`
- **Gap**: `do_alias` used non-ROM list/set output and skipped ROM query mode, validation rules, and alias-limit enforcement.
- **Fix**: Restored ROM list/query/set/realias messages, reserved-word handling, quote/name validation, `delete`/`prefix` expansion guards, and `MAX_ALIAS == 5`.
- **Tests**: `tests/integration/test_alias_command_parity.py::test_alias_command_uses_rom_messages_and_listing`, `tests/integration/test_alias_command_parity.py::test_alias_command_rejects_reserved_and_forbidden_expansions` — passing.

### `ALIAS-003` — ✅ FIXED

- **Python**: `mud/commands/dispatcher.py`, `mud/rom_api.py`
- **ROM C**: `src/alias.c:69-99`
- **Gap**: alias substitution recursed through chains instead of running a single ROM pass, and the `rom_api` compatibility helper returned a tuple instead of the expanded string.
- **Fix**: Switched to single-pass expansion, added ROM truncation warnings, and fixed `mud.rom_api.substitute_alias()`.
- **Tests**: `tests/integration/test_alias_command_parity.py::test_alias_substitution_is_single_pass_like_rom` — passing.

### `ALIAS-004` — ✅ FIXED

- **Python**: `mud/commands/alias_cmds.py`
- **ROM C**: `src/alias.c:236-274`
- **Gap**: `do_unalias` emitted usage/help text and non-ROM removal/failure messages.
- **Fix**: Restored ROM `unalias` prompt and removal/failure strings.
- **Tests**: `tests/integration/test_alias_command_parity.py::test_unalias_uses_rom_messages` — passing.

### `ALIAS-005` — ✅ FIXED

- **Python**: `mud/commands/dispatcher.py`
- **ROM C**: `src/alias.c:49-61,88-95`
- **Gap**: prefix preprocessing before alias substitution skipped the ROM overlong-line warning and used a non-ROM bypass rule.
- **Fix**: Added `Line to long, prefix not processed.\r\n` handling and corrected the blocked-prefix set to match ROM `prefix`.
- **Tests**: `tests/test_commands.py::test_prefix_macro_prepends_to_commands` — passing.

## Files Modified

- `mud/commands/alias_cmds.py` — restored ROM alias/unalias validation, output, query mode, and alias-limit semantics.
- `mud/commands/dispatcher.py` — restored single-pass alias expansion plus ROM warning/truncation behavior.
- `mud/commands/typo_guards.py` — restored the ROM `alia` message.
- `mud/rom_api.py` — fixed the compatibility helper return value.
- `tests/integration/test_alias_command_parity.py` — new integration parity coverage for `alias.c`.
- `tests/test_alias_parity.py` — updated stale chain expectations to single-pass ROM behavior.
- `tests/test_commands.py` — updated legacy alias output expectations to ROM strings.
- `docs/parity/ALIAS_C_AUDIT.md` — new audit doc with Phase 1-5 completion.
- `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` — flipped `alias.c` from ❌ Not Audited to ✅ AUDITED.
- `docs/sessions/SESSION_STATUS.md` — advanced the current-state pointer from `healer.c` to `alias.c`.
- `CHANGELOG.md` — added `[Unreleased]` `ALIAS-001`..`005` entries.

## Test Status

- `pytest tests/integration/test_alias_command_parity.py tests/test_alias_parity.py tests/test_commands.py::test_alias_create_expand_and_unalias tests/test_commands.py::test_alias_persists_in_save_load tests/test_commands.py::test_prefix_command_sets_changes_and_clears tests/test_commands.py::test_prefi_rejects_abbreviation tests/test_commands.py::test_prefix_macro_prepends_to_commands -q` — `23/23` passing.
- Full suite not re-run this session.

## Next Steps

`alias.c` is closed. The next obvious P2 targets are larger partial files:
`act_wiz.c` (40%), `special.c` (40%), and `board.c` (35%).
