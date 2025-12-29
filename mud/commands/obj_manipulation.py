"""
Player essential object commands - put, remove, quaff, sacrifice.

ROM Reference: src/act_obj.c
"""

from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import ExtraFlag, ItemType, Position
from mud.world.obj_find import get_obj_carry, get_obj_here, get_obj_wear


# Container flags
CONT_CLOSEABLE = 1
CONT_PICKPROOF = 2
CONT_CLOSED = 4
CONT_LOCKED = 8
CONT_PUT_ON = 16


def get_obj_list(char: Character, name: str, obj_list: list) -> object | None:
    """
    Find an object in a list by name.

    ROM Reference: src/handler.c get_obj_list
    """
    name_lower = name.lower()

    # Handle numbered prefix (2.sword, 3.potion)
    count = 0
    number = 1
    if "." in name and name.split(".")[0].isdigit():
        parts = name.split(".", 1)
        number = int(parts[0])
        name_lower = parts[1].lower()

    for obj in obj_list:
        obj_name = getattr(obj, "name", "").lower()
        short = getattr(obj, "short_descr", "").lower()

        # Check if name matches any keyword
        if name_lower in obj_name.split() or name_lower in obj_name or name_lower in short:
            count += 1
            if count == number:
                return obj

    return None


def do_put(char: Character, args: str) -> str:
    """
    Put an item into a container.

    ROM Reference: src/act_obj.c do_put (lines 346-490)

    Usage:
    - put <item> <container>
    - put <item> in <container>
    - put all <container>
    - put all.<type> <container>
    """
    if not args or not args.strip():
        return "Put what in what?"

    parts = args.strip().split()
    if len(parts) < 2:
        return "Put what in what?"

    item_name = parts[0]
    container_name = parts[-1]

    # Handle "put x in y" or "put x on y"
    if len(parts) >= 3 and parts[1].lower() in ("in", "on"):
        container_name = parts[2] if len(parts) > 2 else parts[-1]

    # Can't put into all
    if container_name.lower() == "all" or container_name.lower().startswith("all."):
        return "You can't do that."

    # Find the container
    container = get_obj_here(char, container_name)
    if container is None:
        return f"I see no {container_name} here."

    # Check if it's a container
    item_type = _get_item_type(container)
    if item_type != ItemType.CONTAINER and str(item_type) != "container":
        return "That's not a container."

    # Check if closed
    container_value = getattr(container, "value", [0, 0, 0, 0, 0])
    if len(container_value) > 1 and (container_value[1] & CONT_CLOSED):
        container_name = getattr(container, "name", "container")
        return f"The {container_name.split()[0]} is closed."

    # Handle single item or all
    if item_name.lower() != "all" and not item_name.lower().startswith("all."):
        # Single item
        obj = get_obj_carry(char, item_name)
        if obj is None:
            return "You do not have that item."

        if obj is container:
            return "You can't fold it into itself."

        # Check if can drop
        if not _can_drop_obj(char, obj):
            return "You can't let go of it."

        # Check weight
        obj_weight = _get_obj_weight(obj)
        container_weight = _get_true_weight(container)
        max_weight = container_value[0] * 10 if len(container_value) > 0 else 1000
        max_single = container_value[3] * 10 if len(container_value) > 3 else 1000

        if obj_weight + container_weight > max_weight or obj_weight > max_single:
            return "It won't fit."

        # Transfer the item
        _obj_from_char(char, obj)
        _obj_to_obj(obj, container)

        obj_name = getattr(obj, "short_descr", "something")
        container_short = getattr(container, "short_descr", "something")

        if len(container_value) > 1 and (container_value[1] & CONT_PUT_ON):
            return f"You put {obj_name} on {container_short}."
        else:
            return f"You put {obj_name} in {container_short}."

    else:
        # Put all or all.<type>
        filter_name = None
        if item_name.lower().startswith("all."):
            filter_name = item_name[4:].lower()

        carrying = list(getattr(char, "carrying", []))
        count = 0
        messages = []

        for obj in carrying:
            # Skip if doesn't match filter
            if filter_name:
                obj_name = getattr(obj, "name", "").lower()
                if filter_name not in obj_name:
                    continue

            # Skip if worn
            if getattr(obj, "wear_loc", -1) != -1:
                continue

            # Skip container itself
            if obj is container:
                continue

            # Skip if can't drop
            if not _can_drop_obj(char, obj):
                continue

            # Check weight
            obj_weight = _get_obj_weight(obj)
            container_weight = _get_true_weight(container)
            max_weight = container_value[0] * 10 if len(container_value) > 0 else 1000
            max_single = container_value[3] * 10 if len(container_value) > 3 else 1000

            if obj_weight + container_weight > max_weight or obj_weight > max_single:
                continue

            # Transfer
            _obj_from_char(char, obj)
            _obj_to_obj(obj, container)

            obj_short = getattr(obj, "short_descr", "something")
            container_short = getattr(container, "short_descr", "something")

            if len(container_value) > 1 and (container_value[1] & CONT_PUT_ON):
                messages.append(f"You put {obj_short} on {container_short}.")
            else:
                messages.append(f"You put {obj_short} in {container_short}.")
            count += 1

        if count == 0:
            return "You have nothing to put."

        return "\n".join(messages)


def do_remove(char: Character, args: str) -> str:
    """
    Remove a worn item.

    ROM Reference: src/act_obj.c do_remove (lines 1740-1763)
                   src/handler.c remove_obj (lines 1372-1392)

    Usage: remove <item>
    """
    if not args or not args.strip():
        return "Remove what?"

    item_name = args.strip().split()[0]

    # Find worn item
    obj = get_obj_wear(char, item_name)
    if obj is None:
        return "You do not have that item."

    # Get wear location
    wear_loc = getattr(obj, "wear_loc", -1)
    if wear_loc == -1:
        return "You aren't wearing that."

    # Check NOREMOVE flag (cursed items) - ROM src/handler.c:1382-1386
    extra_flags = getattr(obj, "extra_flags", 0)
    if extra_flags & ExtraFlag.NOREMOVE:
        obj_name = getattr(obj, "short_descr", "it")
        return f"You can't remove {obj_name}."

    # Remove the item
    _remove_obj(char, obj)

    obj_name = getattr(obj, "short_descr", "something")
    return f"You stop using {obj_name}."


def do_sacrifice(char: Character, args: str) -> str:
    """
    Sacrifice an item for silver coins.

    ROM Reference: src/act_obj.c do_sacrifice (lines 1765-1862)

    Usage: sacrifice <item>
    """
    if not args or not args.strip():
        # Self-sacrifice message
        char_name = getattr(char, "name", "someone")
        return "Mota appreciates your offer and may accept it later."

    item_name = args.strip().split()[0]
    char_name = getattr(char, "name", "someone")

    if item_name.lower() == char_name.lower():
        return "Mota appreciates your offer and may accept it later."

    # Find item in room
    room = getattr(char, "room", None)
    if not room:
        return "You can't find it."

    contents = getattr(room, "contents", [])
    obj = get_obj_list(char, item_name, contents)

    if obj is None:
        return "You can't find it."

    # Check for PC corpse with contents
    item_type = _get_item_type(obj)
    if item_type == ItemType.CORPSE_PC or str(item_type) == "corpse_pc":
        obj_contents = getattr(obj, "contains", [])
        if obj_contents:
            return "Mota wouldn't like that."

    # Check if can take/sacrifice
    wear_flags = getattr(obj, "wear_flags", 0)
    if not hasattr(obj, "wear_flags"):
        proto = getattr(obj, "prototype", None)
        if proto:
            wear_flags = getattr(proto, "wear_flags", 0)

    extra_flags = getattr(obj, "extra_flags", 0)
    if not hasattr(obj, "extra_flags"):
        proto = getattr(obj, "prototype", None)
        if proto:
            extra_flags = getattr(proto, "extra_flags", 0)

    ITEM_TAKE = 1
    ITEM_NO_SAC = 0x4000  # Bit 14

    if not (wear_flags & ITEM_TAKE):
        obj_name = getattr(obj, "short_descr", "That")
        return f"{obj_name} is not an acceptable sacrifice."

    if extra_flags & ITEM_NO_SAC:
        obj_name = getattr(obj, "short_descr", "That")
        return f"{obj_name} is not an acceptable sacrifice."

    # Check if someone is using the object
    room_people = getattr(room, "people", [])
    for person in room_people:
        if getattr(person, "on", None) is obj:
            person_name = getattr(person, "name", "Someone")
            obj_name = getattr(obj, "short_descr", "it")
            return f"{person_name} appears to be using {obj_name}."

    # Calculate silver reward
    obj_level = getattr(obj, "level", 1)
    obj_cost = getattr(obj, "cost", 0)

    silver = max(1, obj_level * 3)

    # Non-corpse items capped at cost
    if item_type not in (ItemType.CORPSE_NPC, ItemType.CORPSE_PC) and str(item_type) not in ("corpse_npc", "corpse_pc"):
        silver = min(silver, obj_cost) if obj_cost > 0 else silver

    # Give silver
    char.silver = getattr(char, "silver", 0) + silver

    # Remove object
    _extract_obj(char, obj)

    # Auto-split if enabled
    act_flags = getattr(char, "act", 0)
    PLR_AUTOSPLIT = 0x00002000
    if act_flags & PLR_AUTOSPLIT and silver > 1:
        # Check for group members
        members = _count_group_members(char)
        if members > 1:
            from mud.commands.group_commands import do_split

            do_split(char, str(silver))

    if silver == 1:
        return "Mota gives you one silver coin for your sacrifice."
    else:
        return f"Mota gives you {silver} silver coins for your sacrifice."


def do_quaff(char: Character, args: str) -> str:
    """
    Drink a potion.

    ROM Reference: src/act_obj.c do_quaff (lines 1865-1906)

    Usage: quaff <potion>
    """
    if not args or not args.strip():
        return "Quaff what?"

    item_name = args.strip().split()[0]

    # Find potion in inventory
    obj = get_obj_carry(char, item_name)
    if obj is None:
        return "You do not have that potion."

    # Check if it's a potion
    item_type = _get_item_type(obj)
    if item_type != ItemType.POTION and str(item_type) != "potion":
        return "You can quaff only potions."

    # Check level
    obj_level = getattr(obj, "level", 1)
    char_level = getattr(char, "level", 1)

    if char_level < obj_level:
        return "This liquid is too powerful for you to drink."

    obj_name = getattr(obj, "short_descr", "something")

    # Cast the spells from the potion
    obj_value = getattr(obj, "value", [0, 0, 0, 0, 0])
    spell_level = obj_value[0] if len(obj_value) > 0 else 1

    for i in range(1, 4):
        if len(obj_value) > i and obj_value[i]:
            _obj_cast_spell(obj_value[i], spell_level, char, char, None)

    # Remove the potion
    _extract_obj(char, obj)

    return f"You quaff {obj_name}."


# Helper functions


def _get_item_type(obj) -> ItemType:
    """Get item type from object or prototype."""
    item_type = getattr(obj, "item_type", None)
    if item_type is None:
        proto = getattr(obj, "prototype", None)
        if proto:
            item_type = getattr(proto, "item_type", ItemType.TRASH)
    return item_type or ItemType.TRASH


def _get_obj_weight(obj) -> int:
    """Get total weight of object including contents."""
    weight = getattr(obj, "weight", 0)
    if not hasattr(obj, "weight"):
        proto = getattr(obj, "prototype", None)
        if proto:
            weight = getattr(proto, "weight", 0)

    # Add contents weight
    contains = getattr(obj, "contains", [])
    for contained in contains:
        weight += _get_obj_weight(contained)

    return weight


def _get_true_weight(container) -> int:
    """Get weight of container's contents only."""
    weight = 0
    contains = getattr(container, "contains", [])
    for obj in contains:
        weight += _get_obj_weight(obj)
    return weight


def _can_drop_obj(char: Character, obj) -> bool:
    """Check if character can drop/put an object."""
    extra_flags = getattr(obj, "extra_flags", 0)
    ITEM_NODROP = 0x0010
    if extra_flags & ITEM_NODROP:
        return False
    return True


def _obj_from_char(char: Character, obj) -> None:
    """Remove object from character's inventory."""
    carrying = getattr(char, "carrying", [])
    if obj in carrying:
        carrying.remove(obj)
    obj.carried_by = None

    # Update carry weight/number
    weight = _get_obj_weight(obj)
    char.carry_weight = max(0, getattr(char, "carry_weight", 0) - weight)
    char.carry_number = max(0, getattr(char, "carry_number", 0) - 1)


def _obj_to_obj(obj, container) -> None:
    """Put object into container."""
    contains = getattr(container, "contains", None)
    if contains is None:
        container.contains = []
        contains = container.contains
    contains.append(obj)
    obj.in_obj = container


def _remove_obj(char: Character, obj) -> None:
    """Remove worn object from character."""
    wear_loc = getattr(obj, "wear_loc", -1)
    if wear_loc == -1:
        return

    obj.wear_loc = -1  # WEAR_NONE

    # Remove from equipment dict
    equipment = getattr(char, "equipment", {})
    if equipment:
        # Find and remove from equipment dict by value
        for slot, equipped_obj in list(equipment.items()):
            if equipped_obj == obj:
                del equipment[slot]
                break

    # Move to inventory (Character model uses 'inventory', not 'carrying')
    inventory = getattr(char, "inventory", None)
    if inventory is None:
        char.inventory = []
        inventory = char.inventory
    if obj not in inventory:
        inventory.append(obj)


def _extract_obj(char: Character, obj) -> None:
    """Remove object from the game."""
    room = getattr(char, "room", None)
    if room:
        contents = getattr(room, "contents", [])
        if obj in contents:
            contents.remove(obj)

    carrying = getattr(char, "carrying", [])
    if obj in carrying:
        carrying.remove(obj)

    # Clear references
    obj.in_room = None
    obj.carried_by = None
    obj.in_obj = None


def _count_group_members(char: Character) -> int:
    """Count members in character's group in same room."""
    room = getattr(char, "room", None)
    if not room:
        return 1

    count = 0
    room_people = getattr(room, "people", [])
    for person in room_people:
        if _is_same_group(person, char):
            count += 1

    return max(1, count)


def _is_same_group(char1: Character, char2: Character) -> bool:
    """Check if two characters are in the same group."""
    if char1 is char2:
        return True

    # Check if following same leader
    leader1 = getattr(char1, "leader", None) or char1
    leader2 = getattr(char2, "leader", None) or char2

    return leader1 is leader2


def _obj_cast_spell(spell_sn, level: int, ch: Character, victim: Character, obj) -> None:
    """Cast a spell from an object (potion/scroll/etc)."""
    # Simplified - just apply basic effects
    # Full implementation would look up spell_sn and call spell function
    pass
