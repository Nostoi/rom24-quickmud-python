# Session Summary — 2026-06-11 — FIGHT-054 do_flee movement mechanism

## Scope

Continuation from v2.13.99 (FIGHT-053 closed). Active pass: cross-file invariants.
Session picked up from SESSION_STATUS.md which listed three probes under INV-044:
group-leader death handoff, `affect_update` expiry dedup, and `do_flee` position after flee.
All three were investigated; the first two had no gap; the third revealed a large structural
divergence in `do_flee`'s exit-selection mechanism (FIGHT-054).

## Outcomes

### Group-leader death handoff probe — ✅ NO GAP

- **ROM C**: `src/act_comm.c:1658-1680` — `die_follower`; `src/fight.c:raw_kill`
- **Python**: `mud/characters/follow.py:die_follower`; `mud/combat/death.py:raw_kill`
- **Finding**: Python `die_follower` correctly walks `character_registry` (ROM's `char_list`),
  sets `fch.leader = fch` for each follower of the dead leader (ROM `:1677`), clears the
  master's `pet` pointer, and calls `stop_follower`. `is_same_group` uses identity comparison
  (`aleader is bleader`). `raw_kill` correctly gates `die_follower` behind `is_npc`. No divergence.

### `affect_update` expiry dedup probe — ✅ NO GAP

- **ROM C**: `src/update.c:760-786` — affect tick loop with `should_emit` guard at `:774-775`
- **Python**: `mud/affects/engine.py:tick_spell_effects`
- **Finding**: Python's `should_emit` at lines 78-82 exactly mirrors ROM's condition:
  `paf_next is None or paf_next.type != paf.type or paf_next.duration > 0`. No divergence.

### FIGHT-054 `do_flee` exit-selection mechanism — ✅ FIXED (2.14.0)

- **Python**: `mud/commands/combat.py:do_flee`
- **ROM C**: `src/fight.c:2970-3030`
- **Gap**: Python replaced ROM's 6-attempt `number_door()` loop with a fake
  dexterity-based `number_percent()` success roll (`chance = 50 + (dex - 13) * 5`) that
  does not exist in ROM. Multiple sub-divergences:
  1. **RNG stream desync** — ROM makes up to 6 `number_door()` draws per call;
     Python drew 1 `number_percent()`.
  2. **No daze check** — ROM `fight.c:2994` checks `number_range(0, ch->daze) != 0` to
     block a flee attempt when the character is dazed; Python never read `char.daze`.
  3. **No ROOM_NO_MOB guard** — ROM `fight.c:2996-2998` prevents NPCs from fleeing into
     ROOM_NO_MOB-flagged rooms; Python had no such check.
  4. **Wrong EX_CLOSED bit** — Python checked `exit_info & 1` (EX_ISDOOR = `1<<0`) instead
     of `exit_info & 2` (EX_CLOSED = `1<<1`). A closed door was not correctly detected.
  5. **Missing POS_STANDING reset** — ROM `fight.c:2979-2980` sets `ch->position = POS_STANDING`
     when called while not fighting; Python returned the message without the position reset.
- **Fix**: replaced the dex-chance block with ROM's 6-attempt `number_door()` loop; added
  per-attempt EX_CLOSED (`& 2`) check, daze block (`rng_mm.number_range(0, daze) != 0`),
  NPC `RoomFlag.ROOM_NO_MOB` guard, and `position = Position.STANDING` reset in the
  not-fighting branch. Imported `EX_CLOSED` from `mud/models/constants.py`. Also updated
  `test_fight043_flee_xp_loss.py` (dict exits → list-of-6; `number_percent` flee-success
  patches → `number_door` patches) and `test_flee_moves_character.py` (same exit migration
  + `number_door` patch).
- **Impact analysis**: `do_flee` — LOW blast radius (0 direct callers in graph).
- **Tests**: `tests/integration/test_fight054_do_flee_mechanism.py` — **5/5 passing**
  - `test_fight054_loop_calls_number_door_six_times` — patches `number_door`; verifies
    exactly 6 calls are made before "PANIC!" when all exits are None.
  - `test_fight054_daze_blocks_flee` — patches `number_door` (return 0) + `number_range`
    (return 1); verifies daze blocks all 6 attempts even on a valid exit.
  - `test_fight054_room_no_mob_blocks_npc` — sets `dst.room_flags = ROOM_NO_MOB`;
    verifies NPC flee returns "PANIC!".
  - `test_fight054_successful_flee_uses_number_door` — warrior (no sneak): verifies
    `number_percent` is NOT called (not involved in exit selection); flee succeeds via
    `number_door(0)`.
  - `test_fight054_not_fighting_sets_position_standing` — verifies `ch.position`
    reset to `POS_STANDING` when `fighting is None`.
  - All 5 verified red before fix, green after.

## Files Modified

- `mud/commands/combat.py` — FIGHT-054: replaced `do_flee` dex-chance block with ROM
  6-attempt `number_door()` loop; added EX_CLOSED, daze, ROOM_NO_MOB, POS_STANDING fixes;
  imported `EX_CLOSED` from constants
- `tests/integration/test_fight054_do_flee_mechanism.py` — new file, 5 tests
- `tests/integration/test_fight043_flee_xp_loss.py` — updated fixtures to list-of-6 exits;
  updated 5 tests to use `number_door` patches instead of `number_percent` for flee success
- `tests/integration/test_flee_moves_character.py` — updated to use Exit object at list
  index 0; replaced `number_percent`/`number_range` patches with `number_door` patch
- `docs/parity/FIGHT_C_AUDIT.md` — FIGHT-054 filed and flipped ✅ FIXED (2.14.0)
- `CHANGELOG.md` — `[2.14.0]` Fixed entry for FIGHT-054
- `pyproject.toml` — 2.13.99 → 2.14.0

## Test Status

- `pytest tests/integration/test_fight054_do_flee_mechanism.py -v` — **5/5 passing**
- `pytest tests/integration/test_fight043_flee_xp_loss.py tests/integration/test_fight054_do_flee_mechanism.py tests/integration/test_flee_moves_character.py` — **11/11 passing**
- Full suite: **2927/2930 passing, 3 skipped** (integration run during session, exit 0)

## Next Steps

Cross-file invariants pass continues. Next free INV ID: **INV-044** (still free).

The three probes from last session's STATUS are now exhausted (group-leader death — no gap;
affect_update expiry dedup — no gap; do_flee — FIGHT-054 filed and closed). Suggested next probes:

1. **`check_assist` ASSIST_ALL vs group-assist ordering** — ROM's NPC-assist block uses a
   single `if (cond1 || cond2 || ...)` expression where group membership is condition 2.
   Python uses `if/elif` for flag checks then a separate `if ch_group...`. Verify no
   behavioral difference when BOTH a flag AND group match (likely NOT a gap, purely structural).

2. **`do_rescue` stop-fighting argument** — ROM `src/fight.c:3094-3095` calls
   `stop_fighting(ch, FALSE)` and `stop_fighting(victim, FALSE)` (not `TRUE`). Python
   `do_rescue` (`mud/commands/combat.py`) — verify it uses `FALSE` (the victim's opponents
   are NOT also stopped, unlike `do_flee`'s `TRUE`).

3. **`violence_update` position guard** — ROM `src/fight.c:2645-2651` skips characters
   where `position != POS_FIGHTING` AND `position != POS_RESTING` (sleepers don't tick
   combat). Verify Python `violence_tick` has an equivalent guard.
