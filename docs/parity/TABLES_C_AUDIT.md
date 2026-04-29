# `tables.c` Parity Audit

**ROM source:** `src/tables.c` (750 lines, 38 data tables)
**Python target:** `mud/models/constants.py` (IntFlag/IntEnum classes)
**Status:** ⚠️ Partial — Phase 1 inventory complete, Phase 2 spot-checks complete, gaps documented and **deferred** (closure scope crosses persistence boundaries — separate focused sessions per gap).
**Date:** 2026-04-28

## Scope of file

`src/tables.c` is a pure data file: 32 `flag_type` tables, 4 `position/sex/size/clan` tables, 1 `apply_types` table, 1 `bitvector_type` table. Each table is a `(name, bit_value, settable)` tuple consumed by `flag_lookup` (via `prefix_lookup_intflag` in Python — see LOOKUP-002 closure) for OLC/`do_flag` abbreviation matching, and by `flag_string`/`act_bit_name` for display.

This file does not contain functions. The audit therefore deviates from the standard 5-phase function-by-function framework: Phase 2 verifies *value equivalence* and *name equivalence* (for prefix-match) of each ROM table against its Python IntFlag counterpart.

## Phase 1 — Inventory (38 tables)

| ROM table (line) | Python equivalent | Notes |
|---|---|---|
| `clan_table` (39) | `mud/models/clans.py:CLAN_TABLE` | ✓ See lookup.c LOOKUP-003. |
| `position_table` (48) | `mud/models/constants.py:Position` | ✓ See LOOKUP-004. |
| `sex_table` (62) | `mud/models/constants.py:Sex` | ✓ See LOOKUP-005. |
| `size_table` (71) | `mud/models/constants.py:Size` | ✓ See LOOKUP-006. |
| `act_flags` (82) | `ActFlag` | ✓ values match; ROM names diverge (e.g. `npc`/`healer`/`changer` vs `IS_NPC`/`IS_HEALER`/`IS_CHANGER`). |
| `plr_flags` (108) | `PlayerFlag` | ✓ values match; ROM `can_loot` vs Python `CANLOOT` (no underscore). |
| `affect_flags` (130) | `AffectFlag` | ❌ **values DIVERGE** — see TABLES-001. |
| `off_flags` (163) | `OffFlag` | ✓ values match; ROM `dirt_kick` vs Python `KICK_DIRT`. |
| `imm_flags` (188) | `ImmFlag` | ⚠️ to verify — see TABLES-003. |
| `form_flags` (215) | `FormFlag` | ⚠️ to verify. |
| `part_flags` (245) | `PartFlag` | ⚠️ to verify. |
| `comm_flags` (271) | `CommFlag` | ✓ values match; names match (lowercase). |
| `mprog_flags` (298) | `MProgTrigger` (or none) | ⚠️ to verify. |
| `area_flags` (318) | `AreaFlag` | ✓ values match. |
| `sex_flags` (328) | (overlap with `Sex`) | ⚠️ to verify. |
| `exit_flags` (339) | `ExitFlag` / `Direction` | ⚠️ to verify. |
| `door_resets` (355) | (loader-internal) | ⚠️ to verify. |
| `room_flags` (364) | `RoomFlag` | ✓ values match (verified spot-check). |
| `sector_flags` (384) | `Sector` | ⚠️ to verify. |
| `type_flags` (401) | `ItemType` | ⚠️ to verify. |
| `extra_flags` (434) | `ExtraFlag` | ⚠️ to verify. |
| `wear_flags` (463) | `WearFlag` | ⚠️ to verify. |
| `apply_flags` (489) | `Apply` / `ApplyType` | ⚠️ to verify. |
| `wear_loc_strings` (525) | `WearLocation` | ⚠️ to verify. |
| `wear_loc_flags` (550) | `WearLocation` | ⚠️ to verify. |
| `container_flags` (574) | `ContainerFlag` | ⚠️ to verify. |
| `ac_type` (590) | (display-only) | ⚠️ to verify. |
| `size_flags` (599) | `Size` | ⚠️ to verify. |
| `weapon_class` (610) | `WeaponClass` | ⚠️ to verify. |
| `weapon_type2` (624) | `WeaponFlag` | ⚠️ to verify. |
| `res_flags` (636) | `ResFlag` / `ImmFlag` | ⚠️ to verify. |
| `vuln_flags` (664) | `VulnFlag` / `ImmFlag` | ⚠️ to verify. |
| `position_flags` (691) | `Position` | ⚠️ to verify. |
| `portal_flags` (704) | `PortalFlag` | ⚠️ to verify. |
| `furniture_flags` (713) | `FurnitureFlag` | ⚠️ to verify. |
| `apply_types` (733) | `Apply` | ⚠️ to verify. |
| `bitvector_type` (743) | (dispatch table) | ⚠️ to verify. |

## Phase 2 — Verification highlights

### `act_flags` ✓ VALUES MATCH
ROM `src/tables.c:82-106` letters A..dd map 1:1 to Python `ActFlag` bit positions (verified by inline `# (X)` comments in `mud/models/constants.py:415-439`).

### `plr_flags` ✓ VALUES MATCH
ROM `src/tables.c:108-128` letters A..aa map 1:1 to `PlayerFlag` bit positions (`mud/models/constants.py:442-462`).

### `comm_flags` ✓ VALUES MATCH
Per `mud/models/constants.py:465-490`. Names are lowercase ROM-style, letters consistent.

### `off_flags` ✓ VALUES MATCH (one name divergence)
`mud/models/constants.py:493-516` matches ROM bit positions. ROM `dirt_kick` (J=1<<9) vs Python `KICK_DIRT` — same value, different name.

### `affect_flags` ❌ VALUES DIVERGE — **TABLES-001 CRITICAL**

ROM `src/merc.h:953-982` defines:
```
AFF_DETECT_HIDDEN  (F)  = 1<<5
AFF_DETECT_GOOD    (G)  = 1<<6
AFF_SANCTUARY      (H)  = 1<<7
AFF_FAERIE_FIRE    (I)  = 1<<8
AFF_INFRARED       (J)  = 1<<9
AFF_CURSE          (K)  = 1<<10
AFF_UNUSED_FLAG    (L)  = 1<<11
AFF_POISON         (M)  = 1<<12
...
AFF_DARK_VISION    (Z)  = 1<<25
AFF_BERSERK        (aa) = 1<<26
AFF_SWIM           (bb) = 1<<27
AFF_REGENERATION   (cc) = 1<<28
AFF_SLOW           (dd) = 1<<29
```

Python `AffectFlag` (`mud/models/constants.py:548-580`) has:
```
DETECT_HIDDEN = 1<<5
SANCTUARY     = 1<<6   ← ROM says G=detect_good
FAERIE_FIRE   = 1<<7   ← ROM says H=sanctuary
INFRARED      = 1<<8   ← ROM says I=faerie_fire
CURSE         = 1<<9   ← ROM says J=infrared
DETECT_GOOD   = 1<<10  ← ROM says K=curse
POISON        = 1<<11  ← ROM says L=unused, M=poison
... (all bits from 6 to 11 shifted)
DARK_VISION   = 1<<26  ← ROM says aa=berserk
SLOW          = 1<<24  ← ROM says dd=slow=1<<29
```

`mud/models/constants.py:1027-1044:convert_flags_from_letters` decodes ROM letters using the **ROM-correct** mapping (A→1<<0, G→1<<6, …). So area files containing `AFF G` (DETECT_GOOD in ROM) decode to bit 6, which Python interprets as `SANCTUARY`. Any mob/item proto, pfile, or race definition expressed in ROM-letter form is silently mis-decoded for affect flags.

Internal Python code is self-consistent (everything uses `AffectFlag.X` symbolically), so unit/integration tests against the enum pass. The bug only manifests at letter→int boundaries.

### Other tables
The remaining 30+ tables marked `⚠️ to verify` need a follow-up pass. Spot-checks above suggest most are values-correct with minor name divergence; AffectFlag is the outlier.

## Phase 3 — Gaps

| ID | Severity | ROM ref | Description | Status |
|---|---|---|---|---|
| `TABLES-001` | CRITICAL | `src/merc.h:953-982` + `src/tables.c:130-160` | `AffectFlag` bit positions in `mud/models/constants.py:548-580` diverge from ROM `merc.h` `AFF_*` defines for bits 6..29. Letter-form area data is mis-decoded by `convert_flags_from_letters`. Closure requires renumbering `AffectFlag` and migrating any persisted character/object/race state — defer to focused session with persistence migration plan. | 🔄 OPEN (deferred) |
| `TABLES-002` | IMPORTANT | `src/tables.c` (multiple) | ROM table names like `npc`/`healer`/`changer`/`can_loot`/`dirt_kick` do not prefix-match Python IntFlag member names (`IS_NPC`/`IS_HEALER`/`IS_CHANGER`/`CANLOOT`/`KICK_DIRT`). Breaks ROM-style abbreviations in `do_flag` and OLC. Closure: add ROM-name aliases via class-level attribute alias or dedicated lookup table. | 🔄 OPEN (deferred) |
| `TABLES-003` | IMPORTANT | `src/tables.c:188-294` (and others) | Per-table value equivalence audit not yet completed for `imm_flags`, `form_flags`, `part_flags`, `mprog_flags`, `extra_flags`, `wear_flags`, `apply_flags`, `wear_loc_flags`, `container_flags`, `weapon_class`, `weapon_type2`, `res_flags`, `vuln_flags`, `portal_flags`, `furniture_flags`, `apply_types`. Apply same letter→bit verification as for AffectFlag. | 🔄 OPEN (deferred) |

## Phase 4 — Closures

None this session. See SESSION_SUMMARY for rationale.

## Phase 5 — Tracker status

`tables.c` row stays ⚠️ Partial. Description updated from "70% Lookups partial" to reflect Phase 1 + Phase 2 spot-checks complete with three open gaps.
