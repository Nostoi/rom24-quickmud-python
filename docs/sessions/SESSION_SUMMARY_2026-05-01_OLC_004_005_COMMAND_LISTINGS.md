# Session Summary — 2026-05-01 — `OLC-004`, `OLC-005` command listings

## What landed

- Closed `OLC-004` and `OLC-005` from `docs/parity/OLC_C_AUDIT.md`.
- Ported ROM `src/olc.c:153-175` command-table formatting into `mud/commands/build.py`.
- Active OLC sessions now handle `commands` in area, room, object, mobile, and help editors.
- The formatter preserves ROM's 15-character fixed-width columns, five commands per row, and final newline behavior.
- Command-name tables now mirror ROM `aedit_table`, `redit_table`, `oedit_table`, `medit_table`, `mpedit_table`, and `hedit_table` names. The tables are currently listing data only; the data-driven dispatcher gaps remain open as `OLC-006`..`OLC-009`.

## Files touched

- `mud/commands/build.py`
- `tests/integration/test_olc_commands_listing.py`
- `docs/parity/OLC_C_AUDIT.md`
- `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`
- `docs/sessions/SESSION_STATUS.md`

## Verification

- `pytest tests/integration/test_olc_commands_listing.py -q`
- `pytest tests/integration/test_olc_commands_listing.py tests/integration/test_olc_001_run_olc_editor.py tests/integration/test_olc_builders.py tests/integration/test_olc_act_011_name_messages.py tests/integration/test_olc_act_014_area_changed_protocol.py -q`
- `ruff check mud/commands/build.py tests/integration/test_olc_commands_listing.py`

## Notes

- GitNexus impact was acknowledged before editing:
  `_interpret_aedit` was CRITICAL; `_interpret_redit`, `_interpret_oedit`, `_interpret_medit`, and `_interpret_hedit` were HIGH.
- The implementation stayed narrow to `commands` branches and shared formatting.
- Broad legacy unit suites `tests/test_olc_aedit.py`, `tests/test_olc_oedit.py`, and `tests/test_olc_medit.py` still contain stale expectations around older OLC session and auto-create behavior; the focused integration paths are green.

## Next intended task

Stay in `olc.c` and close the next structural shell gap:

- `OLC-010` / `OLC-015` — top-level `olc <area|room|object|mobile|mpcode|hedit>` dispatcher.
- Then `OLC-011` — `aedit` area-flag toggle prefix.
