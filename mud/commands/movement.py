from mud.world.movement import move_character
from mud.models.character import Character
from mud.models.constants import ItemType, EX_CLOSED
from mud.registry import room_registry


def do_north(char: Character, args: str = "") -> str:
    return move_character(char, "north")


def do_south(char: Character, args: str = "") -> str:
    return move_character(char, "south")


def do_east(char: Character, args: str = "") -> str:
    return move_character(char, "east")


def do_west(char: Character, args: str = "") -> str:
    return move_character(char, "west")


def do_up(char: Character, args: str = "") -> str:
    return move_character(char, "up")


def do_down(char: Character, args: str = "") -> str:
    return move_character(char, "down")


def do_enter(char: Character, args: str = "") -> str:
    target = (args or "").strip().lower()
    if not target:
        return "Enter what?"

    # Find a portal object in the room matching target token
    portal = None
    for obj in getattr(char.room, "contents", []):
        proto = getattr(obj, "prototype", None)
        if not proto or getattr(proto, "item_type", 0) != int(ItemType.PORTAL):
            continue
        name = (getattr(proto, "short_descr", None) or getattr(proto, "name", "") or "").lower()
        if target in name or target == "portal" or target in (getattr(obj, "short_descr", "") or "").lower():
            portal = obj
            break

    if not portal:
        return f"I see no {target} here."

    flags = 0
    proto = portal.prototype
    values = getattr(proto, "value", [0, 0, 0, 0, 0])
    if len(values) > 1 and isinstance(values[1], int):
        flags = int(values[1])

    if flags & EX_CLOSED:
        return "The portal is closed."

    dest_vnum = values[3] if len(values) > 3 else 0
    dest = room_registry.get(int(dest_vnum))
    if dest is None:
        return "It doesn't seem to go anywhere."

    # Move character
    old_room = char.room
    if char in old_room.people:
        old_room.people.remove(char)
    dest.people.append(char)
    char.room = dest
    char.wait = max(char.wait, 1)
    return f"You enter the portal and arrive in {dest.name}."
