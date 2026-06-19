"""
Equipment commands for wear, wield, and hold.

ROM References: src/act_obj.c lines 1000-1500
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mud.handler import equip_char, unequip_char
from mud.models.constants import ExtraFlag, ItemType, Position, WearFlag, WearLocation
from mud.utils.act import act_to_room

if TYPE_CHECKING:
    from mud.models.character import Character
    from mud.models.object import Object


# ROM str_app wield column for STR 0..25.
# Source: src/const.c:728 str_app[26], fourth field (wield).
# Max wieldable weight = _STR_WIELD[STR] * 10 (ROM src/act_obj.c:1624-1625).
_STR_WIELD = (
    0,
    1,
    2,
    3,
    4,
    5,
    6,
    7,
    8,
    9,
    10,
    11,
    12,
    13,
    14,
    15,
    16,
    22,
    25,
    30,
    35,
    40,
    45,
    50,
    55,
    60,
)


def _str_wield_max(str_stat: int) -> int:
    """Return ROM str_app[STR].wield * 10 — the max wieldable weight."""
    idx = max(0, min(25, int(str_stat)))
    return _STR_WIELD[idx] * 10


def _broadcast_level_fail(ch: Character, obj: Object) -> None:
    """ROM act_obj.c:1410-1411 — emit TO_ROOM observer message for level-too-low."""
    room = getattr(ch, "room", None)
    # INV-025: act_to_room renders $n per-recipient (PERS masking) + dispatches
    # TRIG_ACT (ROM src/act_obj.c:1410, no MOBtrigger wrap).
    act_to_room(room, "$n tries to use $p, but is too inexperienced.", ch, arg1=obj, exclude=ch)


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
    # INV-039 / class-13: ROM src/act_obj.c:1386 obj_to_char(head-insert).
    add_obj = getattr(ch, "add_object", None)
    if callable(add_obj):
        add_obj(obj)
    else:
        inventory = getattr(ch, "inventory", [])
        if obj not in inventory:
            inventory.insert(0, obj)

    obj_name = getattr(obj, "short_descr", "something")
    char_msg = f"You stop using {obj_name}."

    room = getattr(ch, "room", None)
    # INV-025: act_to_room renders $n per-recipient (PERS masking) + dispatches
    # TRIG_ACT (ROM src/act_obj.c:1389, no MOBtrigger wrap).
    act_to_room(room, "$n stops using $p.", ch, arg1=obj, exclude=ch)
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

    # ROM `do_wear <item>` passes fReplace=TRUE — occupied slots are force-
    # replaced (src/act_obj.c:1699-1733 → wear_obj).
    return _wear_obj(ch, obj, fReplace=True)


def _wear_obj(ch: Character, obj: Object, fReplace: bool = True) -> str:
    """ROM `wear_obj(ch, obj, fReplace)` — src/act_obj.c:1401-1695.

    Shared wear/wield/hold dispatch for both `do_wear <item>` (fReplace=True,
    force-replace occupied slots) and `wear all` (fReplace=False, skip occupied
    slots silently). Returns the TO_CHAR message, or "" when the wear was skipped
    — an occupied slot under fReplace=False, or an unwearable item (ROM only
    emits "You can't wear, wield, or hold that." when fReplace is True, and
    `wear all` always passes False).

    WEAR-012 / FINDING-034: `wear all` previously reimplemented a *subset* of this
    dispatch and silently skipped lights, weapons, and HOLD items; routing it
    through this shared function (the same one the single-item path uses) is the
    ROM-faithful fix. The only effect of `fReplace` is per ROM `remove_obj`: an
    occupied slot aborts the wear (returns False) under fReplace=False instead of
    force-removing the existing item.
    """
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
        return _dispatch_wield(ch, obj, fReplace)

    # ROM src/act_obj.c:1415-1422 — wear_obj dispatches ITEM_LIGHT FIRST (before
    # any wear-flag branch) into the WEAR_LIGHT slot. INV-028: the worn-light slot
    # must be keyed consistently (int(WearLocation.LIGHT)) so room-light tracking
    # (Room._has_lit_light_source) and burnout decay (_find_equipped_light) both
    # see it. Pre-fix lights fell through to the HOLD branch and landed in HOLD.
    if item_type == ItemType.LIGHT:
        equipment = getattr(ch, "equipment", {})
        light_loc = int(WearLocation.LIGHT)

        if light_loc in equipment and equipment[light_loc] is not None:
            # ROM remove_obj(ch, WEAR_LIGHT, fReplace): fReplace=False → return
            # FALSE, wear_obj aborts silently (the wear-all skip).
            if not fReplace:
                return ""
            existing = equipment[light_loc]
            if not _unequip_to_inventory(ch, existing):
                existing_name = getattr(existing, "short_descr", "it")
                return f"You can't remove {existing_name}."

        # Alignment zap (mirrors the HOLD/wear paths' _can_wear_alignment block).
        can_wear, error_msg = _can_wear_alignment(ch, obj)
        if not can_wear:
            return error_msg or "You cannot hold that item."

        if not equipment:
            ch.equipment = {}
        ch.equipment[light_loc] = obj
        obj.worn_by = ch

        inventory = getattr(ch, "inventory", [])
        if obj in inventory:
            inventory.remove(obj)

        equip_char(ch, obj, light_loc)

        obj_name = getattr(obj, "short_descr", "something")
        room = getattr(ch, "room", None)
        # ROM src/act_obj.c:1419 — same messages even though slot is WEAR_LIGHT.
        # INV-025: act_to_room renders $n per-recipient (PERS masking) + dispatches TRIG_ACT.
        act_to_room(room, "$n lights $p and holds it.", ch, arg1=obj, exclude=ch)
        return f"You light {obj_name} and hold it."

    # ROM act_obj.c:1595-1614: SHIELD branch removes the existing shield FIRST
    # then performs the two-hand-weapon check. Implemented below after the
    # generic slot-remove (search "WEAR-009 SHIELD post-check").

    # Check if item has HOLD flag - if so, use hold logic (ROM lines 1670-1677)
    if wear_flags & WearFlag.HOLD:
        # Check if hold slot is occupied
        equipment = getattr(ch, "equipment", {})
        hold_loc = int(WearLocation.HOLD)

        if hold_loc in equipment and equipment[hold_loc] is not None:
            # ROM remove_obj(ch, WEAR_HOLD, fReplace): fReplace=False → skip.
            if not fReplace:
                return ""
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

        # ROM act_obj.c:1674 (HOLD branch). ITEM_LIGHT is handled earlier in
        # its own WEAR_LIGHT branch (see ROM 1415-1423 / INV-028), so it never
        # reaches here. ROM uses "$s hand" (gendered possessive), not "their".
        room = getattr(ch, "room", None)
        # INV-025: act_to_room renders $n per-recipient (PERS masking) + $s gendered
        # possessive + dispatches TRIG_ACT (ROM src/act_obj.c:1674, no MOBtrigger wrap).
        act_to_room(room, "$n holds $p in $s hand.", ch, arg1=obj, exclude=ch)
        return f"You hold {obj_name} in your hand."

    # Find appropriate wear location
    wear_loc = _get_wear_location(obj, wear_flags, ch)
    if not wear_loc:
        # No free slot. Under fReplace=False (wear all), ROM's wear_obj skips
        # silently — every multi-slot remove_obj returns FALSE — and an item
        # with no recognized wear flag falls through to the final
        # fReplace-gated "You can't wear, wield, or hold that." (no message).
        if not fReplace:
            return ""
        # Multi-slot items: all slots occupied. Try to make room.
        wear_loc = _try_replace_multislot(ch, wear_flags)
        if not wear_loc:
            return _multislot_full_message(wear_flags)

    wear_loc = int(wear_loc)

    # Check if slot is occupied
    equipment = getattr(ch, "equipment", {})
    if wear_loc in equipment and equipment[wear_loc] is not None:
        # ROM remove_obj(ch, wear_loc, fReplace): fReplace=False → skip silently.
        if not fReplace:
            return ""
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
    room = getattr(ch, "room", None)
    # INV-025: act_to_room renders $n/$s per-recipient (PERS masking) + dispatches
    # TRIG_ACT (ROM src/act_obj.c:1435-1612, no MOBtrigger wrap).
    act_to_room(room, room_template, ch, arg1=obj, exclude=ch)
    return char_template.format(obj_name=obj_name)


def do_wield(ch: Character, args: str) -> str:
    """ROM alias — `wield` and `wear` are the same command in ROM
    (src/interp.c:103, 232 both map to `do_wear`). The dispatcher
    registers `wield` as an alias on the `wear` Command; this thin
    wrapper preserves direct-import callers (tests, scripts).
    """
    return do_wear(ch, args)


def _dispatch_wield(ch: Character, obj: Object, fReplace: bool = True) -> str:
    """ROM `wear_obj` ITEM_WIELD branch — src/act_obj.c:1616-1668.

    Assumes caller has already verified position, level, and item_type.
    Handles slot-replace, STR check, alignment, two-hand/shield check,
    equip, and weapon-skill flavor. `fReplace` mirrors ROM `remove_obj`:
    when False (the `wear all` path) an occupied WIELD slot aborts the wield
    silently instead of force-removing the current weapon.
    """
    from mud.models.constants import Size, WeaponFlag

    equipment = getattr(ch, "equipment", {})
    wear_loc = WearLocation.WIELD

    if wear_loc in equipment and equipment[wear_loc] is not None:
        # ROM remove_obj(ch, WEAR_WIELD, fReplace): fReplace=False → skip silently.
        if not fReplace:
            return ""
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
    # ROM act_obj.c:1639 — TO_ROOM "$n wields $p."
    room = getattr(ch, "room", None)
    # INV-025: act_to_room renders $n per-recipient (PERS masking) + dispatches
    # TRIG_ACT (ROM src/act_obj.c:1639, no MOBtrigger wrap).
    act_to_room(room, "$n wields $p.", ch, arg1=obj, exclude=ch)

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
    """ROM alias — `hold` and `wear` are the same command in ROM
    (src/interp.c:215, 232 both map to `do_wear`). The dispatcher
    registers `hold` as an alias on the `wear` Command; this thin
    wrapper preserves direct-import callers (tests, scripts).
    """
    return do_wear(ch, args)


def _wear_all(ch: Character) -> str:
    """Wear/wield/hold every wearable carried item — ROM `do_wear` "all"
    (src/act_obj.c:1712-1723).

    ROM loops `ch->carrying`, and for each object with `wear_loc == WEAR_NONE`
    the character can see, calls `wear_obj(ch, obj, FALSE)` — the SAME dispatcher
    the single-item path uses, just with fReplace=FALSE so occupied slots are
    skipped silently. WEAR-012 / FINDING-034: the previous `_wear_all` was a
    parallel reimplementation that skipped lights, weapons, and HOLD items ROM
    equips. Routing every item through the shared `_wear_obj` is the fix — lights
    light+hold, weapons wield, HOLD items hold, exactly as `do_wear <item>` does.
    """
    from mud.world.vision import can_see_object

    inventory = getattr(ch, "inventory", [])
    if not inventory:
        return "You are not carrying anything."

    messages = []
    for obj in list(inventory):  # Copy: _wear_obj mutates inventory as it equips.
        # ROM act_obj.c:1716-1721 — only WEAR_NONE (not already worn) items the
        # character can see.
        if getattr(obj, "worn_by", None):
            continue
        if not can_see_object(ch, obj):
            continue

        # ROM `wear_obj(ch, obj, FALSE)` — fReplace=FALSE skips occupied slots
        # silently and suppresses the "You can't wear..." line; "" means skipped.
        message = _wear_obj(ch, obj, fReplace=False)
        if message:
            messages.append(message)

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
        int(WearLocation.WRIST_R): (
            "$n wears $p around $s right wrist.",
            "You wear {obj_name} around your right wrist.",
        ),
        int(WearLocation.SHIELD): ("$n wears $p as a shield.", "You wear {obj_name} as a shield."),
        int(WearLocation.FLOAT): (
            "$n releases $p to float next to $m.",
            "You release {obj_name} and it floats next to you.",
        ),
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
