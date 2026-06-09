# Session Summary — 2026-06-09 — TABLES-004 MEdit mobprog flags

## Scope

Continued Class 11 / dynamic differential widening from
`SESSION_SUMMARY_2026-06-09_ENTRY_TRIGGER_GUARD.md`. The prior handoff suggested
mob entry/greet ordering with real `mprog_flags`, so this session re-read ROM
`src/tables.c:mprog_flags[]`, `src/merc.h:TRIG_*`, ROM `medit_addmprog`
(`src/olc_act.c:4864-4910`), and Python's OLC MEdit implementation.

## Outcomes

### `TABLES-004` — ✅ FIXED

- **Python**: `mud/commands/build.py:_MPROG_TRIG_TABLE`,
  `mud/commands/build.py:_medit_addmprog`
- **ROM C**: `src/tables.c:298-314`, `src/merc.h:1971-1986`,
  `src/olc_act.c:4864-4910`
- **Gap**: MEdit's local `_MPROG_TRIG_TABLE` used shifted/non-ROM values
  (`entry` = `1<<6` instead of ROM `TRIG_ENTRY` = `D` = `1<<3`, `speech` =
  `1<<1` instead of `1<<11`, etc.) and included non-ROM object-program trigger
  names. Builder-created mobprogs could set bits the runtime `HAS_TRIGGER`
  checks did not recognize.
- **Fix**: `_MPROG_TRIG_TABLE` now derives all 16 ROM `mprog_flags[]` entries
  from `mud.mobprog.Trigger` and uses ROM table names (`hpcnt`, `random`, etc.).
- **Tests**: added `test_addmprog_sets_rom_trigger_flag_value` to assert
  `addmprog ... entry` writes `Trigger.ENTRY` to both the program row and
  `mprog_flags`.

## Files Modified

- `mud/commands/build.py` — OLC mobprog trigger table now uses canonical
  `Trigger` values.
- `tests/integration/test_olc_009_medit_missing_cmds.py` — regression coverage
  for ROM trigger bit values.
- `docs/parity/TABLES_C_AUDIT.md` — documented `TABLES-004` as fixed.
- `docs/parity/OLC_ACT_C_AUDIT.md` — noted the scoped `medit_addmprog`
  trigger-value closure while leaving the broader Tier C audit deferred.
- `CHANGELOG.md` — added `2.13.42` fixed entry.
- `pyproject.toml` — `2.13.41` → `2.13.42`.

## Test Status

- `PYTHONPATH=. pytest -q tests/integration/test_olc_009_medit_missing_cmds.py::test_addmprog_sets_rom_trigger_flag_value` — 1 passed.
- `PYTHONPATH=. pytest -q tests/integration/test_olc_009_medit_missing_cmds.py` — 31 passed.
- `PYTHONPATH=. pytest -q tests/integration/test_olc_009_medit_missing_cmds.py tests/test_mobprog_triggers.py tests/integration/test_mobprog_greet_trigger.py tests/test_movement_mobprog.py` — 42 passed.
- `ruff check .` — clean.
- `PYTHONPATH=. pytest -q` — 5466 passed, 5 skipped.
- `gitnexus_detect_changes(scope=unstaged)` — low risk, no affected execution flows.

## Next Steps

Continue Class 11 / dynamic differential widening on another deterministic
command/watch-set surface. Good next candidates:

- Add a generated or source-read probe around OLC-created mobprogs reaching the
  runtime trigger paths, now that `mprog_flags` bit values are aligned.
- Probe another non-combat lifecycle surface with primary ROM source first,
  avoiding `nuke_pets` unless a fresh source read exposes a specific missing
  contract.
