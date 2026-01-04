"""
Object finding utilities - find objects by name.

ROM Reference: src/handler.c get_obj_carry, get_obj_wear, get_obj_here, etc.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mud.models.character import Character
    from mud.models.obj import Obj


def get_obj_carry(char: "Character", name: str) -> "Obj | None":
    """
    Find an object in character's inventory by name.

    ROM Reference: src/handler.c get_obj_carry
    """
    if not name:
        return None

    # Parse N.name format
    count = 0
    target_count = 1

    if "." in name:
        parts = name.split(".", 1)
        try:
            target_count = int(parts[0])
            name = parts[1]
        except ValueError:
            pass

    name_lower = name.lower()

    # Search inventory (unequipped items only)
    # ROM C handler.c:2304: for (obj = ch->carrying; obj != NULL; obj = obj->next_content)
    # ROM C handler.c:2306: if (obj->wear_loc == WEAR_NONE && ...)
    # QuickMUD: inventory = unequipped items, equipment = equipped items
    for obj in getattr(char, "inventory", []):
        obj_name = getattr(obj, "name", "").lower()
        obj_short = (getattr(obj, "short_descr", "") or "").lower()

        if name_lower in obj_name or name_lower in obj_short:
            count += 1
            if count == target_count:
                return obj

    return None


def get_obj_wear(char: "Character", name: str) -> "Obj | None":
    """
    Find an object in character's equipment by name.

    ROM Reference: src/handler.c get_obj_wear
    """
    if not name:
        return None

    # Parse N.name format
    count = 0
    target_count = 1

    if "." in name:
        parts = name.split(".", 1)
        try:
            target_count = int(parts[0])
            name = parts[1]
        except ValueError:
            pass

    name_lower = name.lower()

    # Search equipment (Character model uses 'equipment', not 'equipped')
    equipped = getattr(char, "equipment", {})
    for obj in equipped.values():
        if obj is None:
            continue

        obj_name = getattr(obj, "name", "").lower()
        obj_short = (getattr(obj, "short_descr", "") or "").lower()

        if name_lower in obj_name or name_lower in obj_short:
            count += 1
            if count == target_count:
                return obj

    return None


def get_obj_here(char: "Character", name: str) -> "Obj | None":
    """
    Find an object in the room or in inventory/equipment.

    ROM Reference: src/handler.c get_obj_here (lines 2349-2364)

    Search order (ROM C):
    1. Room contents (get_obj_list on ch->in_room->contents)
    2. Character's inventory (get_obj_carry)
    3. Character's equipment (get_obj_wear)
    """
    from mud.commands.obj_manipulation import get_obj_list

    if not name:
        return None

    # ROM C handler.c:2353 - Check ROOM FIRST!
    room = getattr(char, "room", None)
    if room:
        obj = get_obj_list(char, name, getattr(room, "contents", []))
        if obj:
            return obj

    # ROM C handler.c:2357 - Check inventory
    obj = get_obj_carry(char, name)
    if obj:
        return obj

    # ROM C handler.c:2360 - Check equipment
    obj = get_obj_wear(char, name)
    if obj:
        return obj

    return None


def get_obj_world(char: "Character", name: str) -> "Obj | None":
    """
    Find an object anywhere in the world by name.

    ROM Reference: src/handler.c get_obj_world
    """
    from mud.models.obj import object_registry

    if not name:
        return None

    # Parse N.name format
    count = 0
    target_count = 1

    if "." in name:
        parts = name.split(".", 1)
        try:
            target_count = int(parts[0])
            name = parts[1]
        except ValueError:
            pass

    name_lower = name.lower()

    # object_registry is a list of ObjectData instances (ROM C: object_list)
    for obj in object_registry:
        obj_name = getattr(obj, "name", "").lower()
        obj_short = (getattr(obj, "short_descr", "") or "").lower()

        if name_lower in obj_name or name_lower in obj_short:
            count += 1
            if count == target_count:
                return obj

    return None


def get_obj_type(prototype_vnum: int) -> "Obj | None":
    """
    Find the first object instance with a given prototype vnum.

    ROM Reference: src/handler.c get_obj_type (lines 2252-2263)

    Args:
        prototype_vnum: The vnum of the object prototype to find

    Returns:
        First object instance with matching prototype, or None

    ROM C Implementation:
        for (obj = object_list; obj != NULL; obj = obj->next)
        {
            if (obj->pIndexData == pObjIndex)
                return obj;
        }
    """
    from mud.models.obj import object_registry

    # Iterate through all object instances (ROM C: object_list)
    for obj in object_registry:
        prototype = getattr(obj, "prototype", None)
        if prototype is None:
            continue

        # Check if prototype vnum matches (ROM C: obj->pIndexData == pObjIndex)
        obj_vnum = getattr(prototype, "vnum", None)
        if obj_vnum == prototype_vnum:
            return obj

    return None
