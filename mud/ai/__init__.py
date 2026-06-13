"""AI helpers mirroring ROM update handlers."""

from __future__ import annotations

from collections.abc import Iterable

import mud.mobprog as mobprog
from mud.models.character import Character, character_registry
from mud.models.constants import (
    EX_CLOSED,
    ActFlag,
    AffectFlag,
    Direction,
    PlayerFlag,
    Position,
    RoomFlag,
    WearFlag,
)
from mud.models.object import Object
from mud.models.room import Exit, Room
from mud.utils import rng_mm
from mud.world.movement import move_character

from .aggressive import aggressive_update

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


def _can_loot(mob: Character, obj: Object) -> bool:
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
    owner_group = getattr(owner_char, "group", None)
    if mob_group and owner_group and mob_group == owner_group:
        return True

    return False


def _room_contents(room: Room | None) -> Iterable[Object]:
    if room is None:
        return []
    contents = getattr(room, "contents", None)
    if isinstance(contents, list):
        return list(contents)
    return []


def _take_object(mob: Character, obj: Object) -> None:
    room = getattr(obj, "in_room", None) or getattr(obj, "location", None) or getattr(mob, "room", None)
    if room is not None:
        contents = getattr(room, "contents", None)
        if isinstance(contents, list) and obj in contents:
            contents.remove(obj)

    if hasattr(obj, "in_room"):
        obj.in_room = None
    if hasattr(obj, "location"):
        obj.location = None
    if hasattr(obj, "in_obj"):
        obj.in_obj = None
    # obj.carried_by is set by add_object / add_to_inventory below

    # INV-039 / class-13: route through head-insert chokepoint.
    # Character.add_object / MobInstance.add_to_inventory handles carry_number
    # and carry_weight internally — no manual counter update needed.
    add_obj = getattr(mob, "add_object", None)
    if callable(add_obj):
        add_obj(obj)
    else:
        add_inv = getattr(mob, "add_to_inventory", None)
        if callable(add_inv):
            add_inv(obj)
        else:
            inventory = getattr(mob, "inventory", None)
            if isinstance(inventory, list) and obj not in inventory:
                inventory.insert(0, obj)

    # mirroring ROM src/update.c:491 — act("$n gets $p.", ch, obj_best, NULL, TO_ROOM)
    # act_to_room handles per-recipient formatting + TRIG_ACT dispatch (src/comm.c:2384).
    room = getattr(mob, "room", None)
    if room is not None:
        from mud.utils.act import act_to_room

        act_to_room(room, "$n gets $p.", mob, arg1=obj, exclude=mob)


def _maybe_scavenge(mob: Character, room: Room) -> None:
    if not _mob_has_act_flag(mob, ActFlag.SCAVENGER):
        return
    contents = list(_room_contents(room))
    if not contents:
        return
    if rng_mm.number_bits(6) != 0:
        return

    best_obj: Object | None = None
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

    # mirroring ROM src/update.c:498 — wander draws a SINGLE 5-bit direction
    # `(door = number_bits(5)) <= 5` and aborts the whole wander when the roll
    # exceeds 5 (so a mob only wanders on 6/32 of otherwise-eligible ticks).
    # NOT number_door() (the do_flee/do_mpflee primitive, src/db.c:3541), which
    # re-rolls with a 3-bit mask until ≤5 and therefore always returns a valid
    # door — that over-wanders ~5× and desyncs the shared Mitchell-Moore stream.
    door = rng_mm.number_bits(5)
    if door > 5:
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

    # mirroring ROM src/update.c:416 — mobile_update walks ``char_list``, which
    # src/db.c:2256-2257 (create_mobile) head-inserts, so ROM visits the NEWEST
    # mob first. ``character_registry`` is append-order, so iterate it reversed
    # — load-bearing for the shared RNG draw order (shop-wealth rolls, scavenger
    # 1/64, wander door rolls), like violence_tick/char_update/obj_update. GL-042.
    for mob in list(reversed(character_registry)):
        # mirroring ROM extract_char re-linking — a char removed from char_list
        # mid-tick is never revisited in ROM's walk; skip extracted mobs. GL-042.
        if mob not in character_registry:
            continue
        if not getattr(mob, "is_npc", False):
            continue
        room = getattr(mob, "room", None)
        if room is None:
            continue
        if _is_charmed(mob):
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
                mob.gold = gold
                mob.silver = silver

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
