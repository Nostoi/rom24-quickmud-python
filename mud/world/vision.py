from __future__ import annotations

from mud.models.character import Character
from mud.math.c_compat import c_div
from typing import Any

from mud.models.constants import (
    MAX_LEVEL,
    AffectFlag,
    PlayerFlag,
    RoomFlag,
    Sector,
    Stat,
    ExtraFlag,
    ItemType,
)
from mud.models.room import Room
from mud.time import Sunlight, time_info
from mud.utils import rng_mm

_VISIBILITY_AFFECTS = AffectFlag.INFRARED | AffectFlag.DARK_VISION


def _object_extra_flags(obj: Any) -> int:
    """Return runtime or prototype extra flags for *obj*."""

    try:
        flags = int(getattr(obj, "extra_flags", 0) or 0)
    except (TypeError, ValueError):
        flags = 0
    if flags:
        return flags
    proto = getattr(obj, "prototype", None)
    try:
        return int(getattr(proto, "extra_flags", 0) or 0)
    except (TypeError, ValueError, AttributeError):
        return 0


def _object_item_type(obj: Any) -> ItemType | None:
    """Resolve the item's type using runtime overrides before prototypes."""

    for source in (obj, getattr(obj, "prototype", None)):
        if source is None:
            continue
        try:
            raw_type = int(getattr(source, "item_type", 0) or 0)
        except (TypeError, ValueError):
            continue
        try:
            return ItemType(raw_type)
        except ValueError:
            continue
    return None


def _object_light_timer(obj: Any) -> int:
    """Return the remaining light duration for light objects."""

    for source in (obj, getattr(obj, "prototype", None)):
        if source is None:
            continue
        values = getattr(source, "value", None)
        if isinstance(values, (list, tuple)) and len(values) > 2:
            try:
                return int(values[2])
            except (TypeError, ValueError):
                continue
    return 0


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


def _coerce_int(value: object) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _get_curr_stat_value(char: Character | None, stat: Stat) -> int:
    if char is None:
        return 0
    getter = getattr(char, "get_curr_stat", None)
    if callable(getter):
        try:
            value = getter(stat)
        except Exception:
            value = None
        if value is not None:
            return _coerce_int(value)
    perm_stats = getattr(char, "perm_stat", None)
    if isinstance(perm_stats, (list, tuple)):
        idx = int(stat)
        if 0 <= idx < len(perm_stats):
            return _coerce_int(perm_stats[idx])
    return 0


def _get_skill_percent(char: Character | None, name: str) -> int:
    if char is None:
        return 0
    skills = getattr(char, "skills", None)
    if isinstance(skills, dict):
        value = skills.get(name)
        if value is None:
            value = skills.get(name.lower())
        if value is not None:
            percent = _coerce_int(value)
            return max(0, min(100, percent))
    if getattr(char, "is_npc", False) and name.lower() == "sneak":
        level = _coerce_int(getattr(char, "level", 0))
        return level * 2 + 20
    return 0


def _sneak_success_chance(observer: Character, target: Character) -> int:
    chance = _get_skill_percent(target, "sneak")
    victim_dex = _get_curr_stat_value(target, Stat.DEX)
    chance += (victim_dex * 3) // 2
    observer_int = _get_curr_stat_value(observer, Stat.INT)
    chance -= observer_int * 2
    observer_level = _coerce_int(getattr(observer, "level", 0))
    target_level = _coerce_int(getattr(target, "level", 0))
    chance -= observer_level - c_div(target_level * 3, 2)
    return chance


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
            chance = _sneak_success_chance(observer, target)
            if rng_mm.number_percent() < chance:
                return False

    if _has_affect(target, AffectFlag.HIDE) and getattr(target, "fighting", None) is None:
        if not _has_affect(observer, AffectFlag.DETECT_HIDDEN):
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


def can_see_object(observer: Character | None, obj: Any) -> bool:
    """Replicate ROM ``can_see_obj`` visibility gating for objects."""

    if observer is None or obj is None:
        return False

    if not getattr(observer, "is_npc", False) and _has_holylight(observer):
        return True

    extra_flags = _object_extra_flags(obj)
    if extra_flags & int(ExtraFlag.VIS_DEATH):
        return False

    if _has_affect(observer, AffectFlag.BLIND):
        item_type = _object_item_type(obj)
        if item_type != ItemType.POTION:
            return False

    item_type = _object_item_type(obj)
    if item_type == ItemType.LIGHT and _object_light_timer(obj) != 0:
        return True

    if extra_flags & int(ExtraFlag.INVIS) and not _has_affect(observer, AffectFlag.DETECT_INVIS):
        return False

    if extra_flags & int(ExtraFlag.GLOW):
        return True

    room = getattr(observer, "room", None)
    if room is not None and room_is_dark(room) and not _has_affect(observer, AffectFlag.DARK_VISION):
        return False

    return True


def describe_character(observer: Character, target: Character | None) -> str:
    """Return a ROM-style ``PERS`` description for ``target``."""

    if target is None:
        return "someone"

    if observer is target:
        return "You"

    name: str | None
    if getattr(target, "is_npc", False):
        name = getattr(target, "short_descr", None) or getattr(target, "name", None)
    else:
        name = getattr(target, "name", None)

    if not name:
        return "someone"

    return str(name).strip() or "someone"
