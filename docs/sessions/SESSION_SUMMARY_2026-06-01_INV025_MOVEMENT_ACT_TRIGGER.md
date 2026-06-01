# Session Summary — 2026-06-01 — INV-025 movement/quit/scan ACT trigger dispatch

## Scope

Continued the INV-025 cross-file-invariant sweep from the session pointer.
The next surfaces were directional movement departure/arrival broadcasts,
portal entry/fade-out broadcasts, the quit broadcast, and scan/peer
broadcasts — all ROM `act(TO_ROOM)` calls with no `MOBtrigger` wrap that
Python had routing through plain `broadcast_room` without `mp_act_trigger`
dispatch.

## Outcomes

### Movement departure/arrival — ✅ CLOSED

- **Python**: `mud/world/movement.py:446-450` (directional departure/arrival),
  `:561,593` (portal departure/arrival), `:648,658` (portal fade-out)
- **ROM C**: `src/act_move.c:197,202`; `src/act_enter.c:134,151,204,209-210`
- **Fix**: after each `broadcast_room` call in `move_character` and
  `move_character_through_portal`, added `mp_act_trigger_room` dispatch with
  the correct actor and arg1 threading. Sneaking characters suppress the
  broadcast lines (and therefore TRIG_ACT), matching ROM's
  `!IS_AFFECTED(ch, AFF_SNEAK) && ch->invis_level < LEVEL_HERO` guard.
  Portal fade-out dispatches with the traveller or first witness as actor,
  matching ROM `act_enter.c:204,209-210`.

### Quit broadcast — ✅ CLOSED

- **Python**: `mud/commands/session.py:63`
- **ROM C**: `src/act_comm.c:1482` — `act("$n has left the game.", ch, NULL, NULL, TO_ROOM)`
- **Fix**: added `mp_act_trigger_room` dispatch after the quit broadcast.

### Scan/peer broadcasts — ✅ CLOSED

- **Python**: `mud/commands/inspection.py:76,111`
- **ROM C**: `src/scan.c:60` (`"$n looks all around."`), `:90`
  (`"$n peers intently $T."`)
- **Fix**: added `mp_act_trigger_room` dispatch after both `broadcast_room` calls.

## Files Modified

- `mud/world/movement.py` — added INV-025 `mp_act_trigger_room` dispatch for
  directional departure, directional arrival, portal departure, portal
  arrival, and portal fade-out broadcasts.
- `mud/commands/session.py` — added INV-025 `mp_act_trigger_room` dispatch for
  the quit broadcast.
- `mud/commands/inspection.py` — added INV-025 `mp_act_trigger_room` dispatch
  for scan-all and scan-direction peer broadcasts; added import.
- `tests/integration/test_inv025_movement_act_trigger_dispatch.py` — new
  enforcement tests (8: departure, arrival, sneaking suppression, portal
  departure, portal arrival, quit, scan-all, scan-direction).
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-025 sweep entry:
  movement/quit/scan dispatch.
- `docs/sessions/SESSION_STATUS.md` — updated to 2.12.22.
- `CHANGELOG.md` — added INV-025 movement/quit/scan entry under Fixed.
- `pyproject.toml` — 2.12.21 → 2.12.22.

## Test Status

- `pytest -n0 tests/integration/test_inv025_movement_act_trigger_dispatch.py -v`
  — 8/8 passing.
- `pytest tests/integration/test_inv025_*.py -q` — 66/66 passing.
- `pytest tests/ -k "movement or quit or scan" -q` — 94/94 passing.
- Lint: `ruff check` clean on all modified Python files.

## Next Steps

Continue the broader INV-025 sweep for remaining non-combat narrations whose
matching ROM sites use `act()` and Python still only calls `broadcast_room`
without `mp_act_trigger`. Remaining high-value surfaces:

1. **Spell-effect room broadcasts** in `mud/skills/handlers.py` (~30+
   `broadcast_room` calls without `mp_act_trigger`). These are the largest
   remaining surface: bless, cancellation wear-off messages, chain_lightning,
   faerie_fire/fog, gate, invis, mass_invis, holy_word, etc.
2. **Healer utterance** in `mud/commands/healer.py:234` — ROM
   `src/healer.c:183` uses `act("$n utters the words '$T'.", ... TO_ROOM)`.
3. **Spec_fun broadcasts** in `mud/spec_funs.py` — the `_broadcast_room` and
   `_broadcast_room_message` helpers do not dispatch TRIG_ACT.
4. **Remaining movement-adjacent calls**: recall departure/arrival,
   gate/teleport/word_of_recall in `mud/skills/handlers.py`.