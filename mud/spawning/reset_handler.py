from __future__ import annotations
import logging
from typing import Dict

from mud.models.area import Area
from mud.models.room import Reset
from mud.registry import room_registry
from .mob_spawner import spawn_mob
from .obj_spawner import spawn_object


def apply_resets(area: Area) -> None:
    """Populate rooms based on simplified reset data."""
    last_mob = None
    spawned_objects: Dict[int, object] = {}
    for reset in area.resets:
        cmd = reset.command.upper()
        if cmd == 'M':
            mob_vnum = reset.arg2
            room_vnum = reset.arg4
            mob = spawn_mob(mob_vnum)
            room = room_registry.get(room_vnum)
            if mob and room:
                room.add_mob(mob)
                last_mob = mob
            else:
                logging.warning('Invalid M reset %s -> %s', mob_vnum, room_vnum)
        elif cmd == 'O':
            obj_vnum = reset.arg2
            room_vnum = reset.arg4
            obj = spawn_object(obj_vnum)
            room = room_registry.get(room_vnum)
            if obj and room:
                room.add_object(obj)
                spawned_objects[obj_vnum] = obj
            else:
                logging.warning('Invalid O reset %s -> %s', obj_vnum, room_vnum)
        elif cmd == 'G':
            obj_vnum = reset.arg2
            obj = spawn_object(obj_vnum)
            if obj and last_mob:
                last_mob.add_to_inventory(obj)
            else:
                logging.warning('Invalid G reset %s', obj_vnum)
        elif cmd == 'E':
            obj_vnum = reset.arg2
            slot = reset.arg4
            obj = spawn_object(obj_vnum)
            if obj and last_mob:
                last_mob.equip(obj, slot)
            else:
                logging.warning('Invalid E reset %s', obj_vnum)
        elif cmd == 'P':
            obj_vnum = reset.arg2
            container_vnum = reset.arg4
            obj = spawn_object(obj_vnum)
            container = spawned_objects.get(container_vnum)
            if obj and isinstance(container, type(obj)):
                container.contained_items.append(obj)
            else:
                logging.warning('Invalid P reset %s -> %s', obj_vnum, container_vnum)
