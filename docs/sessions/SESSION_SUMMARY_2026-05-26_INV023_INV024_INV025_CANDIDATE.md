# Session Summary — 2026-05-26 — INV-023 + INV-024 enforced, INV-025 candidate filed

## Scope

Continued the cross-file invariants probe-then-scope pass from the previous
session. Goal: pick the next two INV candidates from the open list
(MOB-PROG-TRIGGER-DISPATCH, PORTAL-TRAVEL-OBJ-DECAY, AREA-NPLAYER-COUNTER,
CONTAINER-CLOSED-VISIBILITY) and either enforce or file with a real-bug
justification per the tracker's "no padding" discipline.

## Outcomes

### `INV-023` — AREA-NPLAYER-COHERENCE — ✅ ENFORCED (2.9.37)

- **ROM C**: `src/handler.c:1491-1568` (`char_from_room` / `char_to_room`)
- **Python**: `mud/models/room.py:Room.add_character` / `Room.remove_character`
- **Bug fixed**: `mud/commands/session.py:do_recall` (lines 392-399) mutated
  `room.people` directly via `.remove`/`.append`, bypassing
  `area.nplayer` / `area.empty` / `area.age` / `room.light` accounting.
  Every cross-area recall left the source area falsely occupied (skewing
  reset gating per `src/db.c:1617-1808`) and the temple area undercounted.
- **Fix**: route through `old_room.remove_character(ch)` /
  `recall_room.add_character(ch)`.
- **Test**: `tests/integration/test_inv023_area_nplayer_coherence.py` —
  2 cases (cross-area decrement/increment + temple empty/age reset).
- **Commit**: `d8c1b6c` (pushed)

### `INV-024` — CONTAINER-CLOSED-VISIBILITY — ✅ ENFORCED (2.9.38)

- **ROM C**: `src/act_obj.c:291-295` (do_get), `:384-388` (do_put);
  `src/act_info.c:1160-1162` (look in), `:1320-1386` (examine delegate).
- **Python**: `mud/commands/inventory.py:do_get`,
  `mud/commands/obj_manipulation.py:do_put`,
  `mud/world/look.py:_look_at_object`,
  `mud/commands/info_extended.py:do_examine`.
- **Bug fixed**: `do_get` (lines 512-518) read CONT_CLOSED off the prototype
  (`container.prototype.value[1]`) instead of the OBJ_DATA instance
  (`container.value[1]`). Production container prototypes default to open;
  every freshly-spawned instance with the closed flag set on its value
  array had a transparent lid to `get all <chest>` / `get <obj> <chest>`.
  `do_put` and `look in` already read the instance correctly.
- **Fix**: switch `do_get` to instance read; align
  `tests/integration/test_container_retrieval.py:create_container` fixture
  with the AGENTS.md "Object.__post_init__ does not auto-sync value" rule
  (copy `proto.value` to instance) — the old test passed only because the
  broken `do_get` happened to mirror the fixture's broken value-sync.
- **Test**: `tests/integration/test_inv024_container_closed_visibility.py` —
  4 cases (get-all blocked, put blocked, look-in hides contents, open
  container allows transfer).
- **Commit**: `cc3f8c7` (pushed)

### `INV-025` — MOBPROG-ACT-TRIGGER-DISPATCH — 📋 CANDIDATE (filed, NOT enforced)

- **ROM C**: `src/comm.c:2384-2385` (inside `act()` itself).
- **Python**: `mud/utils/act.py:act_format` /
  `mud/net/protocol.py:broadcast_room` — no `mp_act_trigger` dispatch.
- **Gap**: ROM `act()` fires `mp_act_trigger(buf, to, ch, arg1, arg2,
  TRIG_ACT)` for every NPC recipient with `HAS_TRIGGER(TRIG_ACT)` —
  every TO_ROOM / TO_NOTVICT / TO_CHAR / TO_VICT broadcast feeds into
  mobprog dispatch. Python dispatches TRIG_ACT only via `mp_speech_trigger`
  from `do_say` / `do_yell`. Every TRIG_ACT mobprog in the world file
  silently no-ops on all non-speech act() lines.
- **Why not closed**: ROM's `MOBtrigger` global (`src/comm.c:311`, toggled
  FALSE in `do_mob` and across recursive paths in `src/act_obj.c:832-836`
  and `src/mob_cmds.c:333-335`) is the only recursion guard against a
  TRIG_ACT response that itself calls `act()` re-firing on the same mob.
  `mud/mobprog.py` has **no** recursion guard (confirmed by grep —
  no `MOBtrigger`, depth counter, or in-progress set). Wiring TRIG_ACT
  into `broadcast_room` without first porting MOBtrigger semantics would
  cause re-entry. That's audit-then-implement scope, not the one-test /
  one-commit / one-gap discipline of `/rom-gap-closer`.
- **Filed**: Watch list in `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`
  with prerequisite documented. Next session can scope it as a multi-commit
  task: (1) port MOBtrigger as a thread-local / context-manager guard in
  `mud/mobprog.py`, (2) wire `mp_act_trigger` from broadcast_room when
  recipient is NPC with TRIG_ACT, (3) write enforcement test.
- **Commit**: `935b373` (pushed, docs only)

### `PORTAL-TRAVEL-OBJ-DECAY` — probed clean, no INV filed

- Portal charge depletion (`mud/world/movement.py:580-584`) reads/writes
  `portal.value[0]` on the instance.
- Timer decay (`mud/game_loop.py:1157-1188`) honours `timer <= 0` as
  "no decay armed", routes through `_extract_obj` (covered by INV-013 /
  INV-021).
- No gap surfaced; not filed. The advisor flagged "don't pad to two when
  one comes up clean" — INV rows pin real divergences, not current-correct
  behaviour just to hit a count.

## Files Modified

- `mud/commands/session.py` — `do_recall` routes through canonical helpers
- `mud/commands/inventory.py` — `do_get` reads instance value for CONT_CLOSED
- `tests/integration/test_inv023_area_nplayer_coherence.py` — new
- `tests/integration/test_inv024_container_closed_visibility.py` — new
- `tests/integration/test_container_retrieval.py` — fixture aligned with
  AGENTS.md no-auto-sync rule
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-023 + INV-024 rows
  added, INV-025 candidate filed in Watch list, budget footer updated
- `CHANGELOG.md` — 2.9.37 / 2.9.38 / 2.9.39 sections
- `pyproject.toml` — 2.9.36 → 2.9.37 → 2.9.38 → 2.9.39

## Test Status

- `pytest tests/integration/test_inv023_area_nplayer_coherence.py` — 2/2 ✅
- `pytest tests/integration/test_inv024_container_closed_visibility.py` — 4/4 ✅
- `pytest tests/integration/test_container_retrieval.py` — green after fixture fix
- Full integration suite at 2.9.38: 2212 passed, 3 skipped
- 2.9.39 is docs-only; no test impact

## Next Steps

INV tracker now at 24 of ~20 enforced (over by four) + 1 candidate. Each
of the 24 enforced rows pinned a distinct cross-module contract, and the
two most recent (INV-023, INV-024) surfaced real production bugs — the
probe-then-scope pass is still load-bearing, not chasing diminishing
returns.

Recommended next session: **close INV-025 properly**. Scope:

1. Port MOBtrigger to `mud/mobprog.py` as a thread-local flag or
   context manager (matching ROM's `bool MOBtrigger` global at
   `src/comm.c:311`); toggle FALSE inside `do_mob` and any recursive
   path that mirrors `src/act_obj.c:832-836` / `src/mob_cmds.c:333-335`.
2. Wire `mp_act_trigger` dispatch into `broadcast_room` (or whichever
   layer owns the per-recipient delivery — needs a deliberate choice
   between `act_format` / `broadcast_room` / `_push_message`; the wrong
   layer doubles or skips delivery per INV-015's lesson).
3. Add `tests/integration/test_inv025_mobprog_act_trigger_dispatch.py`
   with one case for normal dispatch and one for the recursion guard
   (TRIG_ACT response that calls `act()` must not re-fire on the same mob).
4. Flip Watch list entry → enforced row in the tracker; budget will hit
   25 of ~20, which trips the consolidation-or-restructure threshold
   from AGENTS.md.

If consolidation becomes necessary at 25: the four obvious dual pairs
documented in the tracker footer (INV-014/021 creation/extract,
INV-015/018 affect lifecycle/wear-off, INV-023/010 PC-movement under
ROOM-PEOPLE-COHERENCE umbrella, INV-001/002 message-delivery duals).
Each merge gives back one slot.
