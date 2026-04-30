# json_loader.py ↔ src/db.c + src/db2.c Parity Audit

**ROM C Files**: `src/db.c` (functions: `load_area`, `load_rooms`, `load_resets`, `load_shops`, `load_specials`, `load_helps`) + `src/db2.c` (functions: `load_mobiles`, `load_objects`, `convert_mobile`, `convert_objects`, `convert_object`)
**Python Target**: `mud/loaders/json_loader.py` (612 lines)
**Audit Date**: 2026-04-30
**Status**: ✅ **Phase 1–5 complete — ALL 18 GAPS CLOSED** (2026-04-30, v2.6.107)
**Trigger**: Four in-game runtime bugs (BUG-NLOWER, BUG-EDDICT, BUG-CORPSEINT, BUG-MOBHP) traced to the JSON loader being a partial port of the ROM C functions that the `.are` loaders (`mob_loader.py`, `obj_loader.py`) replicate correctly. The prior `DB_C_AUDIT.md` "100% certified" badge covered only the `.are` path; this audit covers the JSON path exclusively.

---

## Scope and Architecture Context

The QuickMUD codebase has **two parallel loader paths** for area data:

| Path | Entry point | Data source | Completeness |
|------|-------------|-------------|--------------|
| `.are` loader | `mob_loader.load_mobiles`, `obj_loader.load_objects`, `room_loader.load_rooms` | Legacy `.are` flat files | ✅ Audited (DB_C_AUDIT.md) |
| JSON loader | `json_loader.load_area_from_json` → `_load_mobs_from_json`, `_load_objects_from_json`, `_load_rooms_from_json` | `data/areas/*.json` files | ⚠️ **This audit** |

Live areas are loaded exclusively from the JSON path. The `.are` loader is used only when importing/converting legacy files. Bugs in the JSON path surface in every running game session; bugs in the `.are` path surface only during conversion passes.

The JSON schema was produced by `mud/scripts/convert_are_to_json.py` (not audited here). Schema shape confirmed from `data/areas/midgaard.json`:

- **mob** keys: `id`, `name` (= short_descr), `player_name`, `long_description`, `description`, `race`, `act_flags`, `affected_by`, `alignment`, `group`, `level`, `thac0`, `ac`, `hit_dice`, `mana_dice`, `damage_dice`, `damage_type`, `ac_pierce/bash/slash/exotic`, `offensive`, `immune`, `resist`, `vuln`, `start_pos`, `default_pos`, `sex`, `wealth`, `form`, `parts`, `size`, `material` — **no `keywords` field separate from `name`**
- **obj** keys: `id`, `name`, `description`, `material`, `item_type`, `extra_flags`, `wear_flags`, `weight`, `cost`, `condition`, `values`, `affects`, `extra_descriptions` — **no `keywords` field, no `level` field**
- **room** keys: `id`, `name`, `description`, `sector_type`, `flags`, `exits`, `extra_descriptions` — no `light`, no separate `owner` 'O' letter field, no clan as string
- **Format 2** (OLC-saved areas, `area_0.json`): area keys are `vnum`, `name`, `filename`, `min_level`, `max_level`, `builders` — missing `security`, `credits`, `min_vnum`, `max_vnum`

---

## Phase 1 — Function Inventory

| ROM C function | Source file:lines | Python equivalent | Python file:line | Status |
|---|---|---|---|---|
| `load_area` | `src/db.c:441-477` | `load_area_from_json` (area header block) | `mud/loaders/json_loader.py:174-297` | ⚠️ PARTIAL |
| `new_load_area` | `src/db.c:518-581` | `load_area_from_json` (Format 2 branch) | `mud/loaders/json_loader.py:181-196` | ⚠️ PARTIAL |
| `load_helps` | `src/db.c:603-676` | `_load_helps_from_json` | `mud/loaders/json_loader.py:505-522` | ✅ COMPLETE |
| `load_mobiles` | `src/db2.c:190-374` | `_load_mobs_from_json` | `mud/loaders/json_loader.py:413-474` | ⚠️ PARTIAL |
| `load_objects` | `src/db2.c:379-598` | `_load_objects_from_json` | `mud/loaders/json_loader.py:477-502` | ⚠️ PARTIAL |
| `load_resets` | `src/db.c:1009-1108` | inline in `load_area_from_json` | `mud/loaders/json_loader.py:256-289` | ⚠️ PARTIAL |
| `load_rooms` | `src/db.c:1113-1282` | `_load_rooms_from_json` | `mud/loaders/json_loader.py:300-361` | ⚠️ PARTIAL |
| `load_shops` | `src/db.c:1287-1339` | `_load_shops_from_json` | `mud/loaders/json_loader.py:525-553` | ✅ COMPLETE |
| `load_specials` | `src/db.c:1344-1376` | `apply_specials_from_json` (delegated) | `mud/loaders/specials_loader.py` | ✅ COMPLETE |
| `fix_exits` | `src/db.c:1384-1518` | `_link_exits_for_area` | `mud/loaders/json_loader.py:364-411` | ⚠️ PARTIAL |
| `load_mobprogs` | `src/db.c:1519-1571` | `_load_mob_programs_from_json` | `mud/loaders/json_loader.py:556-590` | ✅ COMPLETE |
| `convert_mobile` | `src/db2.c:869-970` | **MISSING** — not called from JSON path | — | ❌ MISSING |
| `convert_objects` | `src/db2.c:612-751` | **MISSING** — not called from JSON path | — | ❌ MISSING |
| `convert_object` | `src/db2.c:763-857` | **MISSING** — not called from JSON path | — | ❌ MISSING |

**Functional coverage**: 8/14 (57%); 2 N/A (convert_* only apply to old-format `.are` mobs, not ROM 2.4 new-format — see notes in Phase 3 gap table). Critical gaps in `load_mobiles`, `load_objects`, `load_rooms`, `load_area`.

---

## Phase 2 — Line-by-line Verification

### `load_area` / `new_load_area` — area header

**ROM C (`src/db.c:441-477`, `518-581`)** reads: `file_name`, `name`, `credits`, `min_vnum`, `max_vnum`, and for the OLC format: `Security`, `Builders`, `VNUMs`. It sets `area_flags = AREA_LOADING`, `security = 9`, `age = 15`, `nplayer = 0`, `empty = FALSE`.

**JSON loader (`json_loader.py:181-226`)** handles two JSON formats:
- **Format 1** (converted `.are`): reads `name`, `vnum_range.{min,max}`, `builders`. Sets `area_flags=0`, `security=0`. `credits` is not in the schema and defaults to `""`.
- **Format 2** (OLC-saved): reads `vnum`, `name`, `filename`, `min_level`, `max_level`, `builders`. Missing: `security`, `credits`, `min_vnum`, `max_vnum` (falls back to `vnum` for both). `area_flags` defaults to 0.

ROM-correct values for `age=15`, `nplayer=0`, `empty=False` are set at line 222–224 in both paths — correct.

**Gaps**: `security` always 0 in both formats (ROM defaults to 9); `credits` missing in Format 1; `min_vnum`/`max_vnum` collapse in Format 2; `area_flags` starts as 0 instead of `AREA_LOADING` (ROM strips this flag later, but the "loading" sentinel affects simultaneous area load detection).

---

### `load_mobiles` / `_load_mobs_from_json`

**ROM C (`src/db2.c:190-374`)** reads (new-format): `player_name`, `short_descr`, `long_descr`, `description`, `race` (via `race_lookup` → int), `act` (via `fread_flag | ACT_IS_NPC | race.act`), `affected_by` (via `fread_flag | race.aff`), `alignment`, `group`, `level`, `hitroll`, then dice triples for `hit[3]` / `mana[3]` / `damage[3]` as separate `[NUMBER]`/`[TYPE]`/`[BONUS]` ints, `dam_type` (via `attack_lookup`), `ac[4]` (×10 each), off/imm/res/vuln flags (via `fread_flag | race.X`), `start_pos`/`default_pos` (via `position_lookup`), `sex` (via `sex_lookup`), `wealth`, `form`/`parts` (via `fread_flag | race.X`), `size` (via `size_lookup`), `material` (as string). Then optional `F` (flag-remove) and `M` (mobprog) continuation lines.

**JSON loader (`json_loader.py:426-474`)** reads the same fields **but**:

1. **`hit`, `mana`, `damage` tuples left at `(0, 0, 0)` default** (`mud/models/mob.py:69-71`). The JSON schema only has string fields `hit_dice`, `mana_dice`, `damage_dice` (e.g. `"1d1+999"`). The loader assigns those strings to `MobIndex.hit_dice`/`mana_dice`/`damage_dice` (line 444–446) but never populates `MobIndex.hit`/`mana`/`damage` tuples. `templates.py:_parse_dice` (line 143–165) has a fallback that reads the string at spawn time, patched in commit `715469d`, but the canonical ROM approach is to store parsed ints in the prototype at load time, not re-parse strings each spawn.

2. **`hitroll` field**: ROM reads `pMobIndex->hitroll = fread_number(fp)` (`src/db2.c:248`). JSON schema has `thac0` field, loaded to `MobIndex.thac0` (line 441). The `hitroll` field on `MobIndex` (line 66) stays at 0. These are semantically different: ROM's `hitroll` is the attack roll bonus; `thac0` is legacy (only used in old-format mobs). New-format mobs in ROM set `hitroll` directly, not `thac0`.

3. **`race` stored as string, not int**: ROM calls `race_lookup(fread_string(fp))` and stores an integer index (`src/db2.c:234`). The JSON loader stores `mob_data.get("race", "")` as a raw string (line 434). `merge_race_flags` (line 472) handles the string via `get_race(race_name)`, so this works at load time, but any code path that uses `pMobIndex->race` as an integer index (e.g. `race_table[pMobIndex->race]` patterns in combat) will fail.

4. **`act_flags` / `affected_by` / `off` / `imm` / `res` / `vuln` / `form` / `parts` stored as raw letter strings, not resolved ints**: ROM resolves via `fread_flag` at load time to integer bitmasks; the JSON path defers resolution to `get_act_flags()` lazy conversion (line 97 of `mob.py`). This is architecturally correct for `act_flags`/`affected_by` (they have lazy converters) but `off_flags`, `imm_flags`, `res_flags`, `vuln_flags` on `MobIndex` (lines 73–76 of `mob.py`) are always 0 for JSON-loaded mobs — the string fields `offensive`/`immune`/`resist`/`vuln` are populated but the parallel integer fields are not. Any code using `mob.off_flags` / `mob.imm_flags` etc. directly sees zeros.

5. **`sex` lookup**: ROM uses `sex_lookup(fread_word(fp))` to resolve to an int (`src/db2.c:291`). JSON loader calls `Sex[sex_str.upper()]` (line 421). If the string is `"neutral"` rather than `"NONE"`, the lookup fails and defaults to `Sex.NONE` — same int value, so in practice benign, but the string-to-int conversion is not ROM-faithful (`sex_lookup` uses prefix matching; `Sex[X]` requires exact enum name match).

6. **`size` lookup**: ROM uses `size_lookup` with `CHECK_POS` (`src/db2.c:299`). JSON loader uses `Size[size_str.upper()]` (line 464) which requires exact name match, not prefix. `mob.size` stays as a string in `MobIndex` when the lookup fails gracefully, which can cause type errors at spawn.

---

### `load_objects` / `_load_objects_from_json`

**ROM C (`src/db2.c:379-598`)** reads: `name` (keyword list), `short_descr`, `description`, `material`, `item_type` (via `item_lookup`), `extra_flags` (via `fread_flag`), `wear_flags` (via `fread_flag`), type-specific `value[0..4]` (with per-type coercion: weapon_type, attack_lookup, skill_lookup, liq_lookup, flag parsing), `level`, `weight`, `cost`, `condition` (letter→int), then optional `A`/`F`/`E` continuation lines building typed `AFFECT_DATA *` linked list.

**JSON loader (`json_loader.py:477-502`)** reads the same fields **but**:

1. **`name` (keyword list) missing from schema**: ROM stores `pObjIndex->name` as the keyword list (e.g. `"scimitar blade sword"`) and `pObjIndex->short_descr` as the display name. The JSON schema collapsed both into a single `name` field (e.g. `"a scimitar"`), loaded to `ObjIndex.short_descr` (line 485). `ObjIndex.name` stays `None` (line 32 of `obj.py`). Patched defensively at all `is_name` call sites (commit `658d319`) but the schema-level gap remains: keyword matching falls back to `short_descr` which is a prose string, not a keyword list.

2. **`wear_flags` not converted to int**: `wear_flags=obj_data.get("wear_flags", "")` (line 489) stores the raw string from JSON. The `.are` loader calls `_parse_flag_field(wear_flags_token, WearFlag)` (obj_loader.py line 389). Any code calling `obj.wear_flags` expecting an integer bitmask (e.g. `IS_SET(pObjIndex->wear_flags, ITEM_WEAR_X)`) sees a string.

3. **`extra_descr` stored as raw dicts, not `ExtraDescr` instances**: `extra_descr=obj_data.get("extra_descriptions", [])` (line 498) stores `[{'keyword': str, 'description': str}]` raw dicts. ROM (`src/db2.c:571-580`) allocates typed `EXTRA_DESCR_DATA *` structs. The room loader at line 358 does convert to `ExtraDescr` objects; the object loader does not. Consumer code patched at look/examine sites (commit `cb4eed7`) but the mismatch means `ObjIndex.extra_descr` contains dicts while `Room.extra_descr` contains `ExtraDescr` objects — inconsistent across the codebase.

4. **`level` field absent from JSON schema** (`data/areas/midgaard.json` objects have no `level` key): `int(obj_data.get("level", 0) or 0)` (line 492) always returns 0. ROM (`src/db2.c:479`) reads `pObjIndex->level = fread_number(fp)`. All JSON-loaded objects have `level=0`. This affects: (a) `AFFECT_DATA.level` set to `pObjIndex->level` in `A`/`F` affets blocks; (b) `create_object` stat scaling; (c) shop-level minimum thresholds. Note: the `.are` converter presumably stored level in the JSON but the midgaard JSON doesn't have it — may be a converter omission.

5. **`affects` list stored as raw dicts, not `Affect` instances**: `affects=obj_data.get("affects", [])` (line 497) stores `[{'location': int, 'modifier': int}]`. The `.are` loader (obj_loader.py line 438–447) constructs both `obj.affects` (dict) and `obj.affected` (typed `Affect` objects). The JSON loader only populates `ObjIndex.affects` (raw dicts); `ObjIndex.affected` (line 51 of `obj.py`) stays `[]`. Code reading `obj.affected` for full affect application (bitvector, where, type, duration) sees nothing.

6. **`extra_flags` conversion uses `_rom_flags_to_int` (line 488) but `wear_flags` does not**: `extra_flags` is correctly converted via `_rom_flags_to_int`; `wear_flags` is stored as a raw string. Asymmetric treatment.

7. **Type-specific `value[]` parsing not applied at load time**: `value=obj_data.get("values", [0,0,0,0,0])` (line 496) stores whatever the JSON has. For weapons, the JSON stores numeric values already resolved (e.g. `[1, 4, 10, 21, 48]`), but for DRINK_CON/FOUNTAIN `value[2]` is the liquid index as an integer (appears already resolved in midgaard.json). However, there is no guarantee that weapon `value[3]` (attack type), wand/staff `value[3]` (spell index), or potion/scroll/pill `value[1..4]` (spell indices) are pre-resolved in all JSON files — the converter script is not audited. The `.are` loader calls `_parse_item_values` which runs per-type coercion; the JSON loader does none.

---

### `load_rooms` / `_load_rooms_from_json`

**ROM C (`src/db.c:1113-1282`)** reads: vnum, `name`, `description`, area-number (discarded), `room_flags` (via `fread_flag`), `sector_type` (int), then optional `H`/`M`/`C`/`D`/`E`/`O`/`S` letter blocks for heal_rate, mana_rate, clan, exits, extra_descr, owner. Exit `locks` field (0–4 integer enum) is mapped to `exit_info`/`rs_flags` bit combinations.

**JSON loader (`json_loader.py:300-361`)** reads most fields, **but**:

1. **`clan` field**: ROM reads `pRoomIndex->clan = clan_lookup(fread_string(fp))` (`src/db.c:1192`). JSON loader reads `room_data.get("clan", 0)` (line 328) expecting an integer. If the converter stored the clan name string (as `clan_lookup` in ROM takes a string), this will be 0 or the string stored as-is — not an integer clan id.

2. **`room_flags` sector_type as string name not ROM int**: ROM reads `pRoomIndex->sector_type = fread_number(fp)` (int). JSON loader does `Sector[sector_str.upper()]` (line 311) — correct for named strings, but the fallback warning+default is only triggered on unknown strings; numeric-string sector types (e.g. `"3"`) are handled via `sector_str.isdigit()` check at line 307. Appears correct but more fragile than the `.are` path.

3. **Exit `locks` integer-to-flags mapping is partially incorrect**: ROM (`src/db.c:1218-1238`) maps `locks` values 1–4 to specific `EX_ISDOOR`, `EX_ISDOOR|EX_PICKPROOF`, `EX_ISDOOR|EX_NOPASS`, `EX_ISDOOR|EX_NOPASS|EX_PICKPROOF` combinations. JSON stores pre-resolved `flags` already as bitfields. The JSON loader calls `_parse_exit_flags` which converts ROM letter strings or integers. However, there is no validation that exit `flags` in the JSON files consistently represent `rs_flags` vs `exit_info` — both fields are set to the same parsed value (lines 348–349), which matches ROM only when the exit has never been opened/closed at runtime.

4. **`room.light` not initialized**: ROM explicitly sets `pRoomIndex->light = 0` (`src/db.c:1164`). JSON loader never sets `room.light` — this is a model default (acceptable if `Room.__init__` defaults it to 0, but not explicitly audited here).

5. **`ROOM_NO_MOB` auto-set for isolated rooms**: `_link_exits_for_area` adds `ROOM_NO_MOB` if a room has no exits (line 410). ROM does not do this in `load_rooms`; ROM sets `ROOM_NO_MOB` from the area file flag, not automatically. This is a JSON-loader-specific behavioral addition that may silently block mob spawning in stub/disconnected rooms.

---

### `load_resets` (inline in `load_area_from_json`)

**ROM C (`src/db.c:1009-1108`)** reads resets in order: `command`, `if_flag` (discarded), `arg1`, `arg2`, `arg3` (0 for G/R), `arg4` (0 unless P or M). For `D` resets, ROM applies the door state immediately during loading (`SET_BIT pexit->rs_flags/exit_info`). `D` resets are **not** stored in the room reset list — they are applied once and discarded.

**JSON loader (`json_loader.py:256-289`)**:

1. **`D` resets stored in `area.resets` and room reset lists**: ROM discards `D` reset records after applying door state at load time (`src/db.c:1101-1104`: `free_reset_data(pReset)` without calling `new_reset`). The JSON loader appends all reset types including `D` to `area.resets` (line 283) and to `room.resets` (line 289). This means `D` resets run at every area reset cycle rather than once at boot — doors get re-locked on every reset tick, which matches ROM behavior by coincidence but via a different mechanism.

2. **Legacy vs. current arg layout detection heuristic**: The shifted-args detection (`raw_args[0] in (0,1) and raw_args[1]`, lines 263–265) is a best-effort heuristic, not a specification. It will misfire if arg1 legitimately equals 0 or 1 (e.g. a valid mob vnum of 1 or a global limit of 0).

3. **`R` reset**: `_resolve_room_target` for `R` uses `reset.arg1` as the room vnum (line 166). ROM does the same (`rVnum = pReset->arg1`, `src/db.c:1091`). Appears correct.

---

### `load_shops` / `_load_shops_from_json`

**ROM C (`src/db.c:1287-1339`)**: reads keeper, 5 buy_types, profit_buy, profit_sell, open_hour, close_hour. Exact field-for-field match.

**JSON loader (`json_loader.py:525-553`)**: correct field mapping. `buy_types` is padded to 5 entries with 0. No gaps identified.

---

### `convert_mobile`, `convert_objects`, `convert_object`

**ROM C** (`src/db2.c:612-857`, `869-970`): These functions only apply to **old-format** mobs/objects (`new_format == FALSE`). All ROM 2.4 new-format areas (`new_format = TRUE`) skip them. Since the JSON loader always sets/implies new-format behavior and the converted JSON files contain pre-resolved dice values, these functions have no direct equivalent on the JSON path. **No gap** — but this is contingent on the JSON schema containing correctly pre-resolved dice values from the converter, which is not verified in this audit.

---

## Phase 3 — Gap Table

| Gap ID | Severity | ROM C ref | Python ref | Description | Status |
|---|---|---|---|---|---|
| JSONLD-001 | CRITICAL | `src/db2.c:420` (`pObjIndex->name = fread_string`) | `mud/loaders/json_loader.py:485` | Object `name` (keyword list) is missing from the JSON schema; `ObjIndex.name` stays `None`. JSON `name` field maps to `short_descr` only. All keyword-based `is_name` matching falls back to `short_descr` which is a prose description string. Consumer sites patched (commit `658d319`) but loader-side and schema-side fix pending. | ✅ FIXED (v2.6.107 — converter emits `keywords` field; loader reads it with `name` fallback; all area JSONs regenerated) |
| JSONLD-002 | CRITICAL | `src/db2.c:571-580` (`EXTRA_DESCR_DATA *ed`) | `mud/loaders/json_loader.py:498` | Object `extra_descr` stored as raw `list[dict]` instead of `list[ExtraDescr]`. Room loader (line 358) correctly creates `ExtraDescr` instances; object loader does not. Examine/look at object extra descriptions either fails or requires dict-aware fallback at every consumer site. | ✅ FIXED (v2.6.103 — objects now store `ExtraDescr` instances) |
| JSONLD-003 | CRITICAL | `src/db2.c:479` (`pObjIndex->level = fread_number`) | `mud/loaders/json_loader.py:492` | Object `level` field absent from JSON schema (midgaard.json objects have no `level` key); loader always reads 0. `AFFECT_DATA.level` for object affects incorrectly set to 0. Likely a converter omission: `convert_are_to_json.py` should emit `level`. Fixed in the `.are` path (obj_loader.py:398). | ✅ FIXED (v2.6.107 — converter emits `level`; loader reads it; all area JSONs regenerated) |
| JSONLD-004 | CRITICAL | `src/db2.c:251-269` (`pMobIndex->hit[DICE_NUMBER]` etc.) | `mud/loaders/json_loader.py:444-446`; `mud/models/mob.py:69-71` | Mob `hit`/`mana`/`damage` int triples not populated at load time; stay at `(0, 0, 0)`. JSON path carries only string forms (`hit_dice`, `mana_dice`, `damage_dice`). Spawn-time fallback in `templates.py:_parse_dice` works but is a crutch. The canonical fix parses the strings into the prototype tuples at load time. | ✅ FIXED (v2.6.103 — `hit`/`mana`/`damage` tuples parsed from dice strings at load time via `_parse_dice_tuple`) |
| JSONLD-005 | CRITICAL | `src/db2.c:427-428` (`extra_flags = fread_flag; wear_flags = fread_flag`) | `mud/loaders/json_loader.py:488-489` | `extra_flags` is correctly converted via `_rom_flags_to_int` but `wear_flags` is stored as raw string (e.g. `"abcd"` or `"0"`). Any code calling `IS_SET(obj.wear_flags, ITEM_WEAR_X)` against the integer bitmask will fail on JSON-loaded objects. The `.are` loader calls `_parse_flag_field(wear_flags_token, WearFlag)` (obj_loader.py:389). | ✅ FIXED (v2.6.103 — `wear_flags` now converted to int via `convert_flags_from_letters`) |
| JSONLD-006 | CRITICAL | `src/db2.c:519-568` (`AFFECT_DATA *paf` with `where`, `type`, `level`, `duration`, `bitvector`) | `mud/loaders/json_loader.py:497` (`affects=obj_data.get(...)`) | Object `affects` list populated with raw dicts only; `ObjIndex.affected` (typed `Affect` list) stays empty. The `.are` loader constructs both `obj.affects` (dict) and `obj.affected` (typed). Apply-affect code at equip/unequip time reads `obj.affected`, not `obj.affects`. | ✅ FIXED (v2.6.103 — `affected` list populated with typed `Affect` instances) |
| JSONLD-007 | CRITICAL | `src/db2.c:248` (`pMobIndex->hitroll = fread_number`) | `mud/loaders/json_loader.py:441` (`thac0=mob_data.get("thac0", 20)`) | `hitroll` (attack roll bonus, used in `one_hit`) not populated from JSON; stays 0. JSON schema has `thac0` which is a legacy old-format field (unused in new-format mobs by ROM). New-format mobs set `hitroll` directly; the JSON schema stores the value under the wrong key and the loader assigns it to the wrong field. | ✅ FIXED (v2.6.103 — `hitroll` populated from `hitroll` key with `thac0` fallback) |
| JSONLD-008 | IMPORTANT | `src/db2.c:279-286` (`off_flags = fread_flag | race.off; imm_flags = fread_flag | race.imm` etc.) | `mud/models/mob.py:73-76` | `MobIndex.off_flags`/`imm_flags`/`res_flags`/`vuln_flags` integer fields stay 0 for JSON-loaded mobs. String fields `offensive`/`immune`/`resist`/`vuln` are populated but not converted. `merge_race_flags` (line 472) merges into the string fields, not the int fields. Any code reading `mob.off_flags` etc. directly sees 0. | ✅ FIXED (v2.6.103 — int fields populated via `_to_int_flags` after `merge_race_flags`) |
| JSONLD-009 | IMPORTANT | `src/db.c:452` (`pArea->security = 9`) | `mud/loaders/json_loader.py:214` (`security=0`) | Area `security` hardcoded to 0 in both Format 1 and Format 2 JSON paths. ROM default for `.are` load is 9; OLC format sets it from the `Security` keyword. JSON Format 2 schema (`area_0.json`) lacks the `security` field entirely. OLC permission checks use `area->security` to gate edits. | ✅ FIXED (v2.6.104 — Format 1 and Format 2 areas now default `security` to 9, preserving explicit JSON values) |
| JSONLD-010 | IMPORTANT | `src/db.c:457` (`pArea->credits = fread_string`) | `mud/loaders/json_loader.py:203` (`credits=""`) | Area `credits` field always `""` for Format 1 JSON (not in schema). ROM reads credits from the `.are` `#AREA` header. Displayed in `do_areas` output; cosmetically incorrect. | ✅ FIXED (v2.6.104 — Format 1 `credits` now hydrates from JSON when present) |
| JSONLD-011 | IMPORTANT | `src/db2.c:295-297` (`pMobIndex->form = fread_flag | race.form; parts = fread_flag | race.parts`) | `mud/loaders/json_loader.py:462-463` | `mob.form` and `mob.parts` stored as raw letter strings (from JSON), not integer bitmasks. `merge_race_flags` merges race bits into the string form. Any code reading `mob.form` as an integer (bitwise tests like `IS_SET(mob->form, FORM_EDIBLE)`) will fail on JSON-loaded mobs because `int(mob.form)` raises `ValueError` on a letter string. | ✅ FIXED (v2.6.103 — `form`/`parts` converted to int bitmasks via `_to_int_flags` after `merge_race_flags`) |
| JSONLD-012 | IMPORTANT | `src/db2.c:234` (`pMobIndex->race = race_lookup(fread_string)`) | `mud/loaders/json_loader.py:434` (`race=mob_data.get("race", "")`) | `MobIndex.race` stored as string (`"human"`, `"elf"`, etc.) not integer index. `merge_race_flags` handles this via `get_race(name)` but any code that treats `mob.race` as an integer index for `race_table[mob.race]`-style access will fail. | ✅ FIXED (v2.6.105 — JSON mob race names now resolve through `race_lookup` to int `race_table` indexes; merge/save/display paths preserve name compatibility) |
| JSONLD-013 | IMPORTANT | `src/db.c:1192` (`pRoomIndex->clan = clan_lookup(fread_string)`) | `mud/loaders/json_loader.py:328` (`clan=room_data.get("clan", 0)`) | Room `clan` loaded as raw JSON value (expected integer but not validated). ROM uses `clan_lookup(string)` to resolve by name. If JSON converter stored the clan name string instead of the integer id, `room.clan` will be a string, breaking clan-room membership checks. | ✅ FIXED (v2.6.104 — JSON room clans now resolve through `lookup_clan_id`, including ROM prefix matching) |
| JSONLD-014 | IMPORTANT | `src/db.c:1098-1104` (D-reset discarded after application) | `mud/loaders/json_loader.py:283-289` | `D` resets are stored in `area.resets` and processed each reset cycle. ROM applies `D` resets once at boot to set door initial state and discards the record (`free_reset_data`). While the practical effect is the same (doors get reset to their default state), it is semantically incorrect and may interact with OLC or manual door-state changes unexpectedly. | ✅ FIXED (v2.6.104 — JSON D resets now apply boot door state and are not retained in area/room reset lists) |
| JSONLD-015 | IMPORTANT | `src/db2.c:429-478` (per-type `value[]` coercion via `weapon_type`, `attack_lookup`, `skill_lookup`, `liq_lookup`) | `mud/loaders/json_loader.py:496` (`value=obj_data.get("values", [0,0,0,0,0])`) | No type-specific value coercion at load time. Values are taken directly from JSON as integers. The converter likely pre-resolved them, but: (a) this is not guaranteed; (b) spell-index values for wand/staff/potion/scroll/pill `value[3]`/`value[1..4]` may diverge if skill table ordering changes. The `.are` loader calls `_parse_item_values` which runs `_skill_lookup`, `_liq_lookup`, `_weapon_type_lookup`, etc. | ✅ FIXED (v2.6.107 — `_parse_item_values` called at load time; `attack_lookup` now handles numeric strings for JSON pre-resolved ints) |
| JSONLD-016 | MINOR | `src/db2.c:869-870` (`pObjIndex->short_descr[0] = LOWER`, `description[0] = UPPER`) | `mud/loaders/json_loader.py:485-486` | ROM normalizes `short_descr` to lowercase-first, `description` to uppercase-first on load. JSON loader does neither. Converter likely preserves whatever case the original `.are` had, so this is usually correct — but a defensively correct loader would apply the same normalization. | ✅ FIXED (v2.6.107 — short_descr lower-first, description upper-first applied at load time) |
| JSONLD-017 | MINOR | `src/db.c:1164` (`pRoomIndex->light = 0`) | `mud/loaders/json_loader.py:300-361` | Room `light` field never explicitly initialized by JSON loader — relies on `Room.__init__` default. Audit note only; no known bug. | ✅ CLOSED-BY-DESIGN (v2.6.107 — `Room.light` dataclass default is 0; explicit init is redundant but verified in test) |
| JSONLD-018 | MINOR | `_link_exits_for_area` only-JSON behavior | `mud/loaders/json_loader.py:410` | `ROOM_NO_MOB` auto-added to rooms with no exits. ROM does not do this; it is a JSON-path-only addition that may silently suppress mob spawning in isolated/stub rooms during development. | ✅ FIXED (v2.6.107 — removed the JSON-only ROOM_NO_MOB auto-add) |

---

## Phase 3 — Gap Count Summary

| Severity | Count | Gap IDs |
|---|---|---|
| CRITICAL | 7 | JSONLD-001, 002, 003, 004, 005, 006, 007 |
| IMPORTANT | 8 | JSONLD-008, 009, 010, 011, 012, 013, 014, 015 |
| MINOR | 3 | JSONLD-016, 017, 018 |
| **Total** | **18** | |

**Closed in v2.6.103**: JSONLD-002, 004, 005, 006, 007 (CRITICAL); JSONLD-008, 011 (IMPORTANT). 7 of 18 gaps closed.
**Closed in v2.6.104**: JSONLD-009, 010, 013, 014 (IMPORTANT). 11 of 18 gaps closed.
**Closed in v2.6.105**: JSONLD-012 (IMPORTANT). 12 of 18 gaps closed.
**Closed in v2.6.107**: JSONLD-001, 003 (CRITICAL); JSONLD-015 (IMPORTANT); JSONLD-016, 017, 018 (MINOR). **All 18 of 18 gaps closed.** 🎉

---

## Notes for Phase 4

### Fix location: loader vs. schema vs. converter

Several gaps have two possible fix sites:

| Gap | Loader fix | Schema/converter fix needed? |
|---|---|---|
| JSONLD-001 (name/keywords) | Add `keywords` field to `ObjIndex`, populate from JSON `keywords` key if present, else split `name` | Yes — `convert_are_to_json.py` must emit separate `keywords` and `name` fields |
| JSONLD-003 (obj level) | `int(obj_data.get("level", 0))` already present — no-op once converter emits level | Yes — converter must emit `level` field |
| JSONLD-004 (hit/mana/damage tuples) | Parse `hit_dice` string → 3-tuple at load time (single line: `_parse_dice((0,0,0), mob_data.get("hit_dice", ""))`) | No |
| JSONLD-005 (wear_flags) | Call `_rom_flags_to_int(obj_data.get("wear_flags", ""))` instead of raw get | No |
| JSONLD-006 (Affect typed list) | Construct `Affect` objects from `affects` dicts at load time, same as obj_loader.py:438–447 | No |
| JSONLD-007 (hitroll vs thac0) | Read `mob_data.get("hitroll", mob_data.get("thac0", 0))` and assign to `MobIndex.hitroll` | Yes — converter should emit `hitroll` not `thac0` for new-format mobs |
| JSONLD-008 (off/imm/res/vuln ints) | After `merge_race_flags`, call `_rom_flags_to_int` on string fields and assign to int fields | No |
| JSONLD-011 (form/parts ints) | Same pattern as JSONLD-008: convert string→int after merge | No |

### Single-commit vs. multi-commit scope

- **JSONLD-001** (keywords): requires schema change + converter pass over all `data/areas/*.json` files + loader change. Multi-commit project; scope as 3 commits (schema, converter, loader).
- **JSONLD-002** (extra_descr typed): single-commit loader fix.
- **JSONLD-003** (obj level): requires converter re-run; the loader line is already correct for when the field is present.
- **JSONLD-004** (dice tuples): single-commit loader fix (~3 lines in `_load_mobs_from_json`).
- **JSONLD-005** through **JSONLD-008**, **JSONLD-011**: each is a single-commit loader fix.
- **JSONLD-009**, **JSONLD-010**: single-commit loader fix (read from JSON with ROM default fallbacks).
- **JSONLD-012** (race as int): requires audit of all `mob.race` consumers before changing; may be LOW risk if all consumers use `get_race()` already.
- **JSONLD-013** (clan): single-commit loader fix (call `clan_lookup` on string or accept int).
- **JSONLD-014** (D-resets): single-commit behavioral fix (filter D-resets out of stored list, apply immediately to exit state).
- **JSONLD-015** (value coercion): medium effort — requires running `_parse_item_values`-equivalent logic against the pre-resolved JSON values; risk of double-conversion if converter already resolved them. Needs careful testing.
- **JSONLD-016–018**: deferred MINOR cosmetic/defensive.

### Integration test targets

When closing these gaps, the integration test file should be `tests/integration/test_json_loader_parity.py`. Priority test scenarios:
- Load a mob and verify `mob.hit`, `mob.mana`, `mob.damage` tuples are non-zero (JSONLD-004)
- Load an object with wear_flags and verify `isinstance(obj.wear_flags, int)` (JSONLD-005)
- Load an object with affects and verify `len(obj.affected) > 0` and `obj.affected[0].bitvector` accessible (JSONLD-006)
- Load an object with extra_descriptions and verify `isinstance(obj.extra_descr[0], ExtraDescr)` (JSONLD-002)
- Load an object with a keyword list and verify `is_name("keyword", obj)` returns True (JSONLD-001)
- Load a mob and verify `mob.hitroll != 0` for a mob with non-zero hitroll in source (JSONLD-007)
