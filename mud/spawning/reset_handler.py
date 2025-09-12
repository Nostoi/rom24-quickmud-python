from __future__ import annotations
import logging
from typing import Dict, List, Optional

from mud.models.area import Area
from mud.registry import room_registry, area_registry
from .mob_spawner import spawn_mob
from .obj_spawner import spawn_object
from .templates import MobInstance
from mud.utils import rng_mm

RESET_TICKS = 3


def apply_resets(area: Area) -> None:
    """Populate rooms based on simplified reset data."""
    last_mob = None
    last_obj: Optional[object] = None
    # Track spawned objects per prototype vnum to support simple 'P' lookups
    spawned_objects: Dict[int, List[object]] = {}
    for reset in area.resets:
        cmd = reset.command.upper()
        if cmd == 'M':
            mob_vnum = reset.arg2 or 0
            room_vnum = reset.arg4 or 0
            mob = spawn_mob(mob_vnum)
            room = room_registry.get(room_vnum)
            if mob and room:
                room.add_mob(mob)
                last_mob = mob
                last_obj = None
            else:
                logging.warning('Invalid M reset %s -> %s', mob_vnum, room_vnum)
        elif cmd == 'O':
            obj_vnum = reset.arg2 or 0
            room_vnum = reset.arg4 or 0
            obj = spawn_object(obj_vnum)
            room = room_registry.get(room_vnum)
            if obj and room:
                room.add_object(obj)
                # Update last object instance and index by vnum
                last_obj = obj
                spawned_objects.setdefault(obj_vnum, []).append(obj)
            else:
                logging.warning('Invalid O reset %s -> %s', obj_vnum, room_vnum)
        elif cmd == 'G':
            obj_vnum = reset.arg2 or 0
            obj = spawn_object(obj_vnum)
            if obj and last_mob:
                last_mob.add_to_inventory(obj)
                last_obj = obj
                spawned_objects.setdefault(obj_vnum, []).append(obj)
            else:
                logging.warning('Invalid G reset %s', obj_vnum)
        elif cmd == 'E':
            obj_vnum = reset.arg2 or 0
            slot = reset.arg4 or 0
            obj = spawn_object(obj_vnum)
            if obj and last_mob:
                last_mob.equip(obj, slot)
                last_obj = obj
                spawned_objects.setdefault(obj_vnum, []).append(obj)
            else:
                logging.warning('Invalid E reset %s', obj_vnum)
        elif cmd == 'P':
            obj_vnum = reset.arg2 or 0
            container_vnum = reset.arg4 or 0
            count = max(1, int(reset.arg3 or 1))  # how many to place
            if container_vnum <= 0:
                logging.warning('Invalid P reset %s -> %s', obj_vnum, container_vnum)
                continue
            # Prefer the last created object instance if it matches the container vnum
            container_obj: Optional[object] = None
            if last_obj and getattr(getattr(last_obj, 'prototype', None), 'vnum', None) == container_vnum:
                container_obj = last_obj
            # Otherwise, fall back to the most recent spawned container by vnum
            if not container_obj:
                lst = spawned_objects.get(container_vnum) or []
                container_obj = lst[-1] if lst else None
            if not container_obj:
                logging.warning('Invalid P reset %s -> %s (no container instance)', obj_vnum, container_vnum)
                continue
            # Determine existing count inside
            existing = [o for o in getattr(container_obj, 'contained_items', [])
                        if getattr(getattr(o, 'prototype', None), 'vnum', None) == obj_vnum]
            to_make = max(0, count - len(existing))
            for _ in range(to_make):
                obj = spawn_object(obj_vnum)
                if not obj:
                    break
                getattr(container_obj, 'contained_items').append(obj)
                spawned_objects.setdefault(obj_vnum, []).append(obj)
            # After population, set last_obj to the container (mirrors ROM behavior)
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
