"""AI helpers mirroring ROM update handlers."""

from __future__ import annotations

from collections.abc import Iterable

from mud.models.character import Character, character_registry
from mud.models.constants import (
    ActFlag,
    AffectFlag,
    Direction,
    PlayerFlag,
    Position,
    RoomFlag,
    WearFlag,
    EX_CLOSED,
)
from mud.models.obj import ObjectData
from mud.models.room import Exit, Room, room_registry
from mud.utils import rng_mm
from mud.world.movement import move_character

from .aggressive import aggressive_update

import mud.mobprog as mobprog

__all__ = ["aggressive_update", "mobile_update"]


def _has_flag(value: int, flag: ActFlag) -> bool:
    try:
        return bool(ActFlag(int(value)) & flag)
    except Exception:
        return False


def _mob_has_act_flag(mob: object, flag: ActFlag) -> bool:
    checker = getattr(mob, "has_act_flag", None)
    if callable(checker):
        try:
            return bool(checker(flag))
        except Exception:
            pass
    return _has_flag(getattr(mob, "act", 0) or 0, flag)


def _is_charmed(mob: object) -> bool:
    has_affect = getattr(mob, "has_affect", None)
    if callable(has_affect):
        try:
            return bool(has_affect(AffectFlag.CHARM))
        except Exception:
            pass
    try:
        return bool(int(getattr(mob, "affected_by", 0) or 0) & int(AffectFlag.CHARM))
    except Exception:
        return False


def _resolve_shop_info(mob: object) -> tuple[object | None, int]:
    """Return the active shop pointer and wealth value for a character."""

    shop_sources = (
        getattr(mob, "pShop", None),
        getattr(getattr(mob, "prototype", None), "pShop", None),
        getattr(getattr(mob, "mob_index", None), "pShop", None),
        getattr(getattr(mob, "pIndexData", None), "pShop", None),
    )
    shop = next((candidate for candidate in shop_sources if candidate is not None), None)

    wealth = 0
    wealth_sources = (
        getattr(mob, "wealth", None),
        getattr(getattr(mob, "prototype", None), "wealth", None),
        getattr(getattr(mob, "mob_index", None), "wealth", None),
        getattr(getattr(mob, "pIndexData", None), "wealth", None),
    )
    for source in wealth_sources:
        try:
            value = int(source)
        except (TypeError, ValueError):
            continue
        if value:
            wealth = value
            break
    return shop, wealth


def _normalize_name(name: object | None) -> str:
    if not name:
        return ""
    return str(name).strip().lower()


def _find_character(name: str) -> Character | None:
    if not name:
        return None
    for candidate in character_registry:
        if _normalize_name(getattr(candidate, "name", None)) == name:
            return candidate
    return None


def _broadcast_room(room: Room, message: str, exclude: object | None = None) -> None:
    if hasattr(room, "broadcast"):
        room.broadcast(message, exclude=exclude)
        return
    for occupant in getattr(room, "people", []) or []:
        if occupant is exclude:
            continue
        messages = getattr(occupant, "messages", None)
        if isinstance(messages, list):
            messages.append(message)


def _maybe_return_home(mob: Character, room: Room) -> bool:
    if getattr(mob, "desc", None) is not None:
        return False
    if getattr(mob, "fighting", None) is not None:
        return False
    if _is_charmed(mob):
        return False

    home_vnum = getattr(mob, "home_room_vnum", None)
    try:
        home_vnum_int = int(home_vnum or 0)
    except (TypeError, ValueError):
        return False
    if home_vnum_int <= 0:
        return False

    current_area = getattr(room, "area", None)
    home_area = getattr(mob, "home_area", None) or getattr(mob, "zone", None)
    if home_area is None or home_area is current_area:
        return False

    if rng_mm.number_percent() >= 5:
        return False

    destination = room_registry.get(home_vnum_int)
    if destination is None:
        return False

    name = getattr(mob, "short_descr", None) or getattr(mob, "name", None) or "Someone"
    _broadcast_room(room, f"{name} wanders on home.", exclude=mob)

    if hasattr(room, "remove_character"):
        room.remove_character(mob)
    else:
        occupants = getattr(room, "people", None)
        if isinstance(occupants, list) and mob in occupants:
            occupants.remove(mob)
        setattr(mob, "room", None)

    if isinstance(mob, Character):
        destination.add_character(mob)
    else:
        add_mob = getattr(destination, "add_mob", None)
        if callable(add_mob):
            add_mob(mob)
        else:
            destination.add_character(mob)

    return True


def _can_loot(mob: Character, obj: ObjectData) -> bool:
    if getattr(mob, "is_admin", False):
        return True
    is_immortal = getattr(mob, "is_immortal", None)
    if callable(is_immortal):
        try:
            if is_immortal():
                return True
        except Exception:
            pass

    owner_name = _normalize_name(getattr(obj, "owner", None))
    if not owner_name:
        return True

    mob_name = _normalize_name(getattr(mob, "name", None))
    if mob_name and mob_name == owner_name:
        return True

    owner_char = _find_character(owner_name)
    if owner_char is None:
        return True

    if not getattr(owner_char, "is_npc", False):
        act_bits = int(getattr(owner_char, "act", 0) or 0)
        if act_bits & int(PlayerFlag.CANLOOT):
            return True

    mob_group = getattr(mob, "group", None)
    if mob_group is not None and mob_group == getattr(owner_char, "group", None):
        return True

    return False


def _room_contents(room: Room | None) -> Iterable[ObjectData]:
    if room is None:
        return []
    contents = getattr(room, "contents", None)
    if isinstance(contents, list):
        return list(contents)
    return []


def _take_object(mob: Character, obj: ObjectData) -> None:
    room = getattr(obj, "in_room", None) or getattr(mob, "room", None)
    if room is not None:
        contents = getattr(room, "contents", None)
        if isinstance(contents, list) and obj in contents:
            contents.remove(obj)
    obj.in_room = None
    obj.in_obj = None
    obj.carried_by = mob

    inventory = getattr(mob, "inventory", None)
    if isinstance(inventory, list) and obj not in inventory:
        inventory.append(obj)

    weight = int(getattr(obj, "weight", 0) or 0)
    if hasattr(mob, "carry_number"):
        mob.carry_number = int(getattr(mob, "carry_number", 0) or 0) + 1
    if hasattr(mob, "carry_weight"):
        mob.carry_weight = int(getattr(mob, "carry_weight", 0) or 0) + weight

    room = getattr(mob, "room", None)
    if room is not None and hasattr(room, "broadcast"):
        mob_name = getattr(mob, "short_descr", None) or getattr(mob, "name", None) or "Someone"
        obj_name = getattr(obj, "short_descr", None) or getattr(obj, "name", None) or "something"
        room.broadcast(f"{mob_name} gets {obj_name}.", exclude=mob)


def _maybe_scavenge(mob: Character, room: Room) -> None:
    if not _mob_has_act_flag(mob, ActFlag.SCAVENGER):
        return
    contents = list(_room_contents(room))
    if not contents:
        return
    if rng_mm.number_bits(6) != 0:
        return

    best_obj: ObjectData | None = None
    best_cost = 1
    for obj in contents:
        wear_flags = int(getattr(obj, "wear_flags", 0) or 0)
        if not wear_flags & int(WearFlag.TAKE):
            continue
        if not _can_loot(mob, obj):
            continue
        cost = int(getattr(obj, "cost", 0) or 0)
        if cost <= best_cost:
            continue
        best_cost = cost
        best_obj = obj

    if best_obj is not None:
        _take_object(mob, best_obj)


def _valid_exit(room: Room, door: int) -> Exit | None:
    exits = getattr(room, "exits", None)
    if not isinstance(exits, list) or door >= len(exits):
        return None
    exit_obj = exits[door]
    if exit_obj is None:
        return None
    if not isinstance(exit_obj, Exit):
        return None
    return exit_obj


def _maybe_wander(mob: Character, room: Room) -> None:
    if _mob_has_act_flag(mob, ActFlag.SENTINEL):
        return
    if rng_mm.number_bits(3) != 0:
        return

    door = rng_mm.number_bits(5)
    if door > int(Direction.DOWN):
        return

    exit_obj = _valid_exit(room, door)
    if exit_obj is None:
        return

    destination = getattr(exit_obj, "to_room", None)
    if destination is None:
        return

    exit_flags = int(getattr(exit_obj, "exit_info", 0) or 0)
    if exit_flags & EX_CLOSED:
        return

    dest_flags = int(getattr(destination, "room_flags", 0) or 0)
    if dest_flags & int(RoomFlag.ROOM_NO_MOB):
        return

    if _mob_has_act_flag(mob, ActFlag.STAY_AREA):
        if getattr(destination, "area", None) is not getattr(room, "area", None):
            return

    if _mob_has_act_flag(mob, ActFlag.OUTDOORS) and dest_flags & int(RoomFlag.ROOM_INDOORS):
        return

    if _mob_has_act_flag(mob, ActFlag.INDOORS) and not (dest_flags & int(RoomFlag.ROOM_INDOORS)):
        return

    direction_name = Direction(door).name.lower()
    move_character(mob, direction_name)


def mobile_update() -> None:
    """Mirror ROM ``mobile_update`` scavenging, wandering, and mobprog triggers."""

    for mob in list(character_registry):
        if not getattr(mob, "is_npc", False):
            continue
        room = getattr(mob, "room", None)
        if room is None:
            continue
        if _is_charmed(mob):
            continue

        if _maybe_return_home(mob, room):
            continue

        area = getattr(room, "area", None)
        if area is not None and getattr(area, "empty", False):
            if not _mob_has_act_flag(mob, ActFlag.UPDATE_ALWAYS):
                continue

        shop, wealth = _resolve_shop_info(mob)
        if shop is not None and wealth > 0:
            try:
                gold = int(getattr(mob, "gold", 0))
            except (TypeError, ValueError):
                gold = 0
            try:
                silver = int(getattr(mob, "silver", 0))
            except (TypeError, ValueError):
                silver = 0
            if gold * 100 + silver < wealth:
                gold += wealth * rng_mm.number_range(1, 20) // 5_000_000
                silver += wealth * rng_mm.number_range(1, 20) // 50_000
                setattr(mob, "gold", gold)
                setattr(mob, "silver", silver)

        default_pos_raw = getattr(mob, "default_pos", getattr(mob, "position", Position.STANDING))
        try:
            default_pos = Position(int(default_pos_raw))
        except Exception:
            default_pos = Position.STANDING

        try:
            current_pos = Position(int(getattr(mob, "position", default_pos)))
        except Exception:
            current_pos = default_pos

        if current_pos == default_pos:
            if mobprog.mp_delay_trigger(mob):
                continue
            if mobprog.mp_random_trigger(mob):
                continue

        if current_pos != Position.STANDING:
            continue

        _maybe_scavenge(mob, room)
        _maybe_wander(mob, room)
