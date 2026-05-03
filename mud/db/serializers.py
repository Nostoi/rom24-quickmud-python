from __future__ import annotations

"""Serialization helpers for DB-canonical player persistence (INV-008).

Extracted from mud.persistence (deprecated stub) in 2.8.3.
These helpers convert runtime Character / Object / Pet state to/from
the JSON blob columns written by mud.account.account_manager and read
back by mud.models.character.from_orm.

ROM C reference: src/save.c fwrite_char / fread_char,
fwrite_obj / fread_obj, fwrite_pet / fread_pet.
"""

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from mud.models.character import PCDATA_COLOUR_FIELDS, PCData
from mud.models.constants import WearLocation
from mud.models.json_io import dataclass_from_dict
from mud.models.obj import Affect


# ---------------------------------------------------------------------------
# Integer list helper
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Skill / group helpers
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Internal object helpers
# ---------------------------------------------------------------------------


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


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


def _slot_to_wear_loc(slot: str | None) -> int:
    if not slot:
        return int(WearLocation.NONE)
    key = slot.lower().replace(" ", "")
    if key in _SLOT_TO_WEAR_LOC_MAP:
        return _SLOT_TO_WEAR_LOC_MAP[key]
    return int(WearLocation.NONE)


# ---------------------------------------------------------------------------
# Object dataclasses
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Pet dataclasses
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Object serialize / deserialize
# ---------------------------------------------------------------------------


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
    from mud.spawning.obj_spawner import spawn_object

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


# ---------------------------------------------------------------------------
# Pet serialize / deserialize
# ---------------------------------------------------------------------------


def _serialize_pet(pet: Any) -> PetSave | None:
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


def _deserialize_pet(snapshot: PetSave | dict, owner: Any) -> Any:
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
