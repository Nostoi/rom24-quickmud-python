# Session Summary — 2026-05-01 — `olc.c` `OLC-001` router closure

## Scope

Closed `OLC-001` in `docs/parity/OLC_C_AUDIT.md`: ROM-style descriptor routing for OLC input, with `string_add` precedence and OLC-first dispatch restored inside `process_command()`.

## Outcomes

### `OLC-001` — unified descriptor router

- `mud/commands/dispatcher.py`
  now calls `route_descriptor_input()` before the normal interpreter, mirroring ROM `src/comm.c:833-847`.
- `DescriptorRoute.STRING_EDIT` now routes raw input to `mud.utils.string_editor.string_add()`.
- `DescriptorRoute.OLC_EDITOR` now routes raw input to the active editor handler through `_olc_handler_from_session()`.
- Unknown editor commands fall through to the normal interpreter, preserving current user-visible behavior while `OLC-012` / `OLC-013` / `OLC-014` remain tracked as explicit fallback gaps.

### Session state synchronization

- `mud/commands/build.py`
  now keeps `session.editor_mode` synchronized with legacy `session.editor` in `_ensure_session_area`, `_ensure_session_room`, `_ensure_session_obj`, `_ensure_session_mob`, `_ensure_session_help`, and `_clear_session`.
- This bridges the already-landed descriptor plumbing (`OLC-INFRA-001`) to the live command path.

### `@`-prefixed OLC/admin command parsing

- `_split_command_and_args()` in `mud/commands/dispatcher.py`
  now treats `@redit` / `@aedit` / `@oedit` / `@medit` / `@hedit` / `@asave` as full command tokens instead of collapsing them to the single-character `@` alias.
- This restores the legacy builder entry surface used by existing OLC tests and workflows.

### Test cleanup

- `tests/test_building.py`
  had one stale expectation for the pre-parity room-name message. It now expects the ROM-faithful `Name set.` string already established by the OLC message-alignment work.

## Files changed

- `mud/commands/build.py`
- `mud/commands/dispatcher.py`
- `tests/integration/test_olc_001_run_olc_editor.py`
- `tests/test_building.py`
- `docs/parity/OLC_C_AUDIT.md`
- `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`
- `docs/sessions/SESSION_STATUS.md`

## Verification

- `pytest tests/integration/test_olc_001_run_olc_editor.py -q` → 4 passed
- `pytest tests/integration/test_olc_descriptor_state.py tests/integration/test_olc_act_001_aedit_create.py -q` → 15 passed
- `pytest tests/test_building.py -q` → 14 passed
- `pytest tests/test_olc_save.py -q` → 13 passed, 1 failing pre-existing loader issue:
  `tests/test_olc_save.py::test_roundtrip_edit_save_reload_verify`
  (`mud/loaders/obj_loader.py:_resolve_item_type_code` assumes string `item_type`, but the saved JSON provides an integer)

## Next target

Stay in `olc.c`. The next clean closure is `OLC-021` (`add_reset` insertion semantics), followed by prompt tokens (`OLC-002` / `OLC-003`) and the remaining structural/editor-table gaps (`OLC-004`..`OLC-015`).
