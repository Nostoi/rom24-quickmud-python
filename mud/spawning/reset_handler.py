from __future__ import annotations
import logging
from typing import Dict

from mud.models.area import Area
from mud.registry import room_registry, area_registry
from .mob_spawner import spawn_mob
from .obj_spawner import spawn_object
from .templates import MobInstance

RESET_TICKS = 3


def apply_resets(area: Area) -> None:
    """Populate rooms based on simplified reset data."""
    last_mob = None
    spawned_objects: Dict[int, object] = {}
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
            else:
                logging.warning('Invalid M reset %s -> %s', mob_vnum, room_vnum)
        elif cmd == 'O':
            obj_vnum = reset.arg2 or 0
            room_vnum = reset.arg4 or 0
            obj = spawn_object(obj_vnum)
            room = room_registry.get(room_vnum)
            if obj and room:
                room.add_object(obj)
                spawned_objects[obj_vnum] = obj
            else:
                logging.warning('Invalid O reset %s -> %s', obj_vnum, room_vnum)
        elif cmd == 'G':
            obj_vnum = reset.arg2 or 0
            obj = spawn_object(obj_vnum)
            if obj and last_mob:
                last_mob.add_to_inventory(obj)
                # Track spawned objects so later P resets can reference them
                spawned_objects[obj_vnum] = obj
            else:
                logging.warning('Invalid G reset %s', obj_vnum)
        elif cmd == 'E':
            obj_vnum = reset.arg2 or 0
            slot = reset.arg4 or 0
            obj = spawn_object(obj_vnum)
            if obj and last_mob:
                last_mob.equip(obj, slot)
                spawned_objects[obj_vnum] = obj
            else:
                logging.warning('Invalid E reset %s', obj_vnum)
        elif cmd == 'P':
            obj_vnum = reset.arg2 or 0
            container_vnum = reset.arg4 or 0
            if container_vnum <= 0:
                # Negative or zero container vnums are invalid; skip quietly
                logging.warning('Invalid P reset %s -> %s', obj_vnum, container_vnum)
                continue
            obj = spawn_object(obj_vnum)
            container = spawned_objects.get(container_vnum)
            if obj and isinstance(container, type(obj)):
                container.contained_items.append(obj)
                spawned_objects[obj_vnum] = obj
            else:
                logging.warning('Invalid P reset %s -> %s', obj_vnum, container_vnum)


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
