"""JSON area loader - loads areas from converted JSON files."""

import json
from pathlib import Path
from typing import Any

from mud.models.area import Area
from mud.models.mob import MobIndex
from mud.models.obj import ObjIndex
from mud.models.room import Exit, ExtraDescr, Room
from mud.registry import area_registry, mob_registry, obj_registry, room_registry


def load_area_from_json(json_file_path: str) -> Area:
    """Load an area from a JSON file and populate registries."""

    with open(json_file_path, encoding="utf-8") as f:
        # Load raw JSON data instead of using the dataclass loader to handle missing fields
        data = json.load(f)

    # Create the Area object
    area = Area(
        file_name=Path(json_file_path).name,
        name=data.get("name", "Unknown Area"),
        min_vnum=data.get("vnum_range", {}).get("min", 0),
        max_vnum=data.get("vnum_range", {}).get("max", 0),
        builders=", ".join(data.get("builders", [])),
        vnum=data.get("vnum_range", {}).get("min", 0),
        age=15,  # Default age for areas
        empty=False,
    )

    # Register the area
    area_key = area.min_vnum
    if area_key != 0 and area_key in area_registry and area_registry[area_key].file_name != area.file_name:
        raise ValueError(f"duplicate area vnum {area_key}")
    area_registry[area_key] = area

    # Load rooms
    for room_data in data.get("rooms", []):
        room = _json_to_room(room_data, area)
        room_registry[room.vnum] = room

    # Load mobiles
    for mob_data in data.get("mobiles", []):
        mob = _json_to_mob(mob_data, area)
        mob_registry[mob.vnum] = mob

    # Load objects
    for obj_data in data.get("objects", []):
        obj = _json_to_obj(obj_data, area)
        obj_registry[obj.vnum] = obj

    return area


def _json_to_room(room_data: dict[str, Any], area: Area) -> Room:
    """Convert room JSON data to Room model."""
    room = Room(
        vnum=room_data.get("id", 0),
        name=room_data.get("name", "Unnamed Room"),
        description=room_data.get("description", "No description."),
        area=area,
        sector_type=_sector_name_to_int(room_data.get("sector_type", "inside")),
        room_flags=_flags_to_int(room_data.get("flags", [])),
    )

    # Handle exits - initialize with None for all directions
    room.exits = [None] * 10
    exits_data = room_data.get("exits", {})
    if exits_data:
        direction_map = {
            "north": 0,
            "east": 1,
            "south": 2,
            "west": 3,
            "up": 4,
            "down": 5,
            "northeast": 6,
            "northwest": 7,
            "southeast": 8,
            "southwest": 9,
        }

        for direction, exit_data in exits_data.items():
            if direction in direction_map:
                dir_num = direction_map[direction]
                exit_flags = _flags_to_int(exit_data.get("flags", []))
                exit = Exit(
                    vnum=exit_data.get("to_room", 0),
                    exit_info=exit_flags,
                    rs_flags=exit_flags,
                    keyword=exit_data.get("keyword"),
                    description=exit_data.get("description"),
                )
                room.exits[dir_num] = exit

    # Handle extra descriptions
    extra_descriptions = room_data.get("extra_descriptions", [])
    for extra_desc in extra_descriptions:
        room.extra_descr.append(
            ExtraDescr(keyword=extra_desc.get("keyword"), description=extra_desc.get("description"))
        )

    return room


def _json_to_mob(mob_data: dict[str, Any], area: Area) -> MobIndex:
    """Convert mobile JSON data to MobIndex model."""
    mob = MobIndex(
        vnum=mob_data.get("id", 0),
        player_name=mob_data.get("name", "unnamed mobile"),
        short_descr=mob_data.get("short_description", mob_data.get("name", "unnamed mobile")),
        long_descr=mob_data.get("long_description", ""),
        description=mob_data.get("description", "No description."),
        area=area,
        level=mob_data.get("level", 1),
        alignment=mob_data.get("alignment", 0),
        act=_flags_to_int(mob_data.get("flags", [])),
        new_format=True,
    )

    return mob


def _json_to_obj(obj_data: dict[str, Any], area: Area) -> ObjIndex:
    """Convert object JSON data to ObjIndex model."""
    obj = ObjIndex(
        vnum=obj_data.get("id", 0),
        name=obj_data.get("name", "unnamed object"),
        short_descr=obj_data.get("short_description", obj_data.get("name", "unnamed object")),
        description=obj_data.get("description", "No description."),
        area=area,
        item_type=_item_type_to_int(obj_data.get("item_type", "trash")),
        extra_flags=_flags_to_int(obj_data.get("flags", [])),
        wear_flags=_flags_to_int(obj_data.get("wear_flags", [])),
        level=obj_data.get("level", 0),
        weight=obj_data.get("weight", 0),
        cost=obj_data.get("cost", 0),
        material=obj_data.get("material", "unknown"),
    )

    # Handle values array
    values = obj_data.get("values", [0, 0, 0, 0, 0])
    obj.value = values[:5] if len(values) >= 5 else values + [0] * (5 - len(values))

    return obj


def _sector_name_to_int(sector_name: str) -> int:
    """Convert sector name to integer."""
    sector_map = {
        "inside": 0,
        "city": 1,
        "field": 2,
        "forest": 3,
        "hills": 4,
        "mountain": 5,
        "water_swim": 6,
        "water_noswim": 7,
        "underwater": 8,
        "air": 9,
        "desert": 10,
        "unknown": 11,
    }
    return sector_map.get(sector_name, 0)


def _item_type_to_int(item_type: str) -> int:
    """Convert item type name to integer."""
    type_map = {
        "light": 1,
        "scroll": 2,
        "wand": 3,
        "staff": 4,
        "weapon": 5,
        "fireweapon": 6,
        "missile": 7,
        "treasure": 8,
        "armor": 9,
        "potion": 10,
        "clothing": 11,
        "furniture": 12,
        "trash": 13,
        "oldtrap": 14,
        "container": 15,
        "note": 16,
        "drinkcon": 17,
        "key": 18,
        "food": 19,
        "money": 20,
        "pen": 21,
        "boat": 22,
        "corpse": 23,
        "corpse_pc": 24,
        "fountain": 25,
        "pill": 26,
        "protect": 27,
        "map": 28,
        "portal": 29,
        "warp_stone": 30,
        "room_key": 31,
        "gem": 32,
        "jewelry": 33,
        "jukebox": 34,
    }
    return type_map.get(item_type, 13)  # Default to 'trash'


def _flags_to_int(flags_list) -> int:
    """Convert list of flag names to integer bitfield."""
    if not flags_list:
        return 0

    # For now, return 0 as we don't have the flag mappings
    # This can be extended later with proper flag name to bit mappings
    return 0


def load_all_areas_from_json(areas_dir: str = "data/areas") -> None:
    """Load all areas from JSON files in the specified directory."""
    areas_path = Path(areas_dir)

    if not areas_path.exists():
        raise FileNotFoundError(f"Areas directory not found: {areas_dir}")

    json_files = list(areas_path.glob("*.json"))
    if not json_files:
        raise FileNotFoundError(f"No JSON files found in: {areas_dir}")

    print(f"Loading {len(json_files)} areas from JSON files...")

    for json_file in sorted(json_files):
        try:
            area = load_area_from_json(str(json_file))
            print(f"✅ Loaded area: {area.name} ({area.min_vnum}-{area.max_vnum})")
        except Exception as e:
            print(f"❌ Failed to load {json_file.name}: {e}")
            raise

    print(
        f"🎯 Successfully loaded {len(area_registry)} areas, {len(room_registry)} rooms, "
        f"{len(mob_registry)} mobs, {len(obj_registry)} objects"
    )
