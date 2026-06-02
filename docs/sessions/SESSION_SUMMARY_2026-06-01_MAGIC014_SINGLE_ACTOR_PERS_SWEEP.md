# Session Summary — 2026-06-01 — MAGIC-014 single-actor `$n` PERS sweep

## Scope

Continuation of the same day (after CAST-009/TRAIN-005 and MAGIC-012/013, both
pushed green). With the documented open-gap queue drained, continued the
**INV-025 manual-room-loop PERS sweep** surfaced while closing MAGIC-012/013:
the 2.12.30 INV-025 pass converted the `_act_room` call sites but missed
handlers baking `_character_name()` into `room.broadcast(...)` / hand-rolled
`for occupant in room.people` loops. This session closed the `$n`-only
remainder as one batch (MAGIC-014) and split the one colour/`$s` outlier into a
FIGHT gap.

## Outcomes

### `MAGIC-014` — ✅ FIXED (commit `ed9b35e0`, 2.12.45)

- **Python**: `mud/skills/handlers.py` — 9 handlers (`create_rose`,
  `earthquake`, `giant_strength`, `haste`, `pass_door`, `sleep`, `slow`,
  `stone_skin`, `weaken`), ~11 room-broadcast sites.
- **ROM C**: `src/magic.c` `act("$n …", actor, NULL, NULL, TO_ROOM)` at
  1536 / 2263 / 3041 / 3088 / 3104 / 3887 / 4380 / 4420 / 4434 / 4465 / 4581.
- **Gap**: Each site baked `_character_name()` into the broadcast with an
  `if target.name else "Someone …"` ternary. Two divergences: an **invisible
  actor** leaked its name (no `can_see` gate), and a **visible NPC** rendered the
  literal "Someone …" instead of its `short_descr` (ROM `$n`→`PERS`→short_descr).
- **Fix**: all → `act_to_room(room, "$n …", actor, exclude=actor)`.
- **Batching decision (conscious)**: closed as one commit + one comprehensive
  masking test, mirroring the 2.12.30 26-site INV-025 batch — these are
  `$n`-only mechanical conversions (no per-site `$s` re-baseline, unlike
  MAGIC-012/013). This overrides the earlier INV-025 trail note that said "one
  MAGIC-NNN each"; the trail is updated to reflect the decision.
- **Tests**: `tests/integration/test_magic014_single_actor_room_pers_sweep.py`
  (haste visible→name + invisible→"Someone"; giant_strength `$n's`→"Someone's";
  earthquake caster-actor masking). Pinned 2 `slow` tests in
  `test_skills_debuffs.py` from `Sector.FIELD`→`CITY` (see below).

### FIGHT-039 — 🔄 FILED (open)

The `trip` skill self-trip line (`handlers.py:~7981`, ROM `src/fight.c:2701`
`act("{5$n trips over $s own feet!{x", ch, NULL, NULL, TO_ROOM)`) carries
colour codes + `$s` possessive (not `$n`-only), so it was split out of the
MAGIC-014 batch and filed as FIGHT-039 for a dedicated fix (model on
FIGHT-036/037 dirt-kick).

## Key finding (advisor-flagged, confirmed by the suite)

The advisor warned that `$n`→PERS renders an NPC's `short_descr`, so "visible
actor → no change" was wrong for NPCs and for the dark-room case. Running the
suites (not reasoning) caught it: 2 `slow` tests using `Sector.FIELD` rooms now
masked to "Someone" because an **outdoor room is dark at night** and the new
`can_see` gate fires — but whether it's night depends on **leaked global
`time_info.sunlight`**, so the old baked-name tests were only deterministic
because they skipped `can_see`. Fixed by pinning those rooms to `CITY` (never
dark per ROM `room_is_dark`), making the named render deterministic. This is the
correct ROM-parity outcome, not a test workaround.

## Files Modified

- `mud/skills/handlers.py` — 9 handlers' room legs → `act_to_room`.
- `tests/integration/test_magic014_single_actor_room_pers_sweep.py` — new.
- `tests/test_skills_debuffs.py` — 2 `slow` test rooms `FIELD`→`CITY`.
- `docs/parity/MAGIC_C_AUDIT.md` — MAGIC-014 row (✅).
- `docs/parity/FIGHT_C_AUDIT.md` — FIGHT-039 row (🔄 OPEN).
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-025 trail: batch closed.
- `CHANGELOG.md`, `pyproject.toml` (2.12.44→2.12.45), `README.md` (5246→5249).

## Test Status

- New MAGIC-014 test (3) + all files referencing the converted strings
  (`test_skills_buffs`, `test_skills_healing`, `test_skills_debuffs`,
  `test_spell_buff_debuff_rom_parity`, `test_spell_area_effects_rom_parity`,
  `test_skills_mass`, `test_spell_healing_rom_parity`, `test_skills_conjuration`,
  `test_skills_damage`, `test_spell_creation_rom_parity`,
  `test_magic_003_affect_message_channel`, `test_position_commands`) — green.
- **Full suite: 5249 passed, 4 skipped** (`-p no:xdist -o addopts="" -q`).
- `act_to_room` consumes no RNG, so no global RNG-sequence shift.

## Next Steps

1. **FIGHT-039** — `trip` self-trip colour/`$s`/`$n` (one commit).
2. Verify the dirt-kicking "their" caster line (MAGIC-013 note).
3. Re-probe `mud/commands/`, `mud/combat/`, `mud/spec_funs.py` for
   `room.broadcast(f"…{name}…")` baked-name patterns outside handlers.py that
   bypass `act_to_room` PERS masking.
