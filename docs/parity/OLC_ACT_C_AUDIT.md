# OLC_ACT_C_AUDIT.md — `src/olc_act.c` (5007 lines, ~108 functions)

**Status**: ⚠️ Partial — Phase 1–3 complete (audit doc + gap IDs filed); Phase 4–5 pending closures
**Date**: 2026-04-29
**Audited by**: Sonnet subagent under main loop
**Sibling audits**: OLC_C_AUDIT.md (⚠️ Partial 30%), OLC_SAVE_C_AUDIT.md (not yet filed), OLC_MPCODE_C_AUDIT.md (not yet filed), HEDIT_C_AUDIT.md (not yet filed), STRING_C_AUDIT.md (✅ 100%), BIT_C_AUDIT.md (✅ 100%)
**Out of scope**: `mpedit_*` and `hedit_*` functions (sibling audits); table-of-tables dispatch (covered by OLC-006..009 in OLC_C_AUDIT.md)

---

## Summary

`src/olc_act.c` contains all the per-field builder functions for ROM's Online Creation (OLC) system. It covers four editors:

- **AEdit** (`aedit_*`) — area-level metadata editors (~12 functions)
- **REdit** (`redit_*`) — room editors + exit + extra-desc + reset helpers (~38 functions)
- **OEdit** (`oedit_*`) — object prototype editors (~22 functions)
- **MEdit** (`medit_*`) — mobile prototype editors (~32 functions)
- **`show_*` / helper utilities** — list displays, flag helpers (~4 functions)

`mpedit_*` and `hedit_*` functions do NOT appear in this file; they live in `src/olc_mpcode.c` and `src/hedit.c` respectively. The `aedit_table[]`, `redit_table[]`, `oedit_table[]`, `medit_table[]` command-dispatch tables live in `src/olc.c` (filed as OLC-006..009 in the sibling audit).

**Key finding**: Python's `mud/commands/build.py` implements the four editor entry-points (`cmd_aedit`, `cmd_redit`, `cmd_oedit`, `cmd_medit`) inline as monolithic `if/elif` chains. There is no separate Python module with per-field builder functions mirroring the C `aedit_*/redit_*/oedit_*/medit_*` structure. Most TIER A builders (the four `*_create` functions) are **partially embedded** inside the entry-point commands rather than filed as separate builder functions. Divergences are systematic.

**Tier breakdown**: TIER A: 9 functions · TIER B: 8 functions · TIER C: ~78 functions · N/A (mpedit/hedit): 0 in this file

---

## Phase 1 — Function Inventory

> Legend: ✅ AUDITED · ⚠️ PARTIAL · ❌ MISSING · 🔄 NEEDS DEEP AUDIT · N/A

### Utility / Helper Functions

| ROM Symbol | ROM Lines | Python Counterpart | Tier | Status |
|---|---|---|---|---|
| `show_version` | 62–74 | — | C | ❌ MISSING — TIER C, low priority |
| `show_flag_cmds` | 126–162 | — | C | 🔄 NEEDS DEEP AUDIT |
| `show_skill_cmds` | 163–203 | — | C | 🔄 NEEDS DEEP AUDIT |
| `show_spec_cmds` | 204–235 | — | C | 🔄 NEEDS DEEP AUDIT |
| `show_help` | 236–328 | — | C | 🔄 NEEDS DEEP AUDIT |
| `check_range` | 566–584 | `_get_area_for_vnum` (build.py:1119) — different semantics | C | ⚠️ PARTIAL |
| `get_vnum_area` | 588–599 | `_get_area_for_vnum` (build.py:1119) — covers basic lookup | C | ⚠️ PARTIAL |
| `wear_loc` | 1967–1978 | — | C | 🔄 NEEDS DEEP AUDIT |
| `wear_bit` | 1987–1998 | — | C | 🔄 NEEDS DEEP AUDIT |
| `show_obj_values` | 2210–2732 | partial in `_oedit_show` (build.py) | C | 🔄 NEEDS DEEP AUDIT |
| `show_liqlist` | 4727–4754 | — | C | 🔄 NEEDS DEEP AUDIT |
| `show_damlist` | 4755–4778 | — | C | 🔄 NEEDS DEEP AUDIT |

### AEdit Functions (`aedit_*`)

| ROM Symbol | ROM Lines | Python Counterpart | Tier | Status |
|---|---|---|---|---|
| `aedit_show` | 606–649 | `_aedit_show` (build.py:~1297) | A | ⚠️ PARTIAL — flags display uses `flag_string`; Python version missing flags row |
| `aedit_reset` | 653–663 | — | B | ❌ MISSING |
| `aedit_create` | 667–679 | `cmd_aedit` + `_aedit_create` (build.py) | A | ✅ FIXED (OLC_ACT-001) |
| `aedit_name` | 683–700 | inline in `_interpret_aedit` (build.py:1299) | C | ⚠️ PARTIAL |
| `aedit_credits` | 702–719 | inline in `_interpret_aedit` (build.py:1307) | C | ⚠️ PARTIAL |
| `aedit_file` | 722–766 | `_interpret_aedit` (build.py) — no `filename` subcommand found | C | 🔄 NEEDS DEEP AUDIT |
| `aedit_age` | 770–792 | `_interpret_aedit` (build.py) — no `age` subcommand found | C | 🔄 NEEDS DEEP AUDIT |
| `aedit_recall` | 793–824 | — | C | 🔄 NEEDS DEEP AUDIT |
| `aedit_security` | 825–863 | inline in `_interpret_aedit` (build.py:1315) | C | ⚠️ PARTIAL |
| `aedit_builder` | 864–923 | inline in `_interpret_aedit` (build.py:1330) | C | ⚠️ PARTIAL |
| `aedit_vnum` | 924–978 | inline in `_interpret_aedit` (build.py:1333) | C | ⚠️ PARTIAL |
| `aedit_lvnum` | 979–1021 | inline in `_interpret_aedit` (build.py:1344) | C | ⚠️ PARTIAL |
| `aedit_uvnum` | 1022–1067 | inline in `_interpret_aedit` (build.py) | C | 🔄 NEEDS DEEP AUDIT |

### REdit Functions (`redit_*`)

| ROM Symbol | ROM Lines | Python Counterpart | Tier | Status |
|---|---|---|---|---|
| `redit_rlist` | 329–372 | — | C | 🔄 NEEDS DEEP AUDIT |
| `redit_mlist` | 374–430 | — | C | 🔄 NEEDS DEEP AUDIT |
| `redit_olist` | 431–488 | — | C | 🔄 NEEDS DEEP AUDIT |
| `redit_mshow` | 489–524 | — | C | 🔄 NEEDS DEEP AUDIT |
| `redit_oshow` | 525–565 | — | C | 🔄 NEEDS DEEP AUDIT |
| `redit_show` | 1068–1241 | `_redit_show` (build.py:~961) partial | A | ⚠️ PARTIAL — many fields missing |
| `change_exit` | 1242–1518 | `_handle_exit_command` or similar (build.py) | C | 🔄 NEEDS DEEP AUDIT |
| `redit_north` | 1519–1525 | inline in `_interpret_redit` | C | 🔄 NEEDS DEEP AUDIT |
| `redit_south` | 1529–1535 | inline in `_interpret_redit` | C | 🔄 NEEDS DEEP AUDIT |
| `redit_east` | 1539–1545 | inline in `_interpret_redit` | C | 🔄 NEEDS DEEP AUDIT |
| `redit_west` | 1549–1555 | inline in `_interpret_redit` | C | 🔄 NEEDS DEEP AUDIT |
| `redit_up` | 1559–1565 | inline in `_interpret_redit` | C | 🔄 NEEDS DEEP AUDIT |
| `redit_down` | 1569–1575 | inline in `_interpret_redit` | C | 🔄 NEEDS DEEP AUDIT |
| `redit_ed` | 1579–1715 | — | C | 🔄 NEEDS DEEP AUDIT |
| `redit_create` | 1716–1766 | `cmd_redit` + `_redit_create` (build.py) | A | ✅ FIXED (OLC_ACT-002) |
| `redit_name` | 1770–1787 | inline in `_interpret_redit` | C | ⚠️ PARTIAL |
| `redit_desc` | 1791–1805 | inline in `_interpret_redit` | C | 🔄 NEEDS DEEP AUDIT — needs `string_append` |
| `redit_heal` | 1807–1822 | inline in `_interpret_redit` | C | ⚠️ PARTIAL |
| `redit_mana` | 1824–1839 | inline in `_interpret_redit` | C | ⚠️ PARTIAL |
| `redit_clan` | 1841–1852 | — | C | 🔄 NEEDS DEEP AUDIT |
| `redit_format` | 1853–1863 | — | C | 🔄 NEEDS DEEP AUDIT |
| `redit_mreset` | 1867–1925 | — | C | 🔄 NEEDS DEEP AUDIT |
| `redit_oreset` | 2002–2209 | — | C | 🔄 NEEDS DEEP AUDIT |
| `redit_owner` | 4841–4863 | — | C | 🔄 NEEDS DEEP AUDIT |
| `redit_room` | 4972–4988 | inline in `_interpret_redit` — `room` flag toggle | C | 🔄 NEEDS DEEP AUDIT |
| `redit_sector` | 4990–5007 | inline in `_interpret_redit` — `sector` set | C | 🔄 NEEDS DEEP AUDIT |

**Note on `redit_reset`**: There is no `redit_reset` function in `src/olc_act.c`. The `reset` subcommand of `do_redit` (ROM `src/olc.c:766-781`) calls `reset_area(pRoom->area)` directly in the dispatcher, not via a builder function. The OLC-017 "reset half" gap refers to this dispatcher path — it is a gap in `OLC_C_AUDIT.md` (OLC-017), not a gap in `olc_act.c`. Filed here as `OLC_ACT-003` for clarity since the task description explicitly calls it out.

### OEdit Functions (`oedit_*`)

| ROM Symbol | ROM Lines | Python Counterpart | Tier | Status |
|---|---|---|---|---|
| `oedit_show` | 2733–2817 | `_oedit_show` (build.py:~1514) partial | A | ⚠️ PARTIAL — missing many fields |
| `oedit_addaffect` | 2818–2858 | — | C | 🔄 NEEDS DEEP AUDIT |
| `oedit_addapply` | 2859–2925 | — | C | 🔄 NEEDS DEEP AUDIT |
| `oedit_delaffect` | 2926–2989 | — | C | 🔄 NEEDS DEEP AUDIT |
| `oedit_name` | 2990–3010 | inline in `_interpret_oedit` (build.py:1517) | C | ⚠️ PARTIAL |
| `oedit_short` | 3011–3032 | inline in `_interpret_oedit` (build.py:1525) | C | ⚠️ PARTIAL |
| `oedit_long` | 3033–3076 | inline in `_interpret_oedit` (build.py:1533) | C | 🔄 NEEDS DEEP AUDIT — needs `string_append` |
| `oedit_values` | 3077–3089 | — | C | 🔄 NEEDS DEEP AUDIT |
| `oedit_value0` | 3090–3099 | — | C | 🔄 NEEDS DEEP AUDIT |
| `oedit_value1` | 3100–3109 | — | C | 🔄 NEEDS DEEP AUDIT |
| `oedit_value2` | 3110–3119 | — | C | 🔄 NEEDS DEEP AUDIT |
| `oedit_value3` | 3120–3129 | — | C | 🔄 NEEDS DEEP AUDIT |
| `oedit_value4` | 3130–3139 | — | C | 🔄 NEEDS DEEP AUDIT |
| `oedit_weight` | 3140–3157 | inline in `_interpret_oedit` (build.py) | C | 🔄 NEEDS DEEP AUDIT |
| `oedit_cost` | 3158–3177 | inline in `_interpret_oedit` (build.py) | C | 🔄 NEEDS DEEP AUDIT |
| `oedit_create` | 3178–3225 | `cmd_oedit` + `_oedit_create` (build.py) | A | ✅ FIXED (OLC_ACT-005) |
| `oedit_ed` | 3229–3369 | — | C | 🔄 NEEDS DEEP AUDIT |
| `oedit_extra` | 3370–3393 | — | C | 🔄 NEEDS DEEP AUDIT |
| `oedit_wear` | 3394–3417 | — | C | 🔄 NEEDS DEEP AUDIT |
| `oedit_type` | 3418–3450 | inline in `_interpret_oedit` (build.py:1541) — partial | C | 🔄 NEEDS DEEP AUDIT |
| `oedit_material` | 3451–3469 | — | C | 🔄 NEEDS DEEP AUDIT |
| `oedit_level` | 3470–3489 | inline in `_interpret_oedit` (build.py:1549) | C | ⚠️ PARTIAL |
| `oedit_condition` | 3490–3518 | — | C | 🔄 NEEDS DEEP AUDIT |

### MEdit Functions (`medit_*`)

| ROM Symbol | ROM Lines | Python Counterpart | Tier | Status |
|---|---|---|---|---|
| `medit_show` | 3519–3703 | `_medit_show` (build.py:~1795) partial | A | ⚠️ PARTIAL — missing many fields |
| `medit_create` | 3704–3753 | `cmd_medit` + `_medit_create` (build.py) | A | ✅ FIXED (OLC_ACT-006) |
| `medit_spec` | 3757–3787 | — | C | 🔄 NEEDS DEEP AUDIT |
| `medit_damtype` | 3789–3809 | — | C | 🔄 NEEDS DEEP AUDIT |
| `medit_align` | 3810–3829 | inline in `_interpret_medit` (build.py) | C | ⚠️ PARTIAL |
| `medit_level` | 3830–3849 | inline in `_interpret_medit` (build.py) | C | ⚠️ PARTIAL |
| `medit_desc` | 3850–3868 | — | C | 🔄 NEEDS DEEP AUDIT — needs `string_append` |
| `medit_long` | 3869–3891 | inline in `_interpret_medit` (build.py) | C | ⚠️ PARTIAL |
| `medit_short` | 3892–3912 | inline in `_interpret_medit` (build.py) | C | ⚠️ PARTIAL |
| `medit_name` | 3913–3931 | inline in `_interpret_medit` (build.py) | C | ⚠️ PARTIAL |
| `medit_shop` | 3932–4117 | — | C | 🔄 NEEDS DEEP AUDIT |
| `medit_sex` | 4118–4141 | — | C | 🔄 NEEDS DEEP AUDIT |
| `medit_act` | 4142–4166 | — | C | 🔄 NEEDS DEEP AUDIT |
| `medit_affect` | 4167–4191 | — | C | 🔄 NEEDS DEEP AUDIT |
| `medit_ac` | 4192–4255 | — | C | 🔄 NEEDS DEEP AUDIT |
| `medit_form` | 4256–4277 | — | C | 🔄 NEEDS DEEP AUDIT |
| `medit_part` | 4278–4299 | — | C | 🔄 NEEDS DEEP AUDIT |
| `medit_imm` | 4300–4321 | — | C | 🔄 NEEDS DEEP AUDIT |
| `medit_res` | 4322–4343 | — | C | 🔄 NEEDS DEEP AUDIT |
| `medit_vuln` | 4344–4365 | — | C | 🔄 NEEDS DEEP AUDIT |
| `medit_material` | 4366–4384 | — | C | 🔄 NEEDS DEEP AUDIT |
| `medit_off` | 4385–4406 | — | C | 🔄 NEEDS DEEP AUDIT |
| `medit_size` | 4407–4428 | — | C | 🔄 NEEDS DEEP AUDIT |
| `medit_hitdice` | 4429–4479 | — | C | 🔄 NEEDS DEEP AUDIT |
| `medit_manadice` | 4480–4537 | — | C | 🔄 NEEDS DEEP AUDIT |
| `medit_damdice` | 4538–4595 | — | C | 🔄 NEEDS DEEP AUDIT |
| `medit_race` | 4596–4642 | — | C | 🔄 NEEDS DEEP AUDIT |
| `medit_position` | 4643–4690 | — | C | 🔄 NEEDS DEEP AUDIT |
| `medit_gold` | 4691–4708 | — | C | 🔄 NEEDS DEEP AUDIT |
| `medit_hitroll` | 4709–4726 | — | C | 🔄 NEEDS DEEP AUDIT |
| `medit_group` | 4779–4840 | — | C | 🔄 NEEDS DEEP AUDIT |
| `medit_addmprog` | 4864–4910 | — | C | 🔄 NEEDS DEEP AUDIT |
| `medit_delmprog` | 4911–4971 | — | C | 🔄 NEEDS DEEP AUDIT |

---

## Phase 2 — Verification (TIER A functions)

### `aedit_create` (ROM 667–679) — OLC_ACT-001

**ROM signature**: `bool aedit_create(CHAR_DATA *ch, char *argument)`

**ROM steps (src/olc_act.c:667–679)**:
1. Calls `new_area()` (`src/mem.c:91-122`) — allocates and initialises a fresh `AREA_DATA` with defaults: `name="New area"`, `builders="None"`, `security=1`, `min_vnum=0`, `max_vnum=0`, `age=0`, `nplayer=0`, `empty=TRUE`, `area_flags=AREA_ADDED`, `file_name=sprintf("area%d.are", vnum)`. **Audit-doc correction (2026-04-29)**: original notes said `name="(unnamed)"`/`security=9` — the actual ROM `new_area` source uses `"New area"`/`security=1`; closure replicated authoritative ROM values.
2. Appends to the global linked list: `area_last->next = pArea; area_last = pArea`.
3. Sets `ch->desc->pEdit = (void *)pArea` — the descriptor's edit pointer now tracks this new area.
4. Sets `AREA_ADDED` flag: `SET_BIT(pArea->area_flags, AREA_ADDED)` — marks the area as dynamically added (not loaded from disk), affects how `olc_save.c` handles persistence.
5. Sends `"Area Created.\n\r"` to character.
6. Returns `FALSE` (does NOT set `AREA_CHANGED` — that happens when a field is subsequently edited).

**Data dependencies**:
- `new_area()` — allocates from `top_area` counter + linked list. Python uses `area_registry` dict; no linked-list semantics.
- `area_last` global pointer — Python has no equivalent; `area_registry` is unordered dict.
- `AREA_ADDED` flag — Python has `AreaFlag.ADDED` (value `1 << 1` in `mud/models/constants.py:524`) but it is never set anywhere in `mud/commands/build.py`.
- `desc->pEdit` — Python uses `session.editor_state = {"area": area}`.

**Python counterpart**: `cmd_aedit` (build.py:1226–1253). The Python function has **no `create` subcommand** at all. When called without an existing vnum, it returns `"Area vnum must be a number."` or `"That area does not exist."` — there is no code path that creates a new `Area` object. A builder cannot create a new area from within the OLC system.

**Divergences**:
1. No `create` subcommand path exists in Python at all.
2. `AreaFlag.ADDED` is never set on newly-created areas.
3. No linked-list append semantics (minor — Python uses dict; ordering doesn't matter for correctness, only for `do_alist` ordering which is already a separate gap).
4. `area_registry` key must be determined — ROM uses `pArea->vnum` which starts at 0 (undefined) until `aedit_lvnum`/`aedit_uvnum` are used. Python would need to handle a "not yet assigned vnum" state.

**Closes**: OLC_ACT-001 closure unblocks OLC-016 (the `create` half of `do_aedit`) in OLC_C_AUDIT.md.

---

### `redit_create` (ROM 1716–1766) — OLC_ACT-002

**ROM signature**: `bool redit_create(CHAR_DATA *ch, char *argument)`

**ROM steps (src/olc_act.c:1716–1766)**:
1. Reads vnum from `argument`; rejects `argument[0] == '\0' || value <= 0` with syntax message.
2. Calls `get_vnum_area(value)` — if no area owns that vnum range, rejects with `"REdit: That vnum is not assigned an area.\n\r"`.
3. Checks `IS_BUILDER(ch, pArea)` — if not a builder for that area, rejects with `"REdit: Vnum in an area you cannot build in.\n\r"`.
4. Checks `get_room_index(value)` — if room vnum already exists, rejects with `"REdit: Room vnum already exists.\n\r"`.
5. Calls `new_room_index()` — allocates fresh `ROOM_INDEX_DATA` with defaults (`name="(undefined)"`, `description=""`, `sector_type=SECT_INSIDE`, `room_flags=0`, `heal_rate=100`, `mana_rate=100`).
6. Sets `pRoom->area = pArea`, `pRoom->vnum = value`.
7. Updates `top_vnum_room` if `value > top_vnum_room`.
8. Inserts into `room_index_hash[value % MAX_KEY_HASH]` — prepends to the bucket's linked list.
9. Sets `ch->desc->pEdit = (void *)pRoom`.
10. Sends `"Room created.\n\r"` to character.
11. Returns `TRUE` (triggers `AREA_CHANGED` set in the caller — unlike `aedit_create` which returns FALSE).

**Data dependencies**:
- `get_vnum_area()` — Python equivalent `_get_area_for_vnum` (build.py:1119) exists and is equivalent.
- `IS_BUILDER()` — Python `_is_builder(char, area)` exists.
- `room_index_hash[]` — Python uses `room_registry` dict; no hash-bucket linked list.
- `top_vnum_room` — no Python equivalent; not tracked.
- `new_room_index()` — Python would use `Room(vnum=value, area=area)` plus default field values.

**Python counterpart**: `cmd_redit` (build.py:1071–1102). The Python function has **no `create` subcommand**. It only handles `done`/`exit`, interprets commands in the current room, or activates editing of the character's current room. There is no code path that creates a new room by vnum.

**Divergences**:
1. No `create <vnum>` subcommand path in Python.
2. No `top_vnum_room` tracking.
3. `room_registry` dict used instead of `room_index_hash`.
4. Newly created room's `area` field must be set from `get_vnum_area` — currently Python always uses `char.room.area` which would be wrong for a remote-vnum create.
5. Return value semantics (`TRUE` vs `FALSE`) control whether caller sets `AREA_CHANGED` — Python has no equivalent return-value protocol; uses `area.changed = True` imperatively.

**Closes**: OLC_ACT-002 closure unblocks the `create` half of OLC-017 in OLC_C_AUDIT.md.

---

### `redit_reset` — OLC_ACT-003 (dispatcher-level gap, not a builder function)

**Note**: There is no `redit_reset` function in `src/olc_act.c`. The `reset` subcommand is handled directly in `do_redit` (ROM `src/olc.c:766-781`):
```c
if (!str_cmp(arg, "reset")) {
    reset_area(pRoom->area);
    send_to_char("Room's area has been reset.\n\r", ch);
    return;
}
```

**Python counterpart**: `cmd_redit` (build.py:1071–1102) has no `reset` subcommand path. The Python function's only special-case subcommands are `done`/`exit`.

**Divergences**:
1. No `reset` subcommand in Python `cmd_redit`.
2. `reset_area()` equivalent — Python would need to call the area reset mechanism (which exists for other purposes).

**Closes**: OLC_ACT-003 closure unblocks the `reset` half of OLC-017 in OLC_C_AUDIT.md.

---

### `redit_<vnum>` teleport — OLC_ACT-004 (dispatcher-level gap)

**Note**: There is no `redit_<vnum>` builder function in `src/olc_act.c`. The numeric vnum path is handled directly in `do_redit` (ROM `src/olc.c:783-821`):
```c
// If argument is a number:
// 1. get_vnum_area(value) — check area exists
// 2. IS_BUILDER check
// 3. get_room_index(value) — get or fail
// 4. char_from_room(ch) + char_to_room(ch, pRoom) — teleport character
// 5. pEdit = pRoom, send redit_show output
```

**Python counterpart**: `cmd_redit` (build.py:1071–1102) has no numeric-vnum path. The Python only edits the character's current room.

**Divergences**:
1. No numeric-vnum subcommand in Python `cmd_redit`.
2. No `char_from_room`/`char_to_room` teleport semantics.
3. Character must physically move to a room before editing it in Python; ROM allows remote editing by vnum.

**Closes**: OLC_ACT-004 closure unblocks the `<vnum>` half of OLC-017 in OLC_C_AUDIT.md.

---

### `oedit_create` (ROM 3178–3225) — OLC_ACT-005

**ROM signature**: `bool oedit_create(CHAR_DATA *ch, char *argument)`

**ROM steps (src/olc_act.c:3178–3225)**:
1. Reads vnum from `argument`; rejects empty or zero with syntax message.
2. Calls `get_vnum_area(value)` — if no area, rejects with `"OEdit: That vnum is not assigned an area.\n\r"`.
3. Checks `IS_BUILDER(ch, pArea)` — rejects with `"OEdit: Vnum in an area you cannot build in.\n\r"`.
4. Checks `get_obj_index(value)` — rejects duplicate with `"OEdit: Object vnum already exists.\n\r"`.
5. Calls `new_obj_index()` — allocates fresh `OBJ_INDEX_DATA` with defaults (`item_type=ITEM_TRASH`, `name="ObjName"`, `short_descr="short"`, `description="long"`, `material="unknown"`, `weight=0`, `cost=0`, `level=0`, `condition=100`).
6. Sets `pObj->vnum = value`, `pObj->area = pArea`.
7. Updates `top_vnum_obj` if `value > top_vnum_obj`.
8. Inserts into `obj_index_hash[value % MAX_KEY_HASH]`.
9. Sets `ch->desc->pEdit = (void *)pObj`.
10. Sends `"Object Created.\n\r"` to character.
11. Returns `TRUE`.

**Python counterpart**: `cmd_oedit` (build.py:1430–1469). The Python function **does have an auto-create path** (lines 1452–1462): if `obj_index_registry.get(obj_vnum)` returns None, it looks up the area by vnum range and if found, creates a new `ObjIndex`. However this differs from ROM in several important ways:

**Divergences**:
1. Python's create path is triggered by any unknown vnum (no explicit `create` keyword) — ROM requires `oedit create <vnum>` as a subcommand from `do_oedit`; the distinction matters because ROM's vnum-only path (without `create`) tries to load an existing obj and fails cleanly.
2. Python does not check `IS_BUILDER` before creating — it creates first and sets `area.changed = True` without the security check on creation.
3. Python `ObjIndex` default field values not verified against ROM `new_obj_index()` defaults (e.g., `item_type=ITEM_TRASH`).
4. No `top_vnum_obj` tracking.
5. `obj_index_registry` dict used instead of `obj_index_hash`.
6. Error message differs: ROM sends `"OEdit: Object vnum already exists.\n\r"` for duplicates; Python silently loads the existing one.

**Closes**: OLC_ACT-005 closure unblocks OLC-018 in OLC_C_AUDIT.md.

---

### `medit_create` (ROM 3704–3753) — OLC_ACT-006

**ROM signature**: `bool medit_create(CHAR_DATA *ch, char *argument)`

**ROM steps (src/olc_act.c:3704–3753)**:
1. Reads vnum from `argument`; rejects empty or zero with syntax message.
2. Calls `get_vnum_area(value)` — if no area, rejects with `"MEdit: That vnum is not assigned an area.\n\r"`.
3. Checks `IS_BUILDER(ch, pArea)` — rejects with `"MEdit: Vnum in an area you cannot build in.\n\r"`.
4. Checks `get_mob_index(value)` — rejects duplicate with `"MEdit: Mobile vnum already exists.\n\r"`.
5. Calls `new_mob_index()` — allocates fresh `MOB_INDEX_DATA` with defaults.
6. Sets `pMob->vnum = value`, `pMob->area = pArea`.
7. Updates `top_vnum_mob` if `value > top_vnum_mob`.
8. **Sets `pMob->act = ACT_IS_NPC`** — critical: new mobs always have the NPC flag set by default.
9. Inserts into `mob_index_hash[value % MAX_KEY_HASH]`.
10. Sets `ch->desc->pEdit = (void *)pMob`.
11. Sends `"Mobile Created.\n\r"` to character.
12. Returns `TRUE`.

**Python counterpart**: `cmd_medit` (build.py:1714–1753). Same auto-create pattern as `oedit`. Creates a new `MobIndex(vnum=mob_vnum, area=area)` when vnum is not found.

**Divergences**:
1. Same create-keyword vs auto-create distinction as `oedit_create` above.
2. `MobIndex` construction does not set `act = ACT_IS_NPC` (equivalent: `ActFlag.IS_NPC`) — this is a CRITICAL gap: newly created mobs in Python are missing the NPC flag, which affects all NPC-checking code paths.
3. No `IS_BUILDER` check before creation.
4. No `top_vnum_mob` tracking.
5. `mob_registry` dict used instead of `mob_index_hash`.

**Closes**: OLC_ACT-006 closure unblocks OLC-019 in OLC_C_AUDIT.md.

---

### TIER B — Moderate Phase 2

#### `aedit_reset` (ROM 653–663)

ROM signature: `bool aedit_reset(CHAR_DATA *ch, char *argument)`. Calls `reset_area(pArea)` and sends `"Area reset.\n\r"`. The `reset_area()` function triggers all room resets in the area. **Python counterpart**: no `reset` subcommand found in `_interpret_aedit` (build.py:1261). Verdict: **needs implementation**.

#### `aedit_show` (ROM 606–649) — extra gap beyond OLC_ACT-007

ROM emits 9 fields: Name+vnum, File, Vnums range, Age, Players, Security, Builders, Credits, Flags (via `flag_string(area_flags, ...)`). The Flags line is important — it uses `flag_string` (now implemented as `BIT-002`) to decode `AREA_ADDED`, `AREA_CHANGED`, `AREA_LOADING`. Python `_aedit_show` (build.py) covers most basic fields but likely omits the `Flags` row. Verdict: **partially present, missing flags row** — OLC_ACT-007.

#### `redit_show` (ROM 1068–1241) — extra gap OLC_ACT-008

ROM emits ~15 fields: Description, Name, Area, Vnum, Sector (via `flag_string`), Room flags (via `flag_string`), Heal/Mana rates (conditional), Clan (conditional), Owner (conditional), Extra desc keywords, Characters list, Objects list, Exits (6 directions with flags/keyword/key-vnum/to-vnum), and Extra descs. Python `_redit_show` exists but is substantially incomplete (no exit details, no sector/room-flag decoding, no extra-descs). Verdict: **partially present, many fields missing** — OLC_ACT-008.

#### `oedit_show` (ROM 2733–2817) — extra gap OLC_ACT-009

ROM emits object fields including name, type (via `flag_string(type_flags,...)`), extra/wear flags (via `flag_string`), level, weight, cost, condition, material, then calls `show_obj_values()` for type-specific values, then lists affects/applies. Python `_oedit_show` covers basic fields but misses flags display and `show_obj_values` type-specific section. Verdict: **partially present** — OLC_ACT-009.

#### `medit_show` (ROM 3519–3703) — extra gap OLC_ACT-010

ROM emits: name, area, act-flags, vnum, sex, race, level, align, hitroll, dam-type, group, hit/damage/mana dice, affected-by, armor (4 values), form/parts/imm/res/vuln/off flags, size, position, gold, spec-fun, shop (if present), all via `flag_string`. Also lists mprog programs at the end. Python `_medit_show` covers some basic scalar fields. Verdict: **partially present, most flag fields missing** — OLC_ACT-010.

#### `redit_<vnum>` teleport (dispatcher — OLC_ACT-004 above)

Already documented as a dispatcher-level gap. TIER B classification retained: behavior is clear from ROM `src/olc.c:783-821`; Python needs `char_from_room` + `char_to_room` and the numeric vnum dispatch.

#### `redit_name` / `oedit_name` / `medit_name` (common builders)

These all follow the same ROM pattern: check empty arg → return syntax; `free_string(old); field = str_dup(argument); send_to_char("X set.\n\r")`. Python inlines equivalent logic but uses Python string assignment (no `free_string` — correct for Python) and emits different success messages. The messages differ (e.g., ROM: `"Name set.\n\r"` vs Python: `f"Object name (keywords) set to: {new_name}"`). IMPORTANT-severity message drift across all `*_name` builders — captured under OLC_ACT-011.

---

## Phase 3 — Gap Table

| Gap ID | Severity | ROM C ref | Python ref (or "missing") | Description | Status |
|---|---|---|---|---|---|
| OLC_ACT-001 | CRITICAL | src/olc_act.c:667–679 `aedit_create` | `mud/commands/build.py:_aedit_create` | `aedit create` subcommand wired in `cmd_aedit` and `_interpret_aedit`; new area gets ROM `new_area()` defaults from `src/mem.c:91-122` (name="New area", builders="None", security=1, min/max_vnum=0, empty=True, AREA_ADDED set, file_name=`area<vnum>.are`); 9 integration tests. | ✅ FIXED |
| OLC_ACT-002 | CRITICAL | src/olc_act.c:1716–1766 `redit_create` | `mud/commands/build.py:_redit_create` | `redit create <vnum>` wired with full ROM validation chain. `new_room_index` defaults from `src/mem.c:181-218` (heal_rate=100, mana_rate=100, all else zeroed). After create, builder is silently relocated into the new room via `_char_from_room`/`_char_to_room`. 8 integration tests. | ✅ FIXED |
| OLC_ACT-003 | CRITICAL | src/olc.c:757-769 `do_redit` reset branch | `mud/commands/build.py:cmd_redit` reset branch + `_apply_resets_for_redit` wrapper | `redit reset` wired with security gate, exact ROM message "Room reset.\n\r", area `changed=True`, calls `apply_resets(area)` (broader-scope than ROM's `reset_room(pRoom)` per src/olc.c:765 — documented divergence pending a per-room reset port). 4 integration tests. | ✅ FIXED |
| OLC_ACT-004 | CRITICAL | src/olc.c:789-808 `do_redit` vnum branch | `mud/commands/build.py:_redit_vnum_teleport` | `redit <vnum>` silent-teleport wired. Reuses existing silent primitives `_char_from_room`/`_char_to_room` from `mud.commands.imm_commands` (locked decision — no new movement infra). Validates target exists, IS_BUILDER on TARGET area, then relocates and sets descriptor edit pointer. 5 integration tests. | ✅ FIXED |
| OLC_ACT-005 | CRITICAL | src/olc_act.c:3178–3225 `oedit_create` | `mud/commands/build.py:_oedit_create` | Explicit `oedit create <vnum>` keyword wired with full ROM validation chain: vnum required → `_get_area_for_vnum` → `_is_builder` security → already-exists. ROM `new_obj_index` defaults applied (name="no name", short_descr="(no short description)", description="(no description)", item_type="trash", material="unknown", value=[0]*5, new_format=True). Auto-create-on-unknown-vnum behavior removed. 11 integration tests. | ✅ FIXED |
| OLC_ACT-006 | CRITICAL | src/olc_act.c:3704–3753 `medit_create` | `mud/commands/build.py:_medit_create` | Explicit `medit create <vnum>` keyword wired with full ROM validation chain. `ActFlag.IS_NPC` set on both `act_flags` (modern) and legacy `act` field per ROM `src/olc_act.c:3745`. ROM `new_mob_index` defaults applied (player_name="no name", short_descr="(no short description)", long_descr="(no long description)\\n\\r", description="", level=0, sex=NONE, size=MEDIUM, start/default_pos="standing", material="unknown", new_format=True). Auto-create-on-unknown-vnum behavior removed. 12 integration tests. | ✅ FIXED |
| OLC_ACT-007 | IMPORTANT | src/olc_act.c:644–646 `aedit_show` flags row | `_aedit_show` (build.py:1548) — flags row added via `flag_string(AreaFlag, area.area_flags)` | `aedit show` now includes `Flags: [...]` row with area status flags (ADDED, CHANGED, LOADING); 5 integration tests | ✅ FIXED |
| OLC_ACT-008 | IMPORTANT | src/olc_act.c:1068–1241 `redit_show` | `_redit_show` (build.py) — many fields missing | `redit show` missing sector/room-flag decoded strings, exit details (flags, keyword, key-vnum, to-vnum), extra-descs, clan, owner | 🔄 OPEN |
| OLC_ACT-009 | IMPORTANT | src/olc_act.c:2733–2817 `oedit_show` | `_oedit_show` (build.py) — type-specific values missing | `oedit show` missing `show_obj_values` type-specific section, extra/wear flag decoded strings, affects list | 🔄 OPEN |
| OLC_ACT-010 | IMPORTANT | src/olc_act.c:3519–3703 `medit_show` | `_medit_show` (build.py) — most flag fields missing | `medit show` missing form/parts/imm/res/vuln/off flags, dice fields, armor values, position, size, spec-fun, shop, mprogs | 🔄 OPEN |
| OLC_ACT-011 | IMPORTANT | src/olc_act.c (all `*_name` builders) | `_interpret_*edit` inline handlers (build.py) | Success messages differ from ROM (e.g., `"Name set.\n\r"` → `"Object name (keywords) set to: X"`) across all four editors; builders trained on ROM will not recognize the output | 🔄 OPEN |
| OLC_ACT-012 | IMPORTANT | src/olc_act.c:653–663 `aedit_reset` | missing in `_interpret_aedit` (build.py:1261) | `aedit reset` (triggers `reset_area`) missing; no way to reset area from within area editor | 🔄 OPEN |
| OLC_ACT-013 | MINOR | src/olc_act.c:588–599 `get_vnum_area` | `_get_area_for_vnum` (build.py:1119) — iterates all areas | ROM iterates a linked list starting at `area_first`; Python iterates `area_registry.values()` (dict — unordered); functionally equivalent for lookup, minor ordering difference for `do_alist` output | 🔄 OPEN |
| OLC_ACT-014 | MINOR | src/olc_act.c:1716 `redit_create` return TRUE | `cmd_redit` — no return-value protocol | ROM builder functions return `TRUE`/`FALSE` to signal whether `AREA_CHANGED` should be set in the dispatcher; Python uses `area.changed = True` imperatively in each handler — not a behavioral gap but a structural divergence that could cause missed `changed` sets in future builders | 🔄 OPEN |

---

## Phase 4 — Closures

None this session. See Phase 3 gap table; closures handed off to `rom-gap-closer` per-gap.

**Recommended closure order** (by blocking impact):
1. OLC_ACT-006 (`medit_create` — `ACT_IS_NPC` missing) — highest severity, easiest fix
2. OLC_ACT-001 (`aedit_create` — wholly missing) — unblocks OLC-016
3. OLC_ACT-002 (`redit_create` — wholly missing) — unblocks OLC-017 create half
4. OLC_ACT-003 (`redit reset` — dispatcher gap) — unblocks OLC-017 reset half
5. OLC_ACT-004 (`redit <vnum>` — dispatcher gap) — unblocks OLC-017 vnum half
6. OLC_ACT-005 (`oedit_create` — partial, needs security gate + correct keyword) — unblocks OLC-018
7. OLC_ACT-007..010 (`*_show` completeness) — IMPORTANT, block builder UX
8. OLC_ACT-011 (message strings) — IMPORTANT, lower priority
9. OLC_ACT-012 (`aedit reset`) — IMPORTANT
10. OLC_ACT-013..014 — MINOR, defer

---

## Phase 5 — Completion

`olc_act.c` flips ❌ Not Audited → ⚠️ Partial (audit doc filed, gap IDs OLC_ACT-001..014 stable, no closures yet).

Status will flip to ✅ AUDITED only after:
- OLC_ACT-001..006 (CRITICAL gaps) closed with integration tests.
- OLC_ACT-007..012 (IMPORTANT gaps) closed or explicitly deferred with justification.
- TIER C functions receive a follow-up deep-audit pass (the ~78 functions marked 🔄 NEEDS DEEP AUDIT above).

**Human follow-up questions** (locked 2026-04-29):
1. **LOCKED — replicate**: `aedit_create` initializes `min_vnum=0`/`max_vnum=0` per ROM. Closure subagents replicate verbatim. Parity-faithful ROM quirk, not a bug to patch.
2. **LOCKED — reuse silent primitives**: `redit <vnum>` teleport reuses the existing silent helpers `_char_from_room`/`_char_to_room` in `mud/commands/imm_commands.py`. No new `silent_relocate` infra needed. `do_goto` itself is noisy (bamfout/bamfin acts) but its underlying primitives are silent — exactly what ROM `redit_<vnum>` requires.
3. **LOCKED — stay TIER C**: `medit_shop` remains TIER C. Shop-edit path is unreachable until OLC_ACT-006 (`medit_create`) lands; revisit in a follow-up audit pass after the six anchor gaps close.
