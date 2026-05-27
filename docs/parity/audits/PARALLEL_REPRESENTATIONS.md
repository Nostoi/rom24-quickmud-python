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
| PARALLEL-001 | `mud/commands/misc_player.py:90-98` (`configs` table for `do_config`) | `autoassist`/`autoexit`/`autogold`/`autoloot`/`autosac`/`autosplit`/`compact`/`brief`/`prompt`/`combine` defined as inline raw hex literals (`0x00001000`, etc.) — **the hex literals did NOT match the canonical IntEnum bit values** the toggle commands set, so `do_config` always disagreed with actual flag state. | MEDIUM (active bug) | ✅ FIXED (2.9.55) | Audit's "no current bug" hypothesis was wrong: ROM letter macros are bit-shifts (`C=1<<2`, `E=1<<4`, …) — the hex literals were taken from a different convention and aliased the wrong bits. `do_autoloot` set `PlayerFlag.AUTOLOOT` (bit 4) but the table read bit 15 (`0x00008000`); brief-vs-combine collided on bit 12. Fix: replaced every hex literal with `int(PlayerFlag.X)` / `int(CommFlag.X)`. Also re-pointed `COMM_AFK` alias (PARALLEL-004) at `int(CommFlag.AFK)`. Regression: `tests/integration/test_do_config_flag_alignment.py` (2/2). |
| PARALLEL-002 | `mud/commands/player_config.py:76` (`IMM_SUMMON = 0x00000010`) | NPC `nosummon` branch declared module-local `IMM_SUMMON = 0x00000010` (bit 4) — **wrong**; canonical `DefenseBit.SUMMON = 1<<0 = 0x1` (ROM `merc.h` letter A). The toggle modified an unrelated immunity bit, leaving the NPC actually-summonable. (The PLR_* aliases at lines 12-14 use coincidentally-correct hex; folded into the audit-only cleanup row historically.) | MEDIUM (active bug) | ✅ FIXED (2.9.57) | Replaced with `int(DefenseBit.SUMMON)`. Regression: `tests/integration/test_imm_summon_bit_alignment.py` (3/3). |
| PARALLEL-003a | `mud/commands/remaining_rom.py:211` (`ACT_GAIN = 0x00100000` inside `do_gain` trainer lookup) | Inline hex `0x00100000` (bit 20) does **not** match canonical `ActFlag.GAIN = 1<<27 = 0x8000000` (ROM letter `bb`). Trainer-lookup loop in `do_gain` checked the wrong bit, so NPCs flagged canonically as trainers were not recognized ("You can't do that here.") and NPCs with bit 20 set were spuriously treated as trainers. | MEDIUM (active bug) | ✅ FIXED (2.9.57) | Replaced with `int(ActFlag.GAIN)`. Regression: `tests/integration/test_do_gain_act_gain_bit.py` (3/3). |
| PARALLEL-003b | `mud/commands/remaining_rom.py:105` (`COMM_QUIET = 0x00000004`) | Module-local `COMM_QUIET = 0x4` (bit 2) did **not** match canonical `CommFlag.QUIET = 1<<0 = 0x1` (ROM letter A). `do_quiet` toggled bit 2 of `char.comm` while every other read used bit 0 — a player loaded with canonical QUIET set got "From now on..." instead of "Quiet mode removed." | MEDIUM (active bug) | ✅ FIXED (2.9.57) | Replaced with `int(CommFlag.QUIET)`. Regression: `tests/integration/test_do_quiet_comm_bit.py` (3/3). |
| PARALLEL-004 | `mud/commands/misc_player.py:19` (`COMM_AFK = 0x00000800`) | Module-local hex alias for `CommFlag.AFK` — **value was wrong** (0x800 = bit 11; ROM Z = 1<<25 = 0x2000000). | MEDIUM (active bug) | ✅ FIXED (2.9.55) | Fixed alongside PARALLEL-001: alias now `int(CommFlag.AFK)`. |
| PARALLEL-005 | `mud/commands/obj_manipulation.py:617` (`ITEM_NODROP = 0x0010` inside `_can_drop_obj`) | Inline hex `0x0010` aliased `ExtraFlag.EVIL` (bit 4), **not** `ExtraFlag.NODROP` (ROM H = 1<<7 = 0x80). `_can_drop_obj` is the gate for `do_drop` / `do_put` / `do_give` / `do_drop_all`. Pre-fix: NODROP cursed gear could be dropped; EVIL items spuriously blocked. | MEDIUM (active bug) | ✅ FIXED (2.9.56) | Replaced with `int(ExtraFlag.NODROP)`. Existing test `test_drop_nodrop_item_is_rejected` also used the wrong hex (0x0010) — fixed to use the IntEnum per "ROM is source of truth". New regression: `tests/integration/test_can_drop_obj_nodrop_bit.py` (3/3). |
| PARALLEL-006 | `mud/commands/imm_load.py:176-177` (`ACT_NOPURGE = 0x00002000`, `ITEM_NOPURGE = 0x00000040`) | Inline hex literals: `0x2000` was bit 13 (canonical `ActFlag.NOPURGE = 1<<21 = 0x200000`); `0x40` was bit 6 (canonical `ExtraFlag.NOPURGE = 1<<14 = 0x4000`). `do_purge` checked the wrong bits — canonically-NOPURGE NPCs and objects were purged anyway while unrelated bits spuriously protected mobs/items. | MEDIUM (active bug) | ✅ FIXED (2.9.57) | Replaced with `int(ActFlag.NOPURGE)` / `int(ExtraFlag.NOPURGE)`. Regression: `tests/integration/test_do_purge_nopurge_bits.py` (4/4). |

### Equipment representation

| ID | Site | Issue | Severity | Status | Notes |
|----|------|-------|----------|--------|-------|
| PARALLEL-007 | (none) | Sweep for `equipped[` returned **zero hits** in `mud/`. All equipment access goes through `char.equipment[WearLocation.X]` (IntEnum-keyed dict). | — | ✅ ENFORCED | The legacy `equipped["held"]` shape has been fully retired. No drift surface remains. |

### Inventory representation

| ID | Site | Issue | Severity | Status | Notes |
|----|------|-------|----------|--------|-------|
| PARALLEL-008 | `mud/commands/consumption.py:308-316` (`_find_obj_inventory`) | Defensive fallback: `inventory = getattr(ch, "inventory", None); if inventory is None: inventory = getattr(ch, "carrying", [])`. | LOW (dead-fallback) | ✅ FIXED (2.9.57) | Removed `.carrying` fallback branch; only canonical `char.inventory` remains. Existing consumables suite (47 tests) covers the live path. |
| PARALLEL-009 | Global sweep `grep -rn "\.carrying\b" mud/` | Only one hit: the comment + fallback in `consumption.py:311` above. No production code reads/writes `.carrying`. | — | ✅ ENFORCED | DUPL-003 closed the `carrying` parallel-rep bug class (the buggy `_extract_obj` copies that read `char.carrying`). Verified clean. |

### Room / registry collections

| ID | Site | Issue | Severity | Status | Notes |
|----|------|-------|----------|--------|-------|
| PARALLEL-010 | `mud/commands/combat.py:683-688` (`do_flee` movement branch) | After successful flee, the code wrote to `room.characters`/`new_room.characters`; canonical attr is `room.people`. | MEDIUM (silent no-op) | ✅ FIXED (2.9.54) | Closed by switching to canonical `room.remove_character(char)` / `new_room.add_character(char)` helpers (defined at `mud/models/room.py:140, 157`). The `hasattr(room, "characters")` gate that silently hid the remove is gone; the broad `try/except` that masked the `AttributeError` from the `append` is gone. Also fixed the same bug at line 665 (room-broadcast loop iterated `room.characters` — now iterates `room.people`). Regression pinned by `tests/integration/test_flee_moves_character.py::test_flee_moves_character_to_new_room`. |
| PARALLEL-011 | `mud/handler.py:694` (docstring "Uses obj.in_room.characters instead of linked list") | Docstring claim was stale; function `count_users` walks `in_room.people`. | LOW (doc-drift) | ✅ FIXED (2.9.57) | Docstring now reads "Uses room.people (canonical attribute)". |
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
