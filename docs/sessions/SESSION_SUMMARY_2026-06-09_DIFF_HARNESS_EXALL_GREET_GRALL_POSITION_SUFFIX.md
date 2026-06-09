# Session Summary — 2026-06-09 — Diff-harness TRIG_EXALL + TRIG_GREET/GRALL with position suffix fix

## Scope

Continuing from v2.13.53. The two items from last session's "Next Steps" that had concrete
C-oracle paths were: (1) confirm TRIG_EXALL fires without the position/visibility gate that
EXIT requires, and (2) confirm TRIG_GREET is gated on `mob->position == default_pos` while
TRIG_GRALL is the unconditional fallback. Both required placing the mob at a non-default
position before movement, which meant adding a new `__mob_position=<pos>` meta-command to
both the C shim and Python pyreplay. Adding position-setting exposed a second parity gap:
Python's `_room_occupant_line` had no position suffix logic (ROM C `show_char_to_char_0`
renders `" is resting here."`, `" is here."`, etc., based on the mob's current position
vs its default). Both gaps were fixed and verified by diff-harness replay.

## Outcomes

### `__mob_position=<pos>` meta-command — ✅ ADDED

- **C shim**: `src/diff_shim/diffmain.c` — new `__mob_position=<pos>` handler: walks
  `ch->in_room->people` looking for the first NPC, sets `mob->position = atoi(line+15)`.
- **Python**: `tools/diff_harness/pyreplay.py` — matching handler: finds first `MobInstance`
  in `char.room.people`, sets `mob.position = Position(new_pos)`.
- **Purpose**: enables scenarios that gate TRIG_EXIT/GREET (position-conditional) vs
  TRIG_EXALL/GRALL (unconditional) by moving the mob away from its default standing position.

### `mob_movement_triggers_exall` scenario — ✅ ADDED (diff-harness C-oracle)

- **Scenario**: `tools/diff_harness/scenarios/mob_movement_triggers_exall.json`
- **Golden**: `tests/data/golden/diff/mob_movement_triggers_exall.golden.json` (15 steps, C binary)
- **ROM C refs**:
  - `src/mob_prog.c:1262-1276` — `mp_exit_trigger`: EXIT fires when `mob->position ==
    default_pos && can_see(mob, ch)`; EXALL fires on direction match only, no position/
    visibility gate.
- **Design**: mob 3000 (wizard, default_pos=STANDING) loaded in room 3001. EXIT on direction 0
  blocks movement and fires when mob is STANDING. After `__mob_position=5` (RESTING), EXIT
  is gated out and EXALL fires instead. PC stays in room 3001 throughout (both triggers
  return TRUE blocking movement), confirming dispatch purely from mob speech output.
- **Fix also applied**: `__mob_prog` handler in `pyreplay.py` was APPENDING programs (FIFO),
  but ROM C PREPENDS (`prog->next = mob->pIndexData->mprogs` — LIFO). When EXIT and EXALL
  were both added, C iterated [exit, exall] but Python iterated [exall, exit]. Fixed:
  `mob.mob_programs.insert(0, prog)`.
- **Tests**: `test_python_matches_c_golden[mob_movement_triggers_exall]` — PASSED.

### `mob_movement_triggers_greet_grall` scenario — ✅ ADDED (diff-harness C-oracle)

- **Scenario**: `tools/diff_harness/scenarios/mob_movement_triggers_greet_grall.json`
- **Golden**: `tests/data/golden/diff/mob_movement_triggers_greet_grall.golden.json` (14 steps, C binary)
- **ROM C refs**:
  - `src/mob_prog.c:1325-1345` — `mp_greet_trigger`: GREET fires when `mob->position ==
    mob->pIndexData->default_pos && can_see(mob, ch)`; GRALL fires as `else if` fallback.
- **Design**: PC starts in room 3001 with wizard. `__mob_position=5` (RESTING) → `south`
  (PC leaves to room 3005) → `north` (PC arrives in 3001, triggers `mp_greet_trigger` —
  mob is RESTING so GRALL fires). `__mob_position=8` (STANDING) → `south` → `north` —
  now mob is STANDING (default_pos) so GREET fires.
- **Critical timing detail**: `__mob_position=` must be called while PC is in the SAME room
  as the mob (command searches `char.room.people`). Position is set before `south` moves
  the PC away.
- **Tests**: `test_python_matches_c_golden[mob_movement_triggers_greet_grall]` — PASSED.

### `_room_occupant_line` position suffix — ✅ FIXED (parity gap)

- **Python**: `mud/world/look.py` — added `_POSITION_SUFFIX` dict mapping `Position` →
  ROM string (`" is resting here."`, `" is here."`, etc.) and initial-cap rule, matching
  `show_char_to_char_0` (`src/act_info.c:247-424`). Mobs at non-default positions now
  render position suffix + capitalization. Dark-room path was also calling
  `describe_character` directly; fixed to call `_room_occupant_line` so it inherits the
  same logic.
- **ROM C ref**: `src/act_info.c:421` — `buf[0] = UPPER(buf[0])` after constructing the
  full character line; position suffix table at `act_info.c:393-420`.
- **Impact**: any scenario or test that observed mobs at non-default positions now gets
  the ROM-correct suffix. Two integration test assertions in
  `tests/integration/test_do_look_command.py` updated from `"Sneaky"` to `"Sneaky is here."`
  to match ROM-correct STANDING output.

## Files Modified

- `src/diff_shim/diffmain.c` — added `__mob_position=<pos>` handler
- `tools/diff_harness/pyreplay.py` — added `__mob_position=<pos>` handler; fixed `__mob_prog`
  to prepend (LIFO) instead of append
- `tools/diff_harness/scenarios/mob_movement_triggers_exall.json` — new scenario
- `tools/diff_harness/scenarios/mob_movement_triggers_greet_grall.json` — new scenario
- `tests/data/golden/diff/mob_movement_triggers_exall.golden.json` — C-oracle golden (15 steps)
- `tests/data/golden/diff/mob_movement_triggers_greet_grall.golden.json` — C-oracle golden (14 steps)
- `mud/world/look.py` — `_room_occupant_line` position suffix + capitalization; dark-room path fix
- `tests/integration/test_do_look_command.py` — updated two assertions for STANDING NPC suffix
- `CHANGELOG.md` — added [2.13.54] entry
- `pyproject.toml` — 2.13.53 → 2.13.54

## Test Status

- `pytest tests/integration/test_do_look_command.py` — 8/8 PASSED
- `pytest tests/test_differential_smoke.py` — 21 passed, 1 skipped (includes new scenarios)
- Full suite: 5,481 passed, 5 skipped (pre-commit hook clean, ruff clean)

## Next Steps

Class 11 remaining work:

1. **RNG-locked paths** (`TRIG_RANDOM`, `TRIG_DELAY`) — deferred until seed alignment has a
   grounded probe. These require careful RNG sequencing to get deterministic C output.
2. **Next divergence class** — consult `docs/parity/DIVERGENCE_CLASS_ROSTER.md` for the next
   unverified surface outside Class 11. Candidates: async message delivery ordering,
   affect-tick contracts, position-transition edges.
3. **Class 11 completeness check** — the EXIT/EXALL/GREET/GRALL deterministic paths now have
   C-oracle ground truth. Remaining untested dispatch paths are TRIG_SPEECH, TRIG_ACT,
   TRIG_BRIBE, and the RNG-gated ones above.
