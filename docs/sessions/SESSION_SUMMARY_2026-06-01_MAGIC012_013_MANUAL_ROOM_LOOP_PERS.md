# Session Summary — 2026-06-01 — MAGIC-012/013 manual-room-loop PERS masking

## Scope

Continuation of the same day's work (after CAST-009 + TRAIN-005 closed and the
full suite was pushed green at 2.12.42 — see
`SESSION_SUMMARY_2026-06-01_CAST009_TRAIN005_QUEUE_DRAIN.md`). With the
documented open-gap queue drained, opened the cross-file-invariants probe pass.
Probed two candidate areas that proved **faithful** (group/follower lifecycle —
`die_follower` correctly resets `leader=fch`, `is_same_group` is pointer-correct;
and the affect-tick engine — level-fade + RNG-roll + wear-off de-dup all match
ROM, GL-027/029 documented). Then verified the differential-harness FINDING-015
("affect spells silent on success") and discovered its `KNOWN_DIVERGENCES` note
was stale-resolved BUT surfaced a real **systematic class** the INV-025/027
PERS-masking sweep had missed.

## Outcomes

### `MAGIC-012` — ✅ FIXED (commit `14cf90c4`, 2.12.43)

- **Python**: `mud/skills/handlers.py:frenzy` (~4658)
- **ROM C**: `src/magic.c:2961` — `act("$n gets a wild look in $s eyes!", victim, NULL, NULL, TO_ROOM)`
- **Gap**: The frenzy success room line used a hand-rolled `for occupant in
  room.people` loop emitting `f"{name} gets a wild look in their eyes!"` — baked
  name (no `$n` PERS masking → leaks an invisible victim's name) + literal
  "their" (wrong vs ROM's `$s` gendered possessive).
- **Fix**: Converted to `act_to_room(room, "$n gets a wild look in $s eyes!",
  target, exclude=target)`.
- **Tests**: `tests/integration/test_magic012_frenzy_room_pers_masking.py`
  (male→"his", invisible victim→"Someone"+"her"); re-baselined
  `test_skills_buffs.py:128` ("their"→"its", a sexless Sex.NONE test char).

### `MAGIC-013` — ✅ FIXED (commit `ded5e147`, 2.12.44)

- **Python**: `mud/skills/handlers.py:cure_disease` (~2772)
- **ROM C**: `src/magic.c:1658` — `act("$n looks relieved as $s sores vanish.", victim, NULL, NULL, TO_ROOM)`
- **Gap**: Two divergences in one leg — baked name + literal "their" (MAGIC-012
  class) **and** delivery via the divergent `occupant.messages.append` mailbox
  channel instead of the immediate per-recipient path (MAGIC-003 class).
- **Fix**: Converted the dispel-success room leg to `act_to_room(room, "$n looks
  relieved as $s sores vanish.", victim, exclude=victim)` — fixes both.
- **Tests**: `tests/integration/test_magic013_cure_disease_room_pers_masking.py`
  (male→"his", invisible→"Someone"+"her"); re-baselined `test_skills_healing.py:60`
  ("their"→"its").

### Systematic class surfaced → INV-025 trail extended (not a new INV)

The 2.12.30 INV-025 pass converted the **26 `_act_room` call sites** but NOT
handlers that bake `_character_name()` into a `room.broadcast(...)` call or a
hand-rolled room loop. MAGIC-012/013 closed two of those; **~12 remain**, each
needing its exact ROM `act()` format verified before converting. The full
work-list (with line numbers and ROM lines) is recorded in the **INV-025 "Touched
by" trail** in `CROSS_FILE_INVARIANTS_TRACKER.md`: rose (2624), earthquake
(3550), sleep (7520), giant_strength (4966), haste/slow (5038/5075/7567/7604),
`$n turns translucent` (6298), stone skin (7801), trip→`$s` (7981), weaken (8163).

## Files Modified

- `mud/skills/handlers.py` — `frenzy` + `cure_disease` room legs → `act_to_room`.
- `tests/integration/test_magic012_frenzy_room_pers_masking.py` — new.
- `tests/integration/test_magic013_cure_disease_room_pers_masking.py` — new.
- `tests/test_skills_buffs.py`, `tests/test_skills_healing.py` — re-baselined
  ("their"→"its" for sexless test chars).
- `docs/parity/MAGIC_C_AUDIT.md` — MAGIC-012 ✅, MAGIC-013 ✅ rows added.
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-025 trail + remaining
  ~12-site sweep work-list.
- `CHANGELOG.md` — MAGIC-012, MAGIC-013 entries.
- `pyproject.toml` — 2.12.42 → 2.12.44.

## Test Status

- New MAGIC-012/013 tests + area suites (`test_skills_buffs`, `test_skills_mass`,
  `test_spell_buff_debuff_rom_parity`, `test_spell_area_effects_rom_parity`,
  `test_spell_affects_persistence`, `test_spell_healing_rom_parity`,
  `test_skills_healing`, holy_word) — all green (`-n0`).
- INV-025 enforcement (`test_inv025_spell_self_effect_pers_masking`,
  `test_inv025_spell_effect_act_trigger`) — 16/16 green.
- Full suite: see SESSION_STATUS (run before push).
- `act_to_room` does not consume RNG (no per-recipient roll), so unlike CAST-009
  these changes carry no global RNG-sequence shift.

## Next Steps

1. **Continue the INV-025 manual-room-loop sweep** — close the ~12 remaining
   sites (work-list in the INV-025 trail), one failing-first MAGIC-NNN commit
   each, verifying each handler's exact `src/magic.c` `act()` format string
   (don't assume — the `$s`/`$e`/`$m`/`$p` token and TO_ROOM vs TO_NOTVICT vary).
2. **Verify the dirt-kicking already-affected caster line** (`handlers.py:~3200`,
   `"{name} already has dirt in their eyes."`) — no ROM equivalent found in
   `src/`; confirm Python-invented before touching (MAGIC-013 note).
3. Other cross-file-invariants candidate areas (position transitions, mob script
   triggers) remain available once the PERS sweep is exhausted.
