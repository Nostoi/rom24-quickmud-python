# act_obj.c Consumables & Special-Object Commands — Parity Audit

**Subsystem scope (P1-7 follow-up)**: consumable and special-object commands sourced from
`src/act_obj.c`. This audit covers eight commands and their Python counterparts.

**ROM C reference**: `src/act_obj.c`

| Command     | ROM C lines | Python module                                | Status |
|-------------|-------------|----------------------------------------------|--------|
| `do_eat`    | 1284–1365   | `mud/commands/consumption.py`                | ⚠️ Partial — missing PILL handling, condition deltas, room messages |
| `do_drink`  | 1161–1280   | `mud/commands/consumption.py`                | ⚠️ Partial — missing drunk gating, COND_FULL/COND_HUNGER updates, liq_table-driven amount |
| `do_quaff`  | 1865–1906   | `mud/commands/obj_manipulation.py`           | ✅ Largely faithful (uses get_obj_carry, level check, all 3 spell slots, extract) |
| `do_recite` | 1910–1974   | `mud/commands/magic_items.py`                | ❌ Broken at runtime — references missing `find_char_in_room`, `find_obj_in_room`, `SkillTarget` |
| `do_brandish` | 1978–2064 | `mud/commands/magic_items.py`                | ❌ Broken at runtime — `ItemType.ITEM_STAFF` does not exist; `SkillTarget` undefined |
| `do_zap`    | 2068–2157   | `mud/commands/magic_items.py`                | ❌ Broken at runtime — `ItemType.ITEM_WAND` does not exist; missing helpers |
| `do_pour`   | 1033–1159   | `mud/commands/liquids.py`                    | ⚠️ Partial — uses `equipped` instead of `equipment` slot, no `vch` TO_VICT/TO_NOTVICT, fixed message text |
| `do_fill`   | 965–1032    | `mud/commands/liquids.py`                    | ⚠️ Mostly faithful — TO_ROOM message missing, no `liq_name` interpolation tested |

All eight commands are wired into `mud/commands/dispatcher.py`.

---

## Critical defects (must fix before tests can exercise these commands)

`mud/commands/magic_items.py` will raise `AttributeError` / `NameError` the first time a
player invokes `recite`, `brandish`, or `zap`:

1. `ItemType.ITEM_STAFF` and `ItemType.ITEM_WAND` — the enum members are `ItemType.STAFF`
   (4) and `ItemType.WAND` (3). See `mud/models/constants.py:285-317`.
2. `find_char_in_room` and `find_obj_in_room` are referenced but never imported. ROM
   uses `get_char_room` / `get_obj_here`; Python equivalents live in
   `mud/world/char_find.py` and `mud/world/obj_find.py`.
3. `SkillTarget` is referenced as a bare name throughout `obj_cast_spell`, `do_brandish`,
   and elsewhere but is never imported — likely should come from
   `mud.models.constants` or `mud.skills.target`.

**Recommendation**: replace `ItemType.ITEM_STAFF`/`ITEM_WAND` with
`ItemType.STAFF`/`WAND`; add the missing imports; replace
`getattr(ch, "equipment", {}).get("held")` with the canonical equipment lookup
(`get_eq_char` style helper) used elsewhere in the codebase.

---

## do_eat (act_obj.c:1284-1365)

**ROM behaviour**:
- `one_argument` -> "Eat what?" if blank.
- `get_obj_carry(ch, arg, ch)` -> "You do not have that item." (note: `ch.inventory`).
- Immortals bypass type/full checks; mortals must hold ITEM_FOOD or ITEM_PILL.
- Mortals reject when `condition[COND_FULL] > 40` -> "You are too full to eat more."
- TO_ROOM `"$n eats $p."` and TO_CHAR `"You eat $p."`.
- ITEM_FOOD: `gain_condition(COND_FULL, value[0])` and `gain_condition(COND_HUNGER, value[1])`.
  - Hunger transition messages: "no longer hungry" or "You are full." gates.
  - If `value[3] != 0` -> poison TO_ROOM gag, choke message, AFFECT (gsn_poison,
    `level=number_fuzzy(value[0])`, `duration=2*value[0]`, `bitvector=AFF_POISON`).
- ITEM_PILL: cast `value[1..3]` via `obj_cast_spell` at `value[0]` level.
- Always `extract_obj(obj)`.

**Python (`consumption.py:18-84`) gaps**:
- ❌ ITEM_PILL not handled — only ItemType.FOOD accepted.
- ❌ Uses `ch.condition['hunger']` arbitrary scalar instead of ROM `condition[COND_FULL]`
  + `condition[COND_HUNGER]`; ROM updates BOTH counters per food, with separate
  thresholds. Position check uses `Position.RESTING` minimum but ROM imposes no such
  restriction in `do_eat` (the dispatcher already handles min position).
- ❌ Reads `value[0]` as hunger gain (with default 5); ROM reads `value[1]` for hunger
  and `value[0]` for full.
- ❌ No "You are too full" pre-check (ROM blocks > 40 full).
- ❌ TO_ROOM message ("$n eats $p.") missing.
- ❌ Poison affect uses `duration=3`/`modifier=-2` instead of ROM `duration=2*value[0]`,
  level `number_fuzzy(value[0])`, `location=APPLY_NONE`, `modifier=0`. Strength malus
  is non-canonical.
- ❌ Object destruction is hand-rolled (`_destroy_object`) instead of `extract_obj`,
  so weight/equipment indices and area registries may diverge.
- ❌ Does not search room contents — ROM's `get_obj_carry` is inventory-only here, so
  this is correct; but uses substring match instead of ROM keyword/number prefix
  matching.

## do_drink (act_obj.c:1161-1280)

**ROM behaviour**:
- Empty arg -> search room contents for `ITEM_FOUNTAIN`; otherwise `get_obj_here(ch, arg)`
  (room **and** inventory).
- Mortals with `condition[COND_DRUNK] > 10` -> "*Hic*" rejection.
- Switch on item_type:
  - ITEM_FOUNTAIN: `amount = liq_table[liquid].liq_affect[4] * 3` (infinite).
  - ITEM_DRINK_CON: empty check on `value[1]`, `amount = UMIN(liq_affect[4], value[1])`.
- Mortals with `condition[COND_FULL] > 45` -> "too full to drink more."
- TO_ROOM/TO_CHAR include the liquid name from `liq_table`.
- Updates four conditions: COND_DRUNK, COND_FULL, COND_THIRST, COND_HUNGER, each scaled
  by `liq_affect/{36,4,10,2}`.
- Threshold messages for drunk/full/thirst.
- Poisoned `value[3]` -> AFF_POISON via `affect_join`, level `number_fuzzy(amount)`,
  duration `3*amount`.
- DRINK_CON only: `if value[0] > 0` (i.e. not infinite) `value[1] -= amount`.

**Python (`consumption.py:87-198`) gaps**:
- ❌ Fountain detection requires the literal word "fountain" — ROM auto-finds the
  fountain when no argument is supplied.
- ❌ Fountain lookup uses `room.objects` (the field is `room.contents` in this codebase).
- ❌ Uses `get_obj_carry`-style inventory-only lookup; ROM uses `get_obj_here`.
- ❌ Drunk gate (`COND_DRUNK > 10`) missing.
- ❌ Full gate (`COND_FULL > 45`) missing.
- ❌ Hunger/full/drunk condition deltas missing — only `condition['thirst']` is updated.
- ❌ Hard-coded `+10` thirst is wrong; ROM uses per-liquid `liq_affect` table.
- ❌ Decrements container by `1` per drink instead of `amount` (full sip).
- ❌ Poison effect is structurally wrong (constant duration, strength penalty).
- ❌ TO_ROOM messages missing entirely.

## do_quaff (act_obj.c:1865-1906) — `obj_manipulation.py:441-484`

- ✅ "Quaff what?" / inventory lookup / item_type guard / level check.
- ✅ Casts spells from `value[1..3]` at `value[0]` level.
- ✅ Calls `_extract_obj`.
- ⚠️ Acts as TO_CHAR only — TO_ROOM "$n quaffs $p." is missing.
- ⚠️ Spell name lookup passes `obj_value[i]` directly; ROM uses sn integer indices.
  Python codebase appears to mix string spell names and integer SNs.

## do_recite (act_obj.c:1910-1974) — `magic_items.py:124-222`

- ❌ Will raise `NameError: find_char_in_room` if a target argument is supplied.
- ⚠️ Behaviour with empty target argument is also wrong: ROM defaults `victim = ch`
  and passes `obj = NULL`; Python sets `victim = ch` correctly here, but the failure
  path is unreachable due to the import bug above.
- ⚠️ Uses `ch.inventory.remove(scroll)` instead of `extract_obj` — does not update
  global object registry.
- ⚠️ ROM extracts the scroll **always**, even on mispronunciation; Python's success
  path also extracts but only if `scroll in ch.inventory` — fragile.

## do_brandish (act_obj.c:1978-2064) — `magic_items.py:225-340`

- ❌ `ItemType.ITEM_STAFF` raises `AttributeError`; the correct member is
  `ItemType.STAFF`.
- ❌ `SkillTarget` symbol is never imported.
- ❌ Uses `ch.equipment.get("held")`; ROM uses `get_eq_char(ch, WEAR_HOLD)`. Other
  Python modules (e.g. `equipment.py`) use `WearLocation.HOLD` integer keys.
- ⚠️ Decrements charges via `staff.value[2] - 1` after success path; ROM decrements
  unconditionally via `--staff->value[2]` (always loses one charge per attempt).
- ⚠️ ROM destroys the staff via `extract_obj(staff)` when charges hit 0; Python only
  removes from equipment dict and leaves the object in memory.
- ⚠️ Wait state hard-coded to `2 * 3`; PULSE_VIOLENCE is configurable.

## do_zap (act_obj.c:2068-2157) — `magic_items.py:343-450`

- ❌ `ItemType.ITEM_WAND` raises `AttributeError`; correct member is `ItemType.WAND`.
- ❌ Same missing `find_char_in_room` / `find_obj_in_room` references.
- ❌ Same `SkillTarget` import gap.
- ⚠️ Same equipment-lookup, wait-state, and charge-decrement issues as `do_brandish`.

## do_pour (act_obj.c:1033-1159) — `liquids.py:93-198`

- ✅ "Pour what into what?" / source inventory lookup / drink-container guard.
- ✅ "out" branch clears `value[1]` and `value[3]`.
- ✅ Cross-container transfer recomputes `amount = min(out.value[1], in.value[0]-in.value[1])`.
- ⚠️ Uses `target_char.equipped` — actual attribute is `equipment`. Pour-into-character
  branch never finds held container.
- ⚠️ TO_ROOM/TO_VICT/TO_NOTVICT messages missing for all three flows.
- ⚠️ `_pour_out` returns plain text but does not broadcast to room.
- ⚠️ Self-pour check `target is source` works only when same Python instance.

## do_fill (act_obj.c:965-1032) — `liquids.py:13-90`

- ✅ Argument check, container lookup, fountain lookup, drink-con guard, liquid
  compatibility check, capacity check, value mutation.
- ⚠️ TO_ROOM "$n fills $p with %s from $P." missing.
- ⚠️ Uses `room.contents` correctly. Liquid name resolved via `LIQUID_TABLE`. Good.

---

## Recommended fix order

1. **Stop the bleeding in `magic_items.py`** — fix `ItemType.STAFF`/`WAND`, import
   `SkillTarget` from the right module, and route through `get_char_room` /
   `get_obj_here` like the rest of the codebase. Until this is done, all three magic
   item commands raise on invocation.
2. **Re-implement `do_eat`/`do_drink` against the real `condition[]` array.** ROM
   stores four conditions (DRUNK, FULL, THIRST, HUNGER); the current code ignores
   three of them and synthesises a `condition['hunger']`/`condition['thirst']` dict
   that no other system reads.
3. **Replace `_destroy_object`/`ch.inventory.remove(...)` with the central
   `extract_obj` helper** so consumed items are removed from registries consistently.
4. **Fix `do_pour` character-target branch** (`equipped` → `equipment`).
5. **Add the missing TO_ROOM act() broadcasts** for parity with player perception
   tests.

## Test coverage

A new integration suite is added at `tests/integration/test_consumables.py`. Tests for
broken commands skip with a pointer to this audit until the gaps above are closed.
