# Session Summary — 2026-05-26 — `affect_check` prototype fallback (2.9.45)

## Scope

Continuation of the 2026-05-26 session that closed `check_assist`
misplacement (2.9.44, pushed). Per SESSION_STATUS, next move was the
affect-tick probe at 23/~20 INV budget. Read ROM `src/update.c:762-786
affect_update` and `src/handler.c:1317-1359 affect_remove` against the
Python equivalents in `mud/affects/engine.py:tick_spell_effects` and
`mud/handler.py:affect_remove`. The affect-tick loop and `affect_remove`
itself matched ROM cleanly; the divergence surfaced one level down in
`affect_check` (the bitvector-restoration sweep called by
`affect_remove`).

## Outcomes

### `affect_check` prototype walk — ✅ FIXED (`1ffc06f`, 2.9.45)

- **Python**: `mud/handler.py:affect_check` (lines 386-468 area) — added
  the prototype-affect fallback to the equipment walk. After iterating
  per-instance `obj.affected`, if the obj is not enchanted, iterate
  `obj.prototype.affected` (handling both `Affect` dataclass and `dict`
  entries — the loader paths produce both shapes).
- **ROM C**: `src/handler.c:1240-1257` — `for (paf =
  obj->pIndexData->affected; ...)` walk, gated on `if (obj->enchanted)
  continue;` (line 1237-1238).
- **Symptom**: a player wearing a `+sanc` ring whose `AFF_SANCTUARY`
  grant lives on the prototype (the normal ROM pattern — `.are`
  files put `A` entries on prototypes, not on every spawned instance)
  and a temporary `sanctuary` spell would lose the `AFF_SANCTUARY`
  bit when the spell expired. `affect_modify(ch, paf, FALSE)`
  inside `affect_remove` cleared the bit; `affect_check` then failed
  to find the prototype-level grant on the equipment walk and didn't
  re-set it.
- **Asymmetry**: `equip_char` / `unequip_char`
  (`mud/handler.py:179, 240`) already walked `obj.prototype.affected`
  correctly — so the bit was granted at equip time but stripped on
  any temporary-spell expiry while equipped. Only `affect_check` had
  the gap. Now symmetric.
- **Tests**: `tests/integration/test_affect_check_prototype_fallback.py`
  — 2/2:
  - `test_affect_check_walks_equipped_obj_prototype_affects` — proves
    the bug pre-fix; unenchanted ring grants `AFF_SANCTUARY` via
    prototype; `affect_check(ch, where=0, vector=SANCTUARY)` must
    re-set the bit.
  - `test_affect_check_skips_prototype_when_enchanted` — verifies the
    `obj.enchanted` gate; enchanted instance's empty per-instance
    list is authoritative.
  Full suite: **4769 passed, 4 skipped** in 628s.
- **No new INV row**: the contract ("affect_check must walk three
  layers — ch.affected → obj.affected → obj.prototype.affected") is
  intra-module to `mud/handler.py`. Filed as a regular gap-closer.

## Files Modified

- `mud/handler.py` — `affect_check` extended with prototype walk
- `tests/integration/test_affect_check_prototype_fallback.py` — NEW
  (2 tests)
- `CHANGELOG.md` — 2.9.45 section
- `pyproject.toml` — 2.9.44 → 2.9.45

## Test Status

- `tests/integration/test_affect_check_prototype_fallback.py` — 2/2 ✅
- Affect-area suites
  (`test_inv015_affect_tick_lifecycle`,
  `test_inv022_equip_applies_object_affects`,
  `test_affects.py`, `test_spell_affects_persistence.py`,
  `test_update_c_parity.py`) — 79/79 ✅
- Full suite: **4769 passed, 4 skipped** in 628s wall-clock

## Probe Notes (negative results worth recording)

The affect-tick probe also covered these contracts; all matched ROM
already, no gap to close:

- `affect_update` loop in `mud/affects/engine.py:tick_spell_effects`
  vs ROM `src/update.c:762-786`: duration decrement, the
  `number_range(0, 4) == 0` level-decay, the
  `paf_next == NULL || paf_next->type != paf->type || paf_next->duration > 0`
  msg_off suppression guard, and the split between
  `spell_effects`-managed (bare list removal + `remove_spell_effect`)
  vs raw-`AffectData` (`affect_remove`) paths. All matched.
- `affect_remove` (`mud/handler.py:445`) vs ROM
  `src/handler.c:1317-1359`: `affect_modify(FALSE)` → save `where`
  + `vector` → unlink → `affect_check`. All matched.
- `affect_check` character-affected walk and equipment per-instance
  walk vs ROM `src/handler.c:1190-1236`. Matched.

The only divergence was the prototype fallback at ROM
`src/handler.c:1240-1257` — closed by 2.9.45.

## Next Steps

1. **Push approval** required for 2.9.45 (`1ffc06f`).
   Per standing rule: do NOT push without explicit per-cluster
   approval ("yes push v2.9.45 to origin/master").
2. **GitNexus refresh** — index now stale at `5d3ce9d` (two commits
   behind: `cf126f0` 2.9.44, `1ffc06f` 2.9.45). Run
   `npx gitnexus analyze --skip-agents-md` before the next probe.
3. **Continue probe-then-scope at 23/~20 INV budget**. The affect-
   tick area is now fully ROM-correct (the prototype fallback was
   the only gap surfaced). Remaining candidates not yet covered by
   an INV row:
   - **PC-quit follower/pet cleanup vs INV-020** — INV-020 covers
     `raw_kill → die_follower`; the adjacent quit path
     (`nuke_pets` / `stop_follower(pet)`) may have a contract gap
     when a master quits with charmed pets.
   - **TRIG_KILL / TRIG_DEATH dispatch** — engine.py audit notes
     they're correctly wired but no INV row pins it; would be a
     contract-lock more than a bug find.
   - **Position-transition adjacency** — INV-016 / INV-019 cover
     the broadcast and silent-promotion-on-heal sides; the
     `update_pos` callers (do_yell, do_emote-while-down, etc.)
     could surface a missing transition.
