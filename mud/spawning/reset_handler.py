from __future__ import annotations

import logging

from mud.models.area import Area
from mud.models.character import character_registry
from mud.models.constants import (
    EX_CLOSED,
    EX_ISDOOR,
    EX_LOCKED,
    ITEM_INVENTORY,
    LEVEL_HERO,
    ROOM_VNUM_SCHOOL,
    ActFlag,
    AffectFlag,
    Direction,
    ExtraFlag,
    ItemType,
    Position,
    RoomFlag,
    convert_flags_from_letters,
)
from mud.registry import area_registry, mob_registry, obj_registry, room_registry, shop_registry
from mud.utils import rng_mm
from mud.world.vision import room_is_dark

from .mob_spawner import spawn_mob
from .obj_spawner import spawn_object
from .templates import MobInstance

RESET_TICKS = 3


_REVERSE_DIR = {
    Direction.NORTH.value: Direction.SOUTH.value,
    Direction.EAST.value: Direction.WEST.value,
    Direction.SOUTH.value: Direction.NORTH.value,
    Direction.WEST.value: Direction.EAST.value,
    Direction.UP.value: Direction.DOWN.value,
    Direction.DOWN.value: Direction.UP.value,
}


def _count_existing_mobs() -> dict[int, int]:
    """Rebuild MOB_INDEX_DATA->count style tallies from the current world."""

    counts: dict[int, int] = {}
    for room in room_registry.values():
        for mob in getattr(room, "people", []):
            if not isinstance(mob, MobInstance):
                continue
            proto = getattr(mob, "prototype", None)
            vnum = getattr(proto, "vnum", None)
            if vnum is None:
                continue
            counts[vnum] = counts.get(vnum, 0) + 1
    for vnum, proto in mob_registry.items():
        if hasattr(proto, "count"):
            proto.count = counts.get(vnum, 0)
    return counts


def _gather_object_state() -> tuple[dict[int, int], dict[int, list[object]]]:
    """Rebuild OBJ_INDEX_DATA->count and capture instances by prototype vnum."""

    counts: dict[int, int] = {}
    instances: dict[int, list[object]] = {}
    seen_chars: set[int] = set()

    def tally(obj: object) -> None:
        proto = getattr(obj, "prototype", None)
        vnum = getattr(proto, "vnum", None)
        if vnum is None:
            return
        counts[vnum] = counts.get(vnum, 0) + 1
        instances.setdefault(vnum, []).append(obj)
        for contained in getattr(obj, "contained_items", []) or []:
            tally(contained)

    def tally_character_items(char: object) -> None:
        if char is None:
            return
        ident = id(char)
        if ident in seen_chars:
            return
        seen_chars.add(ident)
        for carried in getattr(char, "inventory", []) or []:
            if carried is not None:
                tally(carried)
        equipment = getattr(char, "equipment", None)
        if isinstance(equipment, dict):
            for equipped in equipment.values():
                if equipped is not None:
                    tally(equipped)

    for room in room_registry.values():
        for obj in getattr(room, "contents", []):
            tally(obj)
        for occupant in getattr(room, "people", []) or []:
            tally_character_items(occupant)

    for char in character_registry:
        tally_character_items(char)

    for vnum, proto in obj_registry.items():
        if hasattr(proto, "count"):
            proto.count = counts.get(vnum, 0)

    return counts, instances


def _restore_exit_states(area: Area) -> None:
    """Copy rs_flags onto exit_info for exits and their reverse links."""

    for room in room_registry.values():
        if room.area is not area:
            continue
        exits = getattr(room, "exits", []) or []
        for idx, exit_obj in enumerate(exits):
            if exit_obj is None:
                continue
            base_flags = int(getattr(exit_obj, "rs_flags", 0) or 0)
            exit_obj.exit_info = base_flags
            to_room = getattr(exit_obj, "to_room", None)
            if to_room is None:
                continue
            rev_idx = _REVERSE_DIR.get(idx)
            if rev_idx is None:
                continue
            rev_exits = getattr(to_room, "exits", None)
            if not rev_exits or rev_idx >= len(rev_exits):
                continue
            rev_exit = rev_exits[rev_idx]
            if rev_exit is None:
                continue
            rev_exit.exit_info = int(getattr(rev_exit, "rs_flags", 0) or 0)


def _record_object_counts(obj: object, counts: dict[int, int]) -> None:
    """Recursively tally object instances by prototype vnum."""

    proto = getattr(obj, "prototype", None)
    vnum = getattr(proto, "vnum", None)
    if vnum is not None:
        counts[vnum] = counts.get(vnum, 0) + 1
    for contained in getattr(obj, "contained_items", []) or []:
        _record_object_counts(contained, counts)


def _count_existing_objects() -> dict[int, int]:
    """Rebuild OBJ_INDEX_DATA->count values based on current world state."""

    counts: dict[int, int] = {}

    for room in room_registry.values():
        for obj in getattr(room, "contents", []) or []:
            _record_object_counts(obj, counts)
        for occupant in getattr(room, "people", []) or []:
            for item in getattr(occupant, "inventory", []) or []:
                _record_object_counts(item, counts)
            equipment = getattr(occupant, "equipment", None)
            if isinstance(equipment, dict):
                for item in equipment.values():
                    _record_object_counts(item, counts)

    for vnum, proto in obj_registry.items():
        if hasattr(proto, "count"):
            proto.count = counts.get(vnum, 0)

    return counts


def _sync_object_count(obj_vnum: int, object_counts: dict[int, int]) -> None:
    """Keep the local object count cache aligned with prototype counters."""

    proto = obj_registry.get(obj_vnum)
    if proto is not None and hasattr(proto, "count"):
        try:
            object_counts[obj_vnum] = int(getattr(proto, "count", 0))
            return
        except Exception:
            object_counts[obj_vnum] = int(object_counts.get(obj_vnum, 0)) + 1
            return
    object_counts[obj_vnum] = object_counts.get(obj_vnum, 0) + 1


def _resolve_vnum(primary: int, secondary: int, registry: dict[int, object]) -> tuple[int, bool]:
    """Return the best available vnum, signalling if the fallback was used."""

    if primary and primary in registry and (primary > 1 or secondary not in registry):
        return primary, False
    if secondary and secondary in registry:
        return secondary, True
    if primary and primary in registry:
        return primary, False
    return primary, False


def _resolve_reset_limit(raw: int | None) -> int:
    """Mirror ROM's limit coercion for resets (old format, unlimited markers)."""

    if raw is None:
        return 1
    if raw > 50:
        return 6
    if raw in (-1, 0):
        return 999
    return raw


def _compute_object_level(obj: object, mob: object) -> int:
    """Derive object level for G/E resets using ROM parity rules.

    Shopkeepers keep the simplified random ranges from ROM for
    vendor stock, while regular mobs receive gear scaled from the
    last mob's level with `number_fuzzy` clamping below `LEVEL_HERO`.
    """

    if mob is None:
        return 0

    proto = getattr(obj, "prototype", None)
    mob_proto = getattr(mob, "prototype", None)

    try:
        item_type = int(getattr(proto, "item_type", 0) or 0)
    except Exception:
        item_type = 0

    is_shopkeeper = False
    if mob_proto is not None:
        keeper_vnum = getattr(mob_proto, "vnum", None)
        is_shopkeeper = keeper_vnum in shop_registry

    if is_shopkeeper:
        if getattr(proto, "new_format", False):
            return 0
        if item_type == int(ItemType.WAND):
            return rng_mm.number_range(10, 20)
        if item_type == int(ItemType.STAFF):
            return rng_mm.number_range(15, 25)
        if item_type == int(ItemType.ARMOR):
            return rng_mm.number_range(5, 15)
        if item_type == int(ItemType.WEAPON):
            return rng_mm.number_range(5, 15)
        if item_type == int(ItemType.TREASURE):
            return rng_mm.number_range(10, 20)
        return 0

    try:
        mob_level = int(getattr(mob, "level", 0) or 0)
    except Exception:
        mob_level = 0

    base_level = max(0, mob_level - 2)
    hero_cap = max(0, LEVEL_HERO - 1)
    if base_level > hero_cap:
        base_level = hero_cap

    fuzzed = rng_mm.number_fuzzy(base_level)
    if fuzzed > hero_cap:
        return hero_cap
    if fuzzed < 0:
        return 0
    return fuzzed


def _mark_shopkeeper_inventory(mob: MobInstance, obj: object) -> None:
    """Ensure shopkeeper inventory copies carry ITEM_INVENTORY like ROM."""

    proto = getattr(mob, "prototype", None)
    if getattr(proto, "vnum", None) not in shop_registry:
        return

    item_proto = getattr(obj, "prototype", None)
    if item_proto is None or not hasattr(item_proto, "extra_flags"):
        return

    extra_flags = getattr(item_proto, "extra_flags", 0)
    if isinstance(extra_flags, str):
        extra_flags = convert_flags_from_letters(extra_flags, ExtraFlag)

    item_proto.extra_flags = int(extra_flags) | int(ITEM_INVENTORY)
    obj.extra_flags = int(item_proto.extra_flags)


def apply_resets(area: Area) -> None:
    """Populate rooms based on ROM reset data semantics."""

    last_mob: MobInstance | None = None
    last_obj: object | None = None
    last_mob_level = 0
    object_counts, existing_objects = _gather_object_state()
    spawned_objects: dict[int, list[object]] = {vnum: list(instances) for vnum, instances in existing_objects.items()}
    mob_counts = _count_existing_mobs()
    object_counts = _count_existing_objects()

    _restore_exit_states(area)

    for reset in area.resets:
        cmd = (reset.command or "").upper()
        if cmd == "M":
            mob_vnum, used_fallback = _resolve_vnum(reset.arg1 or 0, reset.arg2 or 0, mob_registry)
            if used_fallback:
                global_limit = reset.arg3 or 0
                room_vnum = reset.arg4 or 0
                room_limit = 1
            else:
                global_limit = reset.arg2 or 0
                room_vnum = reset.arg3 or 0
                room_limit = reset.arg4 or 0

            room_limit = max(1, room_limit)

            room = room_registry.get(room_vnum)
            if mob_vnum <= 0 or room is None:
                logging.warning("Invalid M reset %s -> %s", mob_vnum, room_vnum)
                last_mob = None
                last_obj = None
                continue

            if global_limit > 0 and mob_counts.get(mob_vnum, 0) >= global_limit:
                last_mob = None
                last_obj = None
                continue

            if room_limit <= 0:
                last_mob = None
                last_obj = None
                continue

            existing_in_room = sum(
                1
                for mob in room.people
                if isinstance(mob, MobInstance) and getattr(getattr(mob, "prototype", None), "vnum", None) == mob_vnum
            )
            if existing_in_room >= room_limit:
                last_mob = None
                last_obj = None
                continue

            mob = spawn_mob(mob_vnum)
            if not mob:
                logging.warning("Invalid M reset %s (missing prototype)", mob_vnum)
                last_mob = None
                last_obj = None
                continue

            mob.is_npc = True
            proto_default = getattr(getattr(mob, "prototype", None), "default_pos", None)
            default_pos = proto_default or getattr(mob, "position", Position.STANDING)
            mob.default_pos = default_pos
            mob.mprog_target = None
            mob.mprog_delay = int(getattr(mob, "mprog_delay", 0))
            if not hasattr(mob, "mob_programs"):
                programs = list(getattr(getattr(mob, "prototype", None), "mprogs", []) or [])
                mob.mob_programs = programs

            if room_is_dark(room):
                mob.affected_by = int(getattr(mob, "affected_by", 0)) | int(AffectFlag.INFRARED)

            room_vnum_value = getattr(room, "vnum", None)
            if room_vnum_value is not None:
                prev_room = room_registry.get(room_vnum_value - 1)
                if prev_room is not None:
                    prev_flags = int(getattr(prev_room, "room_flags", 0) or 0)
                    if prev_flags & int(RoomFlag.ROOM_PET_SHOP):
                        mob.act = int(getattr(mob, "act", 0)) | int(ActFlag.PET)

            room.add_mob(mob)
            mob_counts[mob_vnum] = mob_counts.get(mob_vnum, 0) + 1
            proto = getattr(mob, "prototype", None)
            if proto is not None and hasattr(proto, "count"):
                proto.count = mob_counts[mob_vnum]
            try:
                mob_level = int(getattr(mob, "level", 0) or 0)
            except Exception:
                mob_level = 0
            hero_cap = max(0, LEVEL_HERO - 1)
            base_level = max(0, mob_level - 2)
            if base_level > hero_cap:
                base_level = hero_cap
            last_mob_level = base_level
            last_mob = mob
            last_obj = None
        elif cmd == "O":
            obj_vnum = reset.arg1 or 0
            limit = _resolve_reset_limit(reset.arg2)
            room_vnum = reset.arg3 or 0
            room = room_registry.get(room_vnum)
            if obj_vnum <= 0 or room is None:
                logging.warning("Invalid O reset %s -> %s", obj_vnum, room_vnum)
                last_obj = None
                continue
            if getattr(area, "nplayer", 0) > 0:
                last_obj = None
                continue
            existing_in_room = [
                obj
                for obj in getattr(room, "contents", [])
                if getattr(getattr(obj, "prototype", None), "vnum", None) == obj_vnum
            ]
            if len(existing_in_room) >= limit:
                last_obj = None
                continue
            obj = spawn_object(obj_vnum)
            if obj:
                hero_cap = max(0, LEVEL_HERO - 1)
                base_level = max(0, min(last_mob_level, hero_cap))
                fuzzed_level = rng_mm.number_fuzzy(base_level)
                if fuzzed_level > hero_cap:
                    fuzzed_level = hero_cap
                if fuzzed_level < 0:
                    fuzzed_level = 0
                proto = getattr(obj, "prototype", None)
                if proto is None or not getattr(proto, "new_format", False):
                    obj.level = fuzzed_level
                obj.cost = 0
                room.add_object(obj)
                _sync_object_count(obj_vnum, object_counts)
                last_obj = obj
                spawned_objects.setdefault(obj_vnum, []).append(obj)
            else:
                logging.warning("Invalid O reset %s -> %s", obj_vnum, room_vnum)
                last_obj = None
        elif cmd == "D":
            room_vnum = reset.arg1 or 0
            door = reset.arg2 or 0
            state = reset.arg3 or 0

            room = room_registry.get(room_vnum)
            if room is None:
                logging.warning("Invalid D reset room %s", room_vnum)
                continue
            if door < 0 or door >= len(room.exits):
                logging.warning("Invalid D reset direction %s in room %s", door, room_vnum)
                continue

            exit_obj = room.exits[door]
            if exit_obj is None:
                logging.warning("Invalid D reset missing exit %s in room %s", door, room_vnum)
                continue

            base_flags = int(getattr(exit_obj, "rs_flags", 0) or 0)
            if not base_flags:
                base_flags = int(getattr(exit_obj, "exit_info", 0) or 0)

            base_flags |= EX_ISDOOR
            base_flags &= ~(EX_CLOSED | EX_LOCKED)

            if state >= 1:
                base_flags |= EX_CLOSED
            if state >= 2:
                base_flags |= EX_LOCKED

            exit_obj.rs_flags = base_flags
            exit_obj.exit_info = base_flags
            to_room = getattr(exit_obj, "to_room", None)
            rev_idx = _REVERSE_DIR.get(door)
            if to_room is not None and rev_idx is not None:
                rev_exits = getattr(to_room, "exits", None)
                if rev_exits and rev_idx < len(rev_exits):
                    rev_exit = rev_exits[rev_idx]
                    if rev_exit is not None:
                        rev_exit.rs_flags = base_flags
                        rev_exit.exit_info = base_flags
        elif cmd == "G":
            obj_vnum, used_fallback = _resolve_vnum(reset.arg1 or 0, reset.arg2 or 0, obj_registry)
            limit_raw = reset.arg2
            if used_fallback:
                limit_raw = reset.arg3
            limit = _resolve_reset_limit(limit_raw)
            proto_count = object_counts.get(obj_vnum, 0)
            if not last_mob:
                logging.warning("Invalid G reset %s (no LastMob)", obj_vnum)
                continue
            existing = [
                o
                for o in getattr(last_mob, "inventory", [])
                if getattr(getattr(o, "prototype", None), "vnum", None) == obj_vnum
            ]
            if len(existing) >= limit:
                continue
            proto_count = object_counts.get(obj_vnum, 0)
            is_shopkeeper = getattr(getattr(last_mob, "prototype", None), "vnum", None) in shop_registry
            if proto_count >= limit and rng_mm.number_range(0, 4) != 0:
                continue
            obj = spawn_object(obj_vnum)
            if obj:
                obj.level = _compute_object_level(obj, last_mob)
                if is_shopkeeper:
                    _mark_shopkeeper_inventory(last_mob, obj)
                _sync_object_count(obj_vnum, object_counts)
                last_mob.add_to_inventory(obj)
                last_obj = obj
                spawned_objects.setdefault(obj_vnum, []).append(obj)
            else:
                logging.warning("Invalid G reset %s", obj_vnum)
        elif cmd == "E":
            obj_vnum, used_fallback = _resolve_vnum(reset.arg1 or 0, reset.arg2 or 0, obj_registry)
            limit_raw = reset.arg2
            slot = reset.arg3 or 0
            if used_fallback:
                limit_raw = reset.arg3
                slot = reset.arg4 or slot
            limit = _resolve_reset_limit(limit_raw)
            proto_count = object_counts.get(obj_vnum, 0)
            if not last_mob:
                logging.warning("Invalid E reset %s (no LastMob)", obj_vnum)
                continue
            existing = [
                o
                for o in getattr(last_mob, "inventory", [])
                if getattr(getattr(o, "prototype", None), "vnum", None) == obj_vnum
            ]
            if len(existing) >= limit:
                continue
            proto_count = object_counts.get(obj_vnum, 0)
            is_shopkeeper = getattr(getattr(last_mob, "prototype", None), "vnum", None) in shop_registry
            if proto_count >= limit and rng_mm.number_range(0, 4) != 0:
                continue
            obj = spawn_object(obj_vnum)
            if obj:
                obj.level = _compute_object_level(obj, last_mob)
                if is_shopkeeper:
                    _mark_shopkeeper_inventory(last_mob, obj)
                _sync_object_count(obj_vnum, object_counts)
                last_mob.equip(obj, slot)
                last_obj = obj
                spawned_objects.setdefault(obj_vnum, []).append(obj)
            else:
                logging.warning("Invalid E reset %s", obj_vnum)
        elif cmd == "P":
            obj_vnum, _ = _resolve_vnum(reset.arg1 or 0, reset.arg2 or 0, obj_registry)
            container_vnum = reset.arg3 or 0
            target_count = max(1, int(reset.arg4 or 1))
            limit_raw = reset.arg2 if reset.arg2 is not None else 0
            limit = _resolve_reset_limit(limit_raw)
            if obj_vnum <= 0 or container_vnum <= 0:
                logging.warning("Invalid P reset %s -> %s", obj_vnum, container_vnum)
                last_obj = None
                continue
            if getattr(area, "nplayer", 0) > 0:
                last_obj = None
                continue
            obj_proto = obj_registry.get(obj_vnum)
            container_proto = obj_registry.get(container_vnum)
            if obj_proto is None or container_proto is None:
                logging.warning("Invalid P reset %s -> %s (missing prototype)", obj_vnum, container_vnum)
                last_obj = None
                continue
            remaining_global = max(0, limit - object_counts.get(obj_vnum, 0))
            if remaining_global <= 0:
                last_obj = None
                continue
            container_obj: object | None = None
            if last_obj and getattr(getattr(last_obj, "prototype", None), "vnum", None) == container_vnum:
                location = getattr(last_obj, "location", None)
                if location is not None and getattr(location, "area", None) is area:
                    container_obj = last_obj
            if not container_obj:
                candidates = spawned_objects.get(container_vnum) or []
                for candidate in reversed(candidates):
                    room = getattr(candidate, "location", None)
                    if room is not None and getattr(room, "area", None) is area:
                        container_obj = candidate
                        break
            if not container_obj:
                for room in room_registry.values():
                    if room.area is not area:
                        continue
                    for obj in getattr(room, "contents", []):
                        if getattr(getattr(obj, "prototype", None), "vnum", None) == container_vnum:
                            container_obj = obj
                            spawned_objects.setdefault(container_vnum, []).append(obj)
                            break
                    if container_obj:
                        break
            if not container_obj:
                logging.warning("Invalid P reset %s -> %s (no container instance)", obj_vnum, container_vnum)
                last_obj = None
                continue

            if getattr(area, "nplayer", 0) > 0:
                last_obj = container_obj
                continue

            effective_limit = limit if limit > 0 else 999
            current_total = object_counts.get(obj_vnum, 0)
            if effective_limit != 999 and current_total >= effective_limit:
                last_obj = container_obj
                continue

            existing = [
                o
                for o in getattr(container_obj, "contained_items", [])
                if getattr(getattr(o, "prototype", None), "vnum", None) == obj_vnum
            ]
            if len(existing) >= target_count:
                last_obj = container_obj
                continue
            to_make = min(target_count - len(existing), remaining_global)
            made = 0
            for _ in range(to_make):
                if effective_limit != 999 and object_counts.get(obj_vnum, 0) >= effective_limit:
                    break
                obj = spawn_object(obj_vnum)
                if not obj:
                    logging.warning("Invalid P reset %s", obj_vnum)
                    break
                container_obj.contained_items.append(obj)
                spawned_objects.setdefault(obj_vnum, []).append(obj)
                made += 1
                _sync_object_count(obj_vnum, object_counts)
                remaining_global = max(0, limit - object_counts.get(obj_vnum, 0))
                if remaining_global <= 0:
                    break
            try:
                container_obj.value[1] = container_obj.prototype.value[1]
            except Exception:
                pass
            last_obj = container_obj
        elif cmd == "R":
            room_vnum = reset.arg1 or 0
            max_dirs = int(reset.arg2 or 0)
            if (room_vnum <= 0 or room_vnum not in room_registry) and (reset.arg2 or 0) in room_registry:
                # JSON layout: arg2=room vnum, arg3=max dirs
                room_vnum = reset.arg2 or 0
                max_dirs = int(reset.arg3 or 0)
            room = room_registry.get(room_vnum)
            if not room or not room.exits:
                logging.warning("Invalid R reset %s", room_vnum)
                continue
            n = min(max_dirs, len(room.exits))
            # Fisher–Yates-like partial shuffle matching ROM loop
            for d0 in range(0, max(0, n - 1)):
                d1 = rng_mm.number_range(d0, n - 1)
                room.exits[d0], room.exits[d1] = room.exits[d1], room.exits[d0]


def reset_area(area: Area) -> None:
    """Reapply resets for an area without purging existing mobs or objects."""
    apply_resets(area)


def reset_tick() -> None:
    """Advance area ages and run ROM-style area_update scheduling."""

    for area in area_registry.values():
        nplayer = int(getattr(area, "nplayer", 0) or 0)
        if nplayer > 0:
            area.empty = False

        area.age = int(getattr(area, "age", 0)) + 1
        if area.age < 3:
            continue

        should_reset = False
        if (not getattr(area, "empty", False) and (nplayer == 0 or area.age >= 15)) or area.age >= 31:
            should_reset = True

        if not should_reset:
            continue

        reset_area(area)
        area.age = rng_mm.number_range(0, 3)

        school_room = room_registry.get(ROOM_VNUM_SCHOOL)
        if school_room is not None and school_room.area is area:
            area.age = 13  # Mud School resets quickly after repop
        elif nplayer == 0:
            area.empty = True
