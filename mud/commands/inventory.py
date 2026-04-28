from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from mud.ai import _can_loot
from mud.commands.group_commands import do_split, is_same_group
from mud.commands.obj_manipulation import CONT_CLOSED, _can_drop_obj, _obj_from_char, get_obj_list
from mud.handler import create_money
from mud.models.character import Character
from mud.models.constants import (
    OBJ_VNUM_COINS,
    OBJ_VNUM_GOLD_ONE,
    OBJ_VNUM_GOLD_SOME,
    OBJ_VNUM_MAP,
    OBJ_VNUM_PIT,
    OBJ_VNUM_SCHOOL_BANNER,
    OBJ_VNUM_SCHOOL_SHIELD,
    OBJ_VNUM_SCHOOL_SWORD,
    OBJ_VNUM_SCHOOL_VEST,
    OBJ_VNUM_SILVER_ONE,
    OBJ_VNUM_SILVER_SOME,
    AffectFlag,
    CommFlag,
    ExtraFlag,
    ItemType,
    PlayerFlag,
    WeaponFlag,
    WearFlag,
)
from mud.net.protocol import broadcast_room
from mud.spawning.obj_spawner import spawn_object
from mud.utils.act import act_format
from mud.world.movement import can_carry_n, can_carry_w, get_carry_weight
from mud.world.obj_find import get_obj_carry, get_obj_here
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


def _one_argument(argument: str) -> tuple[str, str]:
    """
    Extract one argument from a string, ROM-style.

    ROM Reference: src/handler.c one_argument

    Returns:
        tuple[arg, rest]: First word and remaining string

    Example:
        >>> _one_argument("sword from chest")
        ("sword", "from chest")
    """
    argument = argument.strip()
    if not argument:
        return ("", "")

    parts = argument.split(None, 1)
    if len(parts) == 1:
        return (parts[0], "")
    return (parts[0], parts[1])


def _is_name(name: str, keywords: str) -> bool:
    """
    Check if name matches any keyword in space-separated keyword list.

    ROM Reference: src/handler.c is_name

    Args:
        name: Name to search for
        keywords: Space-separated list of keywords

    Returns:
        True if name matches any keyword
    """
    name_lower = name.lower()
    for keyword in keywords.lower().split():
        if name_lower == keyword or name_lower in keyword:
            return True
    return False


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


def _get_obj(char: Character, obj: object, container: object | None) -> str | None:
    """
    Helper function to get an object (ROM C get_obj helper).

    ROM Reference: src/act_obj.c get_obj (lines 92-193)

    Args:
        char: Character getting the object
        obj: Object to get
        container: Container object came from (None if from room)

    Returns:
        Error message if failed, None if successful
    """
    # ROM C line 99-103: Check ITEM_TAKE flag.
    # Corpses (PC and NPC) always have ITEM_TAKE set by `make_corpse`
    # (mud/combat/death.py:426); accept either the prototype flag or the
    # well-known corpse item types so manually constructed test corpses still
    # behave like ROM corpses.
    proto = getattr(obj, "prototype", None) or obj
    wear_flags = int(getattr(proto, "wear_flags", 0) or 0)
    inst_wear_flags = int(getattr(obj, "wear_flags", 0) or 0)
    raw_item_type = getattr(obj, "item_type", None) or getattr(proto, "item_type", None)
    try:
        item_type_int = int(raw_item_type) if raw_item_type is not None else None
    except (TypeError, ValueError):
        item_type_int = None
    is_corpse = item_type_int in (int(ItemType.CORPSE_PC), int(ItemType.CORPSE_NPC))
    if not is_corpse and not ((wear_flags | inst_wear_flags) & int(WearFlag.TAKE)):
        return "You can't take that."

    # ROM C lines 105-110: Encumbrance check (carry_number)
    obj_number = _get_obj_number(obj)
    if char.carry_number + obj_number > can_carry_n(char):
        obj_name = getattr(obj, "name", "object")
        return f"{obj_name}: you can't carry that many items."

    # ROM C lines 112-118: Weight check (carry_weight)
    obj_weight = _get_obj_weight(obj)
    # ROM C: Skip weight check if object already carried in container
    obj_in_obj = getattr(obj, "in_obj", None)
    obj_in_obj_carried_by = getattr(obj_in_obj, "carried_by", None) if obj_in_obj else None
    skip_weight_check = obj_in_obj_carried_by == char

    if not skip_weight_check and (get_carry_weight(char) + obj_weight > can_carry_w(char)):
        obj_name = getattr(obj, "name", "object")
        return f"{obj_name}: you can't carry that much weight."

    # ROM C lines 120-124: can_loot() check
    if not _can_loot(char, obj):
        return "Corpse looting is not permitted."

    # ROM C lines 126-134: Furniture occupancy check
    obj_location = getattr(obj, "location", None)
    if obj_location:
        room = getattr(char, "room", None)
        if room:
            for gch in getattr(room, "people", []):
                gch_on = getattr(gch, "on", None)
                if gch_on == obj:
                    gch_name = getattr(gch, "name", "Someone")
                    obj_short = getattr(obj, "short_descr", "it")
                    return f"{gch_name} appears to be using {obj_short}."

    # ROM C lines 137-154: Container extraction logic
    if container:
        # ROM C lines 139-144: Pit level check
        container_proto = getattr(container, "prototype", None) or container
        container_vnum = int(getattr(container_proto, "vnum", 0) or 0)

        if container_vnum == OBJ_VNUM_PIT:
            char_trust = int(getattr(char, "trust", 0) or getattr(char, "level", 0) or 0)
            obj_level = int(getattr(obj, "level", 0) or 0)
            if char_trust < obj_level:
                return "You are not powerful enough to use it."

        # ROM C lines 146-149, 152: Pit timer handling (ITEM_HAD_TIMER flag)
        container_proto = getattr(container, "prototype", None) or container
        container_vnum = int(getattr(container_proto, "vnum", 0) or 0)
        container_wear_flags = int(getattr(container_proto, "wear_flags", 0) or 0)
        can_wear_take = container_wear_flags & int(WearFlag.TAKE)

        # ROM C line 146-149: If pit donation box (!TAKE) and object doesn't have HAD_TIMER, set timer to 0
        if container_vnum == OBJ_VNUM_PIT and not can_wear_take:
            obj_extra_flags = int(getattr(obj, "extra_flags", 0) or 0)
            has_had_timer = obj_extra_flags & int(ExtraFlag.HAD_TIMER)
            if not has_had_timer:
                obj.timer = 0

        # ROM C lines 150-153: Container get messages
        obj_short = getattr(obj, "short_descr", "something")
        container_short = getattr(container, "short_descr", "something")

        # ROM C line 151: act("$n gets $p from $P.", ch, obj, container, TO_ROOM)
        room = getattr(char, "room", None)
        if room:
            room_message = act_format("$n gets $p from $P.", recipient=None, actor=char, arg1=obj, arg2=container)
            broadcast_room(room, room_message, exclude=char)

        # Remove from container
        if hasattr(container, "contained_items"):
            container_items = getattr(container, "contained_items", [])
            if obj in container_items:
                container_items.remove(obj)

        # ROM C line 152: REMOVE_BIT(obj->extra_flags, ITEM_HAD_TIMER)
        obj_extra_flags = int(getattr(obj, "extra_flags", 0) or 0)
        obj.extra_flags = obj_extra_flags & ~int(ExtraFlag.HAD_TIMER)

        message = f"You get {obj_short} from {container_short}."
    else:
        # ROM C lines 155-160: Room extraction logic
        obj_short = getattr(obj, "short_descr", "something")

        # ROM C line 158: act("$n gets $p.", ch, obj, container, TO_ROOM)
        room = getattr(char, "room", None)
        if room:
            room_message = act_format("$n gets $p.", recipient=None, actor=char, arg1=obj, arg2=None)
            broadcast_room(room, room_message, exclude=char)

        # Remove from room
        room = getattr(char, "room", None)
        if room and hasattr(room, "contents"):
            room_contents = getattr(room, "contents", [])
            if obj in room_contents:
                room_contents.remove(obj)

        message = f"You get {obj_short}."

    # ROM C lines 162-184: AUTOSPLIT for ITEM_MONEY
    proto = getattr(obj, "prototype", None) or obj
    raw_item_type = getattr(proto, "item_type", 0) or 0
    try:
        item_type = int(raw_item_type)
    except (TypeError, ValueError):
        # Some loaders/tests store item_type as the ROM keyword string ("trash",
        # "weapon", etc.). Resolve via the ItemType lookup table or skip the
        # AUTOSPLIT path if unrecognized.
        item_type = ItemType.from_name(raw_item_type) if hasattr(ItemType, "from_name") else 0
        if not isinstance(item_type, int):
            try:
                item_type = int(item_type)
            except (TypeError, ValueError):
                item_type = 0
    if item_type == int(ItemType.MONEY):
        obj_value = getattr(obj, "value", [0, 0, 0, 0, 0])
        silver = int(obj_value[0]) if len(obj_value) > 0 else 0
        gold = int(obj_value[1]) if len(obj_value) > 1 else 0

        # Add to character's currency
        char.silver = getattr(char, "silver", 0) + silver
        char.gold = getattr(char, "gold", 0) + gold

        # Check for AUTOSPLIT flag (ROM C line 166)
        act_flags = int(getattr(char, "act", 0) or 0)

        if act_flags & int(PlayerFlag.AUTOSPLIT):
            # Count group members (non-charmed, same group) - ROM C lines 168-174
            members = 0
            room = getattr(char, "room", None)
            if room:
                for gch in getattr(room, "people", []):
                    gch_aff = int(getattr(gch, "affected_by", 0) or 0)
                    if not (gch_aff & int(AffectFlag.CHARM)):
                        if is_same_group(gch, char):
                            members += 1

            # Auto-split if >1 member and money > 1 (ROM C lines 176-180).
            # ROM passes ``"silver gold"`` as a single sprintf-formatted string.
            if members > 1 and (silver > 1 or gold):
                do_split(char, f"{silver} {gold}")

        # Extract money object (ROM C line 183) - don't add to inventory
        return None  # Success, message already set
    else:
        # ROM C lines 185-188: obj_to_char() for normal objects
        char.add_object(obj)
        return None  # Success, message already set


def do_get(char: Character, args: str) -> str:
    """
    Get object from room or container.

    ROM Reference: src/act_obj.c:195-344 (do_get) and :92-193 (get_obj helper)

    Usage:
        get <object>                  - Get object from room
        get all                       - Get all objects from room
        get all.<type>                - Get all objects of type from room
        get <object> <container>      - Get object from container
        get <object> from <container> - Get object from container (alternate syntax)
        get all <container>           - Get all from container
        get all.<type> <container>    - Get all of type from container

    Features:
        - Container retrieval support
        - "from" keyword parsing
        - "all" and "all.type" support
        - Container type validation
        - Container closed check
        - Pit greed check
        - AUTOSPLIT for ITEM_MONEY
        - Encumbrance checks
        - Furniture occupancy check
    """
    # ROM C lines 197-208: Argument parsing
    if not args:
        return "Get what?"

    # Parse arguments: "obj" and "container"
    arg1, rest = _one_argument(args)
    arg2, rest2 = _one_argument(rest)

    # Handle "from" keyword (ROM C line 209-210)
    if arg2.lower() == "from":
        arg2, rest2 = _one_argument(rest2)

    # ROM C lines 211-215: Empty argument check
    if not arg1:
        return "Get what?"

    room = getattr(char, "room", None)
    if not room:
        return "You're not anywhere."

    # ROM C lines 217-253: No container argument (get from room)
    if not arg2:
        # Check if "all" or "all.type"
        if arg1.lower() != "all" and not arg1.lower().startswith("all."):
            # ROM C lines 222-230: Get single object from room
            obj = get_obj_list(char, arg1, room.contents)
            if not obj:
                return f"I see no {arg1} here."

            if not can_see_object(char, obj):
                return f"I see no {arg1} here."

            # Use helper function to get the object
            error = _get_obj(char, obj, None)
            if error:
                return error

            # Return success message (set by _get_obj)
            obj_short = getattr(obj, "short_descr", "something")
            return f"You get {obj_short}."
        else:
            # ROM C lines 231-253: Get all or all.type from room
            found = False
            messages = []

            for obj in list(room.contents):
                # ROM C line 237-238: Check if matches "all" or "all.type"
                if arg1.lower() == "all":
                    matches = True
                elif arg1.lower().startswith("all."):
                    type_filter = arg1[4:]  # Skip "all."
                    obj_name = getattr(obj, "name", "")
                    matches = _is_name(type_filter, obj_name)
                else:
                    matches = False

                if matches and can_see_object(char, obj):
                    found = True
                    error = _get_obj(char, obj, None)
                    if error:
                        messages.append(error)
                    else:
                        obj_short = getattr(obj, "short_descr", "something")
                        messages.append(f"You get {obj_short}.")

            if not found:
                if arg1.lower() == "all":
                    return "I see nothing here."
                else:
                    type_filter = arg1[4:]
                    return f"I see no {type_filter} here."

            return "\n".join(messages) if messages else "Done."

    # ROM C lines 255-338: Get from container
    else:
        # ROM C lines 255-262: Validate container arg not "all"
        if arg2.lower() == "all" or arg2.lower().startswith("all."):
            return "You can't do that."

        # ROM C lines 264-268: Find container
        container = get_obj_here(char, arg2)
        if not container:
            return f"I see no {arg2} here."

        # ROM C lines 270-289: Container type validation
        container_proto = getattr(container, "prototype", container)
        item_type = int(getattr(container_proto, "item_type", 0) or 0)

        if item_type not in (int(ItemType.CONTAINER), int(ItemType.CORPSE_NPC), int(ItemType.CORPSE_PC)):
            return "That's not a container."

        # ROM C lines 283: Can_loot check for CORPSE_PC
        if item_type == int(ItemType.CORPSE_PC):
            if not _can_loot(char, container):
                return "You can't do that."

        # ROM C lines 291-295: Container closed check
        container_proto = getattr(container, "prototype", container)
        container_value = getattr(container_proto, "value", [0, 0, 0, 0, 0])
        if len(container_value) > 1 and (container_value[1] & CONT_CLOSED):
            container_name = getattr(container, "name", "container")
            return f"The {container_name.split()[0]} is closed."

        # Get container's contents
        container_items = getattr(container, "contained_items", [])

        # Check if single object or all
        if arg1.lower() != "all" and not arg1.lower().startswith("all."):
            # ROM C lines 297-307: Get single object from container
            obj = get_obj_list(char, arg1, container_items)
            if not obj:
                return f"I see nothing like that in the {arg2}."

            if not can_see_object(char, obj):
                return f"I see nothing like that in the {arg2}."

            error = _get_obj(char, obj, container)
            if error:
                return error

            obj_short = getattr(obj, "short_descr", "something")
            container_short = getattr(container, "short_descr", "something")
            return f"You get {obj_short} from {container_short}."
        else:
            # ROM C lines 309-338: Get all or all.type from container
            found = False
            messages = []

            for obj in list(container_items):
                # ROM C line 316-317: Check if matches "all" or "all.type"
                if arg1.lower() == "all":
                    matches = True
                elif arg1.lower().startswith("all."):
                    type_filter = arg1[4:]
                    obj_name = getattr(obj, "name", "")
                    matches = _is_name(type_filter, obj_name)
                else:
                    matches = False

                if matches and can_see_object(char, obj):
                    found = True

                    # ROM C lines 320-325: Pit greed check
                    container_proto = getattr(container, "prototype", None) or container
                    container_vnum = int(getattr(container_proto, "vnum", 0) or 0)

                    if container_vnum == OBJ_VNUM_PIT:
                        char_trust = int(getattr(char, "trust", 0) or getattr(char, "level", 0) or 0)
                        char_is_immortal = char_trust >= 51  # IMMORTAL level
                        if not char_is_immortal:
                            return "Don't be so greedy!"

                    error = _get_obj(char, obj, container)
                    if error:
                        messages.append(error)
                    else:
                        obj_short = getattr(obj, "short_descr", "something")
                        container_short = getattr(container, "short_descr", "something")
                        messages.append(f"You get {obj_short} from {container_short}.")

            if not found:
                if arg1.lower() == "all":
                    return f"I see nothing in the {arg2}."
                else:
                    type_filter = arg1[4:]
                    return f"I see nothing like that in the {arg2}."

            return "\n".join(messages) if messages else "Done."


def do_drop(char: Character, args: str) -> str:
    argument = (args or "").strip()
    if not argument:
        return "Drop what?"

    arg, _rest = _one_argument(argument)
    room = getattr(char, "room", None)
    if room is None:
        return "You can't do that here."

    if arg.isdigit():
        amount = int(arg)
        coin_type, _unused = _one_argument(_rest)
        coin_type = coin_type.lower()

        if amount <= 0 or coin_type not in {"coins", "coin", "gold", "silver"}:
            return "Sorry, you can't do that."

        gold = 0
        silver = 0
        if coin_type in {"coins", "coin", "silver"}:
            current_silver = int(getattr(char, "silver", 0) or 0)
            if current_silver < amount:
                return "You don't have that much silver."
            char.silver = current_silver - amount
            silver = amount
        else:
            current_gold = int(getattr(char, "gold", 0) or 0)
            if current_gold < amount:
                return "You don't have that much gold."
            char.gold = current_gold - amount
            gold = amount

        for obj in list(getattr(room, "contents", []) or []):
            proto = getattr(obj, "prototype", None) or obj
            vnum = int(getattr(proto, "vnum", 0) or 0)
            if vnum == OBJ_VNUM_SILVER_ONE:
                silver += 1
            elif vnum == OBJ_VNUM_GOLD_ONE:
                gold += 1
            elif vnum == OBJ_VNUM_SILVER_SOME:
                silver += int(getattr(obj, "value", [0, 0])[0] or 0)
            elif vnum == OBJ_VNUM_GOLD_SOME:
                values = getattr(obj, "value", [0, 0]) or [0, 0]
                gold += int(values[1] or 0)
            elif vnum == OBJ_VNUM_COINS:
                values = getattr(obj, "value", [0, 0]) or [0, 0]
                silver += int(values[0] or 0)
                gold += int(values[1] or 0)
            else:
                continue

            room.contents.remove(obj)

        money_obj = create_money(gold=gold, silver=silver)
        if money_obj is not None:
            room.add_object(money_obj)

        room_message = act_format("$n drops some coins.", recipient=None, actor=char, arg1=None, arg2=None)
        broadcast_room(room, room_message, exclude=char)
        return "OK."

    if arg != "all" and not arg.startswith("all."):
        obj = get_obj_carry(char, arg)
        if obj is None:
            return "You do not have that item."
        if not _can_drop_obj(char, obj):
            return "You can't let go of it."

        _obj_from_char(char, obj)
        room.add_object(obj)

        room_message = act_format("$n drops $p.", recipient=None, actor=char, arg1=obj, arg2=None)
        broadcast_room(room, room_message, exclude=char)
        obj_name = getattr(obj, "short_descr", None) or getattr(obj, "name", "something")
        extra_flags = int(getattr(obj, "extra_flags", 0) or 0)
        if extra_flags & int(ExtraFlag.MELT_DROP):
            if obj in room.contents:
                room.contents.remove(obj)
            smoke_message = act_format("$p dissolves into smoke.", recipient=None, actor=char, arg1=obj, arg2=None)
            broadcast_room(room, smoke_message, exclude=char)
            return f"You drop {obj_name}.\n{obj_name} dissolves into smoke."
        return f"You drop {obj_name}."

    found = False
    dropped_messages: list[str] = []
    type_filter = arg[4:] if arg.startswith("all.") else ""
    for obj in list(getattr(char, "inventory", []) or []):
        if getattr(obj, "wear_loc", -1) != -1:
            continue
        if not can_see_object(char, obj):
            continue
        if type_filter:
            obj_name = getattr(obj, "name", "") or ""
            if not _is_name(type_filter, obj_name):
                continue
        if not _can_drop_obj(char, obj):
            continue

        found = True
        _obj_from_char(char, obj)
        room.add_object(obj)

        room_message = act_format("$n drops $p.", recipient=None, actor=char, arg1=obj, arg2=None)
        broadcast_room(room, room_message, exclude=char)
        obj_name = getattr(obj, "short_descr", None) or getattr(obj, "name", "something")
        extra_flags = int(getattr(obj, "extra_flags", 0) or 0)
        if extra_flags & int(ExtraFlag.MELT_DROP):
            if obj in room.contents:
                room.contents.remove(obj)
            smoke_message = act_format("$p dissolves into smoke.", recipient=None, actor=char, arg1=obj, arg2=None)
            broadcast_room(room, smoke_message, exclude=char)
            dropped_messages.append(f"You drop {obj_name}.\n{obj_name} dissolves into smoke.")
        else:
            dropped_messages.append(f"You drop {obj_name}.")

    if not found:
        if type_filter:
            return f"You are not carrying any {type_filter}."
        return "You are not carrying anything."

    return "\n".join(dropped_messages)


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
    # mirrors ROM src/act_wiz.c:251-310
    if getattr(char, "is_npc", False) or int(getattr(char, "level", 0) or 0) > 5:
        return "Find it yourself!\n\r"

    give_school_outfit(char)
    # ROM always says "You have been equipped by Mota." regardless of whether
    # anything was actually equipped.
    return "You have been equipped by Mota.\n\r"
