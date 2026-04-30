"""Area persistence functions for OLC system.

Mirroring ROM src/olc_save.c:76-1134 (save_area_list, save_area, save_mobiles, save_objects, etc.)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from mud.models.area import Area
from mud.models.constants import Direction
from mud.models.room import Room
from mud.registry import area_registry, mob_registry, obj_registry, room_registry

logger = logging.getLogger(__name__)


def _serialize_exit(exit_obj: object, direction_idx: int) -> dict[str, Any] | None:
    if exit_obj is None:
        return None

    to_room_vnum = getattr(exit_obj, "vnum", None)
    if to_room_vnum is None:
        to_room = getattr(exit_obj, "to_room", None)
        to_room_vnum = getattr(to_room, "vnum", None) if to_room else None

    if to_room_vnum is None:
        return None

    result: dict[str, Any] = {"to_room": to_room_vnum}

    description = getattr(exit_obj, "description", None)
    if description:
        result["description"] = description

    keyword = getattr(exit_obj, "keyword", None)
    if keyword:
        result["keyword"] = keyword

    exit_info = int(getattr(exit_obj, "exit_info", 0))
    result["flags"] = str(exit_info) if exit_info else "0"

    key = int(getattr(exit_obj, "key", 0))
    if key:
        result["key"] = key
    else:
        result["key"] = -1

    return result


def _serialize_extra_descr(extra: object) -> dict[str, Any]:
    return {
        "keyword": getattr(extra, "keyword", "") or "",
        "description": getattr(extra, "description", "") or "",
    }


def _serialize_affect(affect: object) -> dict[str, Any]:
    """Normalize a prototype affect into a json-safe dict.

    Mirrors ROM src/olc_save.c:399-429 (save_object affect emission).
    Accepts either a plain dict (already produced by `mud/loaders/obj_loader.py`
    A-line / F-line parsers) or an `Affect` dataclass instance. Emits a
    flat dict with whichever ROM fields are populated; unset fields fall
    back to ROM defaults (`type=-1`, `duration=-1`, `bitvector=0`).
    """
    if isinstance(affect, dict):
        result: dict[str, Any] = {}
        if "where" in affect:
            result["where"] = affect["where"]
        if "type" in affect:
            result["type"] = int(affect["type"])
        if "level" in affect:
            result["level"] = int(affect["level"])
        if "duration" in affect:
            result["duration"] = int(affect["duration"])
        result["location"] = int(affect.get("location", 0) or 0)
        result["modifier"] = int(affect.get("modifier", 0) or 0)
        if "bitvector" in affect:
            result["bitvector"] = int(affect["bitvector"])
        return result

    return {
        "where": int(getattr(affect, "where", 0) or 0),
        "type": int(getattr(affect, "type", -1)),
        "level": int(getattr(affect, "level", 0) or 0),
        "duration": int(getattr(affect, "duration", -1)),
        "location": int(getattr(affect, "location", 0) or 0),
        "modifier": int(getattr(affect, "modifier", 0) or 0),
        "bitvector": int(getattr(affect, "bitvector", 0) or 0),
    }


def _serialize_reset(reset: object) -> dict[str, Any]:
    return {
        "command": getattr(reset, "command", ""),
        "arg1": int(getattr(reset, "arg1", 0)),
        "arg2": int(getattr(reset, "arg2", 0)),
        "arg3": int(getattr(reset, "arg3", 0)),
        "arg4": int(getattr(reset, "arg4", 0)),
    }


def _serialize_room(room: Room) -> dict[str, Any]:
    exits_dict: dict[str, Any] = {}
    for idx, exit_obj in enumerate(getattr(room, "exits", []) or []):
        if exit_obj is None:
            continue
        try:
            direction = Direction(idx)
        except ValueError:
            continue
        serialized = _serialize_exit(exit_obj, idx)
        if serialized:
            exits_dict[direction.name.lower()] = serialized

    room_data: dict[str, Any] = {
        "id": room.vnum,
        "name": room.name or "",
        "description": room.description or "",
        "sector_type": _sector_int_to_name(int(getattr(room, "sector_type", 0))),
        "flags": int(getattr(room, "room_flags", 0)),
        "exits": exits_dict,
        "extra_descriptions": [_serialize_extra_descr(e) for e in getattr(room, "extra_descr", []) or []],
        "area": int(getattr(getattr(room, "area", None), "vnum", 0) or 0),
    }

    resets_list = getattr(room, "resets", []) or []
    if resets_list:
        room_data["resets"] = [_serialize_reset(r) for r in resets_list]

    heal_rate = int(getattr(room, "heal_rate", 100))
    if heal_rate != 100:
        room_data["heal_rate"] = heal_rate

    mana_rate = int(getattr(room, "mana_rate", 100))
    if mana_rate != 100:
        room_data["mana_rate"] = mana_rate

    clan = int(getattr(room, "clan", 0))
    if clan:
        room_data["clan"] = clan

    owner = (getattr(room, "owner", "") or "").strip()
    if owner:
        room_data["owner"] = owner

    return room_data


def _sector_int_to_name(sector: int) -> str:
    mapping = {
        0: "inside",
        1: "city",
        2: "field",
        3: "forest",
        4: "hills",
        5: "mountain",
        6: "water_swim",
        7: "water_noswim",
        8: "unused",
        9: "air",
        10: "desert",
    }
    return mapping.get(sector, "inside")


def _serialize_mobile(mob_proto: object) -> dict[str, Any]:
    vnum = int(getattr(mob_proto, "vnum", 0))

    sex_value = getattr(mob_proto, "sex", "neutral")
    if isinstance(sex_value, int):
        sex_map = {0: "none", 1: "male", 2: "female", 3: "neutral"}
        sex_str = sex_map.get(sex_value, "neutral")
    else:
        sex_str = str(sex_value) if sex_value else "neutral"

    # OLC_SAVE-001: persist defensive/offensive flag sets so save→reload
    # preserves them. Mirrors ROM src/olc_save.c:205-208 (save_mobile emits
    # Off/Imm/Res/Vuln via fwrite_flag). JSON-authoritative framing stores
    # the ROM letter-strings directly, matching json_loader._load_mobs_from_json.
    offensive = getattr(mob_proto, "offensive", "") or ""
    immune = getattr(mob_proto, "immune", "") or ""
    resist = getattr(mob_proto, "resist", "") or ""
    vuln = getattr(mob_proto, "vuln", "") or ""

    # OLC_SAVE-002: persist form/parts/size/material so save→reload preserves
    # physical descriptors. Mirrors ROM src/olc_save.c:213-219 (save_mobile
    # emits Form/Parts/Size/Material). MobIndex stores these as str|int|enum;
    # serialize as strings to match json_loader._load_mobs_from_json defaults.
    form_raw = getattr(mob_proto, "form", "0")
    parts_raw = getattr(mob_proto, "parts", "0")
    size_raw = getattr(mob_proto, "size", "medium")
    material_raw = getattr(mob_proto, "material", "0")
    size_str = getattr(size_raw, "name", None)
    if isinstance(size_str, str):
        size_value = size_str.lower()
    else:
        size_value = str(size_raw) if size_raw is not None else "medium"

    return {
        "id": vnum,
        "name": getattr(mob_proto, "short_descr", "") or "",
        "player_name": getattr(mob_proto, "player_name", "") or "",
        "long_description": getattr(mob_proto, "long_descr", "") or "",
        "description": getattr(mob_proto, "description", "") or "",
        "race": getattr(mob_proto, "race", "human") or "human",
        "act_flags": str(getattr(mob_proto, "act", "") or "0"),
        "affected_by": str(getattr(mob_proto, "affected_by", "") or "0"),
        "alignment": int(getattr(mob_proto, "alignment", 0)),
        "group": int(getattr(mob_proto, "group", 0)),
        "level": int(getattr(mob_proto, "level", 1)),
        "thac0": int(getattr(mob_proto, "hitroll", 0)),
        "ac": str(getattr(mob_proto, "ac", "1d1+0") or "1d1+0"),
        "hit_dice": str(getattr(mob_proto, "hit_dice", "1d1+0") or "1d1+0"),
        "mana_dice": str(getattr(mob_proto, "mana_dice", "1d1+0") or "1d1+0"),
        "damage_dice": str(getattr(mob_proto, "damage_dice", "1d1+0") or "1d1+0"),
        "damage_type": str(getattr(mob_proto, "dam_type", "none") or "none"),
        "offensive": str(offensive),
        "immune": str(immune),
        "resist": str(resist),
        "vuln": str(vuln),
        "form": str(form_raw) if form_raw is not None else "0",
        "parts": str(parts_raw) if parts_raw is not None else "0",
        "size": size_value,
        "material": str(material_raw) if material_raw is not None else "0",
        "start_pos": str(getattr(mob_proto, "start_pos", "stand") or "stand"),
        "default_pos": str(getattr(mob_proto, "default_pos", "stand") or "stand"),
        "sex": sex_str,
        "wealth": int(getattr(mob_proto, "wealth", 0)),
    }


def _serialize_object(obj_proto: object) -> dict[str, Any]:
    vnum = int(getattr(obj_proto, "vnum", 0))
    values = getattr(obj_proto, "value", [0, 0, 0, 0, 0])
    if not isinstance(values, list):
        values = [0, 0, 0, 0, 0]
    while len(values) < 5:
        values.append(0)

    return {
        "id": vnum,
        "name": getattr(obj_proto, "short_descr", "") or "",
        "description": getattr(obj_proto, "description", "") or "",
        "material": getattr(obj_proto, "material", "unknown") or "unknown",
        "item_type": getattr(obj_proto, "item_type", "trash") or "trash",
        "extra_flags": str(getattr(obj_proto, "extra_flags", 0) or 0),
        "wear_flags": str(getattr(obj_proto, "wear_flags", "") or ""),
        # OLC_SAVE-006: persist object level (mirrors ROM src/olc_save.c:378).
        "level": int(getattr(obj_proto, "level", 0) or 0),
        "weight": int(getattr(obj_proto, "weight", 0)),
        "cost": int(getattr(obj_proto, "cost", 0)),
        "condition": str(getattr(obj_proto, "condition", "P") or "P"),
        "values": values[:5],
        # OLC_SAVE-007: structured affect emission (mirrors ROM
        # src/olc_save.c:399-429). Accepts dict or Affect dataclass on
        # input; emits json-safe dicts.
        "affects": [_serialize_affect(a) for a in getattr(obj_proto, "affects", []) or []],
        "extra_descriptions": list(getattr(obj_proto, "extra_descr", []) or []),
    }


def _collect_specials(area: Area, min_vnum: int, max_vnum: int) -> list[dict[str, Any]]:
    """Mirrors ROM src/olc_save.c:578-606 (save_specials).

    Walks every mob in the area; if the mob has a non-empty ``spec_fun``,
    emit a ``{"mob_vnum", "spec"}`` entry matching the format consumed
    by ``mud.loaders.specials_loader.apply_specials_from_json``.
    """
    specials: list[dict[str, Any]] = []
    for vnum in range(min_vnum, max_vnum + 1):
        mob_proto = mob_registry.get(vnum)
        if mob_proto is None or getattr(mob_proto, "area", None) is not area:
            continue
        spec = getattr(mob_proto, "spec_fun", None)
        if not spec:
            continue
        specials.append({"mob_vnum": int(vnum), "spec": str(spec)})
    return specials


def _collect_shops(area: Area, min_vnum: int, max_vnum: int) -> list[dict[str, Any]]:
    """Mirrors ROM src/olc_save.c:786-824 (save_shops).

    Walks every mob in the area; if the mob has a ``pShop`` binding,
    serialize keeper / buy_types / profit_buy / profit_sell / open_hour /
    close_hour. Mob without ``pShop`` contribute nothing.
    """
    from mud.registry import shop_registry

    shops: list[dict[str, Any]] = []
    for vnum in range(min_vnum, max_vnum + 1):
        mob_proto = mob_registry.get(vnum)
        if mob_proto is None or getattr(mob_proto, "area", None) is not area:
            continue
        shop = getattr(mob_proto, "pShop", None) or shop_registry.get(int(vnum))
        if shop is None:
            continue
        keeper = int(getattr(shop, "keeper", vnum) or vnum)
        buy_types = list(getattr(shop, "buy_types", []) or [])
        while len(buy_types) < 5:
            buy_types.append(0)
        shops.append(
            {
                "keeper": keeper,
                "buy_types": [int(b) for b in buy_types[:5]],
                "profit_buy": int(getattr(shop, "profit_buy", 100)),
                "profit_sell": int(getattr(shop, "profit_sell", 100)),
                "open_hour": int(getattr(shop, "open_hour", 0)),
                "close_hour": int(getattr(shop, "close_hour", 23)),
            }
        )
    return shops


def _collect_mob_programs(area: Area, min_vnum: int, max_vnum: int) -> list[dict[str, Any]]:
    """Group per-mob mprog assignments by program vnum for JSON emit.

    Mirrors ROM src/olc_save.c:151-169 (save_mobprogs) — Python's JSON
    layout (see mud/loaders/json_loader.py:_load_mob_programs_from_json)
    keeps program code at the area level and links via assignments, so
    we reverse the loader's projection here.
    """
    from mud.mobprog import format_trigger_flag

    grouped: dict[int, dict[str, Any]] = {}
    for vnum in range(min_vnum, max_vnum + 1):
        mob_proto = mob_registry.get(vnum)
        if mob_proto is None or getattr(mob_proto, "area", None) is not area:
            continue
        for prog in getattr(mob_proto, "mprogs", []) or []:
            prog_vnum = int(getattr(prog, "vnum", 0) or 0)
            if prog_vnum <= 0:
                continue
            entry = grouped.get(prog_vnum)
            if entry is None:
                entry = {
                    "vnum": prog_vnum,
                    "code": getattr(prog, "code", "") or "",
                    "assignments": [],
                }
                grouped[prog_vnum] = entry
            elif not entry["code"] and getattr(prog, "code", None):
                entry["code"] = prog.code
            trigger_name = format_trigger_flag(int(getattr(prog, "trig_type", 0) or 0))
            entry["assignments"].append(
                {
                    "mob_vnum": int(vnum),
                    "trigger": trigger_name,
                    "phrase": getattr(prog, "trig_phrase", "") or "",
                }
            )
    return [grouped[k] for k in sorted(grouped)]


def save_area_to_json(area: Area, output_dir: Path | str = "data/areas") -> bool:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    file_name = getattr(area, "file_name", None)
    if not file_name:
        vnum = int(getattr(area, "vnum", 0))
        file_name = f"area_{vnum}.json"
    else:
        if file_name.endswith(".are"):
            file_name = file_name[:-4] + ".json"
        elif not file_name.endswith(".json"):
            file_name = file_name + ".json"

    min_vnum = int(getattr(area, "min_vnum", 0))
    max_vnum = int(getattr(area, "max_vnum", 0))

    rooms_list: list[dict[str, Any]] = []
    for vnum in range(min_vnum, max_vnum + 1):
        room = room_registry.get(vnum)
        if room is not None and getattr(room, "area", None) is area:
            rooms_list.append(_serialize_room(room))

    mobiles_list: list[dict[str, Any]] = []
    for vnum in range(min_vnum, max_vnum + 1):
        mob_proto = mob_registry.get(vnum)
        if mob_proto is not None and getattr(mob_proto, "area", None) is area:
            mobiles_list.append(_serialize_mobile(mob_proto))

    objects_list: list[dict[str, Any]] = []
    for vnum in range(min_vnum, max_vnum + 1):
        obj_proto = obj_registry.get(vnum)
        if obj_proto is not None and getattr(obj_proto, "area", None) is area:
            objects_list.append(_serialize_object(obj_proto))

    # OLC_SAVE-003: mirror ROM src/olc_save.c:151-169 (save_mobprogs) +
    # ROM src/olc_save.c:245-250 (per-mob MPROG list inside save_mobile).
    # JSON layout factors program code area-wide and links via assignments
    # (see mud/loaders/json_loader.py:496-530). Walk every mob in this
    # area, group their mprogs by program vnum, and emit the structured
    # mob_programs payload.
    mob_programs_list = _collect_mob_programs(area, min_vnum, max_vnum)
    shops_list = _collect_shops(area, min_vnum, max_vnum)
    specials_list = _collect_specials(area, min_vnum, max_vnum)

    builders_str = getattr(area, "builders", "") or ""
    builders_list = [b.strip() for b in builders_str.replace(",", " ").split() if b.strip()]

    area_data: dict[str, Any] = {
        "name": getattr(area, "name", "Unnamed Area") or "Unnamed Area",
        "vnum_range": {
            "min": min_vnum,
            "max": max_vnum,
        },
        "builders": builders_list,
        "rooms": rooms_list,
        "mobiles": mobiles_list,
        "objects": objects_list,
        "mob_programs": mob_programs_list,
        "shops": shops_list,
        "specials": specials_list,
    }

    credits = getattr(area, "credits", None)
    if credits:
        area_data["credits"] = credits

    security = int(getattr(area, "security", 0))
    if security:
        area_data["security"] = security

    low_range = int(getattr(area, "low_range", 0))
    high_range = int(getattr(area, "high_range", 0))
    if low_range or high_range:
        area_data["level_range"] = {"low": low_range, "high": high_range}

    try:
        file_path = output_path / file_name
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(area_data, f, indent=2, ensure_ascii=False)
            f.write("\n")

        logger.info(f"Saved area {area.name} to {file_path}")
        area.changed = False
        return True
    except Exception as e:
        logger.error(f"Failed to save area {area.name}: {e}")
        return False


def save_area_list(output_file: Path | str = "data/areas/area.lst") -> bool:
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            for area in sorted(area_registry.values(), key=lambda a: getattr(a, "vnum", 0)):
                file_name = getattr(area, "file_name", None)
                if file_name:
                    if file_name.endswith(".are"):
                        file_name = file_name[:-4] + ".json"
                    elif not file_name.endswith(".json"):
                        file_name = file_name + ".json"
                    f.write(f"{file_name}\n")
            f.write("$\n")

        logger.info(f"Saved area list to {output_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to save area list: {e}")
        return False
