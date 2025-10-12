from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import (
    MAX_LEVEL,
    AffectFlag,
    PlayerFlag,
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


def _has_affect(char: Character, flag: AffectFlag) -> bool:
    """Gracefully probe ``char`` for an active affect flag."""

    checker = getattr(char, "has_affect", None)
    if callable(checker):
        try:
            return bool(checker(flag))
        except Exception:
            pass
    affected = getattr(char, "affected_by", 0)
    try:
        return bool(int(affected) & int(flag))
    except Exception:
        return False


def _has_holylight(char: Character | None) -> bool:
    if char is None:
        return False
    if getattr(char, "is_npc", False):
        immortal_checker = getattr(char, "is_immortal", None)
        if callable(immortal_checker):
            try:
                return bool(immortal_checker())
            except Exception:
                return False
        return False
    try:
        act_flags = int(getattr(char, "act", 0) or 0)
    except Exception:
        act_flags = 0
    return bool(act_flags & int(PlayerFlag.HOLYLIGHT))


def can_see_character(observer: Character, target: Character | None) -> bool:
    """Replicate ROM ``can_see`` for character-to-character checks."""

    if observer is None or target is None:
        return False
    if observer is target:
        return True

    observer_room = getattr(observer, "room", None)
    target_room = getattr(target, "room", None)
    if observer_room is None or target_room is None:
        return False

    trust = _get_trust(observer)
    invis_level = int(getattr(target, "invis_level", 0) or 0)
    if trust < invis_level:
        return False

    incog_level = int(getattr(target, "incog_level", 0) or 0)
    if incog_level and observer_room is not target_room and trust < incog_level:
        return False

    if _has_holylight(observer):
        return True

    if _has_affect(observer, AffectFlag.BLIND):
        return False

    if observer_room is target_room and room_is_dark(observer_room):
        if not (
            _has_holylight(observer)
            or _has_affect(observer, AffectFlag.INFRARED)
            or _has_affect(observer, AffectFlag.DARK_VISION)
        ):
            return False

    if _has_affect(target, AffectFlag.INVISIBLE) and not _has_affect(observer, AffectFlag.DETECT_INVIS):
        return False

    if _has_affect(target, AffectFlag.SNEAK) and getattr(target, "fighting", None) is None:
        if not _has_affect(observer, AffectFlag.DETECT_HIDDEN):
            return False

    if _has_affect(target, AffectFlag.HIDE) and getattr(target, "fighting", None) is None:
        if not _has_affect(observer, AffectFlag.DETECT_HIDDEN):
            return False

    if observer_room is not target_room:
        return False

    return True


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

    if char.has_affect(AffectFlag.BLIND):
        return False

    if room_is_dark(room):
        if not (
            _has_holylight(char)
            or char.is_immortal()
            or bool(char.affected_by & _VISIBILITY_AFFECTS)
        ):
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
