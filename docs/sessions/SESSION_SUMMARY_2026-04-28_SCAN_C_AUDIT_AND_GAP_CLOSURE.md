# Session Summary — 2026-04-28 — `scan.c` Audit and Gap Closure

## Scope

Picked the next P2 audit candidate after closing `db2.c` earlier in the day.
`scan.c` was at 0% / ❌ Not Audited despite the `do_scan` Python implementation
already existing in `mud/commands/inspection.py`. Audited the 141-line ROM C
file end-to-end against the Python equivalent, identified three gaps, closed
all three (one IMPORTANT TO_ROOM broadcast, one IMPORTANT TO_CHAR/TO_ROOM
act() pair plus spurious-header removal, and one MINOR non-ROM fallback
removal), flipped `scan.c` to ✅ AUDITED, released as 2.6.15.

## Outcomes

### `SCAN-001` — ✅ FIXED

- **Python**: `mud/commands/inspection.py:74`
- **ROM C**: `src/scan.c:60`
- **Gap**: No-arg `do_scan` was missing the `act("$n looks all around.", ch, NULL, NULL, TO_ROOM)` broadcast.
- **Fix**: `do_scan` now calls `broadcast_room(char.room, f"{char.name} looks all around.", exclude=char)` immediately on entering the no-arg branch.
- **Tests**: `tests/integration/test_scan_broadcasts.py::test_scan_no_arg_broadcasts_looks_all_around` — passing.

### `SCAN-002` — ✅ FIXED

- **Python**: `mud/commands/inspection.py:104-110`
- **ROM C**: `src/scan.c:89-91`
- **Gap**: Directional `do_scan` was missing both `act("You peer intently $T.", TO_CHAR)` and `act("$n peers intently $T.", TO_ROOM)`, and emitted a spurious `"Looking <dir> you see:"` header. ROM builds that header into `buf` at `src/scan.c:91` but never calls `send_to_char(buf, ch)`; it's a long-standing ROM bug we replicate per parity rules.
- **Fix**: Replaced the divergent header with the ROM-faithful TO_CHAR (`"You peer intently <dir>."` returned to the scanner) and TO_ROOM (`f"{char.name} peers intently <dir>."` broadcast via `broadcast_room`). Updated 5 legacy unit tests in `tests/test_scan_parity.py` that asserted the divergent header text.
- **Tests**: `tests/integration/test_scan_broadcasts.py::test_scan_directional_emits_peer_intently_pair` — passing.

### `SCAN-003` — ✅ FIXED

- **Python**: `mud/commands/inspection.py:84-86,116-118`
- **ROM C**: `src/scan.c:48-104`
- **Gap**: Python emitted non-ROM fallback lines (`"No one is nearby."` for the no-arg branch, `"Nothing of note."` for the directional branch) when no visible characters were found. ROM emits no such fallbacks.
- **Fix**: Removed both `if len(lines) == 1: lines.append(...)` blocks. Updated 1 legacy test (`test_scan_no_exit`) that asserted the divergent fallback.
- **Tests**: `tests/integration/test_scan_broadcasts.py::test_scan_empty_room_emits_no_fallback` — passing.

## Files Modified

- `mud/commands/inspection.py` — added `broadcast_room` import; added SCAN-001 TO_ROOM broadcast; replaced SCAN-002 header with TO_CHAR/TO_ROOM act() pair; removed SCAN-003 fallback appends.
- `tests/integration/test_scan_broadcasts.py` — new file with 3 parity tests (one per gap).
- `tests/test_scan_parity.py` — updated 6 legacy unit tests to assert ROM-faithful expectations (`"You peer intently <dir>."` instead of `"Looking <dir> you see:"`).
- `docs/parity/SCAN_C_AUDIT.md` — new file; Phase 1-5 complete.
- `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` — `scan.c` row 0% Not Audited → ✅ AUDITED 100%.
- `CHANGELOG.md` — added `[2.6.15]` section + Added/Fixed entries for SCAN-001/002/003.
- `pyproject.toml` — 2.6.14 → 2.6.15.

## Test Status

- `pytest tests/integration/test_scan_broadcasts.py tests/test_scan_parity.py tests/test_spell_farsight_rom_parity.py` — 21/21 passing (3 new integration + 13 legacy unit + 5 farsight neighbour).
- Full suite not re-run this session beyond the scan-area suite; `db2.c` session earlier today already exercised 1190 integration tests.

## Next Steps

`scan.c` is closed. Next P2 audit candidates from `ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`: `healer.c` (0%, single spec_fun, smallest remaining), `alias.c` (0%, command alias system), `act_wiz.c` (40% Partial, large admin commands), `special.c` (40%, mob spec procs), `board.c` (35%). Recommend `healer.c` next as it's a single spec_fun closure and gives another ✅ on the tracker. Survey the tracker at session start and invoke `/rom-parity-audit <file>.c`.
