# Session Summary — 2026-05-25 — INV-014 OBJECT-REGISTRY-MEMBERSHIP + INV-013 carrier-field sweep

(Follows
[SESSION_SUMMARY_2026-05-24_INV012_OBJECT_CONSOLIDATION.md](SESSION_SUMMARY_2026-05-24_INV012_OBJECT_CONSOLIDATION.md)
and the same-day INV-013 work. Session opened against a clean tree
at `791cf046` (v2.9.2) with no Partial / Not Audited rows in the
per-file tracker and an empty INV watch list. Direction chosen was
"end-to-end coverage for INV-012 newly-live systems"; the very first
probe — does `spell_locate_object` find an unplaced object? — surfaced
a new cross-file invariant candidate that drove the rest of the
session.)

## Scope

Four sequential clusters, each its own commit + version bump + push:

1. **INV-014 OBJECT-REGISTRY-MEMBERSHIP** — new invariant. The
   probe revealed that only `spawn_object` appended to
   `object_registry`; six other production sites built `Object`
   instances without registering, so corpses, money piles, gore,
   shop clones, recursive clones, and DB-restored inventory were
   invisible to `spell_locate_object`.
2. **INV-013 / INV-011 reinforcement (`Character.add_object` +
   `do_mpoload`)** — surfaced as a follow-on while scoping option
   3a (mobprog `oload` coverage). `Character.add_object` never set
   `obj.carried_by`, and `do_mpoload` bypassed `add_object`
   entirely with a raw `inventory.append`.
3. **INV-013 carrier-field symmetry (`equip_object` / `remove_object`)**
   — extended the same audit lens to the equip/remove side of the
   inventory lifecycle. `equip_object` didn't set `carried_by` when
   equipping a fresh obj; `remove_object` left a stale back-pointer
   to the former carrier after extraction.
4. **End-to-end decay-loop coverage** — verified the three
   intersecting invariants (INV-011 / INV-013 / INV-014) hold as
   objects pass through `obj_update` → `_extract_obj`. Pure new
   integration tests; no production code changed.

## Outcomes

### `INV-014` OBJECT-REGISTRY-MEMBERSHIP — ✅ ENFORCED (2.9.3)

- **Mechanism (ROM)**: `src/db.c:create_object` appends every fresh
  `OBJ_DATA` to the global `object_list`; every world-scan consumer
  walks that list (`src/magic.c:3737 spell_locate_object`,
  decay sweep, save).
- **Enforcement point (Python)**:
  `mud/models/object.py:create_object(prototype, *, instance_id=None)`
  is the canonical factory — constructs the `Object` and appends to
  `mud.models.obj.object_registry`. Six production sites routed
  through it:
  - `mud/handler.py:create_money`
  - `mud/combat/death.py:_fallback_gore`
  - `mud/combat/death.py:_fallback_corpse`
  - `mud/rom_api.py:recursive_clone`
  - `mud/commands/shop.py:_clone_inventory_object` fallback
  - `mud/models/conversion.py:load_objects_for_character`
- **Iterator**: `mud/skills/handlers.py:_iterate_world_objects` now
  walks `object_registry` first, computing the holder per ROM
  `src/magic.c:3747` (outermost `in_obj` chain → `carried_by` →
  `in_room` → `None` rendered as "somewhere"). Legacy room/character
  walk kept as a compat backstop for unit tests that build
  `Object` directly without registering.
- **Test**: `tests/integration/test_inv014_object_registry_membership.py`
  (8/8 passing) — one per construction path + the homeless-object
  locate symptom that opened the thread.
- **Surfaced symptom**: `spell_locate_object` could not find a
  freshly-created corpse, money pile, shop clone, or DB-restored
  inventory item.

### `add_object` + `do_mpoload` — ✅ FIXED (2.9.4)

- **Python**: `mud/models/character.py:Character.add_object`,
  `mud/mob_cmds.py:do_mpoload`.
- **ROM C**: `src/handler.c:1626 obj_to_char`, `src/mob_cmds.c:538-614`.
- **Gap A**: `Character.add_object` updated `inventory` and carry
  counters but never set `obj.carried_by` — every direct caller
  produced an inventory item with no carrier back-pointer (INV-013
  violation).
- **Gap B**: `do_mpoload` (inventory branch) did
  `inventory.append(obj)` directly instead of routing through
  `add_object`, missing both INV-013 (`carried_by`) and INV-011
  (`carry_weight` / `carry_number`). MOBprog `mob oload <vnum>` thus
  drifted encumbrance on every script-driven item load.
- **Fix**: `add_object` now sets `obj.location = self` (INV-013
  property dispatch). `do_mpoload` routes through
  `ch.add_object(obj)`; the bare `inventory.append` fallback (for
  callers without `add_object`) also sets `obj.location` explicitly.
- **Tests**: 3 new tests in
  `tests/integration/test_inv013_add_object_carrier.py` —
  `add_object` carrier set, mpoload carrier set, mpoload carry
  counters update.

### `equip_object` + `remove_object` — ✅ FIXED (2.9.5)

- **Python**: `mud/models/character.py:Character.equip_object`,
  `Character.remove_object`.
- **ROM C**: `src/handler.c equip_char` (carried_by stays set when
  equipped — only `wear_loc` changes); `src/handler.c:1642
  obj_from_char` (clears `carried_by` atomically).
- **Gap A**: `equip_object` didn't set `obj.carried_by`. An obj
  equipped directly (e.g. `caster.equip_object(disc, "float")` in
  `floating_disc`) ended up with `carried_by=None`.
- **Gap B**: `remove_object` didn't clear `obj.carried_by`. After
  extraction the obj retained a stale back-pointer to the former
  carrier — a wrong-carrier report in `locate object` or save
  serialization waiting to surface.
- **Fix**: `equip_object` sets `obj.carried_by = self` after the
  inventory→equipment move. `remove_object` clears the field
  via `getattr` guard (defensive against legacy tests that pass
  `SimpleNamespace` stand-ins instead of real `Object` instances —
  one regressed test, `test_disarm_strips_weapon_and_trains_skill`,
  was caught and fixed via the guard).
- **Tests**: 3 new tests in the same file as the 2.9.4 cluster.
  Total 6 covering the full add / equip / remove cycle.

### End-to-end decay loop — ✅ ENFORCED (2.9.6)

- **Python**: `mud/game_loop.py:obj_update`, `_extract_obj`.
- **ROM C**: `src/update.c:obj_update`, `src/handler.c:2063-2067
  extract_obj` (recurses through `obj->contains`).
- **Scope**: pre-existing decay tests
  (`test_obj_update_decays_corpse`,
  `test_obj_update_spills_floating_container`) cover the basics but
  did NOT exercise the cross-invariant contracts the 2.9.3-2.9.5
  work relied on.
- **Tests** (`tests/integration/test_decay_loop_inv012.py`):
  1. Carried potion timer expiry → off `object_registry` (INV-014),
     off inventory, `carry_weight` / `carry_number` decrement
     (INV-011).
  2. NPC corpse + nested pouch + ruby: ROM `extract_obj` recursion
     verified end-to-end — all three leave the registry on the
     corpse's decay tick.
  3. Downstream INV-014 consequence: a decayed obj is no longer
     findable by `spell_locate_object`.
- **One test design issue caught and fixed in development**: the
  initial recursive-decay test used a float-marked container,
  expecting recursive extraction. ROM's float branch spills
  contents to the room instead, so the contents survive. Redesigned
  as the NPC-corpse case where no spill condition applies.
- **No production code changed** — pure additive coverage.

## Commit ladder

| # | SHA (short) | Version | Cluster |
|---|-------------|---------|---------|
| 1 | `cfda9ef7` | 2.9.3 | INV-014 OBJECT-REGISTRY-MEMBERSHIP |
| 2 | `cd90c942` | 2.9.4 | `Character.add_object` + `do_mpoload` |
| 3 | `b0d3787f` | 2.9.5 | `equip_object` + `remove_object` symmetry |
| 4 | `040b0726` | 2.9.6 | Decay-loop end-to-end coverage |

All four pushed to `origin/master` with matching `v2.9.3`–`v2.9.6`
tags.

## Files Modified

- `mud/models/object.py` — new `create_object` factory (INV-014).
- `mud/models/character.py` — `add_object` / `equip_object` /
  `remove_object` carrier-field maintenance (INV-013).
- `mud/models/conversion.py` — `load_objects_for_character` routes
  through `create_object`.
- `mud/handler.py` — `create_money` routes through `create_object`.
- `mud/combat/death.py` — `_fallback_gore` / `_fallback_corpse`
  route through `create_object`.
- `mud/rom_api.py` — `recursive_clone` routes through `create_object`.
- `mud/commands/shop.py` — `_clone_inventory_object` fallback routes
  through `create_object`.
- `mud/mob_cmds.py` — `do_mpoload` inventory branch routes through
  `ch.add_object(obj)`.
- `mud/skills/handlers.py` — `_iterate_world_objects` walks
  `object_registry` first.
- `tests/integration/test_inv014_object_registry_membership.py`
  — new file, 8 tests.
- `tests/integration/test_inv013_add_object_carrier.py` — new file,
  6 tests.
- `tests/integration/test_decay_loop_inv012.py` — new file, 3 tests.
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — new INV-014 row
  ✅ ENFORCED; INV-011 and INV-013 "Touched by" trails extended.
- `CHANGELOG.md` — `[2.9.3]`, `[2.9.4]`, `[2.9.5]`, `[2.9.6]` sections.
- `docs/sessions/SESSION_STATUS.md` — refreshed three times in step
  with the cluster cadence; final state points here.
- `pyproject.toml` — 2.9.2 → 2.9.6 across the session.

## Test Status

- `pytest tests/integration/test_inv014_object_registry_membership.py`
  — 8/8 passing.
- `pytest tests/integration/test_inv013_add_object_carrier.py`
  — 6/6 passing.
- `pytest tests/integration/test_decay_loop_inv012.py`
  — 3/3 passing.
- **Full suite**: 4712 passed, 4 skipped, 0 failed (up from
  baseline 4695 — exactly +17 across the session; +8 INV-014, +6
  INV-013 carrier suite, +3 decay loop).

## Process learnings

1. **The probe-then-scope pattern paid off twice.** The locate-object
   probe revealed INV-014 in five minutes of read-only investigation
   (one ROM-C read, one Python read, one Bash `python3 -c` repro).
   The mpoload-coverage scope check revealed the `add_object` gap in
   the same way. Cheap probes before committing to a framing —
   surface real divergences rather than hypothetical ones.
2. **One discovered gap can stack with another.** The mpoload gap
   was actually two stacked gaps (`add_object` itself + `do_mpoload`
   bypassing `add_object`). Resisted the urge to split into two
   commits — they were inseparable for the failing test, so one
   cluster with three failing tests was right.
3. **Pyright noise during edits is signal-to-noise: ignore the
   pre-existing red, attend only to new-this-edit red.** The
   `ObjectData` stub type lag created a wall of diagnostics every
   time character.py or handlers.py changed — none were caused by
   the session's edits, all were pre-existing.
4. **`SimpleNamespace` stand-ins in legacy tests bite back.** The
   `remove_object` change broke `test_disarm_strips_weapon_and_trains_skill`
   because the test used `SimpleNamespace` as an obj. Defensive
   `getattr(obj, "carried_by", None)` resolved without forcing a
   test rewrite. If we standardize on real `Object` for all tests
   later (Phase 2 sweep?), the guard becomes removable.
5. **Decay-loop test design must respect ROM's spill branches.** The
   first recursive-decay test was wrong because float-containers
   spill — contents survive, not destroyed. The NPC-corpse case is
   the real recursive-extract path. Worth re-reading
   `obj_update`'s spill conditions before designing decay tests.

## Next Steps

INV-012's downstream coverage cycle (locate, mpoload, equip/remove
symmetry, decay loop) is sealed. Natural stopping point.

If next session wants to keep pulling on cross-file invariants:

- The Phase 2 cosmetic sweep (`prototype` → `pIndexData`,
  `contained_items` → `contains`) is still backlog-flagged at
  `docs/parity/PHASE_2_ROM_NAME_SWEEP_OPTIONAL.md` — low value, but
  the Object dataclass already has the `@property` aliases ready.
- Watch for the next organic cross-module bug to file as INV-015 —
  no candidate currently sitting in the watch list.
- The per-file audit tracker has zero Partial / Not Audited rows
  across P0/P1/P2 and only ✅ entries in P3; default audit path is
  exhausted unless a previously-audited file shows live
  user-visible drift.
