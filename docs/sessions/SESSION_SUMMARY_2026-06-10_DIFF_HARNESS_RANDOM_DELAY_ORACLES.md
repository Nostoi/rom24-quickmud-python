# Session Summary — 2026-06-10 — Diff-harness C-oracle for TRIG_RANDOM and TRIG_DELAY

## Scope

Continuing from v2.13.58. The "Next Steps" from the KILL/DEATH session listed
TRIG_RANDOM and TRIG_DELAY as the final two Class 11 dispatch paths without
C-oracle scenarios. Both require `mobile_update()` to run (not `violence_update`
or `char_update`). This session added `__mobile_update` + `__mob_delay=N`
meta-commands to both the C shim and Python replay, then captured C-oracle
goldens for both triggers.

## Key insight corrected

The previous session's handoff described TRIG_RANDOM as requiring "a seed that
aligns a 1-in-8 roll." This was incorrect — the 1-in-8 roll belongs to the
wander/scavenge path that comes *after* the trigger block. TRIG_RANDOM fires
every `mobile_update` tick when `position == default_pos` and
`number_percent() < atoi(trig_phrase)`. With `trig_phrase=101`, it is
unconditional (as with KILL/DEATH/FIGHT/etc. in prior scenarios).

## Outcomes

### `__mobile_update` meta-command — ✅ ADDED

- **C**: `src/diff_shim/diffmain.c` — `mobile_update` extern declared; new
  `strncmp(line, "__mobile_update", 15)` handler calls `mobile_update()`.
- **Python**: `tools/diff_harness/pyreplay.py` — imports and calls
  `mud.ai.mobile_update()`.
- **ROM C ref**: `src/update.c:408 mobile_update()`.

### `__mob_delay=N` meta-command — ✅ ADDED

- **C**: `src/diff_shim/diffmain.c` — `strncmp(line, "__mob_delay=", 12)` handler;
  sets `mob->mprog_delay = N` on the first NPC in the room.
- **Python**: `tools/diff_harness/pyreplay.py` — sets `mob.mprog_delay = N`
  on the first `MobInstance` in the room.
- **ROM C ref**: `src/mob_prog.c:mp_delay_trigger` countdown.

### `mob_random_trigger` C-oracle scenario — ✅ ADDED + PASSING

- **Scenario**: `tools/diff_harness/scenarios/mob_random_trigger.json`
- **Golden**: `tests/data/golden/diff/mob_random_trigger.golden.json` (7 steps)
- **Design**: mob 3064 (drunk, level 2) in room 3008, `__mob_prog=random:101:say
  RANDOM trigger fired!`. `__mobile_update` fires trigger unconditionally.
- **C oracle step 6 output**: `"The drunk says 'RANDOM trigger fired!'"` confirmed.
- **Tests**: `test_python_matches_c_golden[mob_random_trigger]` — PASSED first try.

### `mob_delay_trigger` C-oracle scenario — ✅ ADDED + PASSING

- **Scenario**: `tools/diff_harness/scenarios/mob_delay_trigger.json`
- **Golden**: `tests/data/golden/diff/mob_delay_trigger.golden.json` (8 steps)
- **Design**: mob 3064 in room 3008, `__mob_prog=delay:101:say DELAY trigger
  fired!`, `__mob_delay=1`. One `__mobile_update` decrements delay 1→0 and fires.
- **C oracle step 7 output**: `"The drunk says 'DELAY trigger fired!'"` confirmed.
- **Tests**: `test_python_matches_c_golden[mob_delay_trigger]` — PASSED first try.

### Stale golden removed

`tests/data/golden/diff/mob_death_test.golden.json` — leftover dev-run artifact
from commit `c49ccff1` (scenario was renamed to `mob_death_trigger` before that
commit was pushed). No matching scenario file existed; the replay test was silently
skipping it. Removed to avoid confusion.

## Files Modified

- `src/diff_shim/diffmain.c` — `mobile_update` extern + `__mobile_update` +
  `__mob_delay=N` handlers added
- `tools/diff_harness/pyreplay.py` — `__mobile_update` + `__mob_delay=N` handlers
  added
- `tools/diff_harness/scenarios/mob_random_trigger.json` — new scenario (7 steps)
- `tools/diff_harness/scenarios/mob_delay_trigger.json` — new scenario (8 steps)
- `tests/data/golden/diff/mob_random_trigger.golden.json` — C-oracle golden
- `tests/data/golden/diff/mob_delay_trigger.golden.json` — C-oracle golden
- `tests/data/golden/diff/mob_death_test.golden.json` — deleted (stale)
- `CHANGELOG.md` — added [2.13.59] entry
- `pyproject.toml` — 2.13.58 → 2.13.59

## Test Status

- `pytest tests/test_differential_smoke.py tests/test_diff_harness_unit.py` — 38/38
  passed (2 new: mob_random_trigger, mob_delay_trigger)
- Full suite: pending at time of write (expected ~5,493+ passed)

## Class 11 Coverage — COMPLETE

All 15 Class 11 mobprog dispatch paths now have C-oracle diff-harness ground truth:

| Trigger | Scenario |
|---------|---------|
| TRIG_EXIT | mob_movement_triggers.json |
| TRIG_EXALL | mob_movement_triggers_exall.json |
| TRIG_GREET | mob_movement_triggers_greet_grall.json |
| TRIG_GRALL | mob_movement_triggers_greet_grall.json |
| TRIG_SPEECH | mob_speech_trigger.json |
| TRIG_ACT | mob_act_trigger.json |
| TRIG_BRIBE | mob_bribe_trigger.json |
| TRIG_GIVE | mob_give_trigger.json |
| TRIG_SURR | mob_surr_trigger.json |
| TRIG_FIGHT | mob_fight_trigger.json |
| TRIG_HPCNT | mob_hpcnt_trigger.json |
| TRIG_KILL | mob_kill_trigger.json |
| TRIG_DEATH | mob_death_trigger.json |
| TRIG_RANDOM | mob_random_trigger.json ← **new** |
| TRIG_DELAY | mob_delay_trigger.json ← **new** |

## Next Steps

Class 11 is now complete. Next divergence class candidates:

1. **Next divergence class** — consult `docs/parity/DIVERGENCE_CLASS_ROSTER.md`
   for the next unverified surface. Candidates: async message delivery ordering,
   affect-tick edge contracts, position-transition invariants.
2. **Latent parity gap: wizard shop status** — Python's `_has_shop` returns False
   for mob 3000 (wizard) because the midgaard JSON area file has no `shops`
   section. C's midgaard.are defines wizard as a shopkeeper.
