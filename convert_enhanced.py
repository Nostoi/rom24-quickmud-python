#!/usr/bin/env python3
"""
Simple JSON converter for areas with comprehensive field mapping.
"""

import json
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mud.loaders import load_all_areas
from mud.models.constants import Direction, Sector
from mud.registry import area_registry, mob_registry, obj_registry, room_registry


def room_to_dict(room) -> dict:
    exits = {}
    for idx, exit_obj in enumerate(room.exits):
        if not exit_obj:
            continue
        direction = Direction(idx).name.lower()
        exits[direction] = {
            "to_room": exit_obj.vnum or 0,
        }
        if exit_obj.description:
            exits[direction]["description"] = exit_obj.description
        if exit_obj.keyword:
            exits[direction]["keyword"] = exit_obj.keyword
        exits[direction]["flags"] = getattr(exit_obj, "flags", "0")
        if exit_obj.key:
            exits[direction]["key"] = exit_obj.key

    extra = []
    for ed in room.extra_descr:
        if ed.keyword and ed.description:
            extra.append({"keyword": ed.keyword, "description": ed.description})

    resets = []
    for r in room.resets:
        resets.append(
            {
                "command": r.command,
                "arg1": r.arg1,
                "arg2": r.arg2,
                "arg3": r.arg3,
                "arg4": r.arg4,
            }
        )

    try:
        sector = Sector(room.sector_type).name.lower()
    except ValueError:
        sector = str(room.sector_type)

    return {
        "id": room.vnum,
        "name": room.name or "",
        "description": room.description or "",
        "sector_type": sector,
        "flags": room.room_flags or 0,
        "exits": exits,
        "extra_descriptions": extra,
        "resets": resets,
        "area": room.area.vnum if room.area else 0,
    }


def mob_to_dict(mob) -> dict:
    return {
        "id": mob.vnum,
        "name": mob.short_descr or "",
        "player_name": mob.player_name or "",
        "long_description": mob.long_descr or "",
        "description": mob.description or "",
        "race": getattr(mob, "race", ""),
        "act_flags": getattr(mob, "act_flags", ""),
        "affected_by": getattr(mob, "affected_by", ""),
        "alignment": getattr(mob, "alignment", 0),
        "group": getattr(mob, "group", 0),
        "level": getattr(mob, "level", 1),
        "thac0": getattr(mob, "thac0", 20),
        "ac": getattr(mob, "ac", "1d1+0"),
        "hit_dice": getattr(mob, "hit_dice", "1d1+0"),
        "mana_dice": getattr(mob, "mana_dice", "1d1+0"),
        "damage_dice": getattr(mob, "damage_dice", "1d4+0"),
        "damage_type": getattr(mob, "damage_type", "beating"),
        "ac_pierce": getattr(mob, "ac_pierce", 0),
        "ac_bash": getattr(mob, "ac_bash", 0),
        "ac_slash": getattr(mob, "ac_slash", 0),
        "ac_exotic": getattr(mob, "ac_exotic", 0),
        "offensive": getattr(mob, "offensive", ""),
        "immune": getattr(mob, "immune", ""),
        "resist": getattr(mob, "resist", ""),
        "vuln": getattr(mob, "vuln", ""),
        "start_pos": getattr(mob, "start_pos", "standing"),
        "default_pos": getattr(mob, "default_pos", "standing"),
        "sex": getattr(mob, "sex", "neutral"),
        "wealth": getattr(mob, "wealth", 0),
        "form": getattr(mob, "form", "0"),
        "parts": getattr(mob, "parts", "0"),
        "size": getattr(mob, "size", "medium"),
        "material": getattr(mob, "material", "0"),
    }


def object_to_dict(obj) -> dict:
    return {
        "id": obj.vnum,
        "name": obj.short_descr or "",
        "description": obj.description or "",
        "material": obj.material or "",
        "item_type": getattr(obj, "item_type", "trash"),
        "extra_flags": getattr(obj, "extra_flags", ""),
        "wear_flags": getattr(obj, "wear_flags", ""),
        "weight": getattr(obj, "weight", 0),
        "cost": getattr(obj, "cost", 0),
        "condition": getattr(obj, "condition", "P"),
        "values": getattr(obj, "value", [0, 0, 0, 0, 0]),
        "affects": getattr(obj, "affects", []),
        "extra_descriptions": getattr(obj, "extra_descr", []),
    }


def main():
    print("Converting areas to JSON with comprehensive field mapping...")

    # Clear registries
    area_registry.clear()
    room_registry.clear()
    mob_registry.clear()
    obj_registry.clear()

    # Load all areas
    load_all_areas("area/area.lst")

    # Create output directory
    output_dir = Path("data/areas")
    output_dir.mkdir(parents=True, exist_ok=True)

    print(
        f"Loaded {len(area_registry)} areas, {len(room_registry)} rooms, {len(mob_registry)} mobs, {len(obj_registry)} objects"
    )

    # Convert each area
    for area_vnum, area in area_registry.items():
        area_name = (area.name or f"area_{area_vnum}").replace(" ", "_").lower()

        # Get rooms, mobs, and objects for this area
        area_rooms = [room for room in room_registry.values() if room.area and room.area.vnum == area_vnum]
        area_mobs = [mob for mob in mob_registry.values() if mob.area and mob.area.vnum == area_vnum]
        area_objects = [obj for obj in obj_registry.values() if obj.area and obj.area.vnum == area_vnum]

        area_data = {
            "area": {
                "vnum": area_vnum,
                "name": area.name,
                "filename": area.file_name,
                "min_level": getattr(area, "min_level", 0),
                "max_level": getattr(area, "max_level", 0),
                "builders": getattr(area, "builders", ""),
            },
            "rooms": [room_to_dict(room) for room in area_rooms],
            "mobs": [mob_to_dict(mob) for mob in area_mobs],
            "objects": [object_to_dict(obj) for obj in area_objects],
        }

        output_file = output_dir / f"{area_name}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(area_data, f, indent=2)

        print(
            f"Converted {area.name} -> {output_file} ({len(area_rooms)} rooms, {len(area_mobs)} mobs, {len(area_objects)} objects)"
        )

    print("Conversion complete!")


if __name__ == "__main__":
    main()
