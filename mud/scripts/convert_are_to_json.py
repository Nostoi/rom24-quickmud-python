import argparse
import json
from pathlib import Path

from mud.loaders.area_loader import load_area_file
from mud.models.constants import Direction, Sector
from mud.registry import area_registry, room_registry, mob_registry, obj_registry


def clear_registries() -> None:
    """Reset global registries to avoid cross-contamination."""
    area_registry.clear()
    room_registry.clear()
    mob_registry.clear()
    obj_registry.clear()


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
        exits[direction]["flags"] = []
    extra = []
    for ed in room.extra_descr:
        if ed.keyword and ed.description:
            extra.append({"keyword": ed.keyword, "description": ed.description})
    resets = []
    for r in room.resets:
        resets.append({
            "command": r.command,
            "arg1": r.arg1,
            "arg2": r.arg2,
            "arg3": r.arg3,
            "arg4": r.arg4,
        })
    try:
        sector = Sector(room.sector_type).name.lower()
    except ValueError:
        sector = str(room.sector_type)
    return {
        "id": room.vnum,
        "name": room.name or "",
        "description": room.description or "",
        "sector_type": sector,
        "flags": [],
        "exits": exits,
        "extra_descriptions": extra,
        "resets": resets,
        "area": room.area.vnum if room.area else 0,
    }


def mob_to_dict(mob) -> dict:
    return {
        "id": mob.vnum,
        "name": mob.short_descr or "",
        "description": mob.long_descr or "",
    }

def object_to_dict(obj) -> dict:
    return {
        "id": obj.vnum,
        "name": obj.short_descr or "",
        "description": obj.description or "",
    }

def convert_area(path: str) -> dict:
    clear_registries()
    area = load_area_file(path)
    rooms = [room_to_dict(r) for r in room_registry.values() if r.area is area]
    mobiles = [mob_to_dict(m) for m in mob_registry.values() if m.area is area]
    objects = [object_to_dict(o) for o in obj_registry.values() if o.area is area]
    # Extract #SPECIALS mapping from prototypes for persistence
    specials: list[dict] = []
    for m in mob_registry.values():
        if m.area is area and getattr(m, "spec_fun", None):
            specials.append({"mob_vnum": m.vnum, "spec": str(m.spec_fun)})

    data = {
        "name": area.name or "",
        "vnum_range": {"min": area.min_vnum, "max": area.max_vnum},
        "builders": [b.strip() for b in (area.builders or "").split(",") if b.strip()],
        "rooms": rooms,
        "mobiles": mobiles,
        "objects": objects,
        "specials": specials,
    }
    return data


def main():
    parser = argparse.ArgumentParser(description="Convert ROM .are file to JSON")
    parser.add_argument("input", help="Path to .are file")
    parser.add_argument(
        "--out-dir",
        default=Path("data/areas"),
        type=Path,
        help="Directory to write JSON files (default: data/areas)",
    )
    args = parser.parse_args()
    data = convert_area(args.input)
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{Path(args.input).stem}.json"
    out_file.write_text(json.dumps(data, indent=2) + "\n")

if __name__ == "__main__":
    main()
