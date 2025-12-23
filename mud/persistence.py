from __future__ import annotations

# ============================================================================
# DEPRECATED: This module is deprecated in favor of mud.account.account_manager
# ============================================================================
# This JSON-based persistence system is kept for backward compatibility only.
# All new code should use mud.account.account_manager for database persistence.
# 
# Migration status: All active save_character() calls now use database version.
# ============================================================================

import json
import os
import time
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from mud.models.character import Character, PCData, PCDATA_COLOUR_FIELDS, character_registry
from mud.models.constants import (
    PlayerFlag,
    WearLocation,
    ROOM_VNUM_LIMBO,
    ROOM_VNUM_TEMPLE,
)
from mud.models.clans import lookup_clan_id
from mud.models.json_io import dataclass_from_dict, dump_dataclass, load_dataclass
from mud.models.obj import Affect
from mud.notes import DEFAULT_BOARD_NAME, find_board, get_board
from mud.registry import room_registry
from mud.spawning.obj_spawner import spawn_object
from mud.time import Sunlight, time_info


def _normalize_int_list(values: Iterable[int] | None, length: int) -> list[int]:
    """Return a list of ``length`` integers padded/truncated from ``values``."""

    normalized = [0] * length
    if not values:
        return normalized
    for idx, value in enumerate(list(values)[:length]):
        try:
            normalized[idx] = int(value)
        except (TypeError, ValueError):
            normalized[idx] = 0
    return normalized


def _serialize_skill_map(raw_skills: Any) -> dict[str, int]:
    """Return a sanitized mapping of skill name -> learned percent."""

    if not raw_skills:
        return {}
    try:
        items = dict(raw_skills).items()
    except Exception:
        return {}
    snapshot: dict[str, int] = {}
    for name, value in items:
        try:
            key = str(name).strip()
        except Exception:
            continue
        if not key:
            continue
        try:
            learned = int(value)
        except (TypeError, ValueError):
            continue
        learned = max(0, min(100, learned))
        if learned <= 0:
            continue
        snapshot[key] = learned
    return snapshot


def _serialize_groups(raw_groups: Any) -> list[str]:
    """Return a deduplicated, normalized list of known group names."""

    if not raw_groups:
        return []
    if isinstance(raw_groups, str):
        iterable = [raw_groups]
    else:
        try:
            iterable = list(raw_groups)
        except Exception:
            return []
    seen: set[str] = set()
    ordered: list[str] = []
    for entry in iterable:
        try:
            name = str(entry).strip().lower()
        except Exception:
            continue
        if not name or name in seen:
            continue
        seen.add(name)
        ordered.append(name)
    return ordered


def _normalize_colour_entry(values: Any) -> list[int]:
    """Return a sanitized colour triplet drawn from ``values``."""

    iterable: Iterable[int] | None
    if isinstance(values, dict):
        try:
            iterable = list(values.values())
        except Exception:
            iterable = None
    elif isinstance(values, Iterable) and not isinstance(values, (str, bytes)):
        iterable = values
    else:
        iterable = None
    return _normalize_int_list(iterable, 3)


def _serialize_colour_table(pcdata: PCData) -> dict[str, list[int]]:
    """Capture the player's colour configuration arrays."""

    table: dict[str, list[int]] = {}
    for field_name in PCDATA_COLOUR_FIELDS:
        values = getattr(pcdata, field_name, None)
        table[field_name] = _normalize_colour_entry(values)
    return table


def _apply_colour_table(pcdata: PCData, table: Any) -> None:
    """Restore colour configuration arrays onto ``pcdata``."""

    if not isinstance(table, dict):
        return
    for field_name in PCDATA_COLOUR_FIELDS:
        values = table.get(field_name)
        setattr(pcdata, field_name, _normalize_colour_entry(values))


def _deserialize_skill_map(raw_skills: Any) -> dict[str, int]:
    """Convert persisted skill data back into a runtime map."""

    if isinstance(raw_skills, dict):
        items = raw_skills.items()
    else:
        try:
            items = dict(raw_skills or {}).items()
        except Exception:
            return {}
    skills: dict[str, int] = {}
    for name, value in items:
        try:
            key = str(name).strip()
        except Exception:
            continue
        if not key:
            continue
        try:
            learned = int(value)
        except (TypeError, ValueError):
            continue
        learned = max(0, min(100, learned))
        if learned <= 0:
            continue
        skills[key] = learned
    return skills


def _deserialize_groups(raw_groups: Any) -> tuple[str, ...]:
    """Convert persisted group knowledge into a tuple of group names."""

    if isinstance(raw_groups, str):
        iterable = [raw_groups]
    elif raw_groups is None:
        iterable = []
    else:
        try:
            iterable = list(raw_groups)
        except Exception:
            iterable = []
    seen: set[str] = set()
    ordered: list[str] = []
    for entry in iterable:
        try:
            name = str(entry).strip().lower()
        except Exception:
            continue
        if not name or name in seen:
            continue
        seen.add(name)
        ordered.append(name)
    return tuple(ordered)


@dataclass
class ObjectAffectSave:
    """Serializable snapshot of an object's affect."""

    where: int = 0
    type: int = 0
    level: int = 0
    duration: int = 0
    location: int = 0
    modifier: int = 0
    bitvector: int = 0


@dataclass
class ObjectSave:
    """Serializable snapshot of a runtime object and its nested contents."""

    vnum: int
    wear_slot: str | None = None
    wear_loc: int = int(WearLocation.NONE)
    level: int = 0
    timer: int = 0
    cost: int = 0
    value: list[int] = field(default_factory=lambda: [0, 0, 0, 0, 0])
    extra_flags: int = 0
    condition: int | str | None = None
    enchanted: bool = False
    item_type: str | None = None
    contains: list[ObjectSave] = field(default_factory=list)
    affects: list[ObjectAffectSave] = field(default_factory=list)


@dataclass
class PlayerSave:
    """Serializable snapshot of a player's state."""

    name: str
    level: int
    race: int = 0
    ch_class: int = 0
    clan: int = 0
    sex: int = 0
    trust: int = 0
    security: int = 0
    invis_level: int = 0
    incog_level: int = 0
    hit: int = 0
    max_hit: int = 0
    mana: int = 0
    max_mana: int = 0
    move: int = 0
    max_move: int = 0
    perm_hit: int = 0
    perm_mana: int = 0
    perm_move: int = 0
    gold: int = 0
    silver: int = 0
    exp: int = 0
    practice: int = 0
    train: int = 0
    played: int = 0
    lines: int = 0
    logon: int = 0
    prompt: str | None = None
    prefix: str | None = None
    title: str | None = None
    bamfin: str | None = None
    bamfout: str | None = None
    saving_throw: int = 0
    alignment: int = 0
    hitroll: int = 0
    damroll: int = 0
    wimpy: int = 0
    points: int = 0
    true_sex: int = 0
    last_level: int = 0
    position: int = 0
    armor: list[int] = field(default_factory=lambda: [0, 0, 0, 0])
    perm_stat: list[int] = field(default_factory=lambda: [0, 0, 0, 0, 0])
    mod_stat: list[int] = field(default_factory=lambda: [0, 0, 0, 0, 0])
    conditions: list[int] = field(default_factory=lambda: [0, 48, 48, 48])
    # ROM bitfields to preserve flags parity
    act: int = 0
    affected_by: int = 0
    comm: int = 0
    wiznet: int = 0
    log_commands: bool = False
    newbie_help_seen: bool = False
    room_vnum: int | None = None
    inventory: list[ObjectSave] = field(default_factory=list)
    equipment: dict[str, ObjectSave] = field(default_factory=dict)
    aliases: dict[str, str] = field(default_factory=dict)
    skills: dict[str, int] = field(default_factory=dict)
    groups: list[str] = field(default_factory=list)
    board: str = DEFAULT_BOARD_NAME
    last_notes: dict[str, float] = field(default_factory=dict)
    colours: dict[str, list[int]] = field(default_factory=dict)


_SLOT_TO_WEAR_LOC_MAP: dict[str, int] = {}
for _loc in WearLocation:
    _SLOT_TO_WEAR_LOC_MAP[_loc.name.lower()] = int(_loc)
    _SLOT_TO_WEAR_LOC_MAP[_loc.name.lower().replace("_", "")] = int(_loc)
_SLOT_TO_WEAR_LOC_MAP.update(
    {
        "fingerleft": int(WearLocation.FINGER_L),
        "fingerright": int(WearLocation.FINGER_R),
        "neck1": int(WearLocation.NECK_1),
        "neck2": int(WearLocation.NECK_2),
        "wristleft": int(WearLocation.WRIST_L),
        "wristright": int(WearLocation.WRIST_R),
    }
)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _slot_to_wear_loc(slot: str | None) -> int:
    if not slot:
        return int(WearLocation.NONE)
    key = slot.lower().replace(" ", "")
    if key in _SLOT_TO_WEAR_LOC_MAP:
        return _SLOT_TO_WEAR_LOC_MAP[key]
    return int(WearLocation.NONE)


def _serialize_affects(obj: Any) -> list[ObjectAffectSave]:
    affects: list[ObjectAffectSave] = []
    for affect in getattr(obj, "affected", []) or []:
        affects.append(
            ObjectAffectSave(
                where=_safe_int(getattr(affect, "where", 0)),
                type=_safe_int(getattr(affect, "type", 0)),
                level=_safe_int(getattr(affect, "level", 0)),
                duration=_safe_int(getattr(affect, "duration", 0)),
                location=_safe_int(getattr(affect, "location", 0)),
                modifier=_safe_int(getattr(affect, "modifier", 0)),
                bitvector=_safe_int(getattr(affect, "bitvector", 0)),
            )
        )
    return affects


def _serialize_object(obj: Any, *, wear_slot: str | None = None) -> ObjectSave:
    proto = getattr(obj, "prototype", None)
    vnum = getattr(proto, "vnum", None)
    if vnum is None:
        raise ValueError("Cannot serialize object without prototype vnum")

    value_source = getattr(obj, "value", None)
    if not value_source and proto is not None:
        value_source = getattr(proto, "value", None)

    return ObjectSave(
        vnum=_safe_int(vnum),
        wear_slot=wear_slot,
        wear_loc=_safe_int(getattr(obj, "wear_loc", _slot_to_wear_loc(wear_slot)), int(WearLocation.NONE)),
        level=_safe_int(getattr(obj, "level", getattr(proto, "level", 0))),
        timer=_safe_int(getattr(obj, "timer", 0)),
        cost=_safe_int(getattr(obj, "cost", getattr(proto, "cost", 0))),
        value=_normalize_int_list(value_source, 5),
        extra_flags=_safe_int(getattr(obj, "extra_flags", getattr(proto, "extra_flags", 0))),
        condition=getattr(obj, "condition", getattr(proto, "condition", None)),
        enchanted=bool(getattr(obj, "enchanted", False)),
        item_type=getattr(obj, "item_type", getattr(proto, "item_type", None)),
        contains=[_serialize_object(child) for child in getattr(obj, "contained_items", []) or []],
        affects=_serialize_affects(obj),
    )


def _deserialize_object(snapshot: ObjectSave) -> Any:
    obj = spawn_object(snapshot.vnum)
    if obj is None:
        return None

    obj.level = _safe_int(snapshot.level, getattr(obj, "level", 0))
    obj.timer = _safe_int(snapshot.timer, getattr(obj, "timer", 0))
    obj.cost = _safe_int(snapshot.cost, getattr(obj, "cost", 0))
    obj.value = _normalize_int_list(snapshot.value, 5)
    obj.extra_flags = _safe_int(snapshot.extra_flags, getattr(obj, "extra_flags", 0))
    obj.condition = snapshot.condition if snapshot.condition is not None else getattr(obj, "condition", 0)
    obj.enchanted = bool(snapshot.enchanted)
    obj.item_type = snapshot.item_type or getattr(obj, "item_type", None)
    wear_loc = snapshot.wear_loc if snapshot.wear_loc is not None else _slot_to_wear_loc(snapshot.wear_slot)
    obj.wear_loc = _safe_int(wear_loc, int(WearLocation.NONE))

    obj.affected = []
    for affect in snapshot.affects:
        obj.affected.append(
            Affect(
                where=_safe_int(getattr(affect, "where", 0)),
                type=_safe_int(getattr(affect, "type", 0)),
                level=_safe_int(getattr(affect, "level", 0)),
                duration=_safe_int(getattr(affect, "duration", 0)),
                location=_safe_int(getattr(affect, "location", 0)),
                modifier=_safe_int(getattr(affect, "modifier", 0)),
                bitvector=_safe_int(getattr(affect, "bitvector", 0)),
            )
        )

    obj.contained_items = []
    for child_snapshot in snapshot.contains:
        child = _deserialize_object(child_snapshot)
        if child is not None:
            obj.contained_items.append(child)

    return obj


def _upgrade_legacy_save(raw_data: dict[str, Any]) -> dict[str, Any]:
    upgraded: dict[str, Any] = dict(raw_data)

    raw_inventory = upgraded.get("inventory", [])
    if isinstance(raw_inventory, list):
        new_inventory: list[dict[str, Any]] = []
        for entry in raw_inventory:
            if isinstance(entry, dict):
                normalized = dict(entry)
                normalized.setdefault("wear_loc", normalized.get("wear_loc", int(WearLocation.NONE)))
                normalized.setdefault("wear_slot", normalized.get("wear_slot"))
                normalized.setdefault("value", _normalize_int_list(normalized.get("value", []), 5))
                normalized.setdefault("contains", [])
                normalized.setdefault("affects", [])
                new_inventory.append(normalized)
            elif entry is not None:
                new_inventory.append(
                    {
                        "vnum": _safe_int(entry),
                        "wear_loc": int(WearLocation.NONE),
                        "wear_slot": None,
                        "value": [0, 0, 0, 0, 0],
                        "contains": [],
                        "affects": [],
                    }
                )
        upgraded["inventory"] = new_inventory

    raw_equipment = upgraded.get("equipment", {})
    if isinstance(raw_equipment, dict):
        new_equipment: dict[str, dict[str, Any]] = {}
        for slot, entry in raw_equipment.items():
            if isinstance(entry, dict):
                normalized = dict(entry)
                normalized.setdefault("wear_slot", slot)
                normalized.setdefault("wear_loc", _slot_to_wear_loc(slot))
                normalized.setdefault("value", _normalize_int_list(normalized.get("value", []), 5))
                normalized.setdefault("contains", [])
                normalized.setdefault("affects", [])
                new_equipment[slot] = normalized
            elif entry is not None:
                new_equipment[slot] = {
                    "vnum": _safe_int(entry),
                    "wear_slot": slot,
                    "wear_loc": _slot_to_wear_loc(slot),
                    "value": [0, 0, 0, 0, 0],
                    "contains": [],
                    "affects": [],
                }
        upgraded["equipment"] = new_equipment

    colours = upgraded.get("colours")
    if isinstance(colours, dict):
        normalized_colours: dict[str, list[int]] = {}
        for field_name in PCDATA_COLOUR_FIELDS:
            normalized_colours[field_name] = _normalize_colour_entry(colours.get(field_name))
        upgraded["colours"] = normalized_colours
    else:
        upgraded["colours"] = {}

    return upgraded


PLAYERS_DIR = Path("data/players")
TIME_FILE = Path("data/time.json")


def save_character(char: Character) -> None:
    """Persist ``char`` to ``PLAYERS_DIR`` as JSON."""
    if getattr(char, "is_npc", False):
        return
    PLAYERS_DIR.mkdir(parents=True, exist_ok=True)
    default_conditions = [0, 48, 48, 48]
    raw_conditions: list[int] = []
    pcdata = char.pcdata or PCData()
    raw_conditions = list(getattr(pcdata, "condition", []))
    conditions = default_conditions.copy()
    for idx, value in enumerate(raw_conditions[:4]):
        conditions[idx] = int(value)
    armor = _normalize_int_list(getattr(char, "armor", []), 4)
    perm_stat = _normalize_int_list(getattr(char, "perm_stat", []), 5)
    mod_stat = _normalize_int_list(getattr(char, "mod_stat", []), 5)
    skills_snapshot = _serialize_skill_map(getattr(char, "skills", {}))
    groups_snapshot = _serialize_groups(getattr(pcdata, "group_known", ()))
    pcdata.learned = dict(skills_snapshot)
    pcdata.group_known = tuple(groups_snapshot)
    colour_table = _serialize_colour_table(pcdata)
    ansi_enabled = bool(getattr(char, "ansi_enabled", True))
    act_flags = int(getattr(char, "act", 0))
    colour_bit = int(PlayerFlag.COLOUR)
    if ansi_enabled:
        act_flags |= colour_bit
    else:
        act_flags &= ~colour_bit
    char.act = act_flags
    char.ansi_enabled = ansi_enabled

    room = getattr(char, "room", None)
    current_vnum = getattr(room, "vnum", None)
    room_vnum: int
    if current_vnum == ROOM_VNUM_LIMBO:
        was_in_room = getattr(char, "was_in_room", None)
        fallback_vnum = getattr(was_in_room, "vnum", None)
        if fallback_vnum is not None:
            try:
                room_vnum = int(fallback_vnum)
            except (TypeError, ValueError):
                room_vnum = ROOM_VNUM_TEMPLE
        else:
            room_vnum = ROOM_VNUM_TEMPLE
    elif current_vnum is None:
        room_vnum = ROOM_VNUM_TEMPLE
    else:
        try:
            room_vnum = int(current_vnum)
        except (TypeError, ValueError):
            room_vnum = ROOM_VNUM_TEMPLE
    char_name = char.name or ""
    now = int(time.time())
    try:
        logon_value = int(getattr(char, "logon", 0) or 0)
    except (TypeError, ValueError):
        logon_value = 0
    try:
        base_played = int(getattr(char, "played", 0) or 0)
    except (TypeError, ValueError):
        base_played = 0
    session_played = 0
    if logon_value:
        session_played = max(0, now - logon_value)
    total_played = max(0, base_played + session_played)
    prompt_value = getattr(char, "prompt", None)
    prefix_value = getattr(char, "prefix", None)
    if prefix_value is not None:
        prefix_value = str(prefix_value)
    title_value = getattr(pcdata, "title", None)
    bamfin_value = getattr(pcdata, "bamfin", None)
    if bamfin_value is not None:
        bamfin_value = str(bamfin_value)
    bamfout_value = getattr(pcdata, "bamfout", None)
    if bamfout_value is not None:
        bamfout_value = str(bamfout_value)
    try:
        lines_value = int(getattr(char, "lines", 0) or 0)
    except (TypeError, ValueError):
        lines_value = 0

    data = PlayerSave(
        name=char.name or "",
        level=char.level,
        race=int(getattr(char, "race", 0)),
        ch_class=int(getattr(char, "ch_class", 0)),
        clan=lookup_clan_id(getattr(char, "clan", 0)),
        sex=int(getattr(char, "sex", 0)),
        trust=int(getattr(char, "trust", 0)),
        security=int(getattr(pcdata, "security", 0)),
        invis_level=int(getattr(char, "invis_level", 0)),
        incog_level=int(getattr(char, "incog_level", 0)),
        hit=char.hit,
        max_hit=char.max_hit,
        mana=char.mana,
        max_mana=char.max_mana,
        move=char.move,
        max_move=char.max_move,
        perm_hit=int(getattr(pcdata, "perm_hit", 0)),
        perm_mana=int(getattr(pcdata, "perm_mana", 0)),
        perm_move=int(getattr(pcdata, "perm_move", 0)),
        gold=char.gold,
        silver=char.silver,
        exp=char.exp,
        practice=int(getattr(char, "practice", 0)),
        train=int(getattr(char, "train", 0)),
        played=total_played,
        lines=lines_value,
        logon=logon_value,
        prompt=prompt_value,
        prefix=prefix_value if prefix_value else None,
        title=title_value,
        bamfin=bamfin_value,
        bamfout=bamfout_value,
        saving_throw=int(getattr(char, "saving_throw", 0)),
        alignment=int(getattr(char, "alignment", 0)),
        hitroll=int(getattr(char, "hitroll", 0)),
        damroll=int(getattr(char, "damroll", 0)),
        wimpy=int(getattr(char, "wimpy", 0)),
        points=int(getattr(pcdata, "points", 0)),
        true_sex=int(getattr(pcdata, "true_sex", 0)),
        last_level=int(getattr(pcdata, "last_level", 0)),
        position=char.position,
        armor=armor,
        perm_stat=perm_stat,
        mod_stat=mod_stat,
        conditions=conditions,
        act=act_flags,
        affected_by=getattr(char, "affected_by", 0),
        comm=getattr(char, "comm", 0),
        wiznet=getattr(char, "wiznet", 0),
        log_commands=bool(getattr(char, "log_commands", False)),
        newbie_help_seen=bool(getattr(char, "newbie_help_seen", False)),
        room_vnum=room_vnum,
        inventory=[_serialize_object(obj) for obj in char.inventory],
        equipment={slot: _serialize_object(obj, wear_slot=slot) for slot, obj in char.equipment.items()},
        aliases=dict(getattr(char, "aliases", {})),
        skills=skills_snapshot,
        groups=groups_snapshot,
        board=getattr(pcdata, "board_name", DEFAULT_BOARD_NAME) or DEFAULT_BOARD_NAME,
        last_notes=dict(getattr(pcdata, "last_notes", {}) or {}),
        colours=colour_table,
    )
    path = PLAYERS_DIR / f"{char_name.lower()}.json"
    tmp_path = path.with_suffix(".tmp")
    with tmp_path.open("w") as f:
        dump_dataclass(data, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, path)


def load_character(name: str) -> Character | None:
    """Load a character by ``name`` from ``PLAYERS_DIR``."""
    path = PLAYERS_DIR / f"{name.lower()}.json"
    if not path.exists():
        return None
    with path.open() as f:
        raw_data = json.load(f)
    data = dataclass_from_dict(PlayerSave, _upgrade_legacy_save(raw_data))
    skills_map = _deserialize_skill_map(getattr(data, "skills", {}))
    groups_tuple = _deserialize_groups(getattr(data, "groups", []))
    armor = _normalize_int_list(getattr(data, "armor", []), 4)
    perm_stat = _normalize_int_list(getattr(data, "perm_stat", []), 5)
    mod_stat = _normalize_int_list(getattr(data, "mod_stat", []), 5)
    char = Character(
        name=data.name,
        level=data.level,
        race=int(getattr(data, "race", 0)),
        ch_class=int(getattr(data, "ch_class", 0)),
        clan=lookup_clan_id(getattr(data, "clan", 0)),
        sex=int(getattr(data, "sex", 0)),
        trust=int(getattr(data, "trust", 0)),
        invis_level=int(getattr(data, "invis_level", 0)),
        incog_level=int(getattr(data, "incog_level", 0)),
        prompt=getattr(data, "prompt", None),
        hit=data.hit,
        max_hit=data.max_hit,
        mana=data.mana,
        max_mana=data.max_mana,
        move=data.move,
        max_move=data.max_move,
        gold=data.gold,
        silver=data.silver,
        exp=data.exp,
        act=int(getattr(data, "act", 0)),
        practice=int(getattr(data, "practice", 0)),
        train=int(getattr(data, "train", 0)),
        saving_throw=int(getattr(data, "saving_throw", 0)),
        alignment=int(getattr(data, "alignment", 0)),
        hitroll=int(getattr(data, "hitroll", 0)),
        damroll=int(getattr(data, "damroll", 0)),
        wimpy=int(getattr(data, "wimpy", 0)),
        lines=int(getattr(data, "lines", 0)),
        played=int(getattr(data, "played", 0)),
        logon=int(getattr(data, "logon", 0)),
        comm=int(getattr(data, "comm", 0)),
        position=data.position,
        armor=armor,
        perm_stat=perm_stat,
        mod_stat=mod_stat,
        newbie_help_seen=bool(getattr(data, "newbie_help_seen", False)),
    )
    char.is_npc = False
    act_flags = int(getattr(data, "act", 0))
    char.ansi_enabled = bool(act_flags & int(PlayerFlag.COLOUR))
    prefix_value = getattr(data, "prefix", None)
    char.prefix = str(prefix_value) if prefix_value is not None else ""
    char.skills = skills_map
    # restore bitfields
    char.affected_by = getattr(data, "affected_by", 0)
    char.wiznet = getattr(data, "wiznet", 0)
    target_room = None
    if data.room_vnum is not None:
        try:
            room_key = int(data.room_vnum)
        except (TypeError, ValueError):
            room_key = None
        if room_key is not None:
            target_room = room_registry.get(room_key)
    if target_room is None:
        target_room = room_registry.get(ROOM_VNUM_LIMBO)
    if target_room is None:
        target_room = room_registry.get(ROOM_VNUM_TEMPLE)
    if target_room is not None:
        target_room.add_character(char)
    for snapshot in data.inventory:
        obj = _deserialize_object(snapshot)
        if obj is not None:
            char.add_object(obj)
    for slot, snapshot in data.equipment.items():
        obj = _deserialize_object(snapshot)
        if obj is not None:
            char.equip_object(obj, slot)
    # restore aliases
    try:
        char.aliases.update(getattr(data, "aliases", {}) or {})
    except Exception:
        pass
    board_name = getattr(data, "board", DEFAULT_BOARD_NAME) or DEFAULT_BOARD_NAME
    board = find_board(board_name)
    if board is None:
        board = find_board(DEFAULT_BOARD_NAME)
        if board is None:
            board = get_board(DEFAULT_BOARD_NAME)
    pcdata = PCData()
    saved_conditions = list(getattr(data, "conditions", []))
    conditions = [0, 48, 48, 48]
    for idx, value in enumerate(saved_conditions[:4]):
        conditions[idx] = int(value)
    pcdata.condition = conditions
    pcdata.security = int(getattr(data, "security", 0))
    pcdata.points = int(getattr(data, "points", 0))
    pcdata.true_sex = int(getattr(data, "true_sex", 0))
    pcdata.last_level = int(getattr(data, "last_level", 0))
    pcdata.perm_hit = int(getattr(data, "perm_hit", 0))
    pcdata.perm_mana = int(getattr(data, "perm_mana", 0))
    pcdata.perm_move = int(getattr(data, "perm_move", 0))
    pcdata.board_name = board.storage_key()
    title_value = getattr(data, "title", None)
    if title_value is not None:
        pcdata.title = title_value
    bamfin_value = getattr(data, "bamfin", None)
    if bamfin_value is not None:
        pcdata.bamfin = str(bamfin_value)
    bamfout_value = getattr(data, "bamfout", None)
    if bamfout_value is not None:
        pcdata.bamfout = str(bamfout_value)
    pcdata.last_notes.update(getattr(data, "last_notes", {}) or {})
    pcdata.learned = dict(skills_map)
    pcdata.group_known = groups_tuple
    _apply_colour_table(pcdata, getattr(data, "colours", {}))
    char.pcdata = pcdata
    char.log_commands = bool(getattr(data, "log_commands", False))
    character_registry.append(char)
    return char


def save_world() -> None:
    """Write all registered characters to disk."""
    save_time_info()
    for char in list(character_registry):
        if not getattr(char, "name", None):
            continue
        if getattr(char, "is_npc", False):
            continue
        save_character(char)


def load_world() -> list[Character]:
    """Load all character files from ``PLAYERS_DIR``."""
    chars: list[Character] = []
    load_time_info()
    if not PLAYERS_DIR.exists():
        return chars
    for path in PLAYERS_DIR.glob("*.json"):
        char = load_character(path.stem)
        if char:
            chars.append(char)
    return chars


# --- Time persistence ---


@dataclass
class TimeSave:
    hour: int
    day: int
    month: int
    year: int
    sunlight: int


def save_time_info() -> None:
    """Persist global time_info to TIME_FILE (atomic write)."""
    TIME_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = TimeSave(
        hour=time_info.hour,
        day=time_info.day,
        month=time_info.month,
        year=time_info.year,
        sunlight=int(time_info.sunlight),
    )
    tmp_path = TIME_FILE.with_suffix(".tmp")
    with tmp_path.open("w") as f:
        dump_dataclass(data, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, TIME_FILE)


def load_time_info() -> None:
    """Load global time_info from TIME_FILE if present."""
    if not TIME_FILE.exists():
        return
    with TIME_FILE.open() as f:
        data = load_dataclass(TimeSave, f)
    time_info.hour = data.hour
    time_info.day = data.day
    time_info.month = data.month
    time_info.year = data.year
    try:
        time_info.sunlight = Sunlight(data.sunlight)
    except Exception:
        # Fallback if invalid value
        time_info.sunlight = Sunlight.DARK
