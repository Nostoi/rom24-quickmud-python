from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import (
    MAX_LEVEL,
    AffectFlag,
    RoomFlag,
    Sector,
)
from mud.models.room import Room
from mud.time import Sunlight, time_info

_VISIBILITY_AFFECTS = AffectFlag.INFRARED | AffectFlag.DARK_VISION


def _get_trust(char: Character) -> int:
    """Return the ROM-style trust level for visibility checks."""

    trust = int(getattr(char, "trust", 0) or 0)
    level = int(getattr(char, "level", 0) or 0)
    return trust if trust > 0 else level


def room_is_dark(room: Room) -> bool:
    """Replicate ROM `room_is_dark` visibility logic."""

    if int(getattr(room, "light", 0) or 0) > 0:
        return False

    flags = int(getattr(room, "room_flags", 0) or 0)
    if flags & int(RoomFlag.ROOM_DARK):
        return True

    try:
        sector = Sector(int(getattr(room, "sector_type", 0) or 0))
    except ValueError:
        sector = Sector.INSIDE

    if sector in (Sector.INSIDE, Sector.CITY):
        return False

    return time_info.sunlight in (Sunlight.SET, Sunlight.DARK)


def can_see_room(char: Character, room: Room) -> bool:
    """Return True if `char` may enter or see `room` per ROM rules."""

    if char.is_admin:
        return True

    if char.has_affect(AffectFlag.BLIND):
        return False

    if room_is_dark(room):
        if not (char.is_immortal() or bool(char.affected_by & _VISIBILITY_AFFECTS)):
            return False

    flags = int(getattr(room, "room_flags", 0) or 0)
    trust = _get_trust(char)

    if flags & int(RoomFlag.ROOM_IMP_ONLY) and trust < MAX_LEVEL:
        return False

    if flags & int(RoomFlag.ROOM_GODS_ONLY) and not char.is_immortal():
        return False

    if flags & int(RoomFlag.ROOM_HEROES_ONLY) and not char.is_immortal():
        return False

    if flags & int(RoomFlag.ROOM_NEWBIES_ONLY) and trust > 5 and not char.is_immortal():
        return False

    room_clan = int(getattr(room, "clan", 0) or 0)
    char_clan = int(getattr(char, "clan", 0) or 0)
    if room_clan and not char.is_immortal() and room_clan != char_clan:
        return False

    return True
