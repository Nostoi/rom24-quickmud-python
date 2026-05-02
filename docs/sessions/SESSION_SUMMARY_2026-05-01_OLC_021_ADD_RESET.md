# Session Summary — 2026-05-01 — `olc.c` `OLC-021` add-reset semantics locked

## Scope

Closed `OLC-021` in `docs/parity/OLC_C_AUDIT.md`: verify that Python `_add_reset()` already matches ROM `add_reset()` insertion semantics.

## Outcomes

### `OLC-021` — no code bug, stale audit row

- `mud/commands/imm_olc.py:_add_reset`
  was already ROM-equivalent under Python list storage.
- Verified cases against `src/olc.c:1192-1228`:
  - index `1` inserts at head
  - index `2` inserts after the first existing reset
  - non-positive indices append to tail
  - oversize positive indices also append to tail
- No runtime code changes were required; the gap was documentation debt rather than behavior drift.

## Files changed

- `tests/integration/test_olc_do_resets_subcommands.py`
- `docs/parity/OLC_C_AUDIT.md`
- `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`
- `docs/sessions/SESSION_STATUS.md`

## Verification

- `pytest tests/integration/test_olc_do_resets_subcommands.py -q` → 31 passed
- `pytest tests/integration/test_olc_display_resets.py -q` → 16 passed

## Next target

Stay in `olc.c`. The next clean closure is prompt-token support:

- `OLC-002` — `olc_ed_name`
- `OLC-003` — `olc_ed_vnum`
