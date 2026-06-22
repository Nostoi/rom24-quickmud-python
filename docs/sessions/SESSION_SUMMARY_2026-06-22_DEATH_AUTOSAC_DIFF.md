# Session Summary — 2026-06-22 — Death Autosac Differential Coverage

## Scope

Picked up from the active cross-file invariant / differential-harness pass after
INV-054 descriptor wait buffering. The prior handoff named death auto-actions as
the next probe, specifically `PLR_AUTOSAC` after NPC death and the ROM branch in
`src/fight.c:968-979` that calls `do_sacrifice` unless `AUTOLOOT` left treasure
in the corpse.

## Outcomes

### `INV-054` — ✅ ENFORCED

- **Python**: `mud/net/connection.py:_read_player_command`,
  `mud/net/session.py:Session.pending_command`
- **ROM C**: `src/comm.c:619-623`
- **Fix**: descriptor input typed while `ch.wait > 0` is buffered and replayed
  after recovery clears, instead of dispatching early into command wait guards.
- **Tests**:
  `tests/test_networking_telnet.py::test_wait_state_buffers_command_until_recovered_per_rom`

### `death_auto_sac` — ✅ DIFFERENTIAL COVERAGE ADDED

- **Python**: `tools/diff_harness/pyreplay.py`
- **ROM C shim**: `src/diff_shim/diffmain.c`
- **ROM C**: `src/fight.c:968-979`, `src/act_obj.c:1838-1862`
- **Coverage**: added `__plr_autosac=0|1` to both replay drivers and committed
  `tools/diff_harness/scenarios/death_auto_sac.json` plus the C golden.
- **Result**: the empty-NPC-corpse `PLR_AUTOSAC` death path converges end-to-end;
  no Python behavior fix was needed.
- **Tests**:
  `tests/test_differential_smoke.py::test_python_matches_c_golden[death_auto_sac]`
  and `tests/test_diff_harness_unit.py::test_drive_python_replay_plr_autosac_meta_sets_flag`

## Files Modified

- `mud/net/session.py` — added `Session.pending_command`.
- `mud/net/connection.py` — wait-state descriptor buffering in
  `_read_player_command`.
- `tests/test_networking_telnet.py` — INV-054 regression test.
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — added INV-054 row.
- `src/diff_shim/diffmain.c` — added `__plr_autosac=0|1`.
- `tools/diff_harness/pyreplay.py` — added Python replay support for
  `__plr_autosac=0|1`.
- `tools/diff_harness/scenarios/death_auto_sac.json` — new autosac scenario.
- `tests/data/golden/diff/death_auto_sac.golden.json` — C oracle golden.
- `tests/test_diff_harness_unit.py` — autosac meta-command unit coverage.
- `tests/test_differential_smoke.py` — scenario-count comment refreshed.
- `tools/diff_harness/README.md` — documented the new meta-command.
- `CHANGELOG.md` — added Unreleased entries.
- `pyproject.toml` — `2.14.211` → `2.14.212`.

## Test Status

- `PYTHONPATH=. pytest -n0 tests/test_diff_harness_unit.py::test_drive_python_replay_plr_autosac_meta_sets_flag` — 1 passed.
- `PYTHONPATH=. pytest -n0 tests/test_differential_smoke.py::test_python_matches_c_golden --override-ini addopts='' -k death_auto_sac` — 1 passed, 51 deselected.
- `PYTHONPATH=. pytest -n0 tests/test_networking_telnet.py tests/integration/test_inv038_idle_timer_input_reset.py tests/integration/test_still_recovering_single_delivery.py tests/integration/test_skill_registry_delivery_channel.py` — 23 passed.
- `PYTHONPATH=. pytest tests/test_differential_smoke.py tests/test_diff_harness_unit.py` — 83 passed.
- `PYTHONPATH=. pytest` — 6037 passed, 4 skipped.
- `ruff check .` — clean.
- `make -f Makefile.diffshim diffshim` — C shim rebuilt.
- `gitnexus_detect_changes()` — HIGH risk because the harness edit touches
  `src/diff_shim/diffmain.c:main`, the C oracle's top-level driver. Reviewed
  with `gitnexus_context`; no incoming callers, and the touched path is the new
  harness-only `__plr_autosac` branch.

## Next Steps

Continue death auto-action widening. The remaining suggested probe is grouped
reward `PLR_AUTOSPLIT`; that likely needs a deterministic grouped-PC harness
setup before it can be diffed cleanly against ROM.
