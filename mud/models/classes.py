"""ROM class metadata required by the nanny."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Tuple

from mud.models.constants import (
    OBJ_VNUM_SCHOOL_DAGGER,
    OBJ_VNUM_SCHOOL_MACE,
    OBJ_VNUM_SCHOOL_SWORD,
    Stat,
)


@dataclass(frozen=True)
class ClassType:
    """Entry from ROM's class_table (src/const.c)."""

    name: str
    who_name: str
    prime_stat: Stat
    first_weapon_vnum: int
    guild_vnums: Tuple[int, int]
    skill_adept: int
    thac0_00: int
    thac0_32: int
    hp_min: int
    hp_max: int
    gains_mana: bool
    base_group: str
    default_group: str


CLASS_TABLE: Final[tuple[ClassType, ...]] = (
    ClassType(
        name="mage",
        who_name="Mag",
        prime_stat=Stat.INT,
        first_weapon_vnum=OBJ_VNUM_SCHOOL_DAGGER,
        guild_vnums=(3018, 9618),
        skill_adept=75,
        thac0_00=20,
        thac0_32=6,
        hp_min=6,
        hp_max=8,
        gains_mana=True,
        base_group="mage basics",
        default_group="mage default",
    ),
    ClassType(
        name="cleric",
        who_name="Cle",
        prime_stat=Stat.WIS,
        first_weapon_vnum=OBJ_VNUM_SCHOOL_MACE,
        guild_vnums=(3003, 9619),
        skill_adept=75,
        thac0_00=20,
        thac0_32=2,
        hp_min=7,
        hp_max=10,
        gains_mana=True,
        base_group="cleric basics",
        default_group="cleric default",
    ),
    ClassType(
        name="thief",
        who_name="Thi",
        prime_stat=Stat.DEX,
        first_weapon_vnum=OBJ_VNUM_SCHOOL_DAGGER,
        guild_vnums=(3028, 9639),
        skill_adept=75,
        thac0_00=20,
        thac0_32=-4,
        hp_min=8,
        hp_max=13,
        gains_mana=False,
        base_group="thief basics",
        default_group="thief default",
    ),
    ClassType(
        name="warrior",
        who_name="War",
        prime_stat=Stat.STR,
        first_weapon_vnum=OBJ_VNUM_SCHOOL_SWORD,
        guild_vnums=(3022, 9633),
        skill_adept=75,
        thac0_00=20,
        thac0_32=-10,
        hp_min=11,
        hp_max=15,
        gains_mana=False,
        base_group="warrior basics",
        default_group="warrior default",
    ),
)


_CLASS_BY_NAME: Final[dict[str, ClassType]] = {cls.name: cls for cls in CLASS_TABLE}


def list_player_classes() -> tuple[ClassType, ...]:
    """Return all playable classes in ROM order."""

    return CLASS_TABLE


def get_player_class(name: str) -> ClassType | None:
    """Case-insensitive lookup for class metadata."""

    return _CLASS_BY_NAME.get(name.lower())

