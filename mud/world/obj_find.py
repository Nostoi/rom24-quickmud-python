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

    # Search inventory
    for obj in getattr(char, "carrying", []):
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
    Find an object in the room by name.

    ROM Reference: src/handler.c get_obj_here

    Searches:
    1. Character's inventory
    2. Character's equipment
    3. Room contents
    """
    if not name:
        return None

    # Check inventory first
    obj = get_obj_carry(char, name)
    if obj:
        return obj

    # Check equipment
    obj = get_obj_wear(char, name)
    if obj:
        return obj

    # Check room
    room = getattr(char, "room", None)
    if not room:
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

    for obj in getattr(room, "contents", []):
        obj_name = getattr(obj, "name", "").lower()
        obj_short = (getattr(obj, "short_descr", "") or "").lower()

        if name_lower in obj_name or name_lower in obj_short:
            count += 1
            if count == target_count:
                return obj

    return None


def get_obj_world(char: "Character", name: str) -> "Obj | None":
    """
    Find an object anywhere in the world by name.

    ROM Reference: src/handler.c get_obj_world
    """
    from mud.registry import object_registry

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

    for obj in object_registry.values():
        obj_name = getattr(obj, "name", "").lower()
        obj_short = (getattr(obj, "short_descr", "") or "").lower()

        if name_lower in obj_name or name_lower in obj_short:
            count += 1
            if count == target_count:
                return obj

    return None
