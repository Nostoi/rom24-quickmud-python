# Session Summary — 2026-06-07 — Diff-Harness: sit + __char_update + affect expiration (2.13.19–2.13.20)

## Scope

Picked up from SESSION_STATUS "Next Intended Task — continue cross-INV probe-then-scope;
remaining surface areas: mob scripts, spell casting, shop interactions, affect expiration."
Two diff-harness widening tasks were completed as separate commits:

1. **`sit` position transition** — the Hypothesis state machine was missing `sit` entirely
   and had incorrect preconditions on `rest`, `sleep`, and `stand`. Fixed to match the full
   ROM position transition graph from `src/act_move.c`.

2. **Affect expiration via `__char_update`** — added `__char_update` and
   `__set_affect_duration=N` meta-commands (C shim + Python replay), then added two Hypothesis
   rules (`learn_and_cast_armor`, `char_update_tick`) that exercise the real `char_update()`
   affect-duration tick loop on both sides, including the `number_range(0,4)` level-decay RNG
   call (cf. GL-026).

## Outcomes

### `sit` position transition — ✅ FIXED (2.13.19)

- **Python**: `tools/diff_harness/generated.py` — `DeterministicNoRngDiffMachine`
- **ROM C**: `src/act_move.c` — `do_sit` (line 1249), `do_rest` (line 1110), `do_sleep`
  (line 1375), `do_stand` (line 999), `do_wake` (line 1453)
- **Gap**: `sit` rule was missing; `rest`/`sleep`/`stand` preconditions modelled only a linear
  STANDING→RESTING→SLEEPING chain, omitting SITTING as a legal source state
- **Fix**: Added `sit` rule (STANDING/RESTING → SITTING); updated `rest` precondition
  (STANDING/SITTING → RESTING); updated `sleep` precondition (any non-sleeping position);
  updated `stand` precondition (RESTING/SITTING → STANDING). `wake` precondition
  (SLEEPING → STANDING) was already correct.
- **Tests**: 20/20 diff harness + 28/28 state transition tests passing

### `__char_update` + affect-expiration rules — ✅ ADDED (2.13.20)

- **Python**: `tools/diff_harness/pyreplay.py` (handlers), `tools/diff_harness/generated.py`
  (state + rules), `src/diff_shim/diffmain.c` (C-side handlers)
- **ROM C**: `src/update.c:char_update` (line 661), affect loop (lines 762–784)
- **Gap**: No mechanism existed to drive `char_update()` on both sides; affect expiration
  (and the `number_range(0,4)` level-decay RNG stream) was untested by the harness
- **Fix**:
  - `__char_update`: calls real `char_update()` on both C and Python sides; captures output
    via the same `shim_reset_output`/`emit_output` pattern as `__tick`
  - `__set_affect_duration=N`: harness fixture that sets all active affect durations to N;
    makes ROM's hardcoded armor duration (24) practical for expiration tests (3 ticks vs 25)
  - `learn_and_cast_armor` rule: emits `__learn=armor` + `__seed=1234` + `cast 'armor'` +
    `__seed=5678` + `__set_affect_duration=2`; fires at most once per run; seed brackets
    isolate cast RNG from char_update RNG stream
  - `char_update_tick` rule: emits `__char_update`, capped at 8 per run (ROM's idle-to-limbo
    threshold is 12; cap keeps the test char in the watch room)
  - C shim rebuilt cleanly
- **Tests**: 20/20 diff harness; 5434 passed, 0 failed, 4 skipped full suite

## Files Modified

- `tools/diff_harness/generated.py` — `sit` rule + fixed `rest`/`sleep`/`stand` preconditions;
  `learned_armor`/`char_update_count` state; `learn_and_cast_armor` + `char_update_tick` rules
- `tools/diff_harness/pyreplay.py` — `__char_update` and `__set_affect_duration=` handlers
- `src/diff_shim/diffmain.c` — `void char_update(void)` forward decl; `__char_update` and
  `__set_affect_duration=` handler blocks; C shim rebuilt
- `CHANGELOG.md` — 2.13.19 and 2.13.20 entries
- `pyproject.toml` — 2.13.18 → 2.13.20

## Test Status

- **Diff harness**: 20/20 passing (`tests/test_differential_smoke.py` +
  `tests/test_diff_harness_unit.py`)
- **State transition tests**: 28/28 passing (`tests/test_state_transitions.py`)
- **Full suite**: 5434 passed, 0 failed, 4 skipped
- `ruff check .` clean

## Next Steps

1. Continue cross-INV probe-then-scope. Remaining diff-harness surface areas:
   - **Mob scripts** (`mob_prog.c`) — `mprog_driver` trigger types; no RNG alignment needed
     for `mprog_act_trigger` / `mprog_entry_trigger`
   - **Shop interactions** (`act_obj.c:do_buy/do_sell`) — gold/silver transaction verification;
     no RNG; straightforward Hypothesis rules
   - **Spell casting beyond armor** — any non-combat utility spell with observable state
     change (e.g. `detect_evil`, `fly`, `bless`); need seed alignment for the skill check
2. Cross-INV candidates still open: affect-tick ordering contracts (INV probe for
   `tick_spell_effects` call order within `char_update` vs ROM), shop transaction atomicity.
