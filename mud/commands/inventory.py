from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from mud.ai import _can_loot
from mud.models.character import Character
from mud.models.constants import (
    CommFlag,
    ItemType,
    OBJ_VNUM_MAP,
    OBJ_VNUM_SCHOOL_BANNER,
    OBJ_VNUM_SCHOOL_SHIELD,
    OBJ_VNUM_SCHOOL_SWORD,
    OBJ_VNUM_SCHOOL_VEST,
    WeaponFlag,
)
from mud.spawning.obj_spawner import spawn_object
from mud.world.movement import can_carry_n, can_carry_w, get_carry_weight
from mud.world.vision import can_see_object

if TYPE_CHECKING:
    from mud.models.object import Object


def _get_obj_weight(obj: object) -> int:
    """Return object's weight following ROM get_obj_weight logic."""
    proto = getattr(obj, "prototype", None)
    if proto is not None:
        base_weight = int(getattr(proto, "weight", 0) or 0)
    else:
        base_weight = int(getattr(obj, "weight", 0) or 0)

    contained_items = getattr(obj, "contained_items", []) or []
    for item in contained_items:
        base_weight += _get_obj_weight(item)
    return base_weight


def _get_obj_number(obj: object) -> int:
    """Return object count following ROM get_obj_number logic.

    Money and gems don't count toward carry_number in ROM.
    Containers don't count, but their non-gem/non-money contents do.
    """
    from mud.models.constants import ItemType

    proto = getattr(obj, "prototype", None)
    if proto is None:
        proto = obj

    item_type_raw = getattr(proto, "item_type", 0)
    if item_type_raw is None:
        item_type = 0
    elif isinstance(item_type_raw, (int, ItemType)):
        item_type = int(item_type_raw)
    else:
        try:
            item_type = int(item_type_raw)
        except (ValueError, TypeError):
            item_type = 0

    if item_type in (int(ItemType.MONEY), int(ItemType.GEM), int(ItemType.CONTAINER)):
        count = 0
    else:
        count = 1

    contained_items = getattr(obj, "contained_items", []) or []
    for item in contained_items:
        count += _get_obj_number(item)

    return count


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
        if not _objects_match_vnum(inventory, OBJ_VNUM_MAP) and not _objects_match_vnum(equipped_items, OBJ_VNUM_MAP):
            map_obj = spawn_object(OBJ_VNUM_MAP)
            if map_obj is not None:
                map_obj.cost = 0
                char.add_object(map_obj)
                equipped = True

    return equipped


def do_get(char: Character, args: str) -> str:
    """Get object from room, following ROM src/act_obj.c:do_get encumbrance checks."""
    if not args:
        return "Get what?"
    name = args.lower()
    for obj in list(char.room.contents):
        obj_name = (obj.short_descr or obj.name or "").lower()
        if name in obj_name:
            # ROM src/act_obj.c:61-89 - Check corpse looting permission
            item_type = int(getattr(obj, "item_type", 0) or 0)
            if item_type in (int(ItemType.CORPSE_PC), int(ItemType.CORPSE_NPC)):
                if not _can_loot(char, obj):
                    return "You cannot loot that corpse."

            obj_number = _get_obj_number(obj)
            obj_weight = _get_obj_weight(obj)

            if char.carry_number + obj_number > can_carry_n(char):
                return f"{obj.short_descr or obj.name}: you can't carry that many items."

            if get_carry_weight(char) + obj_weight > can_carry_w(char):
                return f"{obj.short_descr or obj.name}: you can't carry that much weight."

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


def _show_inventory_list(objects: list[Object], char: Character, show_nothing: bool = True) -> str:
    """
    Display inventory object list with ROM C formatting and combining logic.

    ROM Reference: src/act_info.c show_list_to_char (lines 130-243)

    Features:
    - Filters by visibility (can_see_object)
    - Filters by wear location (WEAR_NONE only, if object has wear_loc)
    - Combines duplicate objects if COMM_COMBINE flag set
    - Shows "(count)" prefix for duplicates
    - Shows "     Nothing." for empty list (with padding if COMM_COMBINE)

    Args:
        objects: List of objects to display
        char: Character viewing the list
        show_nothing: Show "Nothing" message if no visible objects

    Returns:
        Formatted object list string
    """
    # ROM Reference: src/act_info.c lines 162-197 (object filtering and combining)

    # Filter visible objects with WEAR_NONE (in inventory, not equipped)
    visible_objects = []
    for obj in objects:
        # ROM C line 164: if (obj->wear_loc == WEAR_NONE && can_see_obj (ch, obj))
        # ROM C: WEAR_NONE = -1 (src/merc.h line 1336)
        wear_loc = getattr(obj, "wear_loc", None)
        if wear_loc is not None and wear_loc != -1:  # -1 = WEAR_NONE
            continue

        if not can_see_object(char, obj):
            continue

        visible_objects.append(obj)

    # Check if player has COMM_COMBINE flag (ROM C line 170)
    is_npc = getattr(char, "is_npc", False)
    comm_flags = int(getattr(char, "comm", 0) or 0)
    combine_enabled = is_npc or (comm_flags & int(CommFlag.COMBINE))

    # If no visible objects, show "Nothing" message (ROM C lines 227-232)
    if not visible_objects:
        if not show_nothing:
            return ""

        if combine_enabled:
            return "     Nothing.\n"
        else:
            return "Nothing.\n"

    # Format objects (ROM C lines 162-225)
    if combine_enabled:
        # Combine duplicate objects (ROM C lines 170-195)
        object_counts: dict[str, int] = {}
        object_order: list[str] = []

        for obj in visible_objects:
            # Get object description (short description)
            obj_desc = obj.short_descr or obj.name or "something"

            # ROM C lines 176-184: Look for duplicates (case sensitive)
            if obj_desc in object_counts:
                object_counts[obj_desc] += 1
            else:
                object_counts[obj_desc] = 1
                object_order.append(obj_desc)

        # Format output with counts (ROM C lines 202-225)
        lines = []
        for obj_desc in object_order:
            count = object_counts[obj_desc]
            if count > 1:
                # ROM C lines 212-216: Show count prefix
                lines.append(f"({count:2d}) {obj_desc}")
            else:
                # ROM C lines 217-220: Show padding for single items
                lines.append(f"     {obj_desc}")

        return "\n".join(lines) + "\n"

    else:
        # No combining: show each object on separate line (ROM C lines 222-223)
        lines = []
        for obj in visible_objects:
            obj_desc = obj.short_descr or obj.name or "something"
            lines.append(obj_desc)

        return "\n".join(lines) + "\n"


def do_inventory(char: Character, args: str = "") -> str:
    """
    Display character's inventory.

    ROM Reference: src/act_info.c do_inventory (lines 2254-2259)
    """
    # ROM C line 2256: send_to_char ("You are carrying:\n\r", ch);
    output = "You are carrying:\n"

    # ROM C line 2257: show_list_to_char (ch->carrying, ch, TRUE, TRUE);
    inventory = list(getattr(char, "inventory", []) or [])
    output += _show_inventory_list(inventory, char, show_nothing=True)

    return output


def do_equipment(char: Character, args: str = "") -> str:
    """
    Show equipment worn by character.

    ROM Reference: src/act_info.c:do_equipment (lines 2263-2295)
    """
    from mud.models.constants import WearLocation

    # ROM slot names mapping (src/act_info.c:48-67 where_name array)
    slot_names = {
        int(WearLocation.LIGHT): "<used as light>     ",
        int(WearLocation.FINGER_L): "<worn on finger>    ",
        int(WearLocation.FINGER_R): "<worn on finger>    ",
        int(WearLocation.NECK_1): "<worn around neck>  ",
        int(WearLocation.NECK_2): "<worn around neck>  ",
        int(WearLocation.BODY): "<worn on torso>     ",
        int(WearLocation.HEAD): "<worn on head>      ",
        int(WearLocation.LEGS): "<worn on legs>      ",
        int(WearLocation.FEET): "<worn on feet>      ",
        int(WearLocation.HANDS): "<worn on hands>     ",
        int(WearLocation.ARMS): "<worn on arms>      ",
        int(WearLocation.SHIELD): "<worn as shield>    ",
        int(WearLocation.ABOUT): "<worn about body>   ",
        int(WearLocation.WAIST): "<worn about waist>  ",
        int(WearLocation.WRIST_L): "<worn around wrist> ",
        int(WearLocation.WRIST_R): "<worn around wrist> ",
        int(WearLocation.WIELD): "<wielded>           ",
        int(WearLocation.HOLD): "<held>              ",
        int(WearLocation.FLOAT): "<floating nearby>   ",
    }

    # ROM C line 2268: send_to_char ("You are using:\n\r", ch);
    output = "You are using:\n"

    # ROM C lines 2269-2289: Iterate through equipment slots
    equipment = getattr(char, "equipment", {}) or {}
    found = False

    for slot, obj in equipment.items():
        slot_name = slot_names.get(slot, f"<slot {slot}>")

        # ROM C line 2277: if (can_see_obj (ch, obj))
        if can_see_object(char, obj):
            # ROM C line 2279: format_obj_to_char (obj, ch, TRUE)
            obj_name = obj.short_descr or obj.name or "object"
        else:
            # ROM C line 2283: send_to_char ("something.\n\r", ch);
            obj_name = "something."

        output += f"{slot_name}{obj_name}\n"
        found = True

    # ROM C line 2291: if (!found) send_to_char ("Nothing.\n\r", ch);
    if not found:
        output += "Nothing.\n"

    return output


def do_outfit(char: Character, args: str = "") -> str:
    if getattr(char, "is_npc", False) or int(getattr(char, "level", 0) or 0) > 5:
        return "Find it yourself!"

    provided = give_school_outfit(char)
    if not provided:
        return "You already have your equipment."
    return "You have been equipped by Mota."
