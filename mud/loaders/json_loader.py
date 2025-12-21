"""
JSON area loader for QuickMUD.

This loader reads areas from JSON files created by the convert_are_to_json.py script
with complete field mapping from the original ROM .are format.
"""

import json
import logging
from pathlib import Path
from typing import Any

from mud.models.constants import Direction, RoomFlag, Sector, Sex
from mud.registry import area_registry, mob_registry, obj_registry, room_registry

from ..models.area import Area
from ..models.mob import MobIndex, MobProgram
from ..models.obj import ObjIndex
from ..models.room import Exit, ExtraDescr, Room
from ..models.room_json import ResetJson
from ..mobprog import register_program_code, resolve_trigger_flag
from .specials_loader import apply_specials_from_json


def _rom_flags_to_int(flags_str: str) -> int:
    """Convert ROM-style letter flag strings to their integer bitfield."""

    if not flags_str:
        return 0

    if isinstance(flags_str, int):
        return flags_str

    result = 0
    pending_number = 0
    building_number = False
    i = 0
    length = len(flags_str)

    while i < length:
        ch = flags_str[i]

        if ch.isspace() or ch == "|":
            if building_number:
                result += pending_number
                pending_number = 0
                building_number = False
            i += 1
            continue

        if ch.isdigit():
            pending_number = pending_number * 10 + int(ch)
            building_number = True
            i += 1
            continue

        if building_number:
            result += pending_number
            pending_number = 0
            building_number = False

        if i + 1 < length:
            token = flags_str[i : i + 2]
            if token in {"aa", "bb", "cc", "dd"}:
                offset = {"aa": 0, "bb": 1, "cc": 2, "dd": 3}[token]
                result |= 1 << (26 + offset)
                i += 2
                continue

        if "A" <= ch <= "Z":
            result |= 1 << (ord(ch) - ord("A"))
        elif "a" <= ch <= "z":
            result |= 1 << (ord(ch) - ord("a") + 26)

        i += 1

    if building_number:
        result += pending_number

    return result


def _parse_exit_flags(raw: Any) -> int:
    """Convert exit flag representations (numbers or ROM letters) to bitmasks."""

    if isinstance(raw, int):
        return raw
    if isinstance(raw, str):
        stripped = raw.strip()
        if not stripped or stripped == "0":
            return 0
        try:
            return int(stripped)
        except ValueError:
            return _rom_flags_to_int(stripped)
    if isinstance(raw, list):
        bits = 0
        for entry in raw:
            bits |= _parse_exit_flags(entry)
        return bits
    return 0


def _parse_room_flags(raw: Any) -> int:
    """Convert room flag representations to integer bitmasks."""

    if isinstance(raw, int):
        return raw
    if isinstance(raw, str):
        stripped = raw.strip()
        if not stripped or stripped == "0":
            return 0
        try:
            return int(stripped)
        except ValueError:
            return _rom_flags_to_int(stripped)
    if isinstance(raw, list):
        bits = 0
        for entry in raw:
            bits |= _parse_room_flags(entry)
        return bits
    return 0


def _coerce_reset_arg(value: Any) -> int:
    """Best-effort conversion of reset arguments to integers."""

    if value is None:
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return 0
        try:
            return int(stripped)
        except ValueError:
            return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


logger = logging.getLogger(__name__)


def _resolve_room_target(command: str, reset: ResetJson, current_room: int | None) -> tuple[int | None, int | None]:
    """Determine which room a reset applies to and the next baseline room."""

    cmd = command.upper()
    room_vnum: int | None = None
    new_current = current_room

    if cmd == "M":
        room_vnum = int(reset.arg3 or 0) or None
        new_current = room_vnum or current_room
    elif cmd == "O":
        room_vnum = int(reset.arg3 or 0) or None
        new_current = room_vnum or current_room
    elif cmd in {"P", "G", "E"}:
        room_vnum = current_room
    elif cmd in {"D", "R"}:
        room_vnum = int(reset.arg1 or 0) or None
        new_current = room_vnum or current_room
    else:
        room_vnum = current_room

    return room_vnum, new_current


def load_area_from_json(json_file_path: str) -> Area:
    """Load a complete area from JSON file with all ROM fields."""

    with open(json_file_path) as f:
        data = json.load(f)

    # Handle two different JSON formats
    if "area" in data:
        # Format 2: Nested structure with area object
        area_data = data["area"]
        area = Area(
            vnum=area_data.get("vnum", 0),
            name=area_data.get("name", ""),
            file_name=area_data.get("filename", Path(json_file_path).stem),
            low_range=area_data.get("min_level", 0),
            high_range=area_data.get("max_level", 0),
            builders=area_data.get("builders", ""),
            credits=area_data.get("credits", ""),
            min_vnum=area_data.get("min_vnum", area_data.get("vnum", 0)),
            max_vnum=area_data.get("max_vnum", area_data.get("vnum", 0)),
            area_flags=area_data.get("area_flags", 0),
            security=area_data.get("security", 0),
        )
        rooms_key = "rooms"
        mobs_key = "mobs"
        objects_key = "objects"
    else:
        # Format 1: Root-level structure with vnum_range
        vnum_range = data.get("vnum_range", {"min": 0, "max": 0})
        area = Area(
            vnum=vnum_range.get("min", 0),  # Use min vnum as area vnum
            name=data.get("name", ""),
            file_name=Path(json_file_path).stem,
            low_range=vnum_range.get("min", 0),
            high_range=vnum_range.get("max", 0),
            builders=", ".join(data.get("builders", [])),
            min_vnum=vnum_range.get("min", 0),
            max_vnum=vnum_range.get("max", 0),
            area_flags=0,  # Not in JSON, default to 0
            security=0,  # Not in JSON, default to 0
        )
        rooms_key = "rooms"
        mobs_key = "mobiles"  # Different key in format 1
        objects_key = "objects"

    # ROM `load_area` seeds freshly loaded areas with age 15 so the update
    # loop counts down before the first reset and so that `empty` and
    # population counters start from the canonical values. Mirror that here
    # so JSON loads behave like freshly booted areas.
    area.age = 15
    area.nplayer = 0
    area.empty = False

    # Register area
    area_registry[area.vnum] = area

    # Load rooms
    _load_rooms_from_json(data.get(rooms_key, []), area)
    _link_exits_for_area(area)

    # Load mobs
    _load_mobs_from_json(data.get(mobs_key, []), area)
    _load_mob_programs_from_json(data.get("mob_programs", []))
    apply_specials_from_json(data.get("specials", []))

    # Load objects
    _load_objects_from_json(data.get(objects_key, []), area)

    for room in list(room_registry.values()):
        if getattr(room, "area", None) is area:
            room.resets.clear()

    # Load area-level resets. Older conversions stored the `if_flag` in arg1 and
    # shifted the actual ROM arguments (arg1..arg4) to arg2..arg5. Normalise the
    # layout so reset handlers receive ROM-compatible fields regardless of the
    # input JSON version.
    last_room_vnum: int | None = None
    for reset_data in data.get("resets", []):
        command = str(reset_data.get("command", "") or "").upper()
        raw_args = [_coerce_reset_arg(reset_data.get(f"arg{i}", 0)) for i in range(1, 6)]

        # Detect legacy layout with if_flag in arg1 (0/1) and actual args shifted.
        shifted = False
        if command in {"M", "O", "G", "E", "P", "D", "R"}:
            if raw_args[0] in (0, 1) and raw_args[1]:
                shifted = True

        if shifted:
            args = raw_args[1:5]
        else:
            args = raw_args[:4]

        arg1, arg2, arg3, arg4 = args

        if command == "M":
            # Missing room limit defaults to global limit (or 1) in ROM.
            if arg4 == 0:
                arg4 = arg2 if arg2 > 0 else 1
        elif command == "P":
            # Default contained item count mirrors ROM's max(1, arg4).
            if arg4 == 0:
                arg4 = 1

        reset = ResetJson(command=command, arg1=arg1, arg2=arg2, arg3=arg3, arg4=arg4)
        area.resets.append(reset)

        room_vnum, last_room_vnum = _resolve_room_target(command, reset, last_room_vnum)
        if room_vnum is not None:
            room = room_registry.get(room_vnum)
            if room is not None:
                room.resets.append(reset)

    logger.info(
        f"Loaded area {area.name} from JSON with {len(data.get(rooms_key, []))} rooms, "
        f"{len(data.get(mobs_key, []))} mobs, {len(data.get(objects_key, []))} objects, "
        f"{len(data.get('resets', []))} resets"
    )

    return area


def _load_rooms_from_json(rooms_data: list[dict[str, Any]], area: Area) -> None:
    """Load rooms from JSON data with complete field mapping."""

    for room_data in rooms_data:
        # Parse sector type
        sector_str = room_data.get("sector_type", "inside")
        try:
            if sector_str.isdigit():
                sector = Sector(int(sector_str))
            else:
                sector = Sector[sector_str.upper()]
        except (ValueError, KeyError):
            logger.warning(f"Unknown sector type: {sector_str}, defaulting to INSIDE")
            sector = Sector.INSIDE

        # Create room
        room = Room(
            vnum=room_data["id"],
            name=room_data.get("name", ""),
            description=room_data.get("description", ""),
            sector_type=sector,
            room_flags=_parse_room_flags(room_data.get("flags", 0)),
            area=area,
        )

        # Set ROM defaults
        room.heal_rate = room_data.get("heal_rate", 100)
        room.mana_rate = room_data.get("mana_rate", 100)
        room.clan = room_data.get("clan", 0)
        room.owner = room_data.get("owner", "")

        # Set ROOM_LAW flag for Midgaard law zone (vnums 3000-3400)
        if 3000 <= room.vnum < 3400:
            room.room_flags |= int(RoomFlag.ROOM_LAW)

        # Load exits
        exits_data = room_data.get("exits", {})
        for direction_name, exit_data in exits_data.items():
            try:
                direction = Direction[direction_name.upper()]
                raw_flags = exit_data.get("flags", "0")
                exit_flags = _parse_exit_flags(raw_flags)
                exit_obj = Exit(
                    vnum=exit_data.get("to_room", 0),
                    description=exit_data.get("description", ""),
                    keyword=exit_data.get("keyword", ""),
                    flags=raw_flags,
                    key=exit_data.get("key", 0),
                    exit_info=exit_flags,
                    rs_flags=exit_flags,
                    orig_door=direction.value,
                )
                room.exits[direction.value] = exit_obj
            except KeyError:
                logger.warning(f"Unknown direction: {direction_name}")

        # Load extra descriptions
        for extra_data in room_data.get("extra_descriptions", []):
            extra_desc = ExtraDescr(keyword=extra_data["keyword"], description=extra_data["description"])
            room.extra_descr.append(extra_desc)

        room_registry[room.vnum] = room


def _link_exits_for_area(area: Area) -> None:
    """Resolve exit destinations and reverse links like ROM fix_exits."""

    reverse_map = {
        Direction.NORTH: Direction.SOUTH,
        Direction.EAST: Direction.WEST,
        Direction.SOUTH: Direction.NORTH,
        Direction.WEST: Direction.EAST,
        Direction.UP: Direction.DOWN,
        Direction.DOWN: Direction.UP,
    }

    for room in list(room_registry.values()):
        if getattr(room, "area", None) is not area:
            continue

        exits = getattr(room, "exits", []) or []
        has_exit = False

        for idx, exit_obj in enumerate(exits):
            if exit_obj is None:
                continue

            dest_vnum = getattr(exit_obj, "vnum", None)
            to_room = room_registry.get(dest_vnum)
            exit_obj.to_room = to_room

            if to_room is None:
                continue

            has_exit = True
            reverse_dir = reverse_map.get(Direction(idx))
            if reverse_dir is None:
                continue

            reverse_exits = getattr(to_room, "exits", []) or []
            if reverse_dir.value >= len(reverse_exits):
                continue

            reverse_exit = reverse_exits[reverse_dir.value]
            if reverse_exit is None:
                continue

            reverse_exit.to_room = room

        if not has_exit:
            room.room_flags |= int(RoomFlag.ROOM_NO_MOB)


def _load_mobs_from_json(mobs_data: list[dict[str, Any]], area: Area) -> None:
    """Load mobs from JSON data with complete field mapping."""

    for mob_data in mobs_data:
        # Parse sex
        sex_str = mob_data.get("sex", "none")
        try:
            sex = Sex[sex_str.upper()]
        except KeyError:
            logger.warning(f"Unknown sex: {sex_str}, defaulting to NONE")
            sex = Sex.NONE

        # Create mob with all fields
        mob = MobIndex(
            vnum=mob_data["id"],
            player_name=mob_data.get("player_name", ""),
            short_descr=mob_data.get("name", ""),
            long_descr=mob_data.get("long_description", ""),
            description=mob_data.get("description", ""),
            race=mob_data.get("race", ""),
            act_flags=mob_data.get("act_flags", ""),
            affected_by=mob_data.get("affected_by", ""),
            alignment=mob_data.get("alignment", 0),
            group=mob_data.get("group", 0),
            level=mob_data.get("level", 1),
            thac0=mob_data.get("thac0", 20),
            ac=mob_data.get("ac", "1d1+0"),
            hit_dice=mob_data.get("hit_dice", "1d1+0"),
            mana_dice=mob_data.get("mana_dice", "1d1+0"),
            damage_dice=mob_data.get("damage_dice", "1d4+0"),
            damage_type=mob_data.get("damage_type", "beating"),
            ac_pierce=mob_data.get("ac_pierce", 0),
            ac_bash=mob_data.get("ac_bash", 0),
            ac_slash=mob_data.get("ac_slash", 0),
            ac_exotic=mob_data.get("ac_exotic", 0),
            offensive=mob_data.get("offensive", ""),
            immune=mob_data.get("immune", ""),
            resist=mob_data.get("resist", ""),
            vuln=mob_data.get("vuln", ""),
            start_pos=mob_data.get("start_pos", "standing"),
            default_pos=mob_data.get("default_pos", "standing"),
            sex=sex,
            wealth=mob_data.get("wealth", 0),
            form=mob_data.get("form", "0"),
            parts=mob_data.get("parts", "0"),
            size=mob_data.get("size", "medium"),
            material=mob_data.get("material", "0"),
            area=area,
        )

        mob_registry[mob.vnum] = mob


def _load_objects_from_json(objects_data: list[dict[str, Any]], area: Area) -> None:
    """Load objects from JSON data with complete field mapping."""

    for obj_data in objects_data:
        # Create object with all fields
        obj = ObjIndex(
            vnum=obj_data["id"],
            short_descr=obj_data.get("name", ""),
            description=obj_data.get("description", ""),
            material=obj_data.get("material", ""),
            item_type=obj_data.get("item_type", "trash"),
            extra_flags=_rom_flags_to_int(obj_data.get("extra_flags", "")),
            wear_flags=obj_data.get("wear_flags", ""),
            weight=obj_data.get("weight", 0),
            cost=obj_data.get("cost", 0),
            condition=obj_data.get("condition", "P"),
            value=obj_data.get("values", [0, 0, 0, 0, 0]),
            affects=obj_data.get("affects", []),
            extra_descr=obj_data.get("extra_descriptions", []),
            area=area,
        )

        obj_registry[obj.vnum] = obj


def _load_mob_programs_from_json(programs_data: list[dict[str, Any]]) -> None:
    """Register mob program scripts and attach assignments from JSON."""

    for program_entry in programs_data:
        vnum = program_entry.get("vnum")
        if vnum is None:
            continue
        code = program_entry.get("code", "")
        if code:
            register_program_code(vnum, code)

    for program_entry in programs_data:
        vnum = program_entry.get("vnum")
        if vnum is None:
            continue
        code = program_entry.get("code", "")
        assignments = program_entry.get("assignments", [])
        for assignment in assignments:
            mob_vnum = assignment.get("mob_vnum")
            trigger_name = assignment.get("trigger", "")
            phrase = assignment.get("phrase", "")
            mob = mob_registry.get(mob_vnum)
            trigger_flag = resolve_trigger_flag(trigger_name)
            if mob is None or trigger_flag is None:
                continue
            program = MobProgram(
                trig_type=int(trigger_flag),
                trig_phrase=phrase,
                vnum=vnum,
                code=code or None,
            )
            mob.mprogs.append(program)
            mob.mprog_flags |= int(trigger_flag)
            if code:
                register_program_code(vnum, code)


def load_all_areas_from_json(json_dir: str) -> dict[int, Area]:
    """Load all areas from JSON files in a directory."""

    json_path = Path(json_dir)
    if not json_path.exists():
        logger.error(f"JSON directory not found: {json_dir}")
        return {}

    areas = {}

    for json_file in json_path.glob("*.json"):
        try:
            area = load_area_from_json(str(json_file))
            areas[area.vnum] = area
        except Exception as e:
            logger.error(f"Failed to load {json_file}: {e}")

    logger.info(f"Loaded {len(areas)} areas from JSON")
    return areas
