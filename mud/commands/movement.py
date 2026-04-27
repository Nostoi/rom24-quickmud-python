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
    """Enter a portal object.

    # mirroring ROM src/act_enter.c:66-229
    """
    from mud.commands.obj_manipulation import get_obj_list

    target = (args or "").strip()
    if not target:
        # ENTER-002: ROM sends "Nope, can't do it." for no-arg (act_enter.c:227)
        return "Nope, can't do it."

    # ENTER-016: ROM is silent when fighting (act_enter.c:70-71)
    if getattr(char, "fighting", None) is not None:
        return ""

    # ENTER-005: Use get_obj_list for visibility + numbered-prefix support
    # (act_enter.c:82: portal = get_obj_list(ch, argument, ch->in_room->contents))
    room_contents = list(getattr(char.room, "contents", []) or [])
    portal = get_obj_list(char, target, room_contents)

    # ENTER-003: ROM sends "You don't see that here." when object not found
    if portal is None:
        return "You don't see that here."

    # Resolve values — prefer instance value list, fall back to prototype
    proto = getattr(portal, "prototype", None)
    values = getattr(portal, "value", None)
    if not isinstance(values, list):
        proto_values = getattr(proto, "value", None) if proto else None
        values = list(proto_values) if isinstance(proto_values, list) else [0, 0, 0, 0, 0]
        if hasattr(portal, "value"):
            portal.value = values

    exit_flags = int(values[1]) if len(values) > 1 else 0

    is_trusted = char.is_admin or _get_trust(char) >= LEVEL_ANGEL

    # ENTER-004: Combined gate — non-portal OR closed-without-trust → same message
    # (act_enter.c:90-96)
    portal_item_type = int(getattr(proto, "item_type", 0)) if proto else 0
    if portal_item_type != int(ItemType.PORTAL) or (exit_flags & EX_CLOSED and not is_trusted):
        return "You can't seem to find a way in."

    gate_flags = int(values[2]) if len(values) > 2 else 0

    if not is_trusted and not (gate_flags & int(PortalFlag.NOCURSE)):
        room_flags = int(getattr(char.room, "room_flags", 0) or 0)
        if char.has_affect(AffectFlag.CURSE) or room_flags & int(RoomFlag.ROOM_NO_RECALL):
            return "Something prevents you from leaving..."

    return move_character_through_portal(char, portal)
