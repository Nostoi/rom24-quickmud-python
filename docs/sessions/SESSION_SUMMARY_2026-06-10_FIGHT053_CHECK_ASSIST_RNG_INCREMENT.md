# Session Summary — 2026-06-10 — FIGHT-053 check_assist RNG increment

## Scope

Continuation from v2.13.98 (FIGHT-052 closed). Active pass: cross-file invariants.
Session picked up from the SESSION_STATUS.md pointer which flagged `do_flee`/`do_recall`
stop-fighting as the next probe. Three probes were completed before a genuine gap was found.

## Outcomes

### `do_flee` stop-fighting probe — ✅ NO GAP

- **ROM C**: `src/fight.c:3022` — `stop_fighting(ch, TRUE)`
- **Python**: `mud/commands/combat.py:771` — `stop_fighting(char, True)`
- **Finding**: exact match. The SESSION_STATUS candidate that suggested ROM uses `FALSE` for
  `do_flee` was incorrect (those `FALSE` calls at `:3094-3095` belong to `do_rescue`, not
  `do_flee`). No divergence.

### `do_recall` stop-fighting probe — ✅ NO GAP

- **ROM C**: `src/act_move.c:1613` — `stop_fighting(ch, TRUE)`
- **Python**: `mud/commands/session.py:397` — `stop_fighting(ch, True)`
- **Finding**: exact match. No divergence.

### FIGHT-053 candidate — `_murder_safety_check` safe-room for PC-vs-PC — ✅ NO GAP

- **ROM C**: `src/fight.c:2861` — `do_murder` calls `is_safe(ch, victim)` which has a top-level ROOM_SAFE check
- **Python**: `mud/commands/murder.py:_murder_safety_check` — line 116: `if room_flags & RoomFlag.ROOM_SAFE`
- **Finding**: the ROOM_SAFE check sits at line 116, ABOVE all branches including the PC-vs-PC
  clan/level block. The safe-room guard applies universally. Not a gap.

### FIGHT-053 `check_assist` RNG increment — ✅ FIXED (2.13.99)

- **Python**: `mud/combat/assist.py:check_assist` (target-selection loop)
- **ROM C**: `src/fight.c:155-170`
- **Gap**: ROM's target-selection reservoir loop increments `number` inside the
  `if (number_range(0, number) == 0)` block — only when a new target is chosen (`:165`).
  Python incremented `number` unconditionally after each visible group member. With 3+ group
  members where the 2nd is not chosen: ROM calls `number_range(0, 1)` for the 3rd member
  (number stayed at 1); Python called `number_range(0, 2)` (number was erroneously 2).
  Different upper bound from the same MM RNG state → desyncs the shared combat RNG stream
  for all subsequent events this tick. Secondary effect: Python produced uniform distribution
  over group members; ROM has a biased distribution that weights later members more heavily.
- **Fix**: moved `number += 1` inside the `if rng_mm.number_range(0, number) == 0:` block
  in `check_assist`. One-line move. Adds ROM citation comment.
- **Impact analysis**: HIGH blast radius (direct callers: `violence_tick`, `aggressive_update`).
  Change is surgical — only the upper bound passed to the 3rd+ number_range call changes.
- **Tests**: `tests/integration/test_fight053_check_assist_rng_increment.py` — **1/1 passing**
  - `test_fight053_check_assist_number_increments_on_selection_only` — monkeypatches
    `can_see_character` (bypasses FOREST-sector darkness), `number_bits` (passes 50% guard),
    and `number_range` (controls return sequence). Verifies that the 3rd call receives
    `(0, 1)` not `(0, 2)` when the 2nd group member is skipped.

## Files Modified

- `mud/combat/assist.py` — FIGHT-053: `number += 1` moved inside selection if-block
- `tests/integration/test_fight053_check_assist_rng_increment.py` — new file, 1 test
- `docs/parity/FIGHT_C_AUDIT.md` — FIGHT-053 filed and flipped ✅ FIXED (2.13.99)
- `CHANGELOG.md` — `[2.13.99]` Fixed entry for FIGHT-053
- `pyproject.toml` — 2.13.98 → 2.13.99

## Test Status

- `pytest tests/integration/test_fight053_check_assist_rng_increment.py -v` — **1/1 passing**
- `pytest tests/integration/test_fight04*.py tests/integration/test_fight05*.py` — **42/42 passing**
- Full suite: not re-run this session

## Next Steps

Cross-file invariants pass continues. Next free INV ID: **INV-044** (still free).

1. **Probe group-leader death handoff** — ROM `src/act_comm.c:do_follow` / `src/fight.c:raw_kill`:
   when a group leader dies, ROM calls `stop_follower` on each follower, which clears leader
   pointers. Verify Python's `raw_kill` → `_nuke_pets` → `_extract_character` path transfers
   group leadership correctly or disbands the group per ROM. Look for INV candidate here.

2. **Probe `affect_update` expiry ordering** — ROM `src/update.c:762-786` decrements each
   `paf->duration` and removes at 0 with `affect_remove`. Verify Python `tick_spell_effects`
   (mud/affects/engine.py) handles the "multiple affects of same type" dedup check correctly
   (the `should_emit` guard that mirrors ROM `:774-775`).

3. **`check_assist` ASSIST_ALL vs group-assist ordering** — ROM's NPC-assist block uses a
   single `if (cond1 || cond2 || ...)` expression where group membership is condition 2.
   Python uses `if/elif` for flag checks then a separate `if ch_group...` for group. Verify
   this doesn't produce different behavior when BOTH a flag AND group match — both should
   set `should_assist=True`, which they do, so this is likely NOT a gap (purely structural).
