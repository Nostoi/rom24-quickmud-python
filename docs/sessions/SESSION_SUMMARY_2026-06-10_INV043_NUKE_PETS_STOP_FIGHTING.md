# Session Summary — 2026-06-10 — INV-043 Nuke-Pets Stop-Fighting

## Scope

Continuation from v2.13.84 (INV-042 kill-death-XP-trigger ordering). Active pass: cross-file
invariants. Session picked up three probe candidates from the previous handoff, resolved two
as clean, and found a real ghost-pointer bug in the pet extraction path.

**Group XP penalty signed-math probe** — `_handle_death` lines 1352-1358 computes the PC
dying-penalty `c_div(2 * (floor - victim.exp), 3) + 50`. `floor - victim.exp` is negative
when the victim is over the level floor; Python correctly uses `c_div` here (confirmed at
engine.py:1358). `exp_per_level(victim)` takes only the character argument (Python's version
removes the `points` parameter ROM uses as a second arg). No gap; no INV row needed.

**`char_update` autosave slot coherence probe** — ROM `src/update.c:670-673, 892-895` uses
`save_number` (cycles 0..29) with `ch->desc->descriptor % 30 == save_number`. Python uses
`_AUTOSAVE_ROTATION = (_AUTOSAVE_ROTATION + 1) % 30` and `descriptor_id % 30 ==
_AUTOSAVE_ROTATION`. Verified: `character.desc` is always a `Session` (assigned at
`connection.py:1924, 2217` — both `char.desc = session`), and `Session.descriptor_id` is
`count(1)` (sequential integer, equivalent to ROM's sequential socket fds). The `id()`
fallback on game_loop.py:945 is dead code in production. Rotation math is identical. Gate
(`desc is not None`) matches ROM (`ch->desc != NULL`). No gap; no INV row warranted (save-once
contract holds under both `descriptor_id` and the dead-code `id()` fallback).

**`_nuke_pets` ghost fighting-pointer probe** — found a real gap. ROM `nuke_pets`
(`src/act_comm.c:1640`) calls `stop_follower(pet)` then `extract_char(pet, TRUE)`
(`src/handler.c:2103`), which internally calls `stop_fighting(pet, TRUE)` (line 2121)
before removing the pet from `char_list`. Python `_nuke_pets` performs a manual extraction
(stop_follower → remove from room → clear inventory → `character_registry.remove(pet)`)
without calling `stop_fighting`. Any character fighting the charmed pet at the moment of
extraction retains a dangling `fighting` pointer to an unregistered, unroomed mob — a ghost
pointer that `violence_update` would follow on the next combat tick. Filed as INV-043 and
fixed.

## Outcomes

### INV-043 NUKE-PETS-STOP-FIGHTING — ✅ ENFORCED (new, real bug fixed)

- **ROM C**: `src/act_comm.c:1640-1655 nuke_pets` → `src/handler.c:2103-2180 extract_char`
  → line 2121 `stop_fighting(pet, TRUE)` before removing pet from `char_list`
- **Python gap**: `mud/combat/death.py:_nuke_pets` called `stop_follower(pet)` then
  manually removed the pet from room and `character_registry` with no `stop_fighting` call;
  ghost `fighting` pointers survived on any character that was fighting the charmed pet
- **Fix**: added `_stop_fighting(pet, both=True)` in `_nuke_pets` (lines 554-562, lazy
  import from `mud.combat.engine`) — runs before `character_registry.remove(pet)` so the
  sweep has the pet in scope to match against `fighter.fighting is pet`
- **Tests**: `tests/integration/test_inv043_nuke_pets_stop_fighting.py` — 2 tests:
  - `test_nuke_pets_clears_ghost_fighting_pointer` — enemy in combat with charmed pet has
    `fighting = None` after `_nuke_pets(owner)` (was: still pointing at extracted mob)
  - `test_nuke_pets_clears_pet_fighting_pointer` — pet's own `fighting` pointer also cleared
  - Both mutation-verified: removing the `stop_fighting` call returns RED
- **Scope of callers affected**: `_nuke_pets` is called from 4 sites — `_extract_character`,
  `raw_kill` (death path), `_auto_quit_character` (autoquit), `_disconnect_extract_cleanup`
  (connection teardown). All benefit from the fix.

### Group XP penalty signed-math — ✅ CONFIRMED CLEAN

- `mud/combat/engine.py:1358` — `c_div(2 * (floor - victim.exp), 3) + 50` correctly uses
  `c_div` for the negative operand path (floor - victim.exp < 0 when PC is over floor).
  Mirrors ROM `src/fight.c:900-904` exactly. No gap.

### `char_update` autosave slot coherence — ✅ CONFIRMED CLEAN

- `mud/game_loop.py:char_update` + `mud/net/session.py:Session.descriptor_id` implement
  the 30-slot fan-out correctly. `descriptor_id = count(1)` distributes equivalently to
  ROM's socket fd numbers. `desc is not None` gate matches ROM. Rotation math is identical.
  `id()` fallback on game_loop.py:945 is dead code in production (verified grep).

## Files Modified

- `mud/combat/death.py` — `_nuke_pets`: added `stop_fighting(pet, both=True)` before
  `character_registry.remove(pet)` (+10 lines including comment)
- `tests/integration/test_inv043_nuke_pets_stop_fighting.py` — new file, 2 enforcement
  tests (+125 lines)
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-043 row added (28 enforced,
  next free: INV-044)
- `CHANGELOG.md` — `[2.13.85]` Fixed entry
- `pyproject.toml` — 2.13.84 → 2.13.85

## Test Status

- `pytest tests/integration/test_inv043_nuke_pets_stop_fighting.py -v` — **2/2 passing**
- Full suite: **5554 passed, 4 skipped** (was 5552; +2 new enforcement tests)

## Next Steps

Cross-file invariants remains the active pass. Next free INV ID: **INV-044**.

All three probe candidates from the previous handoff are resolved:
- ✅ Group XP penalty signed-math — clean (`c_div` present)
- ✅ `char_update` autosave slot coherence — clean (sequential `descriptor_id`)
- ✅ `_nuke_pets` ghost fighting-pointer — INV-043, fixed and locked

New candidate areas to probe next (none yet covered by an INV row):

1. **Affect expiry → `affect_remove` → `affect_check` ordering** — when a raw `AffectData`
   with `duration == 0` is expired by `tick_spell_effects`, Python calls `affect_remove`
   which calls `affect_modify(FALSE)` and then `affect_check`. ROM
   `src/handler.c:1317-1348 affect_remove` clears the bitvector then re-sets it only if
   another affect still provides it. The cross-file chain is
   `affects/engine.py → handler.py:affect_remove → handler.py:affect_check`. INV-015
   covers the entry point; whether `affect_check` itself is correctly re-setting bitvectors
   from remaining affects is unverified under the cross-INV lens.

2. **`do_flee` / `do_recall` position-transition coherence** — ROM `src/fight.c:3022-3095`
   calls `stop_fighting(ch, TRUE)` on both the fleeing character and the victim before
   moving the character. Python's flee path needs a probe to verify the same ordering
   (stop fighting before char_from_room).

3. **MATH-002/003/004** — ⚠️ OPEN hygiene items in `docs/parity/audits/MATH_AND_RNG.md`
   (LOW severity, no observable gap). Held for a future PARITY008 lint rule.
