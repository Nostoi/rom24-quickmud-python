"""
Equipment commands for wear, wield, and hold.

ROM References: src/act_obj.c lines 1000-1500
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mud.models.constants import ItemType, Position, WearFlag, WearLocation

if TYPE_CHECKING:
    from mud.models.character import Character
    from mud.models.object import Object


def do_wear(ch: Character, args: str) -> str:
    """
    Wear equipment (armor, clothing, jewelry).

    ROM Reference: src/act_obj.c lines 1042-1184 (do_wear)
    """
    args = args.strip()

    if not args:
        return "Wear, wield, or hold what?"

    # Handle "wear all"
    if args.lower() == "all":
        return _wear_all(ch)

    # Find object in inventory
    obj = _find_obj_inventory(ch, args)
    if not obj:
        return "You do not have that item."

    # Check if already wearing/wielding/holding
    if getattr(obj, "worn_by", None) == ch:
        return "You are already wearing that."

    # Check position
    if ch.position < Position.SLEEPING:
        return "You can't do that right now."

    # Determine where this can be worn
    wear_flags = getattr(obj, "wear_flags", 0)
    item_type_str = getattr(obj, "item_type", None)
    item_type = int(item_type_str) if item_type_str else ItemType.TRASH

    # Weapons and held items should use wield/hold
    if item_type == ItemType.WEAPON:
        return "You need to wield weapons, not wear them."
    if wear_flags & WearFlag.HOLD:
        return "You need to hold that, not wear it."

    # Find appropriate wear location
    wear_loc = _get_wear_location(obj, wear_flags)
    if not wear_loc:
        return "You can't wear that."

    # Check if slot is occupied
    equipment = getattr(ch, "equipment", {})
    if wear_loc in equipment and equipment[wear_loc] is not None:
        existing = equipment[wear_loc]
        existing_name = getattr(existing, "short_descr", "something")
        return f"You're already wearing {existing_name}."

    # Wear the item
    if not equipment:
        ch.equipment = {}
    ch.equipment[wear_loc] = obj
    obj.worn_by = ch
    obj.wear_loc = wear_loc

    # Remove from inventory
    inventory = getattr(ch, "inventory", [])
    if obj in inventory:
        inventory.remove(obj)

    obj_name = getattr(obj, "short_descr", "something")
    return f"You wear {obj_name}."


def do_wield(ch: Character, args: str) -> str:
    """
    Wield a weapon.

    ROM Reference: src/act_obj.c lines 1279-1380 (do_wear, weapon section)
    """
    args = args.strip()

    if not args:
        return "Wield what?"

    # Find object in inventory
    obj = _find_obj_inventory(ch, args)
    if not obj:
        return "You do not have that item."

    # Check if already wielding
    if getattr(obj, "worn_by", None) == ch:
        return "You are already using that."

    # Check position
    if ch.position < Position.SLEEPING:
        return "You can't do that right now."

    # Check if it's a weapon (item_type is stored as string, enum value is int)
    item_type_str = getattr(obj, "item_type", None)
    item_type = int(item_type_str) if item_type_str else ItemType.TRASH
    if item_type != ItemType.WEAPON:
        return "You can't wield that."

    # Check if weapon slot is occupied
    equipment = getattr(ch, "equipment", {})
    wear_loc = WearLocation.WIELD

    if wear_loc in equipment and equipment[wear_loc] is not None:
        existing = equipment[wear_loc]
        existing_name = getattr(existing, "short_descr", "something")
        return f"You're already wielding {existing_name}."

    # Check strength requirement (weapon weight)
    weight = getattr(obj, "weight", 0)
    str_stat = (
        ch.get_curr_stat(getattr(ch, "Stat", type("Stat", (), {"STR": 0})).STR) if hasattr(ch, "get_curr_stat") else 13
    )

    # ROM formula: need STR >= weight / 10
    if str_stat * 10 < weight:
        return "It is too heavy for you to wield."

    # Wield the weapon
    if not equipment:
        ch.equipment = {}
    ch.equipment[wear_loc] = obj
    obj.worn_by = ch
    obj.wear_loc = wear_loc

    # Remove from inventory
    inventory = getattr(ch, "inventory", [])
    if obj in inventory:
        inventory.remove(obj)

    obj_name = getattr(obj, "short_descr", "something")
    return f"You wield {obj_name}."


def do_hold(ch: Character, args: str) -> str:
    """
    Hold an item (lights, instruments, etc.).

    ROM Reference: src/act_obj.c lines 1186-1277 (do_wear, hold section)
    """
    args = args.strip()

    if not args:
        return "Hold what?"

    # Find object in inventory
    obj = _find_obj_inventory(ch, args)
    if not obj:
        return "You do not have that item."

    # Check if already holding
    if getattr(obj, "worn_by", None) == ch:
        return "You are already holding that."

    # Check position
    if ch.position < Position.SLEEPING:
        return "You can't do that right now."

    # Check if it can be held
    wear_flags = getattr(obj, "wear_flags", 0)
    if not (wear_flags & WearFlag.HOLD):
        return "You can't hold that."

    # Check if hold slot is occupied
    equipment = getattr(ch, "equipment", {})
    wear_loc = WearLocation.HOLD

    if wear_loc in equipment and equipment[wear_loc] is not None:
        existing = equipment[wear_loc]
        existing_name = getattr(existing, "short_descr", "something")
        return f"You're already holding {existing_name}."

    # Hold the item
    if not equipment:
        ch.equipment = {}
    ch.equipment[wear_loc] = obj
    obj.worn_by = ch
    obj.wear_loc = wear_loc

    # Remove from inventory
    inventory = getattr(ch, "inventory", [])
    if obj in inventory:
        inventory.remove(obj)

    obj_name = getattr(obj, "short_descr", "something")

    # Special message for lights (item_type is stored as string)
    item_type_str = getattr(obj, "item_type", None)
    item_type = int(item_type_str) if item_type_str else ItemType.TRASH
    if item_type == ItemType.LIGHT:
        return f"You hold {obj_name} as your light."

    return f"You hold {obj_name} in your hand."


def _wear_all(ch: Character) -> str:
    """Wear all wearable items in inventory."""
    inventory = getattr(ch, "inventory", [])
    if not inventory:
        return "You are not carrying anything."

    messages = []
    for obj in list(inventory):  # Copy list since we modify it
        # Skip already worn items
        if getattr(obj, "worn_by", None):
            continue

        # Skip weapons and held items
        item_type_str = getattr(obj, "item_type", None)
        item_type = int(item_type_str) if item_type_str else ItemType.TRASH
        wear_flags = getattr(obj, "wear_flags", 0)

        if item_type == ItemType.WEAPON:
            continue
        if wear_flags & WearFlag.HOLD:
            continue

        # Try to wear it
        wear_loc = _get_wear_location(obj, wear_flags)
        if not wear_loc:
            continue

        equipment = getattr(ch, "equipment", {})
        if wear_loc in equipment and equipment[wear_loc] is not None:
            continue  # Slot occupied

        # Wear it
        if not equipment:
            ch.equipment = {}
        ch.equipment[wear_loc] = obj
        obj.worn_by = ch
        obj.wear_loc = wear_loc
        inventory.remove(obj)

        obj_name = getattr(obj, "short_descr", "something")
        messages.append(f"You wear {obj_name}.")

    if not messages:
        return "You have nothing else to wear."

    return "\n".join(messages)


def _get_wear_location(obj: Object, wear_flags: int) -> WearLocation | None:
    """Determine which slot an item should be worn in."""
    # Priority order for wear locations (from ROM)
    # Check WearFlag bits and return corresponding WearLocation slot
    if wear_flags & WearFlag.WEAR_FINGER:
        return WearLocation.FINGER_L  # Will need multi-slot handling later
    if wear_flags & WearFlag.WEAR_NECK:
        return WearLocation.NECK_1
    if wear_flags & WearFlag.WEAR_BODY:
        return WearLocation.BODY
    if wear_flags & WearFlag.WEAR_HEAD:
        return WearLocation.HEAD
    if wear_flags & WearFlag.WEAR_LEGS:
        return WearLocation.LEGS
    if wear_flags & WearFlag.WEAR_FEET:
        return WearLocation.FEET
    if wear_flags & WearFlag.WEAR_HANDS:
        return WearLocation.HANDS
    if wear_flags & WearFlag.WEAR_ARMS:
        return WearLocation.ARMS
    if wear_flags & WearFlag.WEAR_ABOUT:
        return WearLocation.ABOUT
    if wear_flags & WearFlag.WEAR_WAIST:
        return WearLocation.WAIST
    if wear_flags & WearFlag.WEAR_WRIST:
        return WearLocation.WRIST_L  # Will need multi-slot handling later
    if wear_flags & WearFlag.WEAR_SHIELD:
        return WearLocation.SHIELD
    if wear_flags & WearFlag.WEAR_FLOAT:
        return WearLocation.FLOAT

    return None


def _find_obj_inventory(ch: Character, name: str) -> Object | None:
    """Find an object in character's inventory by name."""
    inventory = getattr(ch, "inventory", [])
    if not inventory or not name:
        return None

    name_lower = name.lower()
    for obj in inventory:
        # Check short description
        short_descr = getattr(obj, "short_descr", "")
        if name_lower in short_descr.lower():
            return obj

        # Check name
        obj_name = getattr(obj, "name", "")
        if name_lower in obj_name.lower():
            return obj

    return None
