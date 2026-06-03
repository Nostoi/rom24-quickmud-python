# Session Summary — 2026-06-03 — class-13 bypass sweep + fire_effect fix (2.13.3)

## Scope

Completed the DIVERGENCE-CLASS-13 bypass-site sweep (roster to-do #7): systematically
read every production `.append()` site that places objects into `inventory`,
`contents`, or `contained_items`, classified each as runtime-placement (should
head-insert, routing through the INV-039 chokepoint) or order-preserving
reconstruction (must stay `append`), and fixed all 15 bypass sites. Also surfaced
and fixed FINDING-023 (`fire_effect` dead code using `room.objects`).

## Classification (25 production sites enumerated)

### Runtime-placement bypasses fixed (15 sites → head-insert)

| File | Line (old) | Code | Fix |
|------|-----------|------|-----|
| `game_loop.py` | 1078 | `contained_items.append(obj)` in `_obj_to_obj` | → `insert(0, obj)` |
| `game_loop.py` | 971 | `inventory.append(obj)` in `_obj_to_char` | → routes through `add_object`/`add_to_inventory` |
| `game_loop.py` | 962 | `contents.append(obj)` in `_obj_to_room` fallback | → always `room.add_object(obj)`, dead fallback removed |
| `spawning/templates.py` | 492 | `self.inventory.append(obj)` in `add_to_inventory` | → `insert(0, obj)` |
| `spawning/templates.py` | 243 | `room.contents.append(self)` in `ObjectInstance.move_to_room` | → `room.add_object(self)` |
| `commands/equipment.py` | 91 | `inventory.append(obj)` in `_perform_remove` | → routes through `add_object` |
| `combat/death.py` | 417 | `corpse.contained_items.append(obj)` | → `insert(0, obj)` |
| `combat/death.py` | 453 | `corpse.contained_items.append(money_obj)` | → `insert(0, money_obj)` |
| `spec_funs.py` | 445 | `inventory.append(obj)` in scavenger | → routes through `add_object`/`add_to_inventory` |
| `spec_funs.py` | 627 | `contents.append(obj)` fallback | → dead fallback removed |
| `ai/__init__.py` | 178 | `inventory.append(obj)` in scavenger | → routes through `add_object`/`add_to_inventory` |
| `mob_cmds.py` | 666 | `inventory.append(obj)` fallback | → `insert(0, obj)` + `add_to_inventory` |
| `mob_cmds.py` | 758 | `contents.append(obj)` fallback | → `insert(0, obj)` |
| `commands/imm_load.py` | 163/171 | `.append(obj)` for char/room | → routes through chokepoints |
| `commands/imm_search.py` | 448/456 | `.append(clone)` for char/room | → routes through chokepoints |
| `commands/shop.py` | 993 | `keeper.inventory.append(selected_obj)` fallback | → `add_to_inventory` with insert(0) fallback |
| `spawning/reset_handler.py` | 776 | `container_obj.contained_items.append(obj)` | → `insert(0, obj)` |
| `commands/build.py` | 819 | `container.contained_items.append(obj)` | → `insert(0, obj)` |
| `skills/handlers.py` | 5200/5229/5273/5300 | `room.objects.append(obj)` | → `room.add_object(obj)` (FINDING-023) |

### Order-preserving reconstruction paths left as `append` (4 sites)

| File | Line | Code | Reason |
|------|------|------|--------|
| `db/serializers.py` | 397 | `obj.contained_items.append(child)` | DB reload, preserves save order |
| `models/object.py` | 215 | `clone_to.contained_items.append(new_obj)` | Clones source LIFO order; appending in iteration order yields same result |
| `models/conversion.py` | 22 | `inventory.append(obj)` | DB reload, order-preserving |
| `mob_cmds.py` | 1301 | `new_inventory.append(obj)` | Filtered inventory rebuild, not placement |

### Dead code removed

- `game_loop._obj_to_room` fallback (Room always has `add_object`)
- `spec_funs._drop_object_into_room` fallback (Room always has `add_object`)

## FINDING-023 — `fire_effect` burn-drop items silently lost

Four branches in `mud/skills/handlers.py:_fire_effect` used `room.objects.append(obj)`.
`Room` has no `objects` attribute — only `contents`. The `hasattr(room, "objects")`
guard always returned `False`, so items removed from inventory/equipment by fire
(ARMOR burn-drop, CLOTHING burn-drop, WEAPON burn-drop, LIGHT burn-drop) never
reached the room. All four sites now route through `room.add_object(obj)`.

## Files Modified

- `mud/game_loop.py` — `_obj_to_obj`: `append` → `insert(0)`; `_obj_to_char`: routes
  through chokepoint; `_obj_to_room`: always `room.add_object(obj)`, dead fallback removed.
- `mud/spawning/templates.py` — `MobInstance.add_to_inventory`: `append` → `insert(0)`;
  `ObjectInstance.move_to_room`: routes through `Room.add_object`.
- `mud/commands/equipment.py` — `_perform_remove`: routes through `add_object`.
- `mud/combat/death.py` — `_handle_corpse_item`: `insert(0)`; `make_corpse` money:
  `insert(0)`.
- `mud/spec_funs.py` — scavenger pickup: routes through chokepoint; `_place_corpse_object_in_room`: dead fallback removed.
- `mud/ai/__init__.py` — scavenger pickup: routes through chokepoint; manual carry counter increments removed (chokepoint handles them).
- `mud/mob_cmds.py` — `mpoload` fallback: `insert(0)` + `add_to_inventory`;
  `mptransfer_obj` fallback: `insert(0)`.
- `mud/commands/imm_load.py` — routes through chokepoints.
- `mud/commands/imm_search.py` — routes through chokepoints.
- `mud/commands/shop.py` — sell-to-keeper fallback: routes through `add_to_inventory`.
- `mud/spawning/reset_handler.py` — container-put: `insert(0)`.
- `mud/commands/build.py` — redit container-put: `insert(0)`.
- `mud/skills/handlers.py` — 4 fire_effect burn-drop sites: `room.objects` → `room.add_object`.
- `tests/test_spell_heat_metal_rom_parity.py` — `room.objects` → `room.contents`.
- `tools/diff_harness/FINDINGS.md` — FINDING-023 and FINDING-024 documented.
- `docs/parity/DIVERGENCE_CLASS_ROSTER.md` — class-13 row updated, to-do #7 marked DONE.
- `pyproject.toml` — 2.13.2 → 2.13.3.
- `CHANGELOG.md` — Fixed entries for FINDING-023 and FINDING-024.

## Test Status

- Full suite: **5393 passed, 4 skipped** (`pytest`, 0 failures).
- `ruff check .` — clean repo-wide.
- `test_spell_heat_metal_rom_parity.py` — fixed `room.objects` → `room.contents`.
- `test_game_loop.py::test_mobile_update_scavenges_room_loot` — fixed carry_number
  double-count (removed manual increments now handled by `add_object`).

## Next Steps

1. **FINDING-022** — confirm `look in` contents-line indent against the live C oracle.
2. **FINDING-020** — equipment-dict carry-list position (architectural).
3. Continue Phase C deterministic command/watch-set widening.