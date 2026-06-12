# Session Summary — 2026-06-12 — FIGHT-061: do_flee sector-based move cost, PC guard, exhaustion check

## Scope

Continuation from v2.14.7 (FIGHT-060 closed). The session ran the three cross-file invariant
probe candidates listed in the previous handoff — `check_assist` ASSIST_PLAYERS level check,
`update_pos` position branches, and `group_gain` party-size scaling — plus additional probes
of `tick_spell_effects` affect-tick ordering and `do_flee` movement deduction.

Four probes were clean; one real divergence was found in `do_flee` (FIGHT-061).

## Probe Results

| Candidate | ROM C reference | Python equivalent | Verdict |
|-----------|----------------|-------------------|---------|
| `check_assist` ASSIST_PLAYERS level check | `src/fight.c:116-124` | `mud/combat/assist.py:64-70` | ✅ CLEAN — `rch_level + 6 > victim_level` matches ROM exactly |
| `update_pos` position branches | `src/fight.c:1404-1435` | `mud/combat/engine.py:update_pos` | ✅ CLEAN — all HP thresholds (DEAD/MORTAL/INCAP/STUNNED) and NPC vs PC guards match ROM |
| `group_gain` party-size scaling | `src/fight.c:1736-1788` | `mud/groups/xp.py:group_gain` | ✅ CLEAN — uses `room.people`, NPC level//2 contribution, PC-only XP award all match ROM |
| `tick_spell_effects` affect-tick ordering | `src/update.c:wear-off` | `mud/affects/engine.py:tick_spell_effects` | ✅ CLEAN — last-affect-of-type dedup via `next_affect` check matches ROM |
| `do_flee` movement deduction | `src/fight.c:3001-3002`, `src/act_move.c:115-193` | `mud/commands/combat.py:do_flee` | ❌ DIVERGENCE — three bugs: wrong formula, no PC guard, no exhaustion check → filed+closed as FIGHT-061 |

## Outcomes

### `FIGHT-061` — ✅ FIXED

- **Python**: `mud/commands/combat.py:do_flee` (line ~768 pre-fix)
- **ROM C**: `src/fight.c:3001-3002`, `src/act_move.c:115-193`
- **Divergence**: ROM's `do_flee` calls `move_char(ch, door, FALSE)` which applies movement
  cost inside a `!IS_NPC(ch)` guard using the sector-average formula
  `(movement_loss[in_sector] + movement_loss[out_sector]) / 2`. If `ch->move < move`,
  `move_char` returns without moving (causing that flee attempt to fail silently; the 6-attempt
  loop continues). Python used `max(0, char.move - c_div(char.max_move, 10))` applied to ALL
  characters unconditionally after a successful flee. Three independent bugs:
  1. **Wrong formula**: `max_move/10` instead of sector average. A level-10 PC with max_move=100
     in a FIELD→FIELD flee would pay 10 instead of the correct 2.
  2. **Missing IS_NPC guard**: NPCs had move deducted; ROM never deducts for NPCs.
  3. **Missing exhaustion check**: a PC with `move=0` could still flee; ROM would fail all 6
     attempts if `ch->move < cost`, returning "PANIC! You couldn't escape!".
- **Fix**: Added sector-based cost computation inside the 6-attempt loop, after the destination
  room is resolved but before `remove_character`/`add_character`. Added IS_NPC guard (skips cost
  block for NPCs). Added `if char.move < cost: continue` that mirrors `move_char`'s exhaustion
  early-return. Introduced module-level `_FLEE_MOVEMENT_LOSS` dict matching `src/act_move.c:50-52`.
  Replaced the post-loop `max(0, char.move - c_div(char.max_move, 10))` with
  `if flee_move_cost > 0: char.move -= flee_move_cost`. Added `Sector` to the constants import.
- **Tests**: `tests/integration/test_fight061_flee_move_cost.py` (3 cases):
  - `test_fight061_pc_flee_uses_sector_cost` — FIELD→FIELD cost=2; PC with move=5 ends at 3 (not 0 from old formula)
  - `test_fight061_npc_flee_no_move_deduction` — NPC with move=50 ends at 50 after successful flee
  - `test_fight061_exhausted_pc_cannot_flee` — PC with move=1 (< cost=2) gets PANIC across all 6 attempts
  All 3 verified red before fix, green after.

## Files Modified

- `mud/commands/combat.py` — added `Sector` import; added `_FLEE_MOVEMENT_LOSS` module-level
  dict; inserted PC-only sector-cost + exhaustion check inside the flee attempt loop; replaced
  post-loop flat deduction with `char.move -= flee_move_cost`
- `tests/integration/test_fight061_flee_move_cost.py` — new integration test (3 cases)
- `docs/parity/FIGHT_C_AUDIT.md` — added FIGHT-061 row (✅ FIXED 2.14.8)
- `CHANGELOG.md` — added `[2.14.8]` Fixed entry
- `pyproject.toml` — 2.14.7 → 2.14.8

## Test Status

- `pytest tests/integration/test_fight061_flee_move_cost.py -n0` — 3/3 passing
- `pytest tests/integration/test_fight054_do_flee_mechanism.py tests/integration/test_fight043_flee_xp_loss.py tests/integration/test_fight061_flee_move_cost.py -n0` — 13/13 passing (no regression in related flee tests)
- Full suite: **5614/5614 passing, 4 skipped** (run 2026-06-12, post-fix)

## Next Steps

All five probe candidates from this session have been verified. FIGHT-061 is closed. The
cross-file invariants pass continues. Suggested next probe areas:

1. **`do_recall` movement cost** — ROM `src/act_move.c:do_recall` (near `do_flee`) also calls
   `move_char` for the movement. Verify whether Python's `do_recall` similarly has the correct
   sector-based deduction or reuses a different formula.
2. **`violence_update` round-ordering / stop-fighting gate** — ROM `src/fight.c:63-103`
   `violence_update` sets `rch_next` before the loop body and skips dead characters. Verify
   Python `violence_tick` in `mud/game_loop.py` handles character death mid-tick (character
   removed from registry during iteration) safely.
3. **`do_rescue` target-selection and multi-hit ordering** — ROM `src/fight.c:3032-3107`
   `do_rescue` re-routes the attacker's target with `stop_fighting(victim, FALSE)` and
   `multi_hit(victim, ch, ...)`. Verify Python `do_rescue` in `mud/commands/combat.py` mirrors
   this order exactly and doesn't double-call `stop_fighting`.
