from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set

from mud.models.area import Area
from mud.models.character import character_registry
from mud.models.constants import (
    ITEM_INVENTORY,
    ExtraFlag,
    EX_CLOSED,
    EX_ISDOOR,
    EX_LOCKED,
    Direction,
    ItemType,
    LEVEL_HERO,
    Position,
    ROOM_VNUM_SCHOOL,
    convert_flags_from_letters,
)
from mud.registry import room_registry, area_registry, mob_registry, obj_registry, shop_registry
from .mob_spawner import spawn_mob
from .obj_spawner import spawn_object
from .templates import MobInstance
from mud.utils import rng_mm

RESET_TICKS = 3


_REVERSE_DIR = {
    Direction.NORTH.value: Direction.SOUTH.value,
    Direction.EAST.value: Direction.WEST.value,
    Direction.SOUTH.value: Direction.NORTH.value,
    Direction.WEST.value: Direction.EAST.value,
    Direction.UP.value: Direction.DOWN.value,
    Direction.DOWN.value: Direction.UP.value,
}


_SKILL_MIN_LEVELS: Dict[int, int] | None = None
_SKILL_NAME_TO_ID: Dict[str, int] | None = None


def _load_skill_table() -> None:
    """Parse src/const.c for skill_table level data on demand."""

    global _SKILL_MIN_LEVELS, _SKILL_NAME_TO_ID
    if _SKILL_MIN_LEVELS is not None and _SKILL_NAME_TO_ID is not None:
        return

    const_path = Path(__file__).resolve().parents[2] / "src" / "const.c"
    try:
        content = const_path.read_text(encoding="latin-1")
    except OSError:
        _SKILL_MIN_LEVELS = {}
        _SKILL_NAME_TO_ID = {}
        return

    marker = "const struct skill_type skill_table[MAX_SKILL] = {"
    start = content.find(marker)
    if start == -1:
        _SKILL_MIN_LEVELS = {}
        _SKILL_NAME_TO_ID = {}
        return

    brace_start = content.find("{", start)
    depth = 1
    pos = brace_start + 1
    while pos < len(content) and depth > 0:
        char = content[pos]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
        pos += 1

    table_body = content[brace_start + 1 : pos - 1]
    entry_pattern = re.compile(r'\{\s*"([^"]+)",\s*\{([^}]*)\},', re.MULTILINE)

    levels: Dict[int, int] = {}
    names: Dict[str, int] = {}
    index = 0
    for match in entry_pattern.finditer(table_body):
        name = match.group(1)
        raw_levels = match.group(2)
        min_level = 53
        for token in raw_levels.split(','):
            value = token.strip()
            if not value:
                continue
            try:
                level = int(value)
            except ValueError:
                continue
            if level < min_level:
                min_level = level
        levels[index] = min_level
        names[name.lower()] = index
        index += 1

    _SKILL_MIN_LEVELS = levels
    _SKILL_NAME_TO_ID = names


def _lookup_skill_min_level(skill_id: int) -> Optional[int]:
    if skill_id <= 0:
        return None
    _load_skill_table()
    assert _SKILL_MIN_LEVELS is not None
    return _SKILL_MIN_LEVELS.get(skill_id)


def _lookup_skill_index(name: str) -> Optional[int]:
    if not name:
        return None
    _load_skill_table()
    assert _SKILL_NAME_TO_ID is not None
    return _SKILL_NAME_TO_ID.get(name.lower())


def _count_existing_mobs() -> Dict[int, int]:
    """Rebuild MOB_INDEX_DATA->count style tallies from the current world."""

    counts: Dict[int, int] = {}
    for room in room_registry.values():
        for mob in getattr(room, 'people', []):
            if not isinstance(mob, MobInstance):
                continue
            proto = getattr(mob, 'prototype', None)
            vnum = getattr(proto, 'vnum', None)
            if vnum is None:
                continue
            counts[vnum] = counts.get(vnum, 0) + 1
    for vnum, proto in mob_registry.items():
        if hasattr(proto, 'count'):
            proto.count = counts.get(vnum, 0)
    return counts


def _gather_object_state() -> Tuple[Dict[int, int], Dict[int, List[object]]]:
    """Rebuild OBJ_INDEX_DATA->count and capture instances by prototype vnum."""

    counts: Dict[int, int] = {}
    instances: Dict[int, List[object]] = {}
    seen_chars: Set[int] = set()

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


def _resolve_reset_limit(raw: Optional[int]) -> int:
    """Mirror ROM's limit coercion for resets (old format, unlimited markers)."""

    if raw is None:
        return 1
    if raw > 50:
        return 6
    if raw in (-1, 0):
        return 999
    return raw


def _resolve_item_type(proto: object) -> Optional[int]:
    raw_type = getattr(proto, "item_type", None)
    if isinstance(raw_type, ItemType):
        return int(raw_type)
    if isinstance(raw_type, int):
        return raw_type
    try:
        return int(raw_type)
    except (TypeError, ValueError):
        pass
    if isinstance(raw_type, str):
        try:
            return ItemType[raw_type.upper()].value
        except (KeyError, AttributeError):
            return None
    return None


def _compute_mob_reset_level(mob: Optional[object]) -> int:
    if mob is None:
        return 0
    hero_cap = LEVEL_HERO - 1
    level = getattr(mob, "level", None)
    if level is None:
        proto = getattr(mob, "prototype", None)
        level = getattr(proto, "level", 0) if proto is not None else 0
    try:
        level_int = int(level)
    except (TypeError, ValueError):
        level_int = 0
    base = level_int - 2
    if base < 0:
        base = 0
    if base > hero_cap:
        base = hero_cap
    return base


def _determine_shopkeeper_level(obj_proto: object) -> int:
    if obj_proto is None:
        return 0
    if getattr(obj_proto, "new_format", False):
        try:
            return int(getattr(obj_proto, "level", 0) or 0)
        except (TypeError, ValueError):
            return 0

    item_type = _resolve_item_type(obj_proto)
    if item_type is None:
        return 0

    if item_type in (
        int(ItemType.PILL),
        int(ItemType.POTION),
        int(ItemType.SCROLL),
    ):
        olevel = 53
        values = list(getattr(obj_proto, "value", []) or [])
        for skill_id in values[1:5]:
            try:
                skill_index = int(skill_id)
            except (TypeError, ValueError):
                continue
            if skill_index <= 0:
                continue
            skill_level = _lookup_skill_min_level(skill_index)
            if skill_level is None:
                continue
            if skill_level < olevel:
                olevel = skill_level
        return max(0, (olevel * 3 // 4) - 2)

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


def _determine_object_level(
    obj_proto: object,
    *,
    mob_reset_level: int,
    is_shopkeeper: bool,
) -> int:
    if obj_proto is None:
        return 0
    if is_shopkeeper:
        return _determine_shopkeeper_level(obj_proto)

    hero_cap = LEVEL_HERO - 1
    base = rng_mm.number_fuzzy(mob_reset_level)
    return min(base, hero_cap)


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
    setattr(obj, "extra_flags", int(item_proto.extra_flags))


def apply_resets(area: Area) -> None:
    """Populate rooms based on ROM reset data semantics."""

    last_mob: Optional[MobInstance] = None
    last_obj: Optional[object] = None
    last_mob_level: int = 0
    object_counts, existing_objects = _gather_object_state()
    spawned_objects: Dict[int, List[object]] = {
        vnum: list(instances) for vnum, instances in existing_objects.items()
    }
    mob_counts = _count_existing_mobs()

    _restore_exit_states(area)

    for reset in area.resets:
        cmd = (reset.command or '').upper()
        if cmd == 'M':
            mob_vnum = reset.arg1 or 0
            global_limit = reset.arg2 or 0
            room_vnum = reset.arg3 or 0
            room_limit = reset.arg4 or 0

            room = room_registry.get(room_vnum)
            if mob_vnum <= 0 or room is None:
                logging.warning('Invalid M reset %s -> %s', mob_vnum, room_vnum)
                last_mob = None
                last_obj = None
                last_mob_level = 0
                continue

            if global_limit > 0 and mob_counts.get(mob_vnum, 0) >= global_limit:
                last_mob = None
                last_obj = None
                last_mob_level = 0
                continue

            if room_limit <= 0:
                last_mob = None
                last_obj = None
                last_mob_level = 0
                continue

            existing_in_room = sum(
                1
                for mob in room.people
                if isinstance(mob, MobInstance)
                and getattr(getattr(mob, 'prototype', None), 'vnum', None) == mob_vnum
            )
            if existing_in_room >= room_limit:
                last_mob = None
                last_obj = None
                last_mob_level = 0
                continue

            mob = spawn_mob(mob_vnum)
            if not mob:
                logging.warning('Invalid M reset %s (missing prototype)', mob_vnum)
                last_mob = None
                last_obj = None
                last_mob_level = 0
                continue

            setattr(mob, "is_npc", True)
            proto_default = getattr(getattr(mob, "prototype", None), "default_pos", None)
            default_pos = proto_default or getattr(mob, "position", Position.STANDING)
            setattr(mob, "default_pos", default_pos)
            setattr(mob, "mprog_target", None)
            setattr(mob, "mprog_delay", int(getattr(mob, "mprog_delay", 0)))
            if not hasattr(mob, "mob_programs"):
                programs = list(getattr(getattr(mob, "prototype", None), "mprogs", []) or [])
                setattr(mob, "mob_programs", programs)

            room.add_mob(mob)
            mob_counts[mob_vnum] = mob_counts.get(mob_vnum, 0) + 1
            proto = getattr(mob, 'prototype', None)
            if proto is not None and hasattr(proto, 'count'):
                proto.count = mob_counts[mob_vnum]
            last_mob = mob
            last_mob_level = _compute_mob_reset_level(mob)
            last_obj = None
        elif cmd == 'O':
            obj_vnum = reset.arg1 or 0
            limit = _resolve_reset_limit(reset.arg2)
            room_vnum = reset.arg3 or 0
            room = room_registry.get(room_vnum)
            if obj_vnum <= 0 or room is None:
                logging.warning('Invalid O reset %s -> %s', obj_vnum, room_vnum)
                last_obj = None
                continue
            if getattr(area, 'nplayer', 0) > 0:
                last_obj = None
                continue
            existing_in_room = [
                obj
                for obj in getattr(room, 'contents', [])
                if getattr(getattr(obj, 'prototype', None), 'vnum', None) == obj_vnum
            ]
            if len(existing_in_room) >= limit:
                last_obj = None
                continue
            spawn_level = min(rng_mm.number_fuzzy(last_mob_level), LEVEL_HERO - 1)
            obj = spawn_object(obj_vnum, level=spawn_level)
            if obj:
                room.add_object(obj)
                object_counts[obj_vnum] = object_counts.get(obj_vnum, 0) + 1
                last_obj = obj
                spawned_objects.setdefault(obj_vnum, []).append(obj)
            else:
                logging.warning('Invalid O reset %s -> %s', obj_vnum, room_vnum)
                last_obj = None
        elif cmd == 'D':
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
        elif cmd == 'G':
            obj_vnum = reset.arg1 or 0
            limit = _resolve_reset_limit(reset.arg2)
            if not last_mob:
                logging.warning('Invalid G reset %s (no LastMob)', obj_vnum)
                continue
            existing = [
                o
                for o in getattr(last_mob, 'inventory', [])
                if getattr(getattr(o, 'prototype', None), 'vnum', None) == obj_vnum
            ]
            if len(existing) >= limit:
                continue
            proto_count = object_counts.get(obj_vnum, 0)
            is_shopkeeper = getattr(getattr(last_mob, 'prototype', None), 'vnum', None) in shop_registry
            if proto_count >= limit and rng_mm.number_range(0, 4) != 0:
                continue
            obj_proto = obj_registry.get(obj_vnum)
            item_level = _determine_object_level(
                obj_proto,
                mob_reset_level=last_mob_level,
                is_shopkeeper=is_shopkeeper,
            )
            obj = spawn_object(obj_vnum, level=item_level)
            if obj:
                if is_shopkeeper:
                    _mark_shopkeeper_inventory(last_mob, obj)
                object_counts[obj_vnum] = proto_count + 1
                last_mob.add_to_inventory(obj)
                last_obj = obj
                spawned_objects.setdefault(obj_vnum, []).append(obj)
            else:
                logging.warning('Invalid G reset %s', obj_vnum)
        elif cmd == 'E':
            obj_vnum = reset.arg1 or 0
            limit = _resolve_reset_limit(reset.arg2)
            slot = reset.arg3 or 0
            if not last_mob:
                logging.warning('Invalid E reset %s (no LastMob)', obj_vnum)
                continue
            existing = [
                o
                for o in getattr(last_mob, 'inventory', [])
                if getattr(getattr(o, 'prototype', None), 'vnum', None) == obj_vnum
            ]
            if len(existing) >= limit:
                continue
            proto_count = object_counts.get(obj_vnum, 0)
            is_shopkeeper = getattr(getattr(last_mob, 'prototype', None), 'vnum', None) in shop_registry
            if proto_count >= limit and rng_mm.number_range(0, 4) != 0:
                continue
            obj_proto = obj_registry.get(obj_vnum)
            item_level = _determine_object_level(
                obj_proto,
                mob_reset_level=last_mob_level,
                is_shopkeeper=is_shopkeeper,
            )
            obj = spawn_object(obj_vnum, level=item_level)
            if obj:
                if is_shopkeeper:
                    _mark_shopkeeper_inventory(last_mob, obj)
                object_counts[obj_vnum] = proto_count + 1
                last_mob.equip(obj, slot)
                last_obj = obj
                spawned_objects.setdefault(obj_vnum, []).append(obj)
            else:
                logging.warning('Invalid E reset %s', obj_vnum)
        elif cmd == 'P':
            obj_vnum = reset.arg1 or 0
            container_vnum = reset.arg3 or 0
            target_count = max(1, int(reset.arg4 or 1))
            limit = _resolve_reset_limit(reset.arg2)
            if obj_vnum <= 0 or container_vnum <= 0:
                logging.warning('Invalid P reset %s -> %s', obj_vnum, container_vnum)
                last_obj = None
                continue
            if getattr(area, 'nplayer', 0) > 0:
                last_obj = None
                continue
            obj_proto = obj_registry.get(obj_vnum)
            container_proto = obj_registry.get(container_vnum)
            if obj_proto is None or container_proto is None:
                logging.warning('Invalid P reset %s -> %s (missing prototype)', obj_vnum, container_vnum)
                last_obj = None
                continue
            remaining_global = max(0, limit - object_counts.get(obj_vnum, 0))
            if remaining_global <= 0:
                last_obj = None
                continue
            container_obj: Optional[object] = None
            if last_obj and getattr(getattr(last_obj, 'prototype', None), 'vnum', None) == container_vnum:
                location = getattr(last_obj, 'location', None)
                if location is not None and getattr(location, 'area', None) is area:
                    container_obj = last_obj
            if not container_obj:
                candidates = spawned_objects.get(container_vnum) or []
                for candidate in reversed(candidates):
                    room = getattr(candidate, 'location', None)
                    if room is not None and getattr(room, 'area', None) is area:
                        container_obj = candidate
                        break
            if not container_obj:
                for room in room_registry.values():
                    if room.area is not area:
                        continue
                    for obj in getattr(room, 'contents', []):
                        if getattr(getattr(obj, 'prototype', None), 'vnum', None) == container_vnum:
                            container_obj = obj
                            spawned_objects.setdefault(container_vnum, []).append(obj)
                            break
                    if container_obj:
                        break
            if not container_obj:
                logging.warning('Invalid P reset %s -> %s (no container instance)', obj_vnum, container_vnum)
                last_obj = None
                continue
            existing = [
                o
                for o in getattr(container_obj, 'contained_items', [])
                if getattr(getattr(o, 'prototype', None), 'vnum', None) == obj_vnum
            ]
            if len(existing) >= target_count:
                last_obj = container_obj
                continue
            to_make = min(target_count - len(existing), remaining_global)
            made = 0
            base_level = getattr(container_obj, 'level', None)
            if base_level is None:
                proto = getattr(container_obj, 'prototype', None)
                base_level = getattr(proto, 'level', 0) if proto is not None else 0
            try:
                container_level = int(base_level)
            except (TypeError, ValueError):
                container_level = 0
            for _ in range(to_make):
                item_level = rng_mm.number_fuzzy(container_level)
                obj = spawn_object(obj_vnum, level=item_level)
                if not obj:
                    logging.warning('Invalid P reset %s', obj_vnum)
                    break
                getattr(container_obj, 'contained_items').append(obj)
                spawned_objects.setdefault(obj_vnum, []).append(obj)
                made += 1
                remaining_global -= 1
                object_counts[obj_vnum] = object_counts.get(obj_vnum, 0) + 1
                if remaining_global <= 0:
                    break
            try:
                container_obj.value[1] = container_obj.prototype.value[1]
            except Exception:
                pass
            last_obj = container_obj
        elif cmd == 'R':
            room_vnum = reset.arg1 or 0
            max_dirs = int(reset.arg2 or 0)
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
        if (
            not getattr(area, "empty", False)
            and (nplayer == 0 or area.age >= 15)
        ) or area.age >= 31:
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
