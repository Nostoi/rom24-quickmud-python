# Session Summary — 2026-05-26 — INV-025 (MOBPROG-ACT-TRIGGER-DISPATCH) enforced

## Scope

Closed INV-025 properly per the previous session's deferred scope. ROM
contract: ``src/comm.c:2384-2385`` — inside ``act()`` itself, every NPC
recipient with ``HAS_TRIGGER(TRIG_ACT)`` receives ``mp_act_trigger`` on
the formatted message, gated on the global ``bool MOBtrigger`` flag
(``src/comm.c:311``) which recursive paths (``do_give``, ``do_at``)
toggle FALSE around their own act() calls to prevent re-entry.

Python was missing both halves: no ``MOBtrigger`` recursion guard, and
no dispatch from broadcast surfaces into ``mp_act_trigger`` — only
``do_say`` / ``do_yell`` routed to ``mp_speech_trigger`` via the SPEECH
trigger. Every TRIG_ACT mobprog in the world silently no-opped on PC
emotes.

## Outcomes

### `INV-025` — MOBPROG-ACT-TRIGGER-DISPATCH — ✅ ENFORCED (2.9.40)

- **ROM C**: `src/comm.c:311` (`bool MOBtrigger = TRUE`),
  `src/comm.c:2384-2385` (per-recipient `mp_act_trigger` dispatch
  inside `act()`), `src/act_obj.c:832-836` (do_give recursion guard
  pattern), `src/mob_cmds.c:333-335` (do_at recursion guard pattern),
  `src/act_comm.c:1091` (do_emote — the canonical ROM TRIG_ACT
  producer).
- **Python**: `mud/mobprog.py` (new `MOBtrigger` flag,
  `disable_mobtrigger()` context manager, `mp_act_trigger_room()`
  helper); `mud/commands/communication.py:do_emote` (first wired
  callsite).
- **Fix**: three additions to `mud/mobprog.py`:
  1. Module-level `MOBtrigger: bool = True` flag (line 28).
  2. `disable_mobtrigger()` context manager (lines 31-46) that saves /
     restores the prior value on enter/exit — nesting-safe, so future
     recursive sites can stack the guard without leaking state.
  3. `mp_act_trigger_room(message, room, ch, *, arg1, arg2, exclude)`
     per-room dispatcher: iterates `room.people`, skips PCs / `ch` /
     `exclude`, fires `mp_act_trigger` per NPC, short-circuits when
     `MOBtrigger` is False.

  Wire into `mud/commands/communication.py:do_emote` after the
  per-listener fan-out so an emote string drives TRIG_ACT exactly
  once per NPC listener.
- **Tests**: `tests/integration/test_inv025_mobprog_act_trigger_dispatch.py`
  — 3 cases:
  1. `test_pc_emote_fires_act_trigger_on_listening_npc` — PC emote
     "bows deeply" in a room with NPC bearing TRIG_ACT phrase "bows"
     fires `mp_act_trigger` exactly once on the listener.
  2. `test_disable_mobtrigger_suppresses_act_trigger_dispatch` —
     with `disable_mobtrigger()` context active, the same emote
     does NOT fire any dispatch (ROM `MOBtrigger = FALSE` recursion
     guard contract).
  3. `test_act_trigger_skipped_when_emoter_is_npc` — NPC emoter does
     not self-fire its own TRIG_ACT (the `if listener is char: continue`
     loop guard).
- **Result**: 3/3 ✅. Related suites — `test_mobprog_triggers.py`,
  `test_npc_speaker_does_not_trigger_speech.py`, `test_emote_parity.py`,
  `test_act_comm_gaps.py`, `test_communication_enhancement.py`,
  `test_interp_dispatcher.py` — all 93 passing.
- **Follow-up sweep** (not new INV row): the dispatch helper is in
  place but only `do_emote` is wired. Remaining ROM act() callsites
  to broaden coverage: `do_give` (uses MOBtrigger=FALSE in ROM —
  passes through `with disable_mobtrigger():`), `do_drop`, `do_get`,
  `do_put`, `do_sacrifice`, `do_wear` / `do_remove` / `do_wield` /
  `do_hold`, position-transition broadcasts in
  `mud/combat/engine.py:apply_position_change`, the
  `_push_message` / `broadcast_room` surface for combat narration.
  Each is one-callsite-per-commit. The contract is locked at the
  emote callsite; the sweep extends coverage but cannot regress
  what INV-025 enforces.

## Files Modified

- `mud/mobprog.py` — added `MOBtrigger` flag, `disable_mobtrigger()`
  context manager, `mp_act_trigger_room()` per-room dispatcher.
- `mud/commands/communication.py:do_emote` — wired
  `mp_act_trigger_room(args, char.room, char)` after the per-listener
  fan-out.
- `tests/integration/test_inv025_mobprog_act_trigger_dispatch.py` —
  new (3 cases).
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — added INV-025
  enforced row, flipped Watch list candidate → done, updated
  budget footer to 25/~20 with consolidation candidates pre-named.
- `CHANGELOG.md` — added 2.9.40 section.
- `pyproject.toml` — 2.9.39 → 2.9.40.

## Test Status

- `pytest tests/integration/test_inv025_mobprog_act_trigger_dispatch.py`
  — 3/3 ✅.
- `pytest tests/test_mobprog_triggers.py
  tests/integration/test_npc_speaker_does_not_trigger_speech.py
  tests/integration/test_emote_parity.py
  tests/integration/test_act_comm_gaps.py
  tests/integration/test_communication_enhancement.py
  tests/integration/test_interp_dispatcher.py
  tests/integration/test_inv025_mobprog_act_trigger_dispatch.py`
  — 93/93 ✅.
- Full suite: see CI run on 2.9.40 push.

## Next Steps

INV budget hits **25 of ~20 enforced** — trips the AGENTS.md
"if list grows past ~20 entries, the per-file methodology itself
needs revisiting" threshold. Either:

1. **Continue probe-then-scope at the higher budget** if each new
   INV keeps surfacing real bugs (INV-023/INV-024 both did). The
   "~20" is a soft cap, not hard.
2. **Consolidate the four documented dual pairs** to free 4 slots
   without losing distinct contracts:
   - INV-014 (creation registry) + INV-021 (extract recursive)
     under a single OBJECT-REGISTRY-LIFECYCLE row.
   - INV-015 (affect-tick lifecycle) + INV-018 (wear-off message
     for raw affect) under AFFECT-EXPIRY-LIFECYCLE.
   - INV-023 (area.nplayer coherence) + INV-010 (room.people
     coherence) under ROOM-PEOPLE-COHERENCE.
   - INV-001 (single-delivery) + INV-002 (message routing) under
     MESSAGE-DELIVERY-COHERENCE.
3. **INV-025 follow-up sweep**: wire `mp_act_trigger_room` into
   remaining act() callsites (do_give, drop, get, put, sacrifice,
   equipment, position-transition broadcasts). Each is one
   one-callsite-per-commit. The contract is already locked; this
   widens coverage.

Recommended order: do the consolidation conversation first to bring
the budget back to ~21, then either continue the probe pass or pick
up the INV-025 follow-up sweep. The follow-up sweep is safe to
interleave with new probes — each commit is isolated.
