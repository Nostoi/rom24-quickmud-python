# Session Summary — 2026-05-30 — FIGHT-032/033/034 + VISION-002

## Scope

Continuation of cross-file invariants and FIGHT.c audit gap closures. Session
picked up from SESSION_STATUS.md pointing at FIGHT-034 and VISION-002 as the
remaining open items. All four gaps closed this session:

1. **FIGHT-032** — defense TO_CHAR/TO_VICT PERS masking (parry/shield_block/dodge)
2. **FIGHT-033** — frost/shocking victim TO_CHAR lines drop `$p` weapon name
3. **FIGHT-034** — auto-split per-member line bypasses PERS + capitalize
4. **VISION-002** — dark-gate same-room divergence in `can_see_character`

Four commits: 2.11.44, 2.11.45, 2.11.46, 2.11.47.

## Outcomes

### `FIGHT-032` (defense PERS masking) — ✅ FIXED (2.11.44)

- **Python**: `mud/combat/engine.py` — `check_parry`, `check_shield_block`, `check_dodge`
- **ROM C**: `src/fight.c:1317-1370`
- **Fix**: Route all six defense messages (parry/shield_block/dodge ×
  TO_VICT/TO_CHAR) through `pers(ch/victim, recipient)` per ROM `act()` PERS
  substitution. Invisible attacker/defender rendered as "someone"; NPC defenders
  render `short_descr`.
- **Tests**: `tests/integration/test_fight_032_defense_pers.py` (7 — parry invisible
  attacker/defender/NPC, shield_block invisible attacker/defender, dodge invisible
  attacker/defender)

### `FIGHT-033` (frost/shocking victim TO_CHAR weapon name) — ✅ FIXED (2.11.45)

- **Python**: `mud/combat/engine.py` — WEAPON_FROST/SHOCKING TO_CHAR templates
- **ROM C**: `src/fight.c:664` (FROST `$p`), `:675` (SHOCKING `$p`)
- **Fix**: Thread `weapon_name` into both TO_CHAR victim lines. FROST:
  `"The cold touch of {weapon_name} surrounds you with ice."` (was missing the
  weapon name). SHOCKING: `"You are shocked by {weapon_name}."` (was generic
  "the weapon"). Re-baselined 2 stale unit assertions.
- **Tests**: `tests/integration/test_fight_033_frost_shocking_weapon_name.py` (2)

### `FIGHT-034` (auto-split PERS + capitalize) — ✅ FIXED (2.11.46)

- **Python**: `mud/combat/engine.py:_auto_split`, `mud/commands/group_commands.py:do_split`
- **ROM C**: `src/act_comm.c:1946-1962` (`do_split` via `act(TO_VICT)`)
- **Fix**: Both `_auto_split` (AUTOSPLIT loot path) and `do_split` (manual `split`
  command) now route per-recipient messages through `pers(actor, member)` +
  `capitalize_act_line`, matching ROM `act_new` cap and PERS masking. Removed
  `expand_placeholders` import from `engine.py` (no longer used there). Used
  `_send_to_char_sync` for message delivery in `do_split`. Tests establish
  group membership via `_make_group()` helper.
- **Tests**: `tests/integration/test_fight_034_auto_split_pers_cap.py` (5 — NPC
  short_descr, invisible splitter PERS mask, silver PERS+cap, gold PERS+cap,
  mixed PERS+cap)

### `VISION-002` (dark-gate same-room divergence) — ✅ FIXED (2.11.47)

- **Python**: `mud/world/vision.py:can_see_character` — dark gate
- **ROM C**: `src/handler.c:2638` (`room_is_dark(ch->in_room)`, no same-room guard)
- **Fix**: Removed the `observer_room is target_room` conjunction from the dark
  gate. ROM masks on `room_is_dark(ch->in_room)` unconditionally — an observer
  in a dark room cannot see *any* target (including cross-room), regardless of
  same-room status. Python had an extra same-room guard that let dark-room
  observers see lit-room targets, diverging from ROM. The fix makes the dark
  check key off the observer's room alone, matching ROM.
- **Tests**: `tests/integration/test_vision_002_dark_gate.py` (5 — same-room dark,
  cross-room dark, infrared same-room, infrared cross-room, lit-room sees
  dark-room target)

## Files Modified

- `mud/combat/engine.py` — FIGHT-032 (pers import + defense functions), FIGHT-033
  (frost/shocking TO_CHAR), FIGHT-034 (_auto_split PERS+cap, removed
  expand_placeholders import)
- `mud/commands/group_commands.py` — FIGHT-034 (do_split per-recipient PERS +
  capitalize, _send_to_char_sync delivery)
- `mud/world/vision.py` — VISION-002 (removed `observer_room is target_room`
  conjunction from dark gate)
- `tests/integration/test_fight_032_defense_pers.py` — new (7)
- `tests/integration/test_fight_033_frost_shocking_weapon_name.py` — new (2)
- `tests/integration/test_fight_034_auto_split_pers_cap.py` — new (5)
- `tests/integration/test_vision_002_dark_gate.py` — new (5)
- `tests/test_weapon_special_attacks.py` — re-baselined 2 stale assertions (FIGHT-033)
- `docs/parity/FIGHT_C_AUDIT.md` — flipped FIGHT-032/033/034 to ✅
- `docs/parity/HANDLER_C_AUDIT.md` — flipped VISION-002 to ✅
- `CHANGELOG.md` — added entries for all four gaps
- `pyproject.toml` — 2.11.44 → 2.11.45 → 2.11.46 → 2.11.47

## Test Status

- `pytest tests/integration/test_fight_032_defense_pers.py` — 7/7 passing
- `pytest tests/integration/test_fight_033_frost_shocking_weapon_name.py` — 2/2 passing
- `pytest tests/integration/test_fight_034_auto_split_pers_cap.py` — 5/5 passing
- `pytest tests/integration/test_vision_002_dark_gate.py` — 5/5 passing
- Full suite: 5045 passed, 4 skipped, 0 failed (parallel, ~122s wall-clock)

## Next Steps

All FIGHT.c audit gaps and HANDLER.c VISION divergences are now closed. The
per-file audit tracker shows no remaining ⚠️ Partial / ❌ Not Audited rows.
Cross-file invariants (INV-027, INV-029) are fully enforced. The next focus
area is per AGENTS.md: **cross-file invariants as primary pass** — pick a
candidate contract not yet covered by an INV row (affect ticks, position
transitions, mob script triggers, group/follower chain are current candidates),
run a 5-minute probe, then either close as a gap or file as INV-NNN.

Carried-open: known xdist flakes (`test_combat_death.py`,
`test_backstab_uses_position_and_weapon`); pet-shop haggle / "now follows you"
wrong-channel (INV-001 family); `Character.pet` stale type annotation; `do_cast`
object-targeting legs.

## Outstanding (newly surfaced)

- Pre-existing unused imports in `mud/commands/group_commands.py` (`Position`,
  `character_registry`) left alone to keep diff clean — candidate for a
  separate cleanup commit.