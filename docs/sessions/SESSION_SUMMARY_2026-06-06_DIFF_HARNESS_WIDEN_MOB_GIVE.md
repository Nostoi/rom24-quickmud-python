# Session Summary — 2026-06-06 — Diff-Harness Phase C Widening: mob + give (2.13.13)

## Scope

Picked up from SESSION_STATUS (2026-06-06) "Next Intended Task — mob + give."
Added `__mload` (mob spawn) + `give` (object/gold/silver transfer to NPC) to
the `DeterministicNoRngDiffMachine` deterministic diff harness. This exercises
the `do_give` command path for NPC recipients — previously absent from the
generated state machine (only templated in the `money_drop_get_give` static
scenario).

## Outcomes

### Widening: mob (drunk 3064) + `give` object/gold/silver

- **`_MobState` dataclass**: new model for tracking spawned mobs (vnum, keyword,
  room, gold, silver).
- **State machine**: drunk mob (vnum 3064, keyword "drunk") + 4 new rules:
  `load_drunk` (with `__seed` re-normalization around `__mload=3064`),
  `give_sword_to_drunk`, `give_gold_to_drunk` (2 gold), `give_silver_to_drunk`
  (25 silver).
- **Gold/silver tracking**: `self.player_gold` / `self.player_silver` fields
  initialized to 10/200 in `__init__`; meta-commands `__silver=200` `__gold=10`
  prepended to all generated scenarios in `teardown`.
- **Watch set**: `teardown` now auto-adds `"drunk"` (and any future mobs) to
  `watch_chars` so the C oracle snapshots the mob's hp/gold/silver/inventory.
- **C-oracle test**: `test_generated_mob_give_matches_live_c` — deterministic
  sequence `__oload=3021 → get sword → __mload=3064 → give sword drunk → give
  2 gold drunk → give 25 silver drunk`. Verifies player inventory (sword gone,
  gold/silver decremented) and mob purse (gold 0→2, silver 0→25).

### Bug discovered and fixed: GIVE-013

The C oracle test immediately surfaced **GIVE-013**: `do_give` in
`mud/commands/give.py` called `victim.add_object(obj)` but `MobInstance` has no
`add_object` method (only `Character` does). ROM's `src/handler.c:obj_to_char`
works on any `CHAR_DATA *` pointer (PC or NPC). Fixed by routing through the
existing universal `_obj_to_char(obj, victim)` in `mud/game_loop.py`, which
dispatches to `Character.add_object` or `MobInstance.add_to_inventory` as
appropriate.

### Bug discovered and fixed: Room people list ordering (FINDING-028)

The Hypothesis state machine surfaced a room-people list ordering divergence:
ROM `char_to_room` (`src/handler.c:1497-1503`) head-inserts into
`pRoomIndex->people` (LIFO — last-arrived occupant first). Python's
`Room.add_character` was using `append` (FIFO), so `look` output listed room
occupants in the opposite order. Observed as C listing `drunk` before `Hassan`
but Python listing `Hassan` before `drunk` after `__mload=3064` → `north` →
`south`. Fixed by changing `self.people.append(char)` to
`self.people.insert(0, char)` in `mud/models/room.py:154`, matching the INV-039
head-insert convention already applied to objects.

### Files Modified

- `tools/diff_harness/generated.py` — added `_MobState` dataclass, drunk mob,
  4 give rules, gold/silver tracking, watch_chars auto-include, __silver/__gold
  prepend in teardown.
- `mud/commands/give.py` — GIVE-013 fix: `victim.add_object(obj)` →
  `_obj_to_char(obj, victim)` (universal PC/NPC transfer).
- `mud/models/room.py` — Room-people ordering fix: `append` → `insert(0, char)`
  (ROM LIFO head-insert, FINDING-028).
- `tests/test_diff_harness_generated.py` — 1 new live C-oracle test:
  `test_generated_mob_give_matches_live_c`.
- `CHANGELOG.md` — Added `__mload`+`give` widening + GIVE-013 + room-people
  ordering fixes.
- `pyproject.toml` — 2.13.12 → 2.13.13.

## Test Status

- Diff harness: **28/28 passing** (7 smoke + 13 unit + 8 generated, including 1 new).
- Hypothesis state machine: **passing** (generates sequences with mob rules, C matches).
- Give integration tests: **19/19 passing** (`test_give_command.py` +
  `test_give001_*.py` + `test_inv025_*.py` + `test_mobprog_give_trigger.py`).
- `ruff check .` clean.

## Next Steps

1. Continue Phase C widening:
   - **Drink container** — bottle beer (3001, `ITEM_DRINK_CON`) with `do_drink`
     (deterministic consumption path adjacent to `eat`).
   - **Position transitions** — `rest`/`sleep`/`wake`/`stand` (deterministic,
     exercises `Position` enum transitions).
2. Add RNG-locked combat scenarios only after seed alignment is proven.
