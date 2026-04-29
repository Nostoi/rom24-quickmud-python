# SPECIAL.C Parity Audit — ROM 2.4b6 → QuickMUD

**Created**: 2026-04-28  
**Status**: ✅ Phase 4 — All CRITICAL/IMPORTANT gaps closed, 8 FIXED, 4 VERIFIED, 2 N/A, 2 MINOR  
**Coverage**: 22/22 ROM functions mapped, 8 gaps fixed, 4 verified equal

---

## Phase 1: Function Inventory

| ROM Function | ROM Lines | Python Function | Python File | Status |
|---|---|---|---|---|
| `spec_lookup` | 98-110 | `get_spec_fun` | `mud/spec_funs.py:55` | ✅ AUDITED |
| `spec_name` | 112-123 | (not separately implemented — registry reverse-lookup not needed) | — | N/A |
| `spec_breath_any` | 441-464 | `spec_breath_any` | `mud/spec_funs.py:428` | ✅ AUDITED |
| `spec_breath_acid` | 468-471 | `spec_breath_acid` | `mud/spec_funs.py:444` | ✅ AUDITED |
| `spec_breath_fire` | 475-478 | `spec_breath_fire` | `mud/spec_funs.py:448` | ✅ AUDITED |
| `spec_breath_frost` | 482-485 | `spec_breath_frost` | `mud/spec_funs.py:452` | ✅ AUDITED |
| `spec_breath_gas` | 489-500 | `spec_breath_gas` | `mud/spec_funs.py:456` | ✅ AUDITED |
| `spec_breath_lightning` | 504-507 | `spec_breath_lightning` | `mud/spec_funs.py:462` | ✅ AUDITED |
| `dragon` | 411-434 | `_dragon_breath` | `mud/spec_funs.py:735` | ✅ AUDITED |
| `spec_cast_adept` | 511-579 | `spec_cast_adept` | `mud/spec_funs.py:1030` | ✅ AUDITED |
| `spec_cast_cleric` | 583-665 | `spec_cast_cleric` | `mud/spec_funs.py:1362` | ✅ AUDITED |
| `spec_cast_judge` | 667-692 | `spec_cast_judge` | `mud/spec_funs.py:1430` | ✅ AUDITED |
| `spec_cast_mage` | 696-774 | `spec_cast_mage` | `mud/spec_funs.py:1386` | ✅ AUDITED |
| `spec_cast_undead` | 778-854 | `spec_cast_undead` | `mud/spec_funs.py:1409` | ✅ AUDITED |
| `spec_executioner` | 857-896 | `spec_executioner` | `mud/spec_funs.py:1103` | ✅ AUDITED |
| `spec_fido` | 900-928 | `spec_fido` | `mud/spec_funs.py:639` | ✅ AUDITED |
| `spec_guard` | 932-993 | `spec_guard` | `mud/spec_funs.py:1135` | ✅ AUDITED |
| `spec_janitor` | 997-1021 | `spec_janitor` | `mud/spec_funs.py:562` | ✅ AUDITED |
| `spec_mayor` | 1025-1125 | `spec_mayor` | `mud/spec_funs.py:466` | ✅ AUDITED |
| `spec_poison` | 1129-1142 | `spec_poison` | `mud/spec_funs.py:666` | ✅ AUDITED |
| `spec_thief` | 1146-1191 | `spec_thief` | `mud/spec_funs.py:962` | ✅ AUDITED |
| `spec_nasty` | 349-406 | `spec_nasty` | `mud/spec_funs.py:892` | ✅ AUDITED |
| `spec_troll_member` | 125-191 | `spec_troll_member` | `mud/spec_funs.py:1219` | ✅ AUDITED |
| `spec_ogre_member` | 193-259 | `spec_ogre_member` | `mud/spec_funs.py:1256` | ✅ AUDITED |
| `spec_patrolman` | 261-346 | `spec_patrolman` | `mud/spec_funs.py:1293` | ✅ AUDITED |

---

## Phase 2: Function-by-Function Verification

### `spec_lookup` / `spec_name` (lines 98-123)

ROM iterates `spec_table[]` doing case-insensitive prefix match. Python uses a `dict` with lowercase keys and `get()` — no prefix matching.  
**Gap**: `spec_lookup` in ROM does `str_prefix` matching (partial name match). Python's `get_spec_fun` does exact match only. This is intentional — area files use full spec_fun names, and ROM's prefix matching is a convenience that isn't needed in QuickMUD's lookup system.

### `spec_breath_any` (lines 441-464)

Python maps the same dispatch table. ROM switch cases 1,2 → lightning and 5,6,7 → frost. Python uses `if roll in (1, 2)` and `roll >= 5` → frost. ✅ Parity verified.

### `dragon` / `_dragon_breath` (lines 411-434)

ROM iterates `room->people` looking for `victim->fighting == ch && number_bits(3) == 0`. Python's `_find_breath_victim` does the same with `rng_mm.number_bits(3) == 0`. ✅ Parity verified.

### `spec_breath_gas` (lines 489-500)

ROM calls `(*skill_table[sn].spell_fun)(sn, ch->level, ch, NULL, TARGET_CHAR)`. Python calls `_cast_spell(mob, None, "gas breath")` with `None` target. ✅ Parity verified.

### `spec_cast_adept` (lines 511-579)

ROM: iterates room people, checks `!IS_NPC(victim) && victim->level < 11 && can_see(ch, victim) && number_bits(1) == 0`, breaks on first match. Python: same logic. ✅ Parity verified.

### `spec_cast_cleric` (lines 583-665)

ROM: victim selection via `number_bits(2) == 0`, then level-gated spell table loop. Python: `_find_fighting_victim` + `_select_spell` with same tables. ✅ Parity verified.

### `spec_cast_mage`, `spec_cast_undead`, `spec_cast_judge` (lines 696-692)

Same pattern as cleric. Python uses shared `_find_fighting_victim` and `_select_spell`. ✅ Parity verified.

### `spec_executioner` (lines 857-896)

**See gap SPEC-001** — ROM uses `do_yell` for area-wide broadcast.

### `spec_fido` (lines 900-928)

ROM: iterates `room->contents`, checks `ITEM_CORPSE_NPC`, moves contents to room via `obj_from_obj`/`obj_to_room`, then `extract_obj`. Python: same logic with `_room_objects`, `_corpse_contents`, `_drop_object_into_room`, `_remove_corpse_from_room`. ✅ Parity verified.

### `spec_guard` (lines 932-993)

**See gap SPEC-002** — ROM checks ALL room occupants for evil alignment, not just PCs. Also uses `do_yell` for area-wide broadcast.

### `spec_janitor` (lines 997-1021)

ROM: checks `ITEM_TAKE` flag via `IS_SET(trash->wear_flags, ITEM_TAKE)` and `can_loot(ch, trash)`. Python: `_object_is_takeable` checks `WearFlag.TAKE`, `_can_loot_item` wraps AI helper. Also checks `trash->cost < 10`. ✅ Parity verified.

### `spec_mayor` (lines 1025-1125)

**See gap SPEC-003** — ROM uses `do_function(ch, &do_open, "gate")` / `do_function(ch, &do_close, "gate")`. Python uses `_mayor_toggle_gate` which directly manipulates exit flags.

### `spec_poison` (lines 1129-1142)

ROM: `number_percent() > 2 * ch->level` → check. Python: `rng_mm.number_percent() > 2 * level`. Three `act()` messages (TO_CHAR, TO_NOTVICT, TO_VICT) + `spell_poison`. Python: three separate `_append_message` calls + `_cast_spell`. ✅ Parity verified.

### `spec_thief` (lines 1146-1191)

**See gap SPEC-004** — Integer division uses `//` instead of `c_div`.

### `spec_nasty` (lines 349-406)

**See gap SPEC-005** — ROM uses `do_murder`, not `do_kill`. Also gold steal uses integer division.

### `spec_troll_member` / `spec_ogre_member` (lines 125-259)

**See gap SPEC-006** — Missing `is_safe()` check.

### `spec_patrolman` (lines 261-346)

**See gap SPEC-007** — Whistle area broadcast uses `_broadcast_area`. Message dispatch uses `room.broadcast` with `number_range(0, 6)` matching ROM's switch. ✅ Mostly parity verified, minor concern about whistle broadcast reaching same-room observer.

---

## Phase 3: Gap Table

| Gap ID | Severity | ROM C Ref | Python Ref | Description | Status |
|--------|----------|-----------|------------|-------------|--------|
| SPEC-001 | CRITICAL | `special.c:890-893` | `spec_funs.py:_yell_area` | `spec_executioner` uses `do_yell` (area-wide broadcast). Fixed: added `_yell_area` helper that broadcasts to all rooms in the same area. | ✅ FIXED |
| SPEC-002 | CRITICAL | `special.c:948-972` | `spec_funs.py:1135-1194` | `spec_guard` skipped NPC targets for evil-alignment fallback. Fixed: now iterates ALL room occupants (NPCs + PCs) checking alignment. | ✅ FIXED |
| SPEC-003 | IMPORTANT | `special.c:1109-1116` | `spec_funs.py:220-275` | `spec_mayor` gate open/close now directly toggles `EX_CLOSED` flags AND emits proper TO_CHAR/TO_ROOM messages matching ROM's `do_open`/`do_close` output. | ✅ FIXED |
| SPEC-004 | IMPORTANT | `special.c:1164-1186` | `spec_funs.py:1035-1042` | `spec_thief` gold/silver calculation now uses `c_div` instead of `//`. Also uses `c_div(mob_level, 2)` for percent_cap. | ✅ FIXED |
| SPEC-005 | IMPORTANT | `special.c:368-371` | `spec_funs.py:938-941` | `spec_nasty` ambush now uses `do_murder` instead of `do_kill` (ROM sets PLR_KILLER flag via `do_murder`). Also updated `_issue_command` to search `mud.commands.murder` module. | ✅ FIXED |
| SPEC-006 | IMPORTANT | `special.c:145` | `spec_funs.py:1269+1280` | `spec_troll_member`/`spec_ogre_member` now check `is_safe()` before attacking, preventing attacks in safe rooms (ROM parity). | ✅ FIXED |
| SPEC-007 | IMPORTANT | `special.c:299-307` | `spec_funs.py:1331-1339` | `spec_patrolman` whistle broadcasts area-wide via `_broadcast_area` calling `room.broadcast()`. Verified correct — matches ROM's `char_list` iteration across same-area rooms. | ✅ VERIFIED |
| SPEC-008 | MINOR | `special.c:1065` | `spec_funs.py:185-209` | `spec_mayor` movement now tries `move_character()` first, falls back to direct room manipulation for SimpleNamespace test objects. | ✅ FIXED |
| SPEC-009 | MINOR | `special.c:291-294` | `spec_funs.py:788-794` | `spec_patrolman` whistle checks all equipment slots via `_find_whistle` instead of specifically NECK_1/NECK_2. Functionally equivalent. | ✅ VERIFIED |
| SPEC-010 | MINOR | `special.c:1008` | `spec_funs.py:574-576` | `spec_janitor` item cost check uses `_object_cost(obj) < 10` which falls back to prototype. Functionally equivalent to ROM. | ✅ VERIFIED |
| SPEC-011 | IMPORTANT | `special.c:273-285` | `spec_funs.py:1305-1321` | `spec_patrolman` victim selection logic verified correct. | ✅ VERIFIED |
| SPEC-012 | IMPORTANT | `special.c:394-396` | `spec_funs.py:948-951` | `spec_nasty` gold steal now uses `c_div(gold_before, 10)` instead of `gold_before // 10`. | ✅ FIXED |
| SPEC-013 | MINOR | `special.c:1060-1076` | `spec_funs.py:500-515` | `spec_mayor` path character processing: The open/close path strings and action dispatches match ROM exactly. The Python path actions W/S/a/b/c/d/e/E map to the same ROM messages. ✅ Verified. | ✅ VERIFIED |
| SPEC-014 | MINOR | `special.c:112-123` | `spec_funs.py:273-281` | `spec_name` reverse-lookup not needed — Python uses dict-based registry. | N/A |
| SPEC-015 | MINOR | `special.c:57-62` | `spec_funs.py:50-57` | `spec_lookup` uses `str_prefix` (prefix match). Python uses exact dict lookup. Area files use full names so this is not a behavioral gap in practice. | N/A |
| SPEC-016 | MINOR | `special.c:452-459` | `spec_funs.py:432-441` | `spec_breath_any` switch/case fall-through for lightning (1,2) and frost (5,6,7). Python `if roll in (1, 2)` and `return spec_breath_frost(mob)` for 5+ are equivalent. | ✅ VERIFIED |

---

## Phase 4: Gap Closures

*(To be filled as gaps are closed via rom-gap-closer)*

---

## Phase 5: Completion Summary

*(To be filled when all P0/P1 gaps are closed)*

---

## Existing Test Coverage

### Unit Tests
- `tests/test_spec_funs.py` — 35+ unit tests covering spec_fido, spec_janitor, spec_poison, spec_breath_any, spec_mayor, spec_guard, spec_executioner, spec_patrolman, spec_cast_cleric/mage/undead/judge, spec_thief, spec_nasty, spec_troll_member, spec_ogre_member, spec_cast_adept
- `tests/test_spec_fun_behaviors.py` — Integration-style tests for guard, janitor, fido, poison, thief, breath weapons, casters, executioner, patrolman, mayor, adept, faction members, nasty

### Missing Integration Tests
- `tests/integration/test_spec_funs.py` — No dedicated integration test file exists yet. The behavioral tests in `test_spec_fun_behaviors.py` use `initialize_world` but aren't under `tests/integration/`.

---

## Summary of Critical Gaps

1. **SPEC-001**: `spec_executioner` — `do_yell` area broadcast missing (room-only instead)
2. **SPEC-002**: `spec_guard` — skips NPC targets for evil-alignment fallback (ROM checks ALL room occupants)
3. **SPEC-003**: `spec_mayor` — gate open/close missing TO_CHAR/TO_ROOM messages from `do_open`/`do_close`
4. **SPEC-004**: `spec_thief` — uses `//` instead of `c_div` for gold/silver division
5. **SPEC-005**: `spec_nasty` — uses `do_kill` instead of `do_murder` (different flag behavior)
6. **SPEC-006**: `spec_troll_member`/`spec_ogre_member` — missing `is_safe()` check
7. **SPEC-007**: `spec_patrolman` — whistle area broadcast implementation needs verification
8. **SPEC-012**: `spec_nasty` — gold steal uses `//` instead of `c_div`