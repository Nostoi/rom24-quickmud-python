# Session Summary — 2026-05-01 — `OLC-002`, `OLC-003` prompt tokens

## What landed

- Closed `OLC-002` and `OLC-003` from `docs/parity/OLC_C_AUDIT.md`.
- Ported ROM `src/olc.c:67-144` prompt helpers into `mud/utils/prompt.py`.
- `%o` now renders the active editor label from descriptor OLC state:
  `AEdit`, `REdit`, `OEdit`, `MEdit`, `MPEdit`, `HEdit`.
- `%O` now renders the active editor target from descriptor OLC state:
  `area.vnum`, live `room.vnum`, `obj_proto.vnum`, `mob_proto.vnum`,
  MPCODE vnum when present, and help keywords for `ED_HELP`.
- The prompt code prefers `session.editor_mode` and tolerates the legacy
  `session.editor` string as a fallback so existing builder paths keep working
  while the OLC cluster remains partially migrated.

## Files touched

- `mud/utils/prompt.py`
- `tests/integration/test_prompt_rom_parity.py`
- `docs/parity/OLC_C_AUDIT.md`
- `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`
- `docs/sessions/SESSION_STATUS.md`

## Verification

- `pytest tests/integration/test_prompt_rom_parity.py -q`
- `pytest tests/integration/test_olc_descriptor_state.py tests/integration/test_olc_001_run_olc_editor.py -q`

## Notes

- GitNexus impact on `bust_a_prompt` was `MEDIUM`: 9 direct callers, with the
  live connection prompt path as the main runtime surface. The implementation
  stayed narrow to `%o` / `%O`.
- The unrelated failure in
  `tests/test_olc_save.py::test_roundtrip_edit_save_reload_verify` remains
  open in `mud/loaders/obj_loader.py:_resolve_item_type_code`.

## Next intended task

Stay in `olc.c` and close the next structural shell gaps:

- `OLC-004` / `OLC-005` — `show_olc_cmds` / `show_commands`
- `OLC-010` / `OLC-015` — top-level `olc` dispatcher
- `OLC-006`..`OLC-009` / `OLC-011`..`OLC-014` — data-driven editor tables,
  `aedit` flag toggle, and explicit interpreter fallback alignment
