# Session Summary — 2026-05-30 — ACT-CAP-002 Room.broadcast + _message_room + TO_ALL caster legs

## Scope

Continuation of the same day's ACT-CAP-001 work, picking up **Next Task #1** from
`SESSION_STATUS.md`: close the three parallel room-broadcast delivery surfaces
left uncapped by the `broadcast_room` fix. ROM `act_new` (`src/comm.c:2376-2379`)
caps the first visible char of every `act()` line; `broadcast_room` was fixed in
2.11.40 but `Room.broadcast`, `_message_room`, and the TO_ALL caster legs still
delivered lowercase strings.

One parity commit will land on `feat/act-cap-002`. Version bumped to 2.11.41.

## Outcomes

### `ACT-CAP-002` (Room.broadcast + _message_room + TO_ALL caster legs) — ✅ FIXED (2.11.41)

- **ROM C**: `src/comm.c:2376-2379` (`act_new` cap) applied to three surfaces:
  - **(a)** `Room.broadcast` — the ~20-caller `act(TO_ROOM)` terminal delivery
    primitive (`mud/models/room.py:189`), now caps at entry via
    `capitalize_act_line` (same pattern as `broadcast_room` in ACT-CAP-001).
  - **(b)** `_message_room` — the object wear-off room broadcast
    (`mud/game_loop.py:334`), now caps at entry; the delegation path to
    `Room.broadcast` gets a double-cap, but `capitalize_act_line` is idempotent
    on already-capped text.
  - **(c)** The **TO_ALL caster legs** in object-spell handlers: ROM
    `act("$p fades out of sight.", ch, obj, NULL, TO_ALL)` caps for **everyone**
    including the caster, but the Python handlers split into
    `_send_to_char(caster, message)` (uncapped) + `broadcast_room(room, message,
    exclude=caster)` (now capped), producing a lowercase caster leg. Fixed by
    capping the shared `message` variable at each build site so both legs match
    ROM. Handlers: `invis`, `poison` (object), `remove_curse` (object),
    `continual_light` (object glow), `create_food`.

- **Tests**: `tests/integration/test_act_cap_002_room_broadcast.py` (8):
  Room.broadcast × 4 (plain + `{`-kludge + already-capital + exclude-sender),
  _message_room × 2 (broadcast-delegation + direct-fallback),
  invis caster leg, remove_curse caster leg.

- **Re-baseline**: 8 stale lowercase assertions flipped to their ROM-correct
  capitalized forms: `test_skills_buffs` (invis ×2 + wear-off), `test_skills_debuffs`
  (poison), `test_skills_conjuration` (mushroom + continual-light),
  `test_skills_healing` (remove_curse), `test_spell_creation_rom_parity` (mushroom
  + continual-light), `test_game_loop` (torch-out + corpse-decay +
  container-spill).

- **`broadcast_global` still NOT capped** — mixed (channels are `act()`, ROM
  weather is `send_to_char`); needs per-channel treatment, same as ACT-CAP-001.

- **`do_say`/`do_tell` still uncapped** — INV-029 cousin, tracked in
  CROSS_FILE_INVARIANTS_TRACKER.md.

## Files Modified

- `mud/models/room.py` — `Room.broadcast` caps at entry via `capitalize_act_line`
- `mud/game_loop.py` — `_message_room` caps at entry via `capitalize_act_line`
- `mud/skills/handlers.py` — `invis`, `poison`, `remove_curse`, `continual_light`,
  `create_food` cap shared TO_ALL message at build site
- `tests/integration/test_act_cap_002_room_broadcast.py` — new (8 tests)
- `tests/test_skills_buffs.py` — re-baselined invis ×2 + wear-off (lowercase → Capitalized)
- `tests/test_skills_debuffs.py` — re-baselined poison caster leg
- `tests/test_skills_conjuration.py` — re-baselined mushroom + continual-light
- `tests/test_skills_healing.py` — re-baselined remove_curse caster leg
- `tests/test_spell_creation_rom_parity.py` — re-baselined mushroom + continual-light
- `tests/test_game_loop.py` — re-baselined torch-out + corpse-decay + container-spill
- `docs/parity/FIGHT_C_AUDIT.md` — ACT-CAP-002 row flipped ⚠️ OPEN → ✅ FIXED (2.11.41)
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-029: ACT-CAP-002 cousins CLOSED
- `CHANGELOG.md` — added 2.11.41 Fixed entry
- `pyproject.toml` — 2.11.40 → 2.11.41

## Test Status

- `pytest tests/integration/test_act_cap_002_room_broadcast.py` — 8/8 passing
- Full suite: 5014 passed, 4 skipped, 0 failed (146s wall-clock)

## Next Steps

Per INV-029 / ACT-CAP-001 tracker, remaining uncapped **cousins**:

1. **`do_say` / `do_tell`** (`mud/commands/communication.py`) — INV-029 cousin;
   `test_tell_parity.py:19` notes the cap as a known deferral.
2. **`broadcast_global`** — per-channel treatment (channels vs weather); not a
   blanket chokepoint.
3. **FIGHT-032/033/034** — combat PERS / FROST-SHOCKING `$p` / auto-split (filed in
   FIGHT-031 session).
4. **VISION-002** — dark-gate same-room divergence (`vision.py` vs
   `src/handler.c:2638`).

Carried-open: xdist flakes (`test_combat_death.py`,
`test_backstab_uses_position_and_weapon`); pet-shop haggle / "now follows you"
wrong-channel (INV-001 family); `Character.pet` stale type annotation; `do_cast`
object-targeting legs.