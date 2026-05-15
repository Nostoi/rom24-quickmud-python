from __future__ import annotations

from typing import NamedTuple

from mud.models.constants import (
    OBJ_VNUM_SCHOOL_AXE,
    OBJ_VNUM_SCHOOL_DAGGER,
    OBJ_VNUM_SCHOOL_FLAIL,
    OBJ_VNUM_SCHOOL_MACE,
    OBJ_VNUM_SCHOOL_POLEARM,
    OBJ_VNUM_SCHOOL_STAFF,
    OBJ_VNUM_SCHOOL_SWORD,
    OBJ_VNUM_SCHOOL_WHIP,
    WeaponType,
)


class WeaponTableEntry(NamedTuple):
    """ROM `weapon_table[]` row from `src/const.c:76-86`."""

    name: str
    school_vnum: int
    weapon_type: WeaponType
    skill_name: str


WEAPON_TABLE: tuple[WeaponTableEntry, ...] = (
    WeaponTableEntry("sword", OBJ_VNUM_SCHOOL_SWORD, WeaponType.SWORD, "sword"),
    WeaponTableEntry("mace", OBJ_VNUM_SCHOOL_MACE, WeaponType.MACE, "mace"),
    WeaponTableEntry("dagger", OBJ_VNUM_SCHOOL_DAGGER, WeaponType.DAGGER, "dagger"),
    WeaponTableEntry("axe", OBJ_VNUM_SCHOOL_AXE, WeaponType.AXE, "axe"),
    WeaponTableEntry("staff", OBJ_VNUM_SCHOOL_STAFF, WeaponType.SPEAR, "spear"),
    WeaponTableEntry("flail", OBJ_VNUM_SCHOOL_FLAIL, WeaponType.FLAIL, "flail"),
    WeaponTableEntry("whip", OBJ_VNUM_SCHOOL_WHIP, WeaponType.WHIP, "whip"),
    WeaponTableEntry("polearm", OBJ_VNUM_SCHOOL_POLEARM, WeaponType.POLEARM, "polearm"),
)

_WEAPON_BY_NAME: dict[str, WeaponTableEntry] = {entry.name: entry for entry in WEAPON_TABLE}
_WEAPON_BY_SCHOOL_VNUM: dict[int, WeaponTableEntry] = {entry.school_vnum: entry for entry in WEAPON_TABLE}
_WEAPON_BY_TYPE: dict[WeaponType, WeaponTableEntry] = {}
for _entry in WEAPON_TABLE:
    _WEAPON_BY_TYPE.setdefault(_entry.weapon_type, _entry)


def weapon_table_entry_by_name(name: str | None) -> WeaponTableEntry | None:
    if name is None:
        return None
    return _WEAPON_BY_NAME.get(name.strip().lower())


def weapon_table_entry_by_school_vnum(vnum: int | None) -> WeaponTableEntry | None:
    if vnum is None:
        return None
    try:
        return _WEAPON_BY_SCHOOL_VNUM.get(int(vnum))
    except (TypeError, ValueError):
        return None


def weapon_table_entry_by_type(weapon_type: WeaponType | int | None) -> WeaponTableEntry | None:
    if weapon_type is None:
        return None
    try:
        normalized = WeaponType(int(weapon_type))
    except (TypeError, ValueError):
        return None
    return _WEAPON_BY_TYPE.get(normalized)


def weapon_skill_name_for_school_vnum(vnum: int | None) -> str | None:
    entry = weapon_table_entry_by_school_vnum(vnum)
    return entry.skill_name if entry is not None else None


def weapon_skill_name_for_type(weapon_type: WeaponType | int | None) -> str | None:
    entry = weapon_table_entry_by_type(weapon_type)
    return entry.skill_name if entry is not None else None


def weapon_name_for_type(weapon_type: WeaponType | int | None) -> str:
    entry = weapon_table_entry_by_type(weapon_type)
    if entry is None:
        return "exotic"
    if entry.weapon_type == WeaponType.SPEAR:
        return "spear"
    return entry.name
