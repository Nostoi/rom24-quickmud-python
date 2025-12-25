import argparse
import json
from pathlib import Path

from mud.loaders.area_loader import load_area_file
from mud.loaders.reset_loader import validate_resets
from mud.mobprog import clear_registered_programs, format_trigger_flag, get_registered_program
from mud.models.constants import Direction, Sector
from mud.registry import area_registry, mob_registry, obj_registry, room_registry


def clear_registries() -> None:
    """Reset global registries to avoid cross-contamination."""
    area_registry.clear()
    room_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    clear_registered_programs()


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
    # Note: Resets are stored at area level, not per-room in ROM format
    try:
        sector = Sector(room.sector_type).name.lower()
    except ValueError:
        sector = str(room.sector_type)
    data = {
        "id": room.vnum,
        "name": room.name or "",
        "description": room.description or "",
        "sector_type": sector,
        "flags": room.room_flags or 0,
        "exits": exits,
        "extra_descriptions": extra,
        "area": room.area.vnum if room.area else 0,
    }

    if getattr(room, "heal_rate", 100) != 100:
        data["heal_rate"] = room.heal_rate
    if getattr(room, "mana_rate", 100) != 100:
        data["mana_rate"] = room.mana_rate
    if getattr(room, "clan", 0):
        data["clan"] = room.clan
    if getattr(room, "owner", ""):
        data["owner"] = room.owner

    return data


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


def convert_area(path: str) -> dict:
    clear_registries()
    area = load_area_file(path)
    reset_errors = validate_resets(area)
    if reset_errors:
        joined = "; ".join(reset_errors)
        print(f"Warning: Reset validation issues in {path}: {joined}")
        # Don't raise error - allow conversion to proceed
    rooms = [room_to_dict(r) for r in room_registry.values() if r.area is area]
    mobiles = [mob_to_dict(m) for m in mob_registry.values() if m.area is area]
    objects = [object_to_dict(o) for o in obj_registry.values() if o.area is area]
    # Extract #SPECIALS mapping from prototypes for persistence
    specials: list[dict] = []
    for m in mob_registry.values():
        if m.area is area and getattr(m, "spec_fun", None):
            specials.append({"mob_vnum": m.vnum, "spec": str(m.spec_fun)})

    # Capture mob program scripts and assignments.
    mob_program_records: dict[int, dict[str, object]] = {}
    for mob in mob_registry.values():
        if mob.area is not area:
            continue
        for program in getattr(mob, "mprogs", []) or []:
            program_vnum = int(getattr(program, "vnum", 0) or 0)
            if program_vnum <= 0:
                continue
            record = mob_program_records.setdefault(
                program_vnum,
                {"code": "", "assignments": []},
            )
            trigger_name = format_trigger_flag(getattr(program, "trig_type", 0))
            assignment: dict[str, object] = {"mob_vnum": mob.vnum}
            if trigger_name:
                assignment["trigger"] = trigger_name
            phrase = getattr(program, "trig_phrase", "")
            if phrase:
                assignment["phrase"] = phrase
            record["assignments"].append(assignment)

    for vnum, record in mob_program_records.items():
        program_obj = get_registered_program(vnum)
        if program_obj and getattr(program_obj, "code", ""):
            record["code"] = getattr(program_obj, "code")

    # Convert area-level resets
    resets = []
    for r in area.resets:
        resets.append(
            {
                "command": r.command,
                "arg1": r.arg1,
                "arg2": r.arg2,
                "arg3": r.arg3,
                "arg4": r.arg4,
            }
        )

    data = {
        "name": area.name or "",
        "vnum_range": {"min": area.min_vnum, "max": area.max_vnum},
        "builders": [b.strip() for b in (area.builders or "").split(",") if b.strip()],
        "rooms": rooms,
        "mobiles": mobiles,
        "objects": objects,
        "resets": resets,
        "specials": specials,
    }
    if mob_program_records:
        data["mob_programs"] = [
            {"vnum": vnum, **record}
            for vnum, record in sorted(mob_program_records.items())
        ]
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
