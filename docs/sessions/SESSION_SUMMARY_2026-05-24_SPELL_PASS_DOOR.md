# Session Summary — 2026-05-24 — `spell_pass_door` close-out

## Goal

Close the final documented `magic.c + magic2.c` parity gap by confirming `spell_pass_door()` ROM parity and locking it in with runtime-path integration coverage.

## Outcome

`magic.c + magic2.c` row promoted from 98% → 100%. No missing functions remain.

## ROM Source of Truth

- `src/magic.c:3864-3890` — `spell_pass_door()`
- `src/update.c:765-784` — `affect_update()` decay + wear-off broadcast

## Python Implementation (already present, verified)

- `mud/skills/handlers.py:5884` — `pass_door()` mirrors ROM line-for-line:
  - Self vs. other "already out of phase" gating (`AFF_PASS_DOOR` check)
  - `duration = number_fuzzy(level / 4)` via `rng_mm.number_fuzzy`
  - Applies `AffectFlag.PASS_DOOR` through `SpellEffect` / `apply_spell_effect`
  - Sends `"You turn translucent."` to the target and `"$n turns translucent."` to the room
  - Wear-off message `"You feel solid again."` fires through the standard affect-expiry path
- `data/skills.json` registers the spell with `function: "pass_door"`, `target: "self"`, `mana_cost: 20`, `lag: 12`.
- `mud/world/movement.py:226-230` already honors `AffectFlag.PASS_DOOR` for closed-door traversal (existing test coverage in `tests/test_movement_doors.py`).

## New Coverage

`tests/integration/test_spell_affects_persistence.py::TestSpellPassDoorIntegration`:

1. `test_pass_door_persists_and_wears_off_through_point_pulses` — proves the affect survives sub-`PULSE_TICK` ticks, drains through `run_point_pulses()`, drops `AffectFlag.PASS_DOOR`, and emits `"You feel solid again.\n\r"` exactly once on the real `game_tick()` cadence.
2. `test_pass_door_duplicate_cast_during_active_affect_is_rejected` — proves a re-cast on an already-affected target returns `False`, leaves duration untouched, and sends the ROM `"You are already out of phase."` message.

## Docs / Bookkeeping

- `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` — P0-3 row 98% → 100%, missing-functions list cleared, next-steps cleared.
- `pyproject.toml` — version `2.8.72` → `2.8.73`.
- `CHANGELOG.md` — new `[2.8.73]` entry documents the close-out and new coverage.
- `docs/sessions/SESSION_STATUS.md` — snapshot updated.

## Verification

- `pytest tests/integration/test_spell_affects_persistence.py::TestSpellPassDoorIntegration -v` → 2 passed
- `pytest tests/test_spell_buff_debuff_additional_rom_parity.py -k pass_door -q` → 3 passed (regression-safe)
- `pytest tests/integration/ -q` → see next-task verification block

## Next Intended Task

Pick the next partial/not-audited subsystem from `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`.
