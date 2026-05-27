# META Audit: PARALLEL_REPRESENTATIONS (Class 7)

> **Parent**: `docs/parity/META_AUDIT_TAXONOMY.md` § Class 7.
> **Related invariants**: `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` rows
> **INV-012** (OBJECT-LIST-CANONICAL), **INV-013**
> (OBJECT-LOCATION-COHERENCE), **INV-014** (OBJECT-REGISTRY-LIFECYCLE).
> **Sibling audit**: `docs/parity/audits/DUPLICATE_IMPLEMENTATIONS.md`.

## Scope

Class 7 covers cases where one conceptual entity has two parallel Python
representations that can silently drift: flag-as-IntEnum vs flag-as-raw-hex,
`equipment[WearLocation]` dict vs `equipped["held"]`-style legacy dict,
`char.inventory` vs `char.carrying`, `room.people` vs `room.characters`,
`character_registry` vs ad-hoc global lists, `Object` vs `ObjectData`,
`Object.in_room`/`carried_by`/`in_obj` vs `Object.location`.

Per the META taxonomy the expectation is **"mostly closed by
INV-012/INV-013/INV-014"** — the dual-class divergence (`Object`/`ObjectData`),
the four-container coherence (`in_room`/`carried_by`/`in_obj` exclusivity via
the `location` property), and the registry-lifecycle contract are all already
locked with enforcement tests. This audit is therefore primarily a closed-row
record verifying the no-drift hypothesis and cataloguing residual sites.

## Method

1. `grep -rn "\.carrying\b\|equipped\[" mud/ --include="*.py"` — straggler attrs.
2. `grep -rn "room\.characters\b" mud/ --include="*.py"` — legacy room list.
3. `grep -rn "0x[0-9A-Fa-f]\{4,\}" mud/commands/ mud/skills/` — raw hex in
   gameplay code paths that should compare against IntEnum.
4. `grep -rn "isinstance.*ObjectData\|isinstance.*AffectData\|hasattr.*location"`
   — legacy-shape dispatch branches (per META rubric step 2).
5. Cross-checked findings against INV-012/13/14 rows and the
   DUPLICATE_IMPLEMENTATIONS closed bugs (DUPL-003 for `carrying`).

## Findings

### Flag storage

| ID | Site | Issue | Severity | Status | Notes |
|----|------|-------|----------|--------|-------|
| PARALLEL-001 | `mud/commands/misc_player.py:90-98` (`configs` table for `do_config`) | `autoassist`/`autoexit`/`autogold`/`autoloot`/`autosac`/`autosplit`/`compact`/`brief`/`prompt`/`combine` defined as inline raw hex literals (`0x00001000`, etc.) rather than `PlayerFlag.AUTOLOOT` / `CommFlag.COMPACT`. Read against `char.act` / `char.comm` ints. | LOW (drift-risk) | ⚠️ DRIFT-RISK | Comparison is hex-vs-int so no current bug, but if any of these flag values are ever shifted in `mud/models/constants.py` the table will silently desync. Same pattern as the (fixed) SAC-004 `autosplit` bug called out in `obj_manipulation.py:461` comment. Recommend replacing each tuple's flag literal with `PlayerFlag.AUTOLOOT` etc. — one mechanical commit, no behavior change. |
| PARALLEL-002 | `mud/commands/player_config.py:12-14` (`PLR_CANLOOT`, `PLR_NOSUMMON`, `PLR_NOFOLLOW`) and `:76` (`IMM_SUMMON = 0x00000010`) | Module-local hex aliases for player/imm flags already defined as enums in `mud/models/constants.py`. | LOW (drift-risk) | ⚠️ DRIFT-RISK | Values are correct today. Replace with `PlayerFlag.CANLOOT` etc. for single-source-of-truth. |
| PARALLEL-003 | `mud/commands/remaining_rom.py:104-105` (`COMM_DEAF`, `COMM_QUIET`) and `:211` (`ACT_GAIN = 0x00100000` inside `do_train`) | Inline hex flag duplication of `CommFlag.DEAF` / `CommFlag.QUIET` and `ActFlag.GAIN`. | LOW (drift-risk) | ⚠️ DRIFT-RISK | Same class as PARALLEL-001. The `ACT_GAIN` literal is also an in-function local — exactly the shape that goes stale silently. |
| PARALLEL-004 | `mud/commands/misc_player.py:19` (`COMM_AFK = 0x00000800`) | Module-local hex alias for `CommFlag.AFK`. | LOW (drift-risk) | ⚠️ DRIFT-RISK | Used by the `configs` table (PARALLEL-001). Fold into the same cleanup. |
| PARALLEL-005 | `mud/commands/obj_manipulation.py:617` (`ITEM_NODROP = 0x0010` inside `_can_drop_obj`) | Inline hex for `ExtraFlag.NODROP`. | LOW (drift-risk) | ⚠️ DRIFT-RISK | Local function-scope duplication of an enum that already exists. |
| PARALLEL-006 | `mud/commands/imm_load.py:176-177` (`ACT_NOPURGE = 0x00002000`, `ITEM_NOPURGE = 0x00000040`) | Inline hex flag aliases. | LOW (drift-risk) | ⚠️ DRIFT-RISK | Same class — fold into the enum-only cleanup pass. |

### Equipment representation

| ID | Site | Issue | Severity | Status | Notes |
|----|------|-------|----------|--------|-------|
| PARALLEL-007 | (none) | Sweep for `equipped[` returned **zero hits** in `mud/`. All equipment access goes through `char.equipment[WearLocation.X]` (IntEnum-keyed dict). | — | ✅ ENFORCED | The legacy `equipped["held"]` shape has been fully retired. No drift surface remains. |

### Inventory representation

| ID | Site | Issue | Severity | Status | Notes |
|----|------|-------|----------|--------|-------|
| PARALLEL-008 | `mud/commands/consumption.py:308-316` (`_find_obj_inventory`) | Defensive fallback: `inventory = getattr(ch, "inventory", None); if inventory is None: inventory = getattr(ch, "carrying", [])`. Comment explicitly documents that the prior `.carrying` read was a bug (closed by DUPL-003 in 2.9.28). | LOW (dead-fallback) | ⚠️ DRIFT-RISK | The `getattr(ch, "carrying", [])` branch is unreachable on real `Character` instances (the attribute does not exist). Kept as belt-and-braces but adds zero value and reads as if `.carrying` were still a supported parallel rep. Recommend deleting the fallback branch; canonical `char.inventory` is enforced everywhere else. |
| PARALLEL-009 | Global sweep `grep -rn "\.carrying\b" mud/` | Only one hit: the comment + fallback in `consumption.py:311` above. No production code reads/writes `.carrying`. | — | ✅ ENFORCED | DUPL-003 closed the `carrying` parallel-rep bug class (the buggy `_extract_obj` copies that read `char.carrying`). Verified clean. |

### Room / registry collections

| ID | Site | Issue | Severity | Status | Notes |
|----|------|-------|----------|--------|-------|
| PARALLEL-010 | `mud/commands/combat.py:683-688` (`do_flee` movement branch) | After successful flee, the code wrote to `room.characters`/`new_room.characters`; canonical attr is `room.people`. | MEDIUM (silent no-op) | ✅ FIXED (2.9.54) | Closed by switching to canonical `room.remove_character(char)` / `new_room.add_character(char)` helpers (defined at `mud/models/room.py:140, 157`). The `hasattr(room, "characters")` gate that silently hid the remove is gone; the broad `try/except` that masked the `AttributeError` from the `append` is gone. Also fixed the same bug at line 665 (room-broadcast loop iterated `room.characters` — now iterates `room.people`). Regression pinned by `tests/integration/test_flee_moves_character.py::test_flee_moves_character_to_new_room`. |
| PARALLEL-011 | `mud/handler.py:694` (docstring "Uses obj.in_room.characters instead of linked list") | Docstring claim is stale; actual code on line 702 uses `getattr(obj, "in_room", None) or getattr(obj, "location", None)` and then iterates `in_room.people` (the function `count_users` walks people, not "characters"). | LOW (doc-drift) | ⚠️ DRIFT-RISK | Comment-only. Update doc to say `in_room.people`. |
| PARALLEL-012 | `character_registry` usage across `mud/mob_cmds.py`, `mud/game_loop.py`, `mud/music/__init__.py`, `mud/net/protocol.py`, `mud/net/connection.py`, `mud/wiznet.py`, `mud/mobprog.py` | Single global registry imported and iterated consistently; only `mud/mobprog.py:785-790` defensively defaults to `[]` on import failure (test-shim). No parallel global list exists. | — | ✅ ENFORCED | `character_registry` is the single source. The mobprog import-fallback is a test-import shim, not a parallel rep. |
| PARALLEL-013 | `Object.location` property dispatching to `in_room` / `carried_by` / `in_obj` | All `hasattr(obj, "location")` / `getattr(obj, "location", None)` sites (≈25 across `mud/handler.py`, `mud/combat/`, `mud/commands/shop.py`, `mud/skills/handlers.py`, `mud/spec_funs.py`, `mud/spawning/templates.py`, `mud/world/movement.py`, `mud/mob_cmds.py`, `mud/ai/__init__.py`, `mud/models/room.py`) read the property — not a parallel field. | — | ✅ ENFORCED (by INV-013) | INV-013 converted `Object.location` from a stored field to a dispatching `@property` over the three ROM-canonical containers. The `hasattr` guards remain because some test mocks (SimpleNamespace) still construct bare objects, but on real `Object` instances all reads route to the canonical fields. No drift surface. |
| PARALLEL-014 | `Object` vs `ObjectData` dual-class | `mud/models/obj.py:ObjectData` deleted in 2.9.0 (INV-012). `grep "isinstance.*ObjectData"` returns zero hits in `mud/`. | — | ✅ ENFORCED (by INV-012) | Closed-row record. |
| PARALLEL-015 | `object_registry` membership | Every creation site (`mud/models/object.py:create_object`, `mud/spawning/obj_spawner.py`, `mud/handler.py:create_money`, `mud/combat/death.py:_fallback_*`, `mud/commands/shop.py`, `mud/models/conversion.py`) routes through the canonical factory; `mud/game_loop.py:_extract_obj` is the single removal site (recursive). | — | ✅ ENFORCED (by INV-014) | Closed-row record. DUPL-003 closed the parallel `_extract_obj` copies in 2.9.28. |

## Summary

**15 rows total.** Breakdown: **1 ❌ ACTIVE-BUG** (PARALLEL-010 —
`do_flee` writing to a non-existent `room.characters` attribute, masked by a
broad `try/except` so the failure surfaces as a misleading "Flee failed"
message and the character silently stays put after paying move cost),
**8 ⚠️ DRIFT-RISK** (PARALLEL-001..006 hex-flag aliases that duplicate
existing IntEnums, PARALLEL-008 dead `.carrying` fallback in `consumption.py`,
PARALLEL-011 stale "uses .characters" docstring), and **6 ✅ ENFORCED**
(PARALLEL-007 equipment-dict retirement, PARALLEL-009 `.carrying` clean,
PARALLEL-012 single `character_registry`, PARALLEL-013/014/015 the three
object-shape invariants).

**The taxonomy's "mostly closed by INV-012/13/14" hypothesis HOLDS.** The
object-shape and registry sides are all ✅ ENFORCED via the existing
invariants. The residual surface is (a) one real bug in `do_flee` that
predates the room-people consolidation and was never updated, and (b) a band
of low-severity hex-flag-alias cleanup work in `mud/commands/` — the same
class of pattern that surfaced the SAC-004 `autosplit` bug previously fixed.
Recommend filing PARALLEL-010 as a single gap-closer commit and batching
PARALLEL-001..006 + PARALLEL-008 + PARALLEL-011 as a mechanical
flag-cleanup follow-up.
