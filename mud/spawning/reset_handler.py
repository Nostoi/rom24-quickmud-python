from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

from mud.models.area import Area
from mud.models.constants import (
    ITEM_INVENTORY,
    ExtraFlag,
    EX_CLOSED,
    EX_ISDOOR,
    EX_LOCKED,
    convert_flags_from_letters,
)
from mud.registry import room_registry, area_registry, mob_registry, obj_registry, shop_registry
from .mob_spawner import spawn_mob
from .obj_spawner import spawn_object
from .templates import MobInstance
from mud.utils import rng_mm

RESET_TICKS = 3


def _count_existing_mobs() -> Dict[int, int]:
    """Rebuild MOB_INDEX_DATA->count style tallies from the current world."""

    counts: Dict[int, int] = {}
    for room in room_registry.values():
        for mob in getattr(room, 'people', []):
            if not isinstance(mob, MobInstance):
                continue
            proto = getattr(mob, 'prototype', None)
            vnum = getattr(proto, 'vnum', None)
            if vnum is None:
                continue
            counts[vnum] = counts.get(vnum, 0) + 1
    for vnum, proto in mob_registry.items():
        if hasattr(proto, 'count'):
            proto.count = counts.get(vnum, 0)
    return counts


def _gather_object_state() -> Tuple[Dict[int, int], Dict[int, List[object]]]:
    """Rebuild OBJ_INDEX_DATA->count and capture instances by prototype vnum."""

    counts: Dict[int, int] = {}
    instances: Dict[int, List[object]] = {}

    def tally(obj: object) -> None:
        proto = getattr(obj, "prototype", None)
        vnum = getattr(proto, "vnum", None)
        if vnum is None:
            return
        counts[vnum] = counts.get(vnum, 0) + 1
        instances.setdefault(vnum, []).append(obj)
        for contained in getattr(obj, "contained_items", []) or []:
            tally(contained)

    for room in room_registry.values():
        for obj in getattr(room, "contents", []):
            tally(obj)
        for mob in getattr(room, "people", []):
            if isinstance(mob, MobInstance):
                for carried in getattr(mob, "inventory", []):
                    tally(carried)

    for vnum, proto in obj_registry.items():
        if hasattr(proto, "count"):
            proto.count = counts.get(vnum, 0)

    return counts, instances


def _resolve_reset_limit(raw: Optional[int]) -> int:
    """Mirror ROM's limit coercion for resets (old format, unlimited markers)."""

    if raw is None:
        return 1
    if raw > 50:
        return 6
    if raw in (-1, 0):
        return 999
    return raw


def _compute_object_level(obj: object, mob: object) -> int:
    """Approximate ROM object level computation for G/E resets.

    Mirrors src/db.c case 'G'/'E' for shopkeepers and equips (simplified):
    - WAND: 10..20
    - STAFF: 15..25
    - ARMOR: 5..15
    - WEAPON: 5..15
    - TREASURE: 10..20
    - Default: 0
    For new-format objects, or unrecognized types, return 0.
    """
    try:
        item_type = int(getattr(getattr(obj, 'prototype', None), 'item_type', 0))
    except Exception:
        item_type = 0
    from mud.models.constants import ItemType
    if item_type == int(ItemType.WAND):
        return rng_mm.number_range(10, 20)
    if item_type == int(ItemType.STAFF):
        return rng_mm.number_range(15, 25)
    if item_type == int(ItemType.ARMOR):
        return rng_mm.number_range(5, 15)
    if item_type == int(ItemType.WEAPON):
        return rng_mm.number_range(5, 15)
    if item_type == int(ItemType.TREASURE):
        return rng_mm.number_range(10, 20)
    return 0


def _mark_shopkeeper_inventory(mob: MobInstance, obj: object) -> None:
    """Ensure shopkeeper inventory copies carry ITEM_INVENTORY like ROM."""

    proto = getattr(mob, "prototype", None)
    if getattr(proto, "vnum", None) not in shop_registry:
        return

    item_proto = getattr(obj, "prototype", None)
    if item_proto is None or not hasattr(item_proto, "extra_flags"):
        return

    extra_flags = getattr(item_proto, "extra_flags", 0)
    if isinstance(extra_flags, str):
        extra_flags = convert_flags_from_letters(extra_flags, ExtraFlag)

    item_proto.extra_flags = int(extra_flags) | int(ITEM_INVENTORY)
    setattr(obj, "extra_flags", int(item_proto.extra_flags))


def apply_resets(area: Area) -> None:
    """Populate rooms based on ROM reset data semantics."""

    last_mob: Optional[MobInstance] = None
    last_obj: Optional[object] = None
    object_counts, existing_objects = _gather_object_state()
    spawned_objects: Dict[int, List[object]] = {
        vnum: list(instances) for vnum, instances in existing_objects.items()
    }
    mob_counts = _count_existing_mobs()

    for reset in area.resets:
        cmd = (reset.command or '').upper()
        if cmd == 'M':
            mob_vnum = reset.arg1 or 0
            global_limit = reset.arg2 or 0
            room_vnum = reset.arg3 or 0
            room_limit = reset.arg4 or 0

            room = room_registry.get(room_vnum)
            if mob_vnum <= 0 or room is None:
                logging.warning('Invalid M reset %s -> %s', mob_vnum, room_vnum)
                last_mob = None
                last_obj = None
                continue

            if global_limit > 0 and mob_counts.get(mob_vnum, 0) >= global_limit:
                last_mob = None
                last_obj = None
                continue

            if room_limit <= 0:
                last_mob = None
                last_obj = None
                continue

            existing_in_room = sum(
                1
                for mob in room.people
                if isinstance(mob, MobInstance)
                and getattr(getattr(mob, 'prototype', None), 'vnum', None) == mob_vnum
            )
            if existing_in_room >= room_limit:
                last_mob = None
                last_obj = None
                continue

            mob = spawn_mob(mob_vnum)
            if not mob:
                logging.warning('Invalid M reset %s (missing prototype)', mob_vnum)
                last_mob = None
                last_obj = None
                continue

            room.add_mob(mob)
            mob_counts[mob_vnum] = mob_counts.get(mob_vnum, 0) + 1
            proto = getattr(mob, 'prototype', None)
            if proto is not None and hasattr(proto, 'count'):
                proto.count = mob_counts[mob_vnum]
            last_mob = mob
            last_obj = None
        elif cmd == 'O':
            obj_vnum = reset.arg1 or 0
            room_vnum = reset.arg3 or 0
            room = room_registry.get(room_vnum)
            if obj_vnum <= 0 or room is None:
                logging.warning('Invalid O reset %s -> %s', obj_vnum, room_vnum)
                last_obj = None
                continue
            if getattr(area, 'nplayer', 0) > 0:
                last_obj = None
                continue
            existing_in_room = [
                obj
                for obj in getattr(room, 'contents', [])
                if getattr(getattr(obj, 'prototype', None), 'vnum', None) == obj_vnum
            ]
            if existing_in_room:
                last_obj = None
                continue
            obj = spawn_object(obj_vnum)
            if obj:
                room.add_object(obj)
                object_counts[obj_vnum] = object_counts.get(obj_vnum, 0) + 1
                last_obj = obj
                spawned_objects.setdefault(obj_vnum, []).append(obj)
            else:
                logging.warning('Invalid O reset %s -> %s', obj_vnum, room_vnum)
                last_obj = None
        elif cmd == 'D':
            room_vnum = reset.arg1 or 0
            direction = int(reset.arg2 or 0)
            state = int(reset.arg3 or 0)
            room = room_registry.get(room_vnum)
            if room is None:
                logging.warning("Invalid D reset %s (missing room)", room_vnum)
                continue
            if direction < 0 or direction >= len(room.exits):
                logging.warning(
                    "Invalid D reset %s direction %s", room_vnum, direction
                )
                continue
            exit_obj = room.exits[direction]
            if exit_obj is None:
                logging.warning(
                    "Invalid D reset %s direction %s (no exit)",
                    room_vnum,
                    direction,
                )
                continue

            base_flags = int(getattr(exit_obj, "rs_flags", 0) or getattr(exit_obj, "exit_info", 0) or 0)
            base_flags |= int(EX_ISDOOR)
            base_flags &= ~(EX_CLOSED | EX_LOCKED)
            if state == 1:
                base_flags |= EX_CLOSED
            elif state == 2:
                base_flags |= EX_CLOSED | EX_LOCKED
            elif state != 0:
                logging.warning("Invalid D reset %s state %s", room_vnum, state)

            exit_obj.rs_flags = base_flags
            exit_obj.exit_info = base_flags
        elif cmd == 'G':
            obj_vnum = reset.arg1 or 0
            limit = _resolve_reset_limit(reset.arg2)
            if not last_mob:
                logging.warning('Invalid G reset %s (no LastMob)', obj_vnum)
                continue
            existing = [
                o
                for o in getattr(last_mob, 'inventory', [])
                if getattr(getattr(o, 'prototype', None), 'vnum', None) == obj_vnum
            ]
            if len(existing) >= limit:
                continue
            proto_count = object_counts.get(obj_vnum, 0)
            is_shopkeeper = getattr(getattr(last_mob, 'prototype', None), 'vnum', None) in shop_registry
            if proto_count >= limit and rng_mm.number_range(0, 4) != 0:
                continue
            obj = spawn_object(obj_vnum)
            if obj:
                obj.level = _compute_object_level(obj, last_mob)
                if is_shopkeeper:
                    _mark_shopkeeper_inventory(last_mob, obj)
                object_counts[obj_vnum] = proto_count + 1
                last_mob.add_to_inventory(obj)
                last_obj = obj
                spawned_objects.setdefault(obj_vnum, []).append(obj)
            else:
                logging.warning('Invalid G reset %s', obj_vnum)
        elif cmd == 'E':
            obj_vnum = reset.arg1 or 0
            limit = _resolve_reset_limit(reset.arg2)
            slot = reset.arg3 or 0
            if not last_mob:
                logging.warning('Invalid E reset %s (no LastMob)', obj_vnum)
                continue
            existing = [
                o
                for o in getattr(last_mob, 'inventory', [])
                if getattr(getattr(o, 'prototype', None), 'vnum', None) == obj_vnum
            ]
            if len(existing) >= limit:
                continue
            proto_count = object_counts.get(obj_vnum, 0)
            is_shopkeeper = getattr(getattr(last_mob, 'prototype', None), 'vnum', None) in shop_registry
            if proto_count >= limit and rng_mm.number_range(0, 4) != 0:
                continue
            obj = spawn_object(obj_vnum)
            if obj:
                obj.level = _compute_object_level(obj, last_mob)
                if is_shopkeeper:
                    _mark_shopkeeper_inventory(last_mob, obj)
                object_counts[obj_vnum] = proto_count + 1
                last_mob.equip(obj, slot)
                last_obj = obj
                spawned_objects.setdefault(obj_vnum, []).append(obj)
            else:
                logging.warning('Invalid E reset %s', obj_vnum)
        elif cmd == 'P':
            obj_vnum = reset.arg1 or 0
            container_vnum = reset.arg3 or 0
            target_count = max(1, int(reset.arg4 or 1))
            limit = _resolve_reset_limit(reset.arg2)
            if obj_vnum <= 0 or container_vnum <= 0:
                logging.warning('Invalid P reset %s -> %s', obj_vnum, container_vnum)
                last_obj = None
                continue
            if getattr(area, 'nplayer', 0) > 0:
                last_obj = None
                continue
            obj_proto = obj_registry.get(obj_vnum)
            container_proto = obj_registry.get(container_vnum)
            if obj_proto is None or container_proto is None:
                logging.warning('Invalid P reset %s -> %s (missing prototype)', obj_vnum, container_vnum)
                last_obj = None
                continue
            remaining_global = max(0, limit - object_counts.get(obj_vnum, 0))
            if remaining_global <= 0:
                last_obj = None
                continue
            container_obj: Optional[object] = None
            if last_obj and getattr(getattr(last_obj, 'prototype', None), 'vnum', None) == container_vnum:
                container_obj = last_obj
            if not container_obj:
                candidates = spawned_objects.get(container_vnum) or []
                for candidate in reversed(candidates):
                    room = getattr(candidate, 'location', None)
                    if room is None or room.area is area:
                        container_obj = candidate
                        break
            if not container_obj:
                for room in room_registry.values():
                    if room.area is not area:
                        continue
                    for obj in getattr(room, 'contents', []):
                        if getattr(getattr(obj, 'prototype', None), 'vnum', None) == container_vnum:
                            container_obj = obj
                            spawned_objects.setdefault(container_vnum, []).append(obj)
                            break
                    if container_obj:
                        break
            if not container_obj:
                logging.warning('Invalid P reset %s -> %s (no container instance)', obj_vnum, container_vnum)
                last_obj = None
                continue
            existing = [
                o
                for o in getattr(container_obj, 'contained_items', [])
                if getattr(getattr(o, 'prototype', None), 'vnum', None) == obj_vnum
            ]
            if len(existing) >= target_count:
                last_obj = container_obj
                continue
            to_make = min(target_count - len(existing), remaining_global)
            made = 0
            for _ in range(to_make):
                obj = spawn_object(obj_vnum)
                if not obj:
                    logging.warning('Invalid P reset %s', obj_vnum)
                    break
                getattr(container_obj, 'contained_items').append(obj)
                spawned_objects.setdefault(obj_vnum, []).append(obj)
                made += 1
                remaining_global -= 1
                object_counts[obj_vnum] = object_counts.get(obj_vnum, 0) + 1
                if remaining_global <= 0:
                    break
            try:
                container_obj.value[1] = container_obj.prototype.value[1]
            except Exception:
                pass
            last_obj = container_obj
        elif cmd == 'R':
            room_vnum = reset.arg1 or 0
            max_dirs = int(reset.arg2 or 0)
            room = room_registry.get(room_vnum)
            if not room or not room.exits:
                logging.warning("Invalid R reset %s", room_vnum)
                continue
            n = min(max_dirs, len(room.exits))
            # Fisher–Yates-like partial shuffle matching ROM loop
            for d0 in range(0, max(0, n - 1)):
                d1 = rng_mm.number_range(d0, n - 1)
                room.exits[d0], room.exits[d1] = room.exits[d1], room.exits[d0]


def reset_area(area: Area) -> None:
    """Clear existing spawns and reapply resets for an area."""
    for room in room_registry.values():
        if room.area is area:
            for exit in room.exits:
                if exit is None:
                    continue
                rs_flags = int(getattr(exit, "rs_flags", 0))
                if rs_flags:
                    exit.exit_info = rs_flags
            room.contents.clear()
            room.people = [p for p in room.people if not isinstance(p, MobInstance)]
    apply_resets(area)


def reset_tick() -> None:
    """Advance area ages and trigger resets when empty."""
    for area in area_registry.values():
        area.nplayer = sum(
            1
            for room in room_registry.values()
            if room.area is area
            for p in room.people
            if not isinstance(p, MobInstance)
        )
        if area.nplayer > 0:
            area.age = 0
            continue
        area.age += 1
        if area.age >= RESET_TICKS:
            reset_area(area)
            area.age = 0
