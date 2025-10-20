from collections.abc import Iterable

from mud.models.character import Character
from mud.models.constants import (
    OBJ_VNUM_MAP,
    OBJ_VNUM_SCHOOL_BANNER,
    OBJ_VNUM_SCHOOL_SHIELD,
    OBJ_VNUM_SCHOOL_SWORD,
    OBJ_VNUM_SCHOOL_VEST,
    WeaponFlag,
)
from mud.spawning.obj_spawner import spawn_object


def _objects_match_vnum(objects: Iterable[object], vnum: int) -> bool:
    for obj in objects:
        proto = getattr(obj, "prototype", None)
        if proto is not None and int(getattr(proto, "vnum", 0) or 0) == vnum:
            return True
    return False


def give_school_outfit(char: Character, *, include_map: bool = True) -> bool:
    """Equip ROM school banner/vest/weapon/shield and optionally a Midgaard map."""

    if getattr(char, "is_npc", False):
        return False

    equipped = False
    equipment = getattr(char, "equipment", {})

    def _equip(slot: str, vnum: int) -> None:
        nonlocal equipped
        if equipment.get(slot) is not None:
            return
        obj = spawn_object(vnum)
        if obj is None:
            return
        obj.cost = 0
        char.equip_object(obj, slot)
        equipped = True

    _equip("light", OBJ_VNUM_SCHOOL_BANNER)
    _equip("body", OBJ_VNUM_SCHOOL_VEST)

    if equipment.get("wield") is None:
        weapon_vnum = int(getattr(char, "default_weapon_vnum", 0) or 0)
        primary_weapon = spawn_object(weapon_vnum) if weapon_vnum else None
        if primary_weapon is None:
            primary_weapon = spawn_object(OBJ_VNUM_SCHOOL_SWORD)
        if primary_weapon is not None:
            primary_weapon.cost = 0
            char.equip_object(primary_weapon, "wield")
            equipped = True

    wielded = equipment.get("wield")
    weapon_flags = 0
    if wielded is not None:
        values = getattr(wielded, "value", [0, 0, 0, 0, 0])
        if len(values) > 4:
            try:
                weapon_flags = int(values[4])
            except (TypeError, ValueError):
                weapon_flags = 0

    if not (weapon_flags & int(WeaponFlag.TWO_HANDS)):
        _equip("shield", OBJ_VNUM_SCHOOL_SHIELD)

    if include_map:
        inventory = list(getattr(char, "inventory", []) or [])
        equipped_items = list(equipment.values())
        if not _objects_match_vnum(inventory, OBJ_VNUM_MAP) and not _objects_match_vnum(
            equipped_items, OBJ_VNUM_MAP
        ):
            map_obj = spawn_object(OBJ_VNUM_MAP)
            if map_obj is not None:
                map_obj.cost = 0
                char.add_object(map_obj)
                equipped = True

    return equipped


def do_get(char: Character, args: str) -> str:
    if not args:
        return "Get what?"
    name = args.lower()
    for obj in list(char.room.contents):
        obj_name = (obj.short_descr or obj.name or "").lower()
        if name in obj_name:
            char.room.contents.remove(obj)
            char.add_object(obj)
            return f"You pick up {obj.short_descr or obj.name}."
    return "You don't see that here."


def do_drop(char: Character, args: str) -> str:
    if not args:
        return "Drop what?"
    name = args.lower()
    for obj in list(char.inventory):
        obj_name = (obj.short_descr or obj.name or "").lower()
        if name in obj_name:
            char.inventory.remove(obj)
            char.room.add_object(obj)
            return f"You drop {obj.short_descr or obj.name}."
    return "You aren't carrying that."


def do_inventory(char: Character, args: str = "") -> str:
    if not char.inventory:
        return "You are carrying nothing."
    return "You are carrying: " + ", ".join(obj.short_descr or obj.name or "object" for obj in char.inventory)


def do_equipment(char: Character, args: str = "") -> str:
    if not char.equipment:
        return "You are wearing nothing."
    parts = []
    for slot, obj in char.equipment.items():
        parts.append(f"{slot}: {obj.short_descr or obj.name or 'object'}")
    return "You are using: " + ", ".join(parts)


def do_outfit(char: Character, args: str = "") -> str:
    if getattr(char, "is_npc", False) or int(getattr(char, "level", 0) or 0) > 5:
        return "Find it yourself!"

    provided = give_school_outfit(char)
    if not provided:
        return "You already have your equipment."
    return "You have been equipped by Mota."
