from mud.models.character import Character
from mud.models.constants import (
    EX_CLOSED,
    ItemType,
    LEVEL_ANGEL,
    LEVEL_IMMORTAL,
    AffectFlag,
    PortalFlag,
    RoomFlag,
)
from mud.world.movement import move_character, move_character_through_portal


def _get_trust(char: Character) -> int:
    trust = int(getattr(char, "trust", 0) or 0)
    if trust <= 0:
        trust = int(getattr(char, "level", 0) or 0)
    if char.is_admin and trust < LEVEL_IMMORTAL:
        return LEVEL_IMMORTAL
    return trust


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

    if getattr(char, "fighting", None) is not None:
        return "No way!  You are still fighting!"

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

    proto = portal.prototype
    values = getattr(portal, "value", None)
    if not isinstance(values, list):
        values = getattr(proto, "value", [0, 0, 0, 0, 0])

    exit_flags = int(values[1]) if len(values) > 1 else 0
    gate_flags = int(values[2]) if len(values) > 2 else 0

    is_trusted = char.is_admin or _get_trust(char) >= LEVEL_ANGEL

    if exit_flags & EX_CLOSED and not is_trusted:
        return "The portal is closed."

    if not is_trusted and not (gate_flags & int(PortalFlag.NOCURSE)):
        room_flags = int(getattr(char.room, "room_flags", 0) or 0)
        if char.has_affect(AffectFlag.CURSE) or room_flags & int(RoomFlag.ROOM_NO_RECALL):
            return "Something prevents you from leaving..."

    return move_character_through_portal(char, portal)
