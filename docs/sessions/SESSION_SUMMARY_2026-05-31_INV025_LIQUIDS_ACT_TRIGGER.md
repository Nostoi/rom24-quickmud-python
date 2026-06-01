# Session Summary — 2026-05-31 — INV-025 liquids ACT triggers

## Scope

Continued the cross-file-invariants INV-025 sweep from the session pointer,
focusing on `fill` / `pour` room narrations whose ROM sites are unsuppressed
`act()` producers.

## Outcome

### INV-025 liquids sweep — ✅ FIXED (2.12.15)

- **ROM C**: `do_fill` and `do_pour` emit visible liquid narrations through
  unsuppressed `act()` calls (`src/act_obj.c:1025,1075,1142,1151,1155`).
  Per `src/comm.c:2384`, NPC recipients with matching `TRIG_ACT` mobprogs
  receive `mp_act_trigger`.
- **Python**: `mud/commands/liquids.py:do_fill` and `do_pour` now dispatch
  `TRIG_ACT` after the existing visible delivery for fill, pour-out,
  object-target pour, and character-target pour's `TO_VICT` / `TO_NOTVICT`
  recipient split.
- **Regression**: new
  `tests/integration/test_inv025_liquids_act_trigger_dispatch.py` locks all
  four liquid command paths.

## Files Modified

- `mud/commands/liquids.py`
- `tests/integration/test_inv025_liquids_act_trigger_dispatch.py`
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`
- `docs/sessions/SESSION_STATUS.md`
- `CHANGELOG.md`
- `pyproject.toml`

## Verification

- `pytest -n0 tests/integration/test_inv025_liquids_act_trigger_dispatch.py -q`
  — 4 passed.
- `pytest -n0 tests/integration/test_consumables.py -q` — 51 passed.

## Next Steps

Continue the INV-025 sweep for remaining non-combat room narrations whose ROM
sites use unsuppressed `act()`:

1. `mud/commands/thief_skills.py` room narrations.
2. Immortal command room narrations.
