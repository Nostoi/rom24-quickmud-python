# Session Summary — 2026-06-06 — Diff-Harness Phase C Widening: hold + eat

## Scope

Picked up from SESSION_STATUS (2026-06-04) "Continue Phase C deterministic
diff-harness widening on adjacent no-RNG paths." The `DeterministicNoRngDiffMachine`
covered weapon/armor lifecycle (sword, jacket) and container put/get (bag). This
session added two new object types — a **light source** (torch 3030, `hold`/`remove`
slot) and **food** (bread 3011, `eat` + consumption) — plus explicit live C-oracle
tests for each. The eat scenario immediately surfaced a test-character-initialization
divergence in `drive_python_replay`'s `condition` array.

## Outcomes

### Widening: torch (3030) — `hold` / `remove` light source

- **State machine**: new `_ObjectState` fields `hold_command`, `eat_command`,
  `consumed`; torch rules (`load_torch`, `get_torch`, `hold_torch`, `remove_torch`,
  `drop_torch`) with preconditions.
- **C-oracle test**: `test_generated_light_hold_cycle_matches_live_c` —
  deterministic sequence `__oload=3030 → get torch → hold torch → remove torch →
  drop torch`. Exercising `WearLocation.HOLD` for the first time in the generated
  harness. **PASSED immediately** (Python already matched ROM on `do_hold` +
  `remove` for light sources).

### Widening: bread (3011) — `eat` food

- **State machine**: bread rules (`load_bread`, `get_bread`, `eat_bread`) with
  `consumed` tracking; bread is a consumable (gone after `eat`).
- **C-oracle test**: `test_generated_eat_food_matches_live_c` — deterministic
  sequence `__oload=3011 → get bread → eat bread`.
- **Surfaced divergence**: C golden returned `"You are too full to eat more."`
  while Python returned `"You eat a bread."`.
- **Root cause (NOT an engine bug):** the C diff shim initializes
  `ch->pcdata->condition[COND_FULL] = 48` (`diffmain.c:456-458`), which triggers
  ROM's `condition[COND_FULL] > 40` gate in `do_eat` (`src/act_obj.c:1310`).
  Python's `drive_python_replay` did not set `char.condition` at all, so the
  `condition[_COND_FULL] > 40` check in `do_eat` (`mud/commands/consumption.py:60`)
  was a no-op. Fixed by initializing `char.condition = [0, 48, 48, 48]` in
  `drive_python_replay`, matching the C shim's defaults. The `do_eat` code itself
  is ROM-correct.

### Files Modified

- `tools/diff_harness/generated.py` — added `hold_command`/`eat_command`/`consumed`
  fields to `_ObjectState`; torch (3030) and bread (3011) objects + 10 new rules;
  `_object_exists` now checks `consumed`.
- `tools/diff_harness/pyreplay.py` — `drive_python_replay` now initializes
  `char.condition = [0, 48, 48, 48]` matching the C shim.
- `tests/test_diff_harness_generated.py` — 2 new live C-oracle tests:
  `test_generated_light_hold_cycle_matches_live_c`,
  `test_generated_eat_food_matches_live_c`.
- `CHANGELOG.md` — added `Added` section with hold/eat widening + pyreplay
  condition init.
- `pyproject.toml` — 2.13.11 → 2.13.12.

## Test Status

- Diff harness: **27/27 passing** (7 smoke + 13 unit + 7 generated, including 2 new).
- Full suite: **5427 passed, 4 skipped** (~252s).
- `ruff check .` clean.

## Next Steps

1. Continue Phase C widening — `__mload` a mob + `give` objects/gold to mob recipients
   (deterministic, exercises `do_give` NPC path; already templated in the
   `money_drop_get_give` scenario but not in the generated state machine).
2. Add a drink container (e.g. bottle beer 3001) with `do_drink` to the state machine
   (deterministic consumption path adjacent to `eat`).
3. Position transitions (`rest`/`sleep`/`wake`/`stand`) — deterministic, exercises
   `Position` enum transitions.
4. Add RNG-locked combat scenarios only after seed alignment is proven.
