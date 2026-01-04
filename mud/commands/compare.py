"""
Compare command - compare equipment stats.

ROM Reference: src/act_info.c do_compare (lines 2297-2395)
"""

from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import ItemType
from mud.utils.act import act_format
from mud.world.obj_find import get_obj_carry


def do_compare(char: Character, args: str) -> str:
    """
    Compare two items or an item against equipped gear.

    ROM Reference: src/act_info.c do_compare (lines 2297-2395)

    Usage:
    - compare <item1> <item2> - Compare two items in inventory
    - compare <item> - Compare item against currently equipped
    """
    args = args.strip()
    parts = args.split()

    if not parts:
        return "Compare what to what?"

    # Find first object (ROM C lines 2315-2319)
    obj1 = get_obj_carry(char, parts[0])
    if obj1 is None:
        return "You do not have that item."

    # Determine what to compare against (ROM C lines 2321-2342)
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

    # ROM C lines 2344-2381: Compare logic
    msg = None
    value1 = 0
    value2 = 0

    # CRITICAL GAP FIX 2: Same object check (ROM C lines 2348-2351)
    if obj1 is obj2:
        msg = "You compare $p to itself.  It looks about the same."
    # CRITICAL GAP FIX 3: Type mismatch check (ROM C lines 2352-2355)
    elif obj1.item_type != obj2.item_type:
        msg = "You can't compare $p and $P."
    else:
        # Compare based on item type (ROM C lines 2356-2381)
        if obj1.item_type == ItemType.ARMOR:
            # CRITICAL GAP FIX 4: Sum all 3 AC values (ROM C lines 2364-2367)
            value1 = obj1.value[0] + obj1.value[1] + obj1.value[2]
            value2 = obj2.value[0] + obj2.value[1] + obj2.value[2]
        elif obj1.item_type == ItemType.WEAPON:
            # CRITICAL GAP FIX 5: Check new_format flag, use ROM formula (ROM C lines 2369-2379)
            proto1 = getattr(obj1, "prototype", None) or getattr(obj1, "pIndexData", None)
            new_format1 = getattr(proto1, "new_format", True) if proto1 else True
            if new_format1:
                value1 = (1 + obj1.value[2]) * obj1.value[1]  # (1 + dice_type) * dice_num
            else:
                value1 = obj1.value[1] + obj1.value[2]  # dice_num + dice_type

            proto2 = getattr(obj2, "prototype", None) or getattr(obj2, "pIndexData", None)
            new_format2 = getattr(proto2, "new_format", True) if proto2 else True
            if new_format2:
                value2 = (1 + obj2.value[2]) * obj2.value[1]
            else:
                value2 = obj2.value[1] + obj2.value[2]
        else:
            # Default case (ROM C lines 2360-2362)
            msg = "You can't compare $p and $P."

    # ROM C lines 2383-2391: Determine message if not already set
    if msg is None:
        if value1 == value2:
            msg = "$p and $P look about the same."
        elif value1 > value2:
            msg = "$p looks better than $P."
        else:
            msg = "$p looks worse than $P."

    # CRITICAL GAP FIX 1: Use act() system with $p and $P placeholders (ROM C line 2393)
    return act_format(msg, recipient=char, actor=char, arg1=obj1, arg2=obj2)


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
