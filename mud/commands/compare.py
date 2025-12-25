"""
Compare command - compare equipment stats.

ROM Reference: src/act_info.c do_compare (lines 2150-2250)
"""
from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import ItemType
from mud.world.obj_find import get_obj_carry


def do_compare(char: Character, args: str) -> str:
    """
    Compare two items or an item against equipped gear.
    
    ROM Reference: src/act_info.c do_compare (lines 2150-2250)
    
    Usage:
    - compare <item1> <item2> - Compare two items in inventory
    - compare <item> - Compare item against currently equipped
    """
    args = args.strip()
    parts = args.split()
    
    if not parts:
        return "Compare what to what?"
    
    # Find first object
    obj1 = get_obj_carry(char, parts[0])
    if obj1 is None:
        return "You do not have that item."
    
    # Determine what to compare against
    if len(parts) >= 2:
        # Compare two items
        obj2 = get_obj_carry(char, parts[1])
        if obj2 is None:
            return "You do not have that second item."
    else:
        # Compare against equipped item of same type
        obj2 = _find_equipped_match(char, obj1)
        if obj2 is None:
            return "You aren't wearing anything comparable."
    
    if obj1 is obj2:
        return "You can't compare an item to itself."
    
    # Get item types
    type1 = getattr(obj1, "item_type", 0)
    type2 = getattr(obj2, "item_type", 0)
    
    # Compare based on item type
    if type1 == ItemType.WEAPON or type2 == ItemType.WEAPON:
        return _compare_weapons(obj1, obj2)
    elif type1 == ItemType.ARMOR or type2 == ItemType.ARMOR:
        return _compare_armor(obj1, obj2)
    else:
        return "You can only compare weapons or armor."


def _find_equipped_match(char: Character, obj) -> object | None:
    """Find an equipped item of the same type to compare against."""
    item_type = getattr(obj, "item_type", 0)
    equipped = getattr(char, "equipped", {})
    
    if item_type == ItemType.WEAPON:
        return equipped.get("wield") or equipped.get("main_hand")
    elif item_type == ItemType.ARMOR:
        # Check all armor slots for matching wear location
        wear_flags = getattr(obj, "wear_flags", 0)
        for slot, eq_obj in equipped.items():
            if eq_obj and slot not in ("wield", "main_hand", "held"):
                return eq_obj
    
    return None


def _compare_weapons(obj1, obj2) -> str:
    """Compare two weapons by average damage."""
    # Get weapon damage values [dice_number, dice_type, damage_type]
    val1 = getattr(obj1, "value", [1, 4, 0, 0, 0])
    val2 = getattr(obj2, "value", [1, 4, 0, 0, 0])
    
    # Average damage = (dice_number * (dice_type + 1)) / 2
    if isinstance(val1, list) and len(val1) >= 2:
        avg1 = (val1[1] * (val1[2] + 1)) / 2 if len(val1) >= 3 else val1[0] * (val1[1] + 1) / 2
    else:
        avg1 = 5  # Default
    
    if isinstance(val2, list) and len(val2) >= 2:
        avg2 = (val2[1] * (val2[2] + 1)) / 2 if len(val2) >= 3 else val2[0] * (val2[1] + 1) / 2
    else:
        avg2 = 5  # Default
    
    obj1_name = getattr(obj1, "short_descr", None) or getattr(obj1, "name", "first item")
    obj2_name = getattr(obj2, "short_descr", None) or getattr(obj2, "name", "second item")
    
    diff = avg1 - avg2
    if diff > 5:
        return f"{obj1_name} looks much better than {obj2_name}."
    elif diff > 2:
        return f"{obj1_name} looks better than {obj2_name}."
    elif diff > 0:
        return f"{obj1_name} looks slightly better than {obj2_name}."
    elif diff == 0:
        return f"{obj1_name} and {obj2_name} look about the same."
    elif diff > -3:
        return f"{obj1_name} looks slightly worse than {obj2_name}."
    elif diff > -6:
        return f"{obj1_name} looks worse than {obj2_name}."
    else:
        return f"{obj1_name} looks much worse than {obj2_name}."


def _compare_armor(obj1, obj2) -> str:
    """Compare two pieces of armor by AC values."""
    # Armor value is typically in value[0]
    val1 = getattr(obj1, "value", [0, 0, 0, 0, 0])
    val2 = getattr(obj2, "value", [0, 0, 0, 0, 0])
    
    ac1 = val1[0] if isinstance(val1, list) and len(val1) > 0 else 0
    ac2 = val2[0] if isinstance(val2, list) and len(val2) > 0 else 0
    
    obj1_name = getattr(obj1, "short_descr", None) or getattr(obj1, "name", "first item")
    obj2_name = getattr(obj2, "short_descr", None) or getattr(obj2, "name", "second item")
    
    # Lower AC is better in ROM
    diff = ac2 - ac1  # Reversed because lower is better
    
    if diff > 10:
        return f"{obj1_name} looks much better than {obj2_name}."
    elif diff > 5:
        return f"{obj1_name} looks better than {obj2_name}."
    elif diff > 0:
        return f"{obj1_name} looks slightly better than {obj2_name}."
    elif diff == 0:
        return f"{obj1_name} and {obj2_name} look about the same."
    elif diff > -6:
        return f"{obj1_name} looks slightly worse than {obj2_name}."
    elif diff > -11:
        return f"{obj1_name} looks worse than {obj2_name}."
    else:
        return f"{obj1_name} looks much worse than {obj2_name}."
