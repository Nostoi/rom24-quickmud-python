"""
Equipment commands for wear, wield, and hold.

ROM References: src/act_obj.c lines 1000-1500
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mud.handler import equip_char, unequip_char
from mud.models.constants import ExtraFlag, ItemType, Position, WearFlag, WearLocation
from mud.net.protocol import broadcast_room
from mud.utils.act import act_format

if TYPE_CHECKING:
    from mud.models.character import Character
    from mud.models.object import Object


# ROM str_app wield column for STR 0..25.
# Source: src/const.c:728 str_app[26], fourth field (wield).
# Max wieldable weight = _STR_WIELD[STR] * 10 (ROM src/act_obj.c:1624-1625).
_STR_WIELD = (
    0,   1,  2,  3,  4,  5,  6,  7,  8,  9,
    10, 11, 12, 13, 14, 15, 16, 22, 25, 30,
    35, 40, 45, 50, 55, 60,
)


def _str_wield_max(str_stat: int) -> int:
    """Return ROM str_app[STR].wield * 10 — the max wieldable weight."""
    idx = max(0, min(25, int(str_stat)))
    return _STR_WIELD[idx] * 10


def _broadcast_level_fail(ch: Character, obj: Object) -> None:
    """ROM act_obj.c:1410-1411 — emit TO_ROOM observer message for level-too-low."""
    obj_name = getattr(obj, "short_descr", "something")
    ch_name = getattr(ch, "name", "Someone")
    broadcast_room(
        getattr(ch, "room", None),
        f"{ch_name} tries to use {obj_name}, but is too inexperienced.",
        exclude=ch,
    )


def _unequip_to_inventory(ch: Character, obj: Object) -> bool:
    """Remove an equipped object, returning it to inventory.

    ROM Reference: src/act_obj.c:1372-1392 (remove_obj)

    Returns True if the object was successfully removed, False if it
    couldn't be removed (e.g. ITEM_NOREMOVE). Also emits ROM-style
    removal messages to the character and room.
    """
    extra_flags = getattr(obj, "extra_flags", 0)
    if hasattr(extra_flags, "__class__") and not isinstance(extra_flags, int):
        extra_flags = int(extra_flags) if extra_flags else 0

    if extra_flags & ExtraFlag.NOREMOVE:
        # ROM act("You can't remove $p.", ch, obj, NULL, TO_CHAR);
        obj_name = getattr(obj, "short_descr", "it")
        if hasattr(ch, "send_to_char"):
            ch.send_to_char(f"You can't remove {obj_name}.")
        return False

    unequip_char(ch, obj)
    obj.worn_by = None
    inventory = getattr(ch, "inventory", [])
    if obj not in inventory:
        inventory.append(obj)

    obj_name = getattr(obj, "short_descr", "something")
    room_msg = f"{getattr(ch, 'name', 'Someone')} stops using {obj_name}."
    char_msg = f"You stop using {obj_name}."

    broadcast_room(getattr(ch, "room", None), room_msg, exclude=ch)
    if hasattr(ch, "send_to_char"):
        ch.send_to_char(char_msg)

    return True


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
        _broadcast_level_fail(ch, obj)
        return f"You must be level {obj_level} to use this object."

    # Determine where this can be worn (read from prototype)
    wear_flags = getattr(obj.prototype, "wear_flags", 0)
    wear_flags = int(wear_flags) if wear_flags else 0
    item_type_str = getattr(obj.prototype, "item_type", None)
    item_type = int(item_type_str) if item_type_str else ItemType.TRASH

    # ROM src/act_obj.c:1616-1668 — `wear_obj` dispatches ITEM_WIELD to the
    # WIELD branch. ROM cmd_table maps "wear", "wield", "hold" all to
    # `do_wear`, so `wear sword` and `wield sword` are identical.
    if item_type == ItemType.WEAPON:
        return _dispatch_wield(ch, obj)

    # ROM act_obj.c:1595-1614: SHIELD branch removes the existing shield FIRST
    # then performs the two-hand-weapon check. Implemented below after the
    # generic slot-remove (search "WEAR-009 SHIELD post-check").

    # Check if item has HOLD flag - if so, use hold logic (ROM lines 1670-1677)
    if wear_flags & WearFlag.HOLD:
        # Check if hold slot is occupied
        equipment = getattr(ch, "equipment", {})
        hold_loc = int(WearLocation.HOLD)

        if hold_loc in equipment and equipment[hold_loc] is not None:
            existing = equipment[hold_loc]
            if not _unequip_to_inventory(ch, existing):
                existing_name = getattr(existing, "short_descr", "it")
                return f"You can't remove {existing_name}."

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
        ch_name = getattr(ch, "name", "Someone")

        # ROM act_obj.c:1415-1423 (LIGHT branch) vs 1670-1677 (HOLD branch).
        if item_type == ItemType.LIGHT:
            broadcast_room(
                getattr(ch, "room", None),
                f"{ch_name} lights {obj_name} and holds it.",
                exclude=ch,
            )
            return f"You light {obj_name} and hold it."

        broadcast_room(
            getattr(ch, "room", None),
            f"{ch_name} holds {obj_name} in their hand.",
            exclude=ch,
        )
        return f"You hold {obj_name} in your hand."

    # Find appropriate wear location
    wear_loc = _get_wear_location(obj, wear_flags, ch)
    if not wear_loc:
        # Multi-slot items: all slots occupied. Try to make room.
        wear_loc = _try_replace_multislot(ch, wear_flags)
        if not wear_loc:
            return _multislot_full_message(wear_flags)

    wear_loc = int(wear_loc)

    # Check if slot is occupied
    equipment = getattr(ch, "equipment", {})
    if wear_loc in equipment and equipment[wear_loc] is not None:
        existing = equipment[wear_loc]
        if not _unequip_to_inventory(ch, existing):
            # _unequip_to_inventory already emits "You can't remove $p." via ch.send.
            # Returning empty string avoids ROM-divergent duplicate output.
            return ""

    # WEAR-009 SHIELD post-check: ROM src/act_obj.c:1602-1608 — after the
    # existing shield has been removed, refuse if the wielded weapon is
    # two-handed and the wearer is smaller than SIZE_LARGE. ROM intentionally
    # leaves the player shieldless in this case; we mirror that.
    if wear_loc == int(WearLocation.SHIELD):
        from mud.models.constants import Size, WeaponFlag

        wield_loc = int(WearLocation.WIELD)
        weapon = equipment.get(wield_loc) if equipment else None
        if weapon is not None:
            weapon_flags = getattr(weapon.prototype, "value", [0, 0, 0, 0, 0])
            ch_size = int(getattr(ch, "size", 0) or 0)
            if len(weapon_flags) > 4 and ch_size < int(Size.LARGE):
                if weapon_flags[4] & WeaponFlag.TWO_HANDS:
                    return "Your hands are tied up with your weapon!"

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

    # ROM-style location-specific messages (src/act_obj.c:1435-1612)
    obj_name = getattr(obj, "short_descr", "something")
    room_template, char_template = _wear_location_messages(wear_loc)
    room_message = act_format(room_template, recipient=None, actor=ch, arg1=obj, arg2=None)
    broadcast_room(getattr(ch, "room", None), room_message, exclude=ch)
    return char_template.format(obj_name=obj_name)


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
        _broadcast_level_fail(ch, obj)
        return f"You must be level {obj_level} to use this object."

    # Check if it's a weapon (read from prototype)
    item_type_str = getattr(obj.prototype, "item_type", None)
    item_type = int(item_type_str) if item_type_str else ItemType.TRASH
    if item_type != ItemType.WEAPON:
        return "You can't wield that."

    return _dispatch_wield(ch, obj)


def _dispatch_wield(ch: Character, obj: Object) -> str:
    """ROM `wear_obj` ITEM_WIELD branch — src/act_obj.c:1616-1668.

    Assumes caller has already verified position, level, and item_type.
    Handles slot-replace, STR check, alignment, two-hand/shield check,
    equip, and weapon-skill flavor.
    """
    from mud.models.constants import Size, WeaponFlag

    equipment = getattr(ch, "equipment", {})
    wear_loc = WearLocation.WIELD

    if wear_loc in equipment and equipment[wear_loc] is not None:
        existing = equipment[wear_loc]
        if not _unequip_to_inventory(ch, existing):
            return ""

    # ROM src/act_obj.c:1623-1629 — strength check skipped for NPCs.
    is_npc = bool(getattr(ch, "is_npc", False))
    if not is_npc:
        weight = getattr(obj.prototype, "weight", 0)
        str_stat = 13
        if hasattr(ch, "get_curr_stat"):
            from mud.models.constants import Stat

            stat_value = ch.get_curr_stat(Stat.STR)
            if stat_value is not None:
                str_stat = stat_value
        if weight > _str_wield_max(str_stat):
            return "It is too heavy for you to wield."

    can_wield, error_msg = _can_wear_alignment(ch, obj)
    if not can_wield:
        return error_msg or "You cannot wield that weapon."

    # ROM src/act_obj.c:1631-1636 — two-hand vs shield check skipped for NPCs
    # and for characters of SIZE_LARGE or greater.
    weapon_flags = getattr(obj.prototype, "value", [0, 0, 0, 0, 0])
    ch_size = int(getattr(ch, "size", 0) or 0)
    if not is_npc and ch_size < int(Size.LARGE) and len(weapon_flags) > 4:
        if weapon_flags[4] & WeaponFlag.TWO_HANDS:
            shield_loc = int(WearLocation.SHIELD)
            if shield_loc in equipment and equipment[shield_loc] is not None:
                return "You need two hands free for that weapon!"

    if not equipment:
        ch.equipment = {}
    ch.equipment[wear_loc] = obj
    obj.worn_by = ch

    inventory = getattr(ch, "inventory", [])
    if obj in inventory:
        inventory.remove(obj)

    equip_char(ch, obj, wear_loc)

    obj_name = getattr(obj, "short_descr", "something")
    ch_name = getattr(ch, "name", "Someone")
    # ROM act_obj.c:1639 — TO_ROOM "$n wields $p."
    broadcast_room(getattr(ch, "room", None), f"{ch_name} wields {obj_name}.", exclude=ch)

    # ROM act_obj.c:1643-1665 — weapon-skill flavor (skip for hand-to-hand).
    flavor = _weapon_skill_flavor(ch, obj)
    if flavor:
        return f"You wield {obj_name}.\n{flavor}"
    return f"You wield {obj_name}."


def _weapon_skill_flavor(ch: Character, obj: Object) -> str | None:
    """ROM act_obj.c:1643-1665 — seven-tier weapon-skill flavor on wield."""
    from mud.combat.engine import HAND_TO_HAND_SKILL, get_weapon_skill, get_weapon_sn

    sn = get_weapon_sn(ch, obj)
    if sn is None or sn == HAND_TO_HAND_SKILL:
        return None
    skill = get_weapon_skill(ch, sn)
    obj_name = getattr(obj, "short_descr", "it")
    if skill >= 100:
        return f"{obj_name} feels like a part of you!"
    if skill > 85:
        return f"You feel quite confident with {obj_name}."
    if skill > 70:
        return f"You are skilled with {obj_name}."
    if skill > 50:
        return f"Your skill with {obj_name} is adequate."
    if skill > 25:
        return f"{obj_name} feels a little clumsy in your hands."
    if skill > 1:
        return f"You fumble and almost drop {obj_name}."
    return f"You don't even know which end is up on {obj_name}."


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
        _broadcast_level_fail(ch, obj)
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
    ch_name = getattr(ch, "name", "Someone")

    # ROM act_obj.c:1415-1423 (LIGHT) vs 1670-1677 (HOLD).
    item_type_str = getattr(obj.prototype, "item_type", None)
    item_type = int(item_type_str) if item_type_str else ItemType.TRASH
    if item_type == ItemType.LIGHT:
        broadcast_room(
            getattr(ch, "room", None),
            f"{ch_name} lights {obj_name} and holds it.",
            exclude=ch,
        )
        return f"You light {obj_name} and hold it."

    broadcast_room(
        getattr(ch, "room", None),
        f"{ch_name} holds {obj_name} in their hand.",
        exclude=ch,
    )
    return f"You hold {obj_name} in your hand."


def _wear_all(ch: Character) -> str:
    """Wear all wearable items in inventory.

    ROM Reference: src/act_obj.c:1716-1721 — only iterate `wear_loc == WEAR_NONE`
    items the character can see (`can_see_obj`).
    """
    from mud.world.vision import can_see_object

    inventory = getattr(ch, "inventory", [])
    if not inventory:
        return "You are not carrying anything."

    messages = []
    for obj in list(inventory):  # Copy list since we modify it
        # Skip already worn items
        if getattr(obj, "worn_by", None):
            continue
        # ROM act_obj.c:1719 — skip items the character can't see.
        if not can_see_object(ch, obj):
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
        room_template, char_template = _wear_location_messages(int(wear_loc))
        room_message = act_format(room_template, recipient=None, actor=ch, arg1=obj, arg2=None)
        broadcast_room(getattr(ch, "room", None), room_message, exclude=ch)
        messages.append(char_template.format(obj_name=obj_name))

    if not messages:
        return "You have nothing else to wear."

    return "\n".join(messages)



def _wear_location_messages(wear_loc: int) -> tuple[str, str]:
    """ROM wear messages for standard armor/accessory slots.

    ROM Reference: src/act_obj.c:1435-1612 (wear_obj act() messages)
    """
    mapping = {
        int(WearLocation.FINGER_L): ("$n wears $p on $s left finger.", "You wear {obj_name} on your left finger."),
        int(WearLocation.FINGER_R): ("$n wears $p on $s right finger.", "You wear {obj_name} on your right finger."),
        int(WearLocation.NECK_1): ("$n wears $p around $s neck.", "You wear {obj_name} around your neck."),
        int(WearLocation.NECK_2): ("$n wears $p around $s neck.", "You wear {obj_name} around your neck."),
        int(WearLocation.BODY): ("$n wears $p on $s torso.", "You wear {obj_name} on your torso."),
        int(WearLocation.HEAD): ("$n wears $p on $s head.", "You wear {obj_name} on your head."),
        int(WearLocation.LEGS): ("$n wears $p on $s legs.", "You wear {obj_name} on your legs."),
        int(WearLocation.FEET): ("$n wears $p on $s feet.", "You wear {obj_name} on your feet."),
        int(WearLocation.HANDS): ("$n wears $p on $s hands.", "You wear {obj_name} on your hands."),
        int(WearLocation.ARMS): ("$n wears $p on $s arms.", "You wear {obj_name} on your arms."),
        int(WearLocation.ABOUT): ("$n wears $p about $s torso.", "You wear {obj_name} about your torso."),
        int(WearLocation.WAIST): ("$n wears $p about $s waist.", "You wear {obj_name} about your waist."),
        int(WearLocation.WRIST_L): ("$n wears $p around $s left wrist.", "You wear {obj_name} around your left wrist."),
        int(WearLocation.WRIST_R): ("$n wears $p around $s right wrist.", "You wear {obj_name} around your right wrist."),
        int(WearLocation.SHIELD): ("$n wears $p as a shield.", "You wear {obj_name} as a shield."),
        int(WearLocation.FLOAT): ("$n releases $p to float next to $m.", "You release {obj_name} and it floats next to you."),
    }
    return mapping.get(wear_loc, ("$n wears $p.", "You wear {obj_name}."))


def _try_replace_multislot(ch: Character, wear_flags: int) -> WearLocation | None:
    """Try to make room on an occupied multi-slot by removing one item.

    ROM Reference: src/act_obj.c:1427-1431 (finger), 1456-1460 (neck), 1565-1569 (wrist)

    For finger/neck/wrist slots where both are occupied, try to remove an
    existing item to make room. Returns the newly freed slot, or None if
    both slots are locked (NOREMOVE).
    """
    equipment = getattr(ch, "equipment", {}) or {}

    if wear_flags & WearFlag.WEAR_FINGER:
        slots = [int(WearLocation.FINGER_L), int(WearLocation.FINGER_R)]
    elif wear_flags & WearFlag.WEAR_NECK:
        slots = [int(WearLocation.NECK_1), int(WearLocation.NECK_2)]
    elif wear_flags & WearFlag.WEAR_WRIST:
        slots = [int(WearLocation.WRIST_L), int(WearLocation.WRIST_R)]
    else:
        return None

    for slot in slots:
        existing = equipment.get(slot)
        if existing is not None:
            if _unequip_to_inventory(ch, existing):
                return WearLocation(slot)
    return None


def _multislot_full_message(wear_flags: int) -> str:
    """ROM-style error message when all multi-slot locations are full."""
    if wear_flags & WearFlag.WEAR_FINGER:
        return "You already wear two rings."
    if wear_flags & WearFlag.WEAR_NECK:
        return "You already wear two neck items."
    if wear_flags & WearFlag.WEAR_WRIST:
        return "You already wear two wrist items."
    return "You can't wear that."


def _get_wear_location(obj: Object, wear_flags: int, ch: Character | None = None) -> WearLocation | None:
    """
    Determine which slot an item should be worn in.

    ROM Reference: src/act_obj.c:wear_obj() lines 1425-1670

    For multi-slot items (rings, neck, wrists), checks which slots are occupied
    and returns the first available slot.
    """
    equipment = getattr(ch, "equipment", {}) if ch else {}

    def slot_free(loc: int) -> bool:
        return loc not in equipment or equipment.get(loc) is None

    if wear_flags & WearFlag.WEAR_FINGER:
        if slot_free(int(WearLocation.FINGER_L)):
            return WearLocation.FINGER_L
        if slot_free(int(WearLocation.FINGER_R)):
            return WearLocation.FINGER_R
        return None

    if wear_flags & WearFlag.WEAR_NECK:
        if slot_free(int(WearLocation.NECK_1)):
            return WearLocation.NECK_1
        if slot_free(int(WearLocation.NECK_2)):
            return WearLocation.NECK_2
        return None

    if wear_flags & WearFlag.WEAR_WRIST:
        if slot_free(int(WearLocation.WRIST_L)):
            return WearLocation.WRIST_L
        if slot_free(int(WearLocation.WRIST_R)):
            return WearLocation.WRIST_R
        return None

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
