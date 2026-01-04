"""
Equipment commands for wear, wield, and hold.

ROM References: src/act_obj.c lines 1000-1500
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mud.handler import equip_char, unequip_char
from mud.models.constants import ExtraFlag, ItemType, Position, WearFlag, WearLocation

if TYPE_CHECKING:
    from mud.models.character import Character
    from mud.models.object import Object


def _can_wear_alignment(ch: Character, obj: Object) -> tuple[bool, str | None]:
    """
    Check if character's alignment allows wearing this item.

    ROM Reference: src/handler.c:1765-1777 (equip_char)

    Returns:
        (can_wear, error_message) - (True, None) if allowed, (False, error_msg) if blocked
    """
    extra_flags = getattr(obj, "extra_flags", 0)
    alignment = getattr(ch, "alignment", 0)

    # ROM alignment thresholds (src/merc.h:2099-2101):
    # IS_GOOD(ch)    -> alignment >= 350
    # IS_EVIL(ch)    -> alignment <= -350
    # IS_NEUTRAL(ch) -> -350 < alignment < 350

    # Check ANTI_EVIL: if item is anti-evil and character is evil
    if (extra_flags & ExtraFlag.ANTI_EVIL) and alignment <= -350:
        return False, "You are zapped by the item and drop it."

    # Check ANTI_GOOD: if item is anti-good and character is good
    if (extra_flags & ExtraFlag.ANTI_GOOD) and alignment >= 350:
        return False, "You are zapped by the item and drop it."

    # Check ANTI_NEUTRAL: if item is anti-neutral and character is neutral
    if (extra_flags & ExtraFlag.ANTI_NEUTRAL) and (-350 < alignment < 350):
        return False, "You are zapped by the item and drop it."

    return True, None


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

    # Check level restriction (ROM src/act_obj.c:1405-1413)
    obj_level = getattr(obj.prototype, "level", 0)
    char_level = getattr(ch, "level", 1)
    if char_level < obj_level:
        return f"You must be level {obj_level} to use this object."

    # Determine where this can be worn (read from prototype)
    wear_flags = getattr(obj.prototype, "wear_flags", 0)
    wear_flags = int(wear_flags) if wear_flags else 0
    item_type_str = getattr(obj.prototype, "item_type", None)
    item_type = int(item_type_str) if item_type_str else ItemType.TRASH

    if item_type == ItemType.WEAPON:
        return "You need to wield weapons, not wear them."

    if wear_flags & WearFlag.WEAR_SHIELD:
        from mud.models.constants import WeaponFlag

        equipment = getattr(ch, "equipment", {})
        wield_loc = int(WearLocation.WIELD)
        if wield_loc in equipment and equipment[wield_loc] is not None:
            weapon = equipment[wield_loc]
            weapon_flags = getattr(weapon.prototype, "value", [0, 0, 0, 0, 0])
            if len(weapon_flags) > 4:
                weapon_flag_val = weapon_flags[4]
                if weapon_flag_val & WeaponFlag.TWO_HANDS:
                    return "Your hands are tied up with your weapon!"

    # Check if item has HOLD flag - if so, use hold logic (ROM lines 1670-1677)
    if wear_flags & WearFlag.HOLD:
        # Check if hold slot is occupied
        equipment = getattr(ch, "equipment", {})
        hold_loc = int(WearLocation.HOLD)

        if hold_loc in equipment and equipment[hold_loc] is not None:
            existing = equipment[hold_loc]
            existing_name = getattr(existing, "short_descr", "something")
            return f"You're already holding {existing_name}."

        # Check alignment restrictions
        can_hold, error_msg = _can_wear_alignment(ch, obj)
        if not can_hold:
            return error_msg or "You cannot hold that item."

        # Hold the item
        if not equipment:
            ch.equipment = {}
        ch.equipment[hold_loc] = obj
        obj.worn_by = ch

        # Remove from inventory
        inventory = getattr(ch, "inventory", [])
        if obj in inventory:
            inventory.remove(obj)

        # Apply equipment bonuses
        equip_char(ch, obj, hold_loc)

        obj_name = getattr(obj, "short_descr", "something")

        # Special message for lights (ROM src/act_obj.c:1676)
        if item_type == ItemType.LIGHT:
            return f"You hold {obj_name} as your light."

        return f"You hold {obj_name} in your hand."

    # Find appropriate wear location
    wear_loc = _get_wear_location(obj, wear_flags, ch)
    if not wear_loc:
        return "You can't wear that."

    # Check if slot is occupied
    equipment = getattr(ch, "equipment", {})
    if wear_loc in equipment and equipment[wear_loc] is not None:
        existing = equipment[wear_loc]
        existing_name = getattr(existing, "short_descr", "something")
        return f"You're already wearing {existing_name}."

    # Check alignment restrictions (ROM src/handler.c:1765-1777)
    can_wear, error_msg = _can_wear_alignment(ch, obj)
    if not can_wear:
        # In ROM, the zap happens in equip_char and item drops to room
        # For now, just prevent wearing with error message
        return error_msg or "You cannot wear that item."

    # Wear the item
    if not equipment:
        ch.equipment = {}
    ch.equipment[wear_loc] = obj
    obj.worn_by = ch

    # Remove from inventory
    inventory = getattr(ch, "inventory", [])
    if obj in inventory:
        inventory.remove(obj)

    # Apply equipment bonuses (ROM src/handler.c:equip_char)
    equip_char(ch, obj, wear_loc)

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

    # Check level restriction (ROM src/act_obj.c:1405-1413)
    obj_level = getattr(obj.prototype, "level", 0)
    char_level = getattr(ch, "level", 1)
    if char_level < obj_level:
        return f"You must be level {obj_level} to use this object."

    # Check if it's a weapon (read from prototype)
    item_type_str = getattr(obj.prototype, "item_type", None)
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
    weight = getattr(obj.prototype, "weight", 0)

    # Get character strength (default to 13 if stat system not available)
    str_stat = 13
    if hasattr(ch, "get_curr_stat"):
        from mud.models.constants import Stat

        stat_value = ch.get_curr_stat(Stat.STR)
        if stat_value is not None:
            str_stat = stat_value

    # ROM formula: need STR >= weight / 10
    if str_stat * 10 < weight:
        return "It is too heavy for you to wield."

    # Check alignment restrictions (ROM src/handler.c:1765-1777)
    can_wield, error_msg = _can_wear_alignment(ch, obj)
    if not can_wield:
        return error_msg or "You cannot wield that weapon."

    from mud.models.constants import WeaponFlag

    weapon_flags = getattr(obj.prototype, "value", [0, 0, 0, 0, 0])
    if len(weapon_flags) > 4:
        weapon_flag_val = weapon_flags[4]
        if weapon_flag_val & WeaponFlag.TWO_HANDS:
            shield_loc = int(WearLocation.SHIELD)
            if shield_loc in equipment and equipment[shield_loc] is not None:
                return "You need two hands free for that weapon!"

    # Wield the weapon
    if not equipment:
        ch.equipment = {}
    ch.equipment[wear_loc] = obj
    obj.worn_by = ch

    # Remove from inventory
    inventory = getattr(ch, "inventory", [])
    if obj in inventory:
        inventory.remove(obj)

    # Apply equipment bonuses (ROM src/handler.c:equip_char)
    equip_char(ch, obj, wear_loc)

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

    # Check level restriction (ROM src/act_obj.c:1405-1413)
    obj_level = getattr(obj.prototype, "level", 0)
    char_level = getattr(ch, "level", 1)
    if char_level < obj_level:
        return f"You must be level {obj_level} to use this object."

    # Check if it can be held (read from prototype)
    wear_flags = getattr(obj.prototype, "wear_flags", 0)
    wear_flags = int(wear_flags) if wear_flags else 0  # Convert string to int if needed
    if not (wear_flags & WearFlag.HOLD):
        return "You can't hold that."

    # Check if hold slot is occupied
    equipment = getattr(ch, "equipment", {})
    wear_loc = WearLocation.HOLD

    if wear_loc in equipment and equipment[wear_loc] is not None:
        existing = equipment[wear_loc]
        existing_name = getattr(existing, "short_descr", "something")
        return f"You're already holding {existing_name}."

    # Check alignment restrictions (ROM src/handler.c:1765-1777)
    can_hold, error_msg = _can_wear_alignment(ch, obj)
    if not can_hold:
        return error_msg or "You cannot hold that item."

    # Hold the item
    if not equipment:
        ch.equipment = {}
    ch.equipment[wear_loc] = obj
    obj.worn_by = ch

    # Remove from inventory
    inventory = getattr(ch, "inventory", [])
    if obj in inventory:
        inventory.remove(obj)

    # Apply equipment bonuses (ROM src/handler.c:equip_char)
    equip_char(ch, obj, wear_loc)

    obj_name = getattr(obj, "short_descr", "something")

    # Special message for lights (read from prototype)
    item_type_str = getattr(obj.prototype, "item_type", None)
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

        # Skip weapons and held items (read from prototype)
        item_type_str = getattr(obj.prototype, "item_type", None)
        item_type = int(item_type_str) if item_type_str else ItemType.TRASH
        wear_flags = getattr(obj.prototype, "wear_flags", 0)
        wear_flags = int(wear_flags) if wear_flags else 0  # Convert string to int if needed

        if item_type == ItemType.WEAPON:
            continue
        if wear_flags & WearFlag.HOLD:
            continue

        # Try to wear it
        wear_loc = _get_wear_location(obj, wear_flags, ch)
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
        inventory.remove(obj)

        # Apply equipment bonuses (ROM src/handler.c:equip_char)
        equip_char(ch, obj, wear_loc)

        obj_name = getattr(obj, "short_descr", "something")
        messages.append(f"You wear {obj_name}.")

    if not messages:
        return "You have nothing else to wear."

    return "\n".join(messages)


def _get_wear_location(obj: Object, wear_flags: int, ch: Character | None = None) -> WearLocation | None:
    """
    Determine which slot an item should be worn in.

    ROM Reference: src/act_obj.c:wear_obj() lines 1425-1670

    For multi-slot items (rings, neck, wrists), checks which slots are occupied
    and returns the first available slot.
    """
    equipment = getattr(ch, "equipment", {}) if ch else {}

    # Priority order for wear locations (from ROM)
    # Check WearFlag bits and return corresponding WearLocation slot

    # Multi-slot: Finger (FINGER_L, FINGER_R)
    if wear_flags & WearFlag.WEAR_FINGER:
        if int(WearLocation.FINGER_L) not in equipment:
            return WearLocation.FINGER_L
        if int(WearLocation.FINGER_R) not in equipment:
            return WearLocation.FINGER_R
        return None  # Both slots occupied

    # Multi-slot: Neck (NECK_1, NECK_2)
    if wear_flags & WearFlag.WEAR_NECK:
        if int(WearLocation.NECK_1) not in equipment:
            return WearLocation.NECK_1
        if int(WearLocation.NECK_2) not in equipment:
            return WearLocation.NECK_2
        return None  # Both slots occupied

    # Multi-slot: Wrist (WRIST_L, WRIST_R)
    if wear_flags & WearFlag.WEAR_WRIST:
        if int(WearLocation.WRIST_L) not in equipment:
            return WearLocation.WRIST_L
        if int(WearLocation.WRIST_R) not in equipment:
            return WearLocation.WRIST_R
        return None  # Both slots occupied

    # Single-slot items
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
