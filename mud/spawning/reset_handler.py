from __future__ import annotations

import logging
from typing import Dict, List, Optional

from mud.models.area import Area
from mud.models.constants import ITEM_INVENTORY
from mud.registry import room_registry, area_registry, mob_registry
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


def apply_resets(area: Area) -> None:
    """Populate rooms based on ROM reset data semantics."""

    last_mob: Optional[MobInstance] = None
    last_obj: Optional[object] = None
    spawned_objects: Dict[int, List[object]] = {}
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
            obj = spawn_object(obj_vnum)
            room = room_registry.get(room_vnum)
            if obj and room:
                room.add_object(obj)
                last_obj = obj
                spawned_objects.setdefault(obj_vnum, []).append(obj)
            else:
                logging.warning('Invalid O reset %s -> %s', obj_vnum, room_vnum)
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
            obj = spawn_object(obj_vnum)
            if obj:
                obj.level = _compute_object_level(obj, last_mob)
                try:
                    from mud.registry import shop_registry

                    is_shopkeeper = (
                        getattr(getattr(last_mob, 'prototype', None), 'vnum', None)
                        in shop_registry
                    )
                except Exception:
                    is_shopkeeper = False

                if is_shopkeeper and hasattr(obj.prototype, 'extra_flags'):
                    from mud.models.constants import ExtraFlag

                    if isinstance(obj.prototype.extra_flags, str):
                        from mud.models.constants import convert_flags_from_letters

                        current_flags = convert_flags_from_letters(
                            obj.prototype.extra_flags, ExtraFlag
                        )
                        obj.prototype.extra_flags = current_flags | ITEM_INVENTORY
                    else:
                        obj.prototype.extra_flags |= ITEM_INVENTORY
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
            obj = spawn_object(obj_vnum)
            if obj:
                obj.level = _compute_object_level(obj, last_mob)
                try:
                    from mud.registry import shop_registry

                    is_shopkeeper = (
                        getattr(getattr(last_mob, 'prototype', None), 'vnum', None)
                        in shop_registry
                    )
                except Exception:
                    is_shopkeeper = False
                if is_shopkeeper and hasattr(obj.prototype, 'extra_flags'):
                    from mud.models.constants import ExtraFlag

                    if isinstance(obj.prototype.extra_flags, str):
                        from mud.models.constants import convert_flags_from_letters

                        current_flags = convert_flags_from_letters(
                            obj.prototype.extra_flags, ExtraFlag
                        )
                        obj.prototype.extra_flags = current_flags | ITEM_INVENTORY
                    else:
                        obj.prototype.extra_flags |= ITEM_INVENTORY
                last_mob.equip(obj, slot)
                last_obj = obj
                spawned_objects.setdefault(obj_vnum, []).append(obj)
            else:
                logging.warning('Invalid E reset %s', obj_vnum)
        elif cmd == 'P':
            obj_vnum = reset.arg1 or 0
            container_vnum = reset.arg3 or 0
            count = max(1, int(reset.arg4 or 1))
            if container_vnum <= 0:
                logging.warning('Invalid P reset %s -> %s', obj_vnum, container_vnum)
                continue
            container_obj: Optional[object] = None
            if last_obj and getattr(getattr(last_obj, 'prototype', None), 'vnum', None) == container_vnum:
                container_obj = last_obj
            if not container_obj:
                lst = spawned_objects.get(container_vnum) or []
                container_obj = lst[-1] if lst else None
            if not container_obj:
                logging.warning('Invalid P reset %s -> %s (no container instance)', obj_vnum, container_vnum)
                continue
            existing = [
                o
                for o in getattr(container_obj, 'contained_items', [])
                if getattr(getattr(o, 'prototype', None), 'vnum', None) == obj_vnum
            ]
            to_make = max(0, count - len(existing))
            for _ in range(to_make):
                obj = spawn_object(obj_vnum)
                if not obj:
                    break
                getattr(container_obj, 'contained_items').append(obj)
                spawned_objects.setdefault(obj_vnum, []).append(obj)
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
