# Session Summary — 2026-05-31 — INV-025 magic item ACT triggers

## Scope

Continued the cross-file-invariants INV-025 sweep from the session pointer,
focusing on magic item room narrations whose ROM sites are unsuppressed
`act()` producers.

## Outcome

### INV-025 magic item sweep — ✅ FIXED (2.12.14)

- **ROM C**: `do_quaff`, `do_recite`, `do_brandish`, and `do_zap` emit room
  narrations through `act()` with no `MOBtrigger = FALSE` wrapper
  (`src/act_obj.c:1897,1955,2008,2014,2058,2121,2129,2139,2151`). Per
  `src/comm.c:2384`, NPC recipients with matching `TRIG_ACT` mobprogs receive
  `mp_act_trigger`.
- **Python**: `mud/commands/obj_manipulation.py:do_quaff` now calls
  `mp_act_trigger_room` after its room broadcast. `mud/commands/magic_items.py`
  now threads actor/arg context through its shared `_broadcast` helper and calls
  `mp_act_trigger_room` for `recite`, `brandish`, and `zap` room lines.
  `mud/mobprog.py:mp_act_trigger_room` accepts iterable excludes so zap's
  `TO_NOTVICT` line fires only for bystanders, not the actor or victim.
- **Regression**: new
  `tests/integration/test_inv025_magic_items_act_trigger_dispatch.py` locks
  quaff, recite, brandish, and zap `TO_NOTVICT` dispatch.

## Files Modified

- `mud/commands/obj_manipulation.py`
- `mud/commands/magic_items.py`
- `mud/mobprog.py`
- `tests/integration/test_inv025_magic_items_act_trigger_dispatch.py`
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`
- `CHANGELOG.md`
- `pyproject.toml`

## Verification

- `pytest -n0 tests/integration/test_inv025_magic_items_act_trigger_dispatch.py -q`
  — 4 passed.
- `pytest -n0 tests/integration/test_consumables.py -q` — 51 passed.

## Next Steps

Continue the INV-025 sweep for the remaining non-combat room narrations whose
ROM sites use unsuppressed `act()`:

1. `mud/commands/liquids.py` (`fill` / `pour` room narrations).
2. `mud/commands/thief_skills.py` room narrations.
3. Immortal command room narrations.
