from mud.models.character import Character
from mud.models.constants import EX_CLOSED, ItemType
from mud.registry import room_registry
from mud.world.movement import move_character, move_character_through_portal


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
    return move_character_through_portal(char, portal)
