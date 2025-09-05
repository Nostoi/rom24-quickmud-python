from __future__ import annotations
import shlex
from mud.models.character import Character
from mud.models.object import Object
from mud.spawning.templates import MobInstance


def _find_object(room, name: str) -> Object | None:
    name = name.lower()
    for obj in room.contents:
        obj_name = (obj.name or "").lower()
        short = (obj.prototype.short_descr or "").lower()
        if name in obj_name or name in short:
            return obj
    return None


def _find_mob(room, name: str) -> MobInstance | None:
    name = name.lower()
    for mob in room.people:
        if isinstance(mob, MobInstance):
            mob_name = (mob.name or "").lower()
            short = (mob.prototype.short_descr or "").lower()
            if name in mob_name or name in short:
                return mob
    return None


def cmd_setroom(char: Character, args: str) -> str:
    parts = shlex.split(args)
    if len(parts) < 2:
        return "Usage: @setroom <name|desc> <value>"
    field = parts[0].lower()
    value = " ".join(parts[1:])
    room = char.room
    if field == "name":
        room.name = value
        return f"Room name set to '{value}'."
    if field in ("desc", "description"):
        room.description = value
        return "Room description set."
    return "Unknown room field."


def cmd_setobj(char: Character, args: str) -> str:
    parts = shlex.split(args)
    if len(parts) < 3:
        return "Usage: @setobj <object> <name|short|desc> <value>"
    target_name = parts[0]
    field = parts[1].lower()
    value = " ".join(parts[2:])
    obj = _find_object(char.room, target_name)
    if not obj:
        return "Object not found."
    proto = obj.prototype
    if field == "name":
        proto.name = value
    elif field in ("short", "short_descr"):
        proto.short_descr = value
    elif field in ("desc", "description"):
        proto.description = value
    else:
        return "Unknown object field."
    return "Object updated."


def cmd_setmob(char: Character, args: str) -> str:
    parts = shlex.split(args)
    if len(parts) < 3:
        return "Usage: @setmob <mob> <name|short|long|desc> <value>"
    target_name = parts[0]
    field = parts[1].lower()
    value = " ".join(parts[2:])
    mob = _find_mob(char.room, target_name)
    if not mob:
        return "Mob not found."
    proto = mob.prototype
    if field == "name":
        proto.player_name = value
    elif field == "short":
        proto.short_descr = value
    elif field == "long":
        proto.long_descr = value
    elif field in ("desc", "description"):
        proto.description = value
    else:
        return "Unknown mob field."
    mob.name = proto.short_descr or proto.player_name
    return "Mob updated."
