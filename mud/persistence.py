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
class PetAffectSave:
    """Serializable snapshot of a pet's affect (ROM save.c:fwrite_pet lines 511-521)."""

    skill_name: str
    where: int = 0
    level: int = 0
    duration: int = 0
    modifier: int = 0
    location: int = 0
    bitvector: int = 0


@dataclass
class PetSave:
    """Serializable snapshot of a pet/follower (ROM save.c:fwrite_pet lines 449-523).

    Mirrors ROM C's fwrite_pet() behavior:
    - Saves mob vnum, stats, position, affects
    - Does NOT save pet inventory (pets can't carry items in ROM)
    - Used for charmed mobs that follow player

    ROM C Reference: src/save.c:449-523 (fwrite_pet)
    """

    vnum: int
    name: str
    short_descr: str | None = None
    long_descr: str | None = None
    description: str | None = None
    race: str | None = None
    clan: str | None = None
    sex: int = 0
    level: int | None = None
    hit: int = 0
    max_hit: int = 0
    mana: int = 0
    max_mana: int = 0
    move: int = 0
    max_move: int = 0
    gold: int = 0
    silver: int = 0
    exp: int = 0
    act: int | None = None
    affected_by: int | None = None
    comm: int | None = None
    position: int = 0
    saving_throw: int | None = None
    alignment: int | None = None
    hitroll: int | None = None
    damroll: int | None = None
    armor: list[int] = field(default_factory=lambda: [0, 0, 0, 0])
    perm_stat: list[int] = field(default_factory=lambda: [0, 0, 0, 0, 0])
    mod_stat: list[int] = field(default_factory=lambda: [0, 0, 0, 0, 0])
    affects: list[PetAffectSave] = field(default_factory=list)


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
    pet: PetSave | None = None  # ROM save.c pet persistence (fwrite_pet/fread_pet)
    # TABLES-001 — schema version for AffectFlag bit-position migration.
    # 0 = legacy pfile (pre-2.6.34) using old Python bits; 1 = ROM-canonical.
    pfile_version: int = 0
    # INV-008 — auth credential round-trip.  Stored here so the JSON pfile is
    # the single source of truth for ALL player state (gameplay + auth).  The
    # DB row's password_hash is only written explicitly (e.g. on do_password)
    # for the auth path that reads from the DB; the JSON copy is the canonical
    # one loaded at login.
    password_hash: str = ""


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


def _serialize_pet(pet: Character) -> PetSave | None:
    """Serialize a pet/follower to PetSave (ROM save.c:fwrite_pet lines 449-523).

    Args:
        pet: Character object representing the pet/follower

    Returns:
        PetSave object or None if pet has no mob_index

    ROM C Reference: src/save.c:449-523 (fwrite_pet)
    """
    from mud.models.mob import MobIndex
    from mud.skills.registry import skill_registry

    mob_index = getattr(pet, "prototype", None)
    if mob_index is None or not isinstance(mob_index, MobIndex):
        return None

    # Serialize pet affects (ROM save.c lines 511-521)
    pet_affects: list[PetAffectSave] = []
    for affect in getattr(pet, "affected", []) or []:
        affect_type = getattr(affect, "type", -1)
        if affect_type < 0:
            continue

        # Lookup skill name by searching registry
        skill_name = ""
        for name, skill in skill_registry.skills.items():
            if hasattr(skill, "slot") and skill.slot == affect_type:
                skill_name = name
                break
        pet_affects.append(
            PetAffectSave(
                skill_name=skill_name,
                where=_safe_int(getattr(affect, "where", 0)),
                level=_safe_int(getattr(affect, "level", 0)),
                duration=_safe_int(getattr(affect, "duration", 0)),
                modifier=_safe_int(getattr(affect, "modifier", 0)),
                location=_safe_int(getattr(affect, "location", 0)),
                bitvector=_safe_int(getattr(affect, "bitvector", 0)),
            )
        )

    # Only save fields that differ from prototype (ROM C pattern)
    pet_race = None
    if getattr(pet, "race", None) != mob_index.race:
        from mud.models.races import race_table

        pet_race = race_table[pet.race].name if pet.race < len(race_table) else None

    pet_clan = None
    if getattr(pet, "clan", 0):
        from mud.models.clans import clan_table

        pet_clan = clan_table[pet.clan].name if pet.clan in clan_table else None

    # Convert POS_FIGHTING to POS_STANDING for save (ROM C line 506)
    from mud.models.constants import Position

    position = pet.position
    if position == int(Position.FIGHTING):
        position = int(Position.STANDING)

    # MobInstance doesn't store descriptions (they're on prototype)
    # So we only save if custom descriptions were somehow set
    pet_short = getattr(pet, "short_descr", None)
    pet_long = getattr(pet, "long_descr", None)
    pet_desc = getattr(pet, "description", None)

    return PetSave(
        vnum=mob_index.vnum,
        name=pet.name,
        short_descr=pet_short if pet_short != mob_index.short_descr else None,
        long_descr=pet_long if pet_long != mob_index.long_descr else None,
        description=pet_desc if pet_desc != mob_index.description else None,
        race=pet_race,
        clan=pet_clan,
        sex=pet.sex,
        level=pet.level if pet.level != mob_index.level else None,
        hit=pet.hit,
        max_hit=pet.max_hit,
        mana=pet.mana,
        max_mana=pet.max_mana,
        move=pet.move,
        max_move=pet.max_move,
        gold=pet.gold if pet.gold > 0 else 0,
        silver=pet.silver if pet.silver > 0 else 0,
        exp=getattr(pet, "exp", 0),
        act=pet.act if pet.act != mob_index.act else None,
        affected_by=pet.affected_by if pet.affected_by != mob_index.affected_by else None,
        comm=pet.comm if pet.comm != 0 else None,
        position=position,
        saving_throw=getattr(pet, "saving_throw", 0),
        alignment=pet.alignment if pet.alignment != mob_index.alignment else None,
        hitroll=pet.hitroll if pet.hitroll != mob_index.hitroll else None,
        damroll=pet.damroll if pet.damroll != mob_index.damage[2] else None,  # DICE_BONUS index
        armor=_normalize_int_list(pet.armor, 4),
        perm_stat=_normalize_int_list(pet.perm_stat, 5),
        mod_stat=_normalize_int_list(getattr(pet, "mod_stat", [0] * 5), 5),
        affects=pet_affects,
    )


def _deserialize_pet(snapshot: PetSave | dict, owner: Character) -> Character | None:
    """Deserialize a PetSave to Character (ROM save.c:fread_pet lines 1406-1595).

    Args:
        snapshot: PetSave object or dict containing pet data
        owner: Character who owns the pet

    Returns:
        Character object representing the pet or None if vnum invalid

    ROM C Reference: src/save.c:1406-1595 (fread_pet)
    """
    from mud.spawning.mob_spawner import spawn_mob
    from mud.skills.registry import skill_registry
    from mud.models.obj import Affect

    # ROM C constant: #define MOB_VNUM_FIDO 3006 (src/merc.h)
    MOB_VNUM_FIDO = 3006

    # Convert dict to dataclass if needed
    if isinstance(snapshot, dict):
        snapshot = dataclass_from_dict(PetSave, snapshot)

    # Create mob from vnum (ROM save.c lines 1412-1425)
    pet = spawn_mob(snapshot.vnum)
    if pet is None:
        # Fallback to Fido if vnum invalid (ROM C pattern)
        pet = spawn_mob(MOB_VNUM_FIDO)
        if pet is None:
            return None

    # Restore basic fields
    pet.name = snapshot.name
    # MobInstance doesn't have short_descr/long_descr/description as instance attrs
    # (they're on prototype), but if we saved custom ones, restore them
    if snapshot.short_descr is not None:
        setattr(pet, "short_descr", snapshot.short_descr)
    if snapshot.long_descr is not None:
        setattr(pet, "long_descr", snapshot.long_descr)
    if snapshot.description is not None:
        setattr(pet, "description", snapshot.description)

    # Restore race
    if snapshot.race is not None:
        from mud.models.races import race_lookup

        pet.race = race_lookup(snapshot.race)

    # Restore clan
    if snapshot.clan is not None:
        from mud.models.clans import lookup_clan_id

        setattr(pet, "clan", lookup_clan_id(snapshot.clan))

    pet.sex = snapshot.sex
    if snapshot.level is not None:
        pet.level = snapshot.level

    # Restore HMV (hit/mana/move)
    pet.hit = snapshot.hit if hasattr(pet, "hit") else snapshot.hit
    pet.max_hit = snapshot.max_hit
    pet.mana = snapshot.mana
    pet.max_mana = snapshot.max_mana
    pet.move = snapshot.move
    pet.max_move = snapshot.max_move

    pet.gold = snapshot.gold
    pet.silver = snapshot.silver
    setattr(pet, "exp", snapshot.exp)

    if snapshot.act is not None:
        pet.act = snapshot.act
    if snapshot.affected_by is not None:
        pet.affected_by = snapshot.affected_by
    if snapshot.comm is not None:
        pet.comm = snapshot.comm

    pet.position = snapshot.position

    if snapshot.saving_throw is not None:
        setattr(pet, "saving_throw", snapshot.saving_throw)
    if snapshot.alignment is not None:
        pet.alignment = snapshot.alignment
    if snapshot.hitroll is not None:
        pet.hitroll = snapshot.hitroll
    if snapshot.damroll is not None:
        pet.damroll = snapshot.damroll

    pet.armor = list(snapshot.armor)  # Convert tuple to list if needed
    pet.perm_stat = list(snapshot.perm_stat)
    # MobInstance might not have mod_stat
    setattr(pet, "mod_stat", list(snapshot.mod_stat))

    # Restore affects (ROM save.c lines 1464-1552)
    pet_affects = []
    for affect_dict in snapshot.affects:
        # Convert dict to PetAffectSave if needed
        if isinstance(affect_dict, dict):
            affect_save = dataclass_from_dict(PetAffectSave, affect_dict)
        else:
            affect_save = affect_dict

        # Lookup skill by name
        skill_num = -1
        for name, skill in skill_registry.skills.items():
            if name == affect_save.skill_name and hasattr(skill, "slot"):
                skill_num = skill.slot
                break

        if skill_num < 0:
            continue

        # Check for duplicate affects (ROM C check_pet_affected pattern)
        # This prevents affect stacking bugs when loading pets
        duplicate = False
        prototype = getattr(pet, "prototype", None)
        if prototype:
            for existing in getattr(prototype, "affected", []) or []:
                if (
                    existing.type == skill_num
                    and existing.location == affect_save.location
                    and existing.modifier == affect_save.modifier
                ):
                    duplicate = True
                    break

        if not duplicate:
            pet_affects.append(
                Affect(
                    type=skill_num,
                    where=affect_save.where,
                    level=affect_save.level,
                    duration=affect_save.duration,
                    location=affect_save.location,
                    modifier=affect_save.modifier,
                    bitvector=affect_save.bitvector,
                )
            )

    # Store affects on pet (MobInstance doesn't have affected by default)
    setattr(pet, "affected", pet_affects)

    # Set owner relationship (MobInstance might not have master/leader by default)
    setattr(pet, "master", owner)
    setattr(pet, "leader", owner)

    return pet


def _migrate_affect_bits_in_objects(entries: Any) -> None:
    """In-place: translate ``affects[*].bitvector`` on object snapshots
    (recursively into ``contains``)."""
    if not isinstance(entries, list):
        return
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        affects = entry.get("affects")
        if isinstance(affects, list):
            for aff in affects:
                if isinstance(aff, dict):
                    aff["bitvector"] = translate_legacy_affect_bits(_safe_int(aff.get("bitvector", 0)))
        _migrate_affect_bits_in_objects(entry.get("contains"))


def _upgrade_legacy_save(raw_data: dict[str, Any]) -> dict[str, Any]:
    upgraded: dict[str, Any] = dict(raw_data)

    # TABLES-001 — translate AffectFlag bits to ROM-canonical layout for
    # legacy pfiles (pfile_version < 1). Touches the character bitvector,
    # any persisted item-affect bitvectors, and the pet's bitvectors.
    pfile_version = _safe_int(upgraded.get("pfile_version", 0))
    if pfile_version < 1:
        upgraded["affected_by"] = translate_legacy_affect_bits(_safe_int(upgraded.get("affected_by", 0)))
        _migrate_affect_bits_in_objects(upgraded.get("inventory"))
        equipment = upgraded.get("equipment")
        if isinstance(equipment, dict):
            _migrate_affect_bits_in_objects(list(equipment.values()))
        pet = upgraded.get("pet")
        if isinstance(pet, dict):
            if pet.get("affected_by") is not None:
                pet["affected_by"] = translate_legacy_affect_bits(_safe_int(pet.get("affected_by", 0)))
            pet_affects = pet.get("affects")
            if isinstance(pet_affects, list):
                for aff in pet_affects:
                    if isinstance(aff, dict):
                        aff["bitvector"] = translate_legacy_affect_bits(_safe_int(aff.get("bitvector", 0)))
        upgraded["pfile_version"] = PFILE_SCHEMA_VERSION

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


# TABLES-001 — AffectFlag bit-position migration.
# Pre-2.6.34 pfiles encoded AffectFlag with the legacy Python bit positions
# (mud/models/constants.py prior to renumber). Those positions diverge from
# ROM merc.h:953-982 for 20 of 29 bits. Saves are now ROM-canonical
# (pfile_version=1); older saves (pfile_version=0) get translated on load.
#
# Map: legacy Python bit index -> ROM-canonical bit index. Bits not listed
# (0..5, 22, 27, 28) coincide between old and new and pass through unchanged.
_AFFECT_BIT_TRANSLATION: dict[int, int] = {
    6: 7,    # SANCTUARY
    7: 8,    # FAERIE_FIRE
    8: 9,    # INFRARED
    9: 10,   # CURSE
    10: 6,   # DETECT_GOOD
    11: 12,  # POISON (legacy bit 11 → ROM bit M=12; old bit 11 vacated)
    12: 13,  # PROTECT_EVIL
    13: 14,  # PROTECT_GOOD
    14: 15,  # SNEAK
    15: 16,  # HIDE
    16: 17,  # SLEEP
    17: 18,  # CHARM
    18: 19,  # FLYING
    19: 20,  # PASS_DOOR
    20: 24,  # WEAKEN
    21: 26,  # BERSERK
    23: 21,  # HASTE
    24: 29,  # SLOW
    25: 23,  # PLAGUE
    26: 25,  # DARK_VISION
}


def translate_legacy_affect_bits(value: int) -> int:
    """Translate a pre-TABLES-001 AffectFlag int to ROM-canonical bits.

    Used during pfile load when pfile_version < 1. See mud/models/constants.py
    AffectFlag and ROM src/merc.h:953-982 for the canonical bit layout.
    """
    if not value:
        return 0
    result = 0
    for bit_index in range(30):
        if value & (1 << bit_index):
            new_bit = _AFFECT_BIT_TRANSLATION.get(bit_index, bit_index)
            result |= 1 << new_bit
    return result


PFILE_SCHEMA_VERSION = 1


# ---------------------------------------------------------------------------
# save_character / load_character have been removed (INV-008 Phase 2).
# Use mud.account.account_manager.save_character / load_character instead.
# The DB row is now the canonical source for all player state.
# ---------------------------------------------------------------------------


def save_world() -> None:
    """Write all registered characters to DB (DB-canonical path, INV-008 phase 2)."""
    from mud.account.account_manager import save_character as _am_save
    save_time_info()
    for char in list(character_registry):
        if not getattr(char, "name", None):
            continue
        if getattr(char, "is_npc", False):
            continue
        _am_save(char)


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
