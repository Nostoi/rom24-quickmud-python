# Session Summary — 2026-06-09 — Diff-harness C-oracle for TRIG_SURR, TRIG_FIGHT, TRIG_HPCNT + look.py parity fix

## Scope

Continuing from v2.13.55. The "Next Steps" from the ACT/BRIBE/GIVE session listed the combat-path
triggers (TRIG_SURR, TRIG_FIGHT, TRIG_HPCNT, TRIG_KILL, TRIG_DEATH) as the remaining Class 11
dispatch paths without C-oracle scenarios. This session covered the three most accessible ones —
SURR, FIGHT, and HPCNT. KILL and DEATH require mob or PC death, which needs additional meta-commands
to orchestrate deterministically; deferred.

The session also required adding a new `__mob_hp=<n>` meta-command to both C (`src/diff_shim/diffmain.c`)
and Python (`tools/diff_harness/pyreplay.py`) so that HPCNT staging does not depend on combat-RNG
damage accumulation over multiple ticks. A parity bug in `mud/world/look.py` was discovered by the
FIGHT and HPCNT C-oracle goldens: the `_room_occupant_line` FIGHTING branch emitted `"You"` instead
of `"YOU!"` when the mob's fight target was the observer. The fix mirrored all four branches from
`src/act_info.c:404-416`. A follow-up commit then added direct unit tests for all four FIGHTING
branches.

## Outcomes

### `__mob_hp=` meta-command — ✅ ADDED

- **Python**: `tools/diff_harness/pyreplay.py` — new `elif command.startswith("__mob_hp="):` block
- **C**: `src/diff_shim/diffmain.c` — new `strncmp(line, "__mob_hp=", 9)` handler (before `__set_affect_duration=`)
- **Effect**: sets `mob->hit` to the specified integer for the first NPC in the room. Enables
  HPCNT-threshold staging without combat-damage-RNG dependency.

### `mob_surr_trigger` C-oracle scenario — ✅ ADDED

- **Scenario**: `tools/diff_harness/scenarios/mob_surr_trigger.json`
- **Golden**: `tests/data/golden/diff/mob_surr_trigger.golden.json` (8 steps, C binary)
- **ROM C refs**:
  - `src/fight.c:3222-3241` — `do_surrender`: stops fighting, then calls `mp_surr_trigger(opponent, ch)`
    if the opponent is an NPC. The mob does NOT retaliate after the trigger fires.
  - `src/mob_prog.c:1207-1222` — `mp_percent_trigger`: phrase "100" always fires (`number_percent() < 100`).
- **Design**: mob 3064 (drunk, level 2) in room 3008, `__mob_prog=surr:100:say SURR trigger fired!`.
  PC does `kill drunk` then `surrender` → trigger fires, drunk says "SURR trigger fired!".
- **C oracle step 7 output**: `["\rYou surrender to the drunk!", "\rThe drunk says 'SURR trigger fired!'"]`
- **Tests**: `test_python_matches_c_golden[mob_surr_trigger]` — PASSED (no engine changes needed).

### `mob_fight_trigger` C-oracle scenario — ✅ ADDED

- **Scenario**: `tools/diff_harness/scenarios/mob_fight_trigger.json`
- **Golden**: `tests/data/golden/diff/mob_fight_trigger.golden.json` (9 steps, C binary)
- **ROM C refs**:
  - `src/fight.c:92-98` — `violence_update`: dispatches `mp_fight_trigger(ch, victim)` after each
    NPC's `multi_hit` (INV-026 dispatch site).
  - `src/mob_prog.c:1207-1222` — `mp_percent_trigger`: phrase "100" always fires.
- **Design**: mob 3064 in room 3008, `__mob_prog=fight:100:say FIGHT trigger fired!`.
  PC does `kill drunk`, then `__tick` advances violence_update once → drunk attacks and trigger fires.
  Final `look` confirms `"The drunk is here, fighting YOU!"` (the look.py parity fix below).
- **C oracle step 8 output**: `["\rThe drunk's beating misses you.", "\rThe drunk says 'FIGHT trigger fired!'", "\rYou miss the drunk."]`
- **Tests**: `test_python_matches_c_golden[mob_fight_trigger]` — PASSED (after look.py fix).

### `mob_hpcnt_trigger` C-oracle scenario — ✅ ADDED

- **Scenario**: `tools/diff_harness/scenarios/mob_hpcnt_trigger.json`
- **Golden**: `tests/data/golden/diff/mob_hpcnt_trigger.golden.json` (9 steps, C binary)
- **ROM C refs**:
  - `src/mob_prog.c:1354-1362` — `mp_hitpnt_trigger`: fires when `100*mob->hit/mob->max_hit < atoi(trig_phrase)`.
  - Called from `violence_update` after `multi_hit` (same INV-026 dispatch site as FIGHT).
- **Design**: mob 3064 in room 3008, `__mob_prog=hpcnt:50:say HPCNT trigger fired!`, then
  `__mob_hp=10` sets mob HP to 10 (29% of max). PC does `kill drunk`, then `__tick` → HPCNT
  fires (10/34 ≈ 29% < 50%).
- **C oracle step 8 output**: `["\rThe drunk's beating hits you.", "\rThe drunk says 'HPCNT trigger fired!'", "\rYou miss the drunk."]`
- **Tests**: `test_python_matches_c_golden[mob_hpcnt_trigger]` — PASSED (after look.py fix).

### `_room_occupant_line` FIGHTING branch parity fix — ✅ FIXED

- **Python**: `mud/world/look.py:49-59` — rewrote FIGHTING branch to mirror all four C cases
- **ROM C**: `src/act_info.c:404-416` — `show_char_to_char_0` POS_FIGHTING: NULL→"thin air??",
  fighting==ch→"YOU!", same_room→`PERS+"."`, else→"someone who left??"
- **Root cause**: old code called `describe_character(observer, fighting)` unconditionally, which
  returned "You" (lowercase-y) instead of "YOU!" for the observer-as-target case.
- **Discovery**: FIGHT and HPCNT C-oracle goldens contained `"The drunk is here, fighting YOU!"`
  while Python emitted `"The drunk is here, fighting You"`. The look step exposed the divergence.

### `_room_occupant_line` FIGHTING branch unit tests — ✅ ADDED

- **Tests**: `tests/integration/test_do_look_command.py` — 4 new tests
  - `test_room_occupant_line_fighting_no_target_shows_thin_air`
  - `test_room_occupant_line_fighting_observer_shows_YOU`
  - `test_room_occupant_line_fighting_same_room_shows_name_with_period`
  - `test_room_occupant_line_fighting_left_room_shows_someone_who_left`
- All four ROM `src/act_info.c:404-416` discriminant branches now have direct unit coverage.
  Previously only the `YOU!` path was exercised (indirectly, via C-oracle golden replay).

## Files Modified

- `src/diff_shim/diffmain.c` — `__mob_hp=` handler added
- `tools/diff_harness/pyreplay.py` — `__mob_hp=` handler added
- `tools/diff_harness/scenarios/mob_surr_trigger.json` — new scenario (8 steps)
- `tools/diff_harness/scenarios/mob_fight_trigger.json` — new scenario (9 steps)
- `tools/diff_harness/scenarios/mob_hpcnt_trigger.json` — new scenario (9 steps)
- `tests/data/golden/diff/mob_surr_trigger.golden.json` — C-oracle golden (8 steps)
- `tests/data/golden/diff/mob_fight_trigger.golden.json` — C-oracle golden (9 steps)
- `tests/data/golden/diff/mob_hpcnt_trigger.golden.json` — C-oracle golden (9 steps)
- `mud/world/look.py` — `_room_occupant_line` FIGHTING branch rewritten (4-case discriminant)
- `tests/integration/test_do_look_command.py` — 4 new unit tests for FIGHTING branches
- `docs/parity/DIVERGENCE_CLASS_ROSTER.md` — item 6 updated: SURR/FIGHT/HPCNT C-oracle status,
  `__mob_hp=` meta-command, look.py parity fix
- `CHANGELOG.md` — added [2.13.56] and [2.13.57] entries
- `pyproject.toml` — 2.13.55 → 2.13.57

## Test Status

- `pytest tests/test_differential_smoke.py tests/test_diff_harness_unit.py` — SURR/FIGHT/HPCNT all pass
- `pytest tests/integration/test_do_look_command.py` — 12/12 passed (8 pre-existing + 4 new)
- Full suite: **5,491 passed, 5 skipped** (run at 2.13.57 HEAD)

## Next Steps

Class 11 remaining work (in priority order):

1. **TRIG_KILL and TRIG_DEATH C-oracle scenarios** — both require a mob or PC to die, which
   needs either additional meta-commands (`__mob_hp=1` + one combat tick brings the mob close
   but RNG determines the killing blow) or a `__kill_mob` / `__set_mob_hp=0` meta-command.
   The `__mob_hp=` infrastructure added this session is a prerequisite; KILL/DEATH scenarios
   are the natural next step.
2. **RNG-locked paths** (`TRIG_RANDOM`, `TRIG_DELAY`) — deferred until a reproducible seed
   sequence is proven via a grounded probe.
3. **Next divergence class** — consult `docs/parity/DIVERGENCE_CLASS_ROSTER.md` for the next
   unverified surface outside Class 11. Candidates: async message delivery ordering, affect-tick
   edge contracts, position-transition invariants.
4. **Latent parity gap: wizard shop status** — pre-existing; Python's `_has_shop` returns False
   for mob 3000 (wizard) because the midgaard JSON area file has no `shops` section. Should be
   reviewed against shop scenario coverage before claiming shop parity is clean.
