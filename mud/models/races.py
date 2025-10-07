"""ROM race metadata used by the nanny creation flow."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntFlag
from typing import Final, Tuple, Type, TypeVar

from mud.models.constants import (
    ActFlag,
    AffectFlag,
    FormFlag,
    ImmFlag,
    OffFlag,
    PartFlag,
    ResFlag,
    Size,
    VulnFlag,
    convert_flags_from_letters,
)


F = TypeVar("F", bound=IntFlag)


@dataclass(frozen=True)
class RaceType:
    """Entry from ROM's race_table (src/const.c)."""

    name: str
    is_playable: bool
    act_flags: ActFlag
    affect_flags: AffectFlag
    offensive_flags: OffFlag
    immunity_flags: ImmFlag
    resistance_flags: ResFlag
    vulnerability_flags: VulnFlag
    form_flags: FormFlag
    part_flags: PartFlag


@dataclass(frozen=True)
class PcRaceType:
    """Entry from ROM's pc_race_table used during player creation."""

    name: str
    who_name: str
    points: int
    class_multipliers: Tuple[int, int, int, int]
    bonus_skills: Tuple[str, ...]
    base_stats: Tuple[int, int, int, int, int]
    max_stats: Tuple[int, int, int, int, int]
    size: Size


def _letters(letters: str, flag_enum: Type[F]) -> F:
    """Convert ROM letter masks into concrete IntFlag values."""

    if not letters:
        return flag_enum(0)
    return convert_flags_from_letters(letters, flag_enum)


_PLAYABLE_RACES: Final[tuple[RaceType, ...]] = (
    RaceType(
        name="human",
        is_playable=True,
        act_flags=ActFlag(0),
        affect_flags=AffectFlag(0),
        offensive_flags=OffFlag(0),
        immunity_flags=ImmFlag(0),
        resistance_flags=ResFlag(0),
        vulnerability_flags=VulnFlag(0),
        form_flags=_letters("AHMV", FormFlag),
        part_flags=_letters("ABCDEFGHIJK", PartFlag),
    ),
    RaceType(
        name="elf",
        is_playable=True,
        act_flags=ActFlag(0),
        affect_flags=AffectFlag.INFRARED,
        offensive_flags=OffFlag(0),
        immunity_flags=ImmFlag(0),
        resistance_flags=ResFlag.CHARM,
        vulnerability_flags=VulnFlag.IRON,
        form_flags=_letters("AHMV", FormFlag),
        part_flags=_letters("ABCDEFGHIJK", PartFlag),
    ),
    RaceType(
        name="dwarf",
        is_playable=True,
        act_flags=ActFlag(0),
        affect_flags=AffectFlag.INFRARED,
        offensive_flags=OffFlag(0),
        immunity_flags=ImmFlag(0),
        resistance_flags=ResFlag.POISON | ResFlag.DISEASE,
        vulnerability_flags=VulnFlag.DROWNING,
        form_flags=_letters("AHMV", FormFlag),
        part_flags=_letters("ABCDEFGHIJK", PartFlag),
    ),
    RaceType(
        name="giant",
        is_playable=True,
        act_flags=ActFlag(0),
        affect_flags=AffectFlag(0),
        offensive_flags=OffFlag(0),
        immunity_flags=ImmFlag(0),
        resistance_flags=ResFlag.FIRE | ResFlag.COLD,
        vulnerability_flags=VulnFlag.MENTAL | VulnFlag.LIGHTNING,
        form_flags=_letters("AHMV", FormFlag),
        part_flags=_letters("ABCDEFGHIJK", PartFlag),
    ),
)


PC_RACE_TABLE: Final[tuple[PcRaceType, ...]] = (
    PcRaceType(
        name="human",
        who_name="Human",
        points=0,
        class_multipliers=(100, 100, 100, 100),
        bonus_skills=(),
        base_stats=(13, 13, 13, 13, 13),
        max_stats=(18, 18, 18, 18, 18),
        size=Size.MEDIUM,
    ),
    PcRaceType(
        name="elf",
        who_name=" Elf ",
        points=5,
        class_multipliers=(100, 125, 100, 120),
        bonus_skills=("sneak", "hide"),
        base_stats=(12, 14, 13, 15, 11),
        max_stats=(16, 20, 18, 21, 15),
        size=Size.SMALL,
    ),
    PcRaceType(
        name="dwarf",
        who_name="Dwarf",
        points=8,
        class_multipliers=(150, 100, 125, 100),
        bonus_skills=("berserk",),
        base_stats=(14, 12, 14, 10, 15),
        max_stats=(20, 16, 19, 14, 21),
        size=Size.MEDIUM,
    ),
    PcRaceType(
        name="giant",
        who_name="Giant",
        points=6,
        class_multipliers=(200, 150, 150, 105),
        bonus_skills=("bash", "fast healing"),
        base_stats=(16, 11, 13, 11, 14),
        max_stats=(22, 15, 18, 15, 20),
        size=Size.LARGE,
    ),
)


_UNIQUE_SENTINEL: Final[RaceType] = RaceType(
    name="unique",
    is_playable=False,
    act_flags=ActFlag(0),
    affect_flags=AffectFlag(0),
    offensive_flags=OffFlag(0),
    immunity_flags=ImmFlag(0),
    resistance_flags=ResFlag(0),
    vulnerability_flags=VulnFlag(0),
    form_flags=FormFlag(0),
    part_flags=PartFlag(0),
)

_NPC_RACES: Final[tuple[RaceType, ...]] = (
    RaceType(
        name="bat",
        is_playable=False,
        act_flags=ActFlag(0),
        affect_flags=AffectFlag.FLYING | AffectFlag.DARK_VISION,
        offensive_flags=OffFlag.DODGE | OffFlag.FAST,
        immunity_flags=ImmFlag(0),
        resistance_flags=ResFlag(0),
        vulnerability_flags=VulnFlag.LIGHT,
        form_flags=_letters("AGV", FormFlag),
        part_flags=_letters("ACDEFHJKP", PartFlag),
    ),
    RaceType(
        name="bear",
        is_playable=False,
        act_flags=ActFlag(0),
        affect_flags=AffectFlag(0),
        offensive_flags=OffFlag.CRUSH | OffFlag.DISARM | OffFlag.BERSERK,
        immunity_flags=ImmFlag(0),
        resistance_flags=ResFlag.BASH | ResFlag.COLD,
        vulnerability_flags=VulnFlag(0),
        form_flags=_letters("AGV", FormFlag),
        part_flags=_letters("ABCDEFHJKUV", PartFlag),
    ),
    RaceType(
        name="cat",
        is_playable=False,
        act_flags=ActFlag(0),
        affect_flags=AffectFlag.DARK_VISION,
        offensive_flags=OffFlag.FAST | OffFlag.DODGE,
        immunity_flags=ImmFlag(0),
        resistance_flags=ResFlag(0),
        vulnerability_flags=VulnFlag(0),
        form_flags=_letters("AGV", FormFlag),
        part_flags=_letters("ACDEFHJKQUV", PartFlag),
    ),
    RaceType(
        name="centipede",
        is_playable=False,
        act_flags=ActFlag(0),
        affect_flags=AffectFlag.DARK_VISION,
        offensive_flags=OffFlag(0),
        immunity_flags=ImmFlag(0),
        resistance_flags=ResFlag.PIERCE | ResFlag.COLD,
        vulnerability_flags=VulnFlag.BASH,
        form_flags=_letters("ABGO", FormFlag),
        part_flags=_letters("ACK", PartFlag),
    ),
    RaceType(
        name="dog",
        is_playable=False,
        act_flags=ActFlag(0),
        affect_flags=AffectFlag(0),
        offensive_flags=OffFlag.FAST,
        immunity_flags=ImmFlag(0),
        resistance_flags=ResFlag(0),
        vulnerability_flags=VulnFlag(0),
        form_flags=_letters("AGV", FormFlag),
        part_flags=_letters("ACDEFHJKUV", PartFlag),
    ),
    RaceType(
        name="doll",
        is_playable=False,
        act_flags=ActFlag(0),
        affect_flags=AffectFlag(0),
        offensive_flags=OffFlag(0),
        immunity_flags=(
            ImmFlag.COLD
            | ImmFlag.POISON
            | ImmFlag.HOLY
            | ImmFlag.NEGATIVE
            | ImmFlag.MENTAL
            | ImmFlag.DISEASE
            | ImmFlag.DROWNING
        ),
        resistance_flags=ResFlag.BASH | ResFlag.LIGHT,
        vulnerability_flags=(
            VulnFlag.SLASH
            | VulnFlag.FIRE
            | VulnFlag.ACID
            | VulnFlag.LIGHTNING
            | VulnFlag.ENERGY
        ),
        form_flags=_letters("EJMcc", FormFlag),
        part_flags=_letters("ABCGHK", PartFlag),
    ),
    RaceType(
        name="dragon",
        is_playable=False,
        act_flags=ActFlag(0),
        affect_flags=AffectFlag.INFRARED | AffectFlag.FLYING,
        offensive_flags=OffFlag(0),
        immunity_flags=ImmFlag(0),
        resistance_flags=ResFlag.FIRE | ResFlag.BASH | ResFlag.CHARM,
        vulnerability_flags=VulnFlag.PIERCE | VulnFlag.COLD,
        form_flags=_letters("AHZ", FormFlag),
        part_flags=_letters("ACDEFGHIJKPQUVX", PartFlag),
    ),
    RaceType(
        name="fido",
        is_playable=False,
        act_flags=ActFlag(0),
        affect_flags=AffectFlag(0),
        offensive_flags=OffFlag.DODGE | OffFlag.ASSIST_RACE,
        immunity_flags=ImmFlag(0),
        resistance_flags=ResFlag(0),
        vulnerability_flags=VulnFlag.MAGIC,
        form_flags=_letters("ABGV", FormFlag),
        part_flags=_letters("ACDEFHJKQV", PartFlag),
    ),
    RaceType(
        name="fox",
        is_playable=False,
        act_flags=ActFlag(0),
        affect_flags=AffectFlag.DARK_VISION,
        offensive_flags=OffFlag.FAST | OffFlag.DODGE,
        immunity_flags=ImmFlag(0),
        resistance_flags=ResFlag(0),
        vulnerability_flags=VulnFlag(0),
        form_flags=_letters("AGV", FormFlag),
        part_flags=_letters("ACDEFHJKQV", PartFlag),
    ),
    RaceType(
        name="goblin",
        is_playable=False,
        act_flags=ActFlag(0),
        affect_flags=AffectFlag.INFRARED,
        offensive_flags=OffFlag(0),
        immunity_flags=ImmFlag(0),
        resistance_flags=ResFlag.DISEASE,
        vulnerability_flags=VulnFlag.MAGIC,
        form_flags=_letters("AHMV", FormFlag),
        part_flags=_letters("ABCDEFGHIJK", PartFlag),
    ),
    RaceType(
        name="hobgoblin",
        is_playable=False,
        act_flags=ActFlag(0),
        affect_flags=AffectFlag.INFRARED,
        offensive_flags=OffFlag(0),
        immunity_flags=ImmFlag(0),
        resistance_flags=ResFlag.DISEASE | ResFlag.POISON,
        vulnerability_flags=VulnFlag(0),
        form_flags=_letters("AHMVY", FormFlag),
        part_flags=_letters("ABCDEFGHIJKY", PartFlag),
    ),
    RaceType(
        name="kobold",
        is_playable=False,
        act_flags=ActFlag(0),
        affect_flags=AffectFlag.INFRARED,
        offensive_flags=OffFlag(0),
        immunity_flags=ImmFlag(0),
        resistance_flags=ResFlag.POISON,
        vulnerability_flags=VulnFlag.MAGIC,
        form_flags=_letters("ABHMV", FormFlag),
        part_flags=_letters("ABCDEFGHIJKQ", PartFlag),
    ),
    RaceType(
        name="lizard",
        is_playable=False,
        act_flags=ActFlag(0),
        affect_flags=AffectFlag(0),
        offensive_flags=OffFlag(0),
        immunity_flags=ImmFlag(0),
        resistance_flags=ResFlag.POISON,
        vulnerability_flags=VulnFlag.COLD,
        form_flags=_letters("AGXcc", FormFlag),
        part_flags=_letters("ACDEFHKQV", PartFlag),
    ),
    RaceType(
        name="modron",
        is_playable=False,
        act_flags=ActFlag(0),
        affect_flags=AffectFlag.INFRARED,
        offensive_flags=OffFlag.ASSIST_RACE | OffFlag.ASSIST_ALIGN,
        immunity_flags=(
            ImmFlag.CHARM | ImmFlag.DISEASE | ImmFlag.MENTAL | ImmFlag.HOLY | ImmFlag.NEGATIVE
        ),
        resistance_flags=ResFlag.FIRE | ResFlag.COLD | ResFlag.ACID,
        vulnerability_flags=VulnFlag(0),
        form_flags=_letters("H", FormFlag),
        part_flags=_letters("ABCGHJK", PartFlag),
    ),
    RaceType(
        name="orc",
        is_playable=False,
        act_flags=ActFlag(0),
        affect_flags=AffectFlag.INFRARED,
        offensive_flags=OffFlag(0),
        immunity_flags=ImmFlag(0),
        resistance_flags=ResFlag.DISEASE,
        vulnerability_flags=VulnFlag.LIGHT,
        form_flags=_letters("AHMV", FormFlag),
        part_flags=_letters("ABCDEFGHIJK", PartFlag),
    ),
    RaceType(
        name="pig",
        is_playable=False,
        act_flags=ActFlag(0),
        affect_flags=AffectFlag(0),
        offensive_flags=OffFlag(0),
        immunity_flags=ImmFlag(0),
        resistance_flags=ResFlag(0),
        vulnerability_flags=VulnFlag(0),
        form_flags=_letters("AGV", FormFlag),
        part_flags=_letters("ACDEFHJK", PartFlag),
    ),
    RaceType(
        name="rabbit",
        is_playable=False,
        act_flags=ActFlag(0),
        affect_flags=AffectFlag(0),
        offensive_flags=OffFlag.DODGE | OffFlag.FAST,
        immunity_flags=ImmFlag(0),
        resistance_flags=ResFlag(0),
        vulnerability_flags=VulnFlag(0),
        form_flags=_letters("AGV", FormFlag),
        part_flags=_letters("ACDEFHJK", PartFlag),
    ),
    RaceType(
        name="school monster",
        is_playable=False,
        act_flags=ActFlag.NOALIGN,
        affect_flags=AffectFlag(0),
        offensive_flags=OffFlag(0),
        immunity_flags=ImmFlag.CHARM | ImmFlag.SUMMON,
        resistance_flags=ResFlag(0),
        vulnerability_flags=VulnFlag.MAGIC,
        form_flags=_letters("AMV", FormFlag),
        part_flags=_letters("ABCDEFHJKQU", PartFlag),
    ),
    RaceType(
        name="snake",
        is_playable=False,
        act_flags=ActFlag(0),
        affect_flags=AffectFlag(0),
        offensive_flags=OffFlag(0),
        immunity_flags=ImmFlag(0),
        resistance_flags=ResFlag.POISON,
        vulnerability_flags=VulnFlag.COLD,
        form_flags=_letters("AGXYcc", FormFlag),
        part_flags=_letters("ADEFKLQVX", PartFlag),
    ),
    RaceType(
        name="song bird",
        is_playable=False,
        act_flags=ActFlag(0),
        affect_flags=AffectFlag.FLYING,
        offensive_flags=OffFlag.FAST | OffFlag.DODGE,
        immunity_flags=ImmFlag(0),
        resistance_flags=ResFlag(0),
        vulnerability_flags=VulnFlag(0),
        form_flags=_letters("AGW", FormFlag),
        part_flags=_letters("ACDEFHKP", PartFlag),
    ),
    RaceType(
        name="troll",
        is_playable=False,
        act_flags=ActFlag(0),
        affect_flags=(
            AffectFlag.REGENERATION | AffectFlag.INFRARED | AffectFlag.DETECT_HIDDEN
        ),
        offensive_flags=OffFlag.BERSERK,
        immunity_flags=ImmFlag(0),
        resistance_flags=ResFlag.CHARM | ResFlag.BASH,
        vulnerability_flags=VulnFlag.FIRE | VulnFlag.ACID,
        form_flags=_letters("ABHMV", FormFlag),
        part_flags=_letters("ABCDEFGHIJKUV", PartFlag),
    ),
    RaceType(
        name="water fowl",
        is_playable=False,
        act_flags=ActFlag(0),
        affect_flags=AffectFlag.SWIM | AffectFlag.FLYING,
        offensive_flags=OffFlag(0),
        immunity_flags=ImmFlag(0),
        resistance_flags=ResFlag.DROWNING,
        vulnerability_flags=VulnFlag(0),
        form_flags=_letters("AGW", FormFlag),
        part_flags=_letters("ACDEFHKP", PartFlag),
    ),
    RaceType(
        name="wolf",
        is_playable=False,
        act_flags=ActFlag(0),
        affect_flags=AffectFlag.DARK_VISION,
        offensive_flags=OffFlag.FAST | OffFlag.DODGE,
        immunity_flags=ImmFlag(0),
        resistance_flags=ResFlag(0),
        vulnerability_flags=VulnFlag(0),
        form_flags=_letters("AGV", FormFlag),
        part_flags=_letters("ACDEFJKQV", PartFlag),
    ),
    RaceType(
        name="wyvern",
        is_playable=False,
        act_flags=ActFlag(0),
        affect_flags=(
            AffectFlag.FLYING | AffectFlag.DETECT_INVIS | AffectFlag.DETECT_HIDDEN
        ),
        offensive_flags=OffFlag.BASH | OffFlag.FAST | OffFlag.DODGE,
        immunity_flags=ImmFlag.POISON,
        resistance_flags=ResFlag(0),
        vulnerability_flags=VulnFlag.LIGHT,
        form_flags=_letters("ABGZ", FormFlag),
        part_flags=_letters("ACDEFHJKQVX", PartFlag),
    ),
    RaceType(
        name="unique",
        is_playable=False,
        act_flags=ActFlag(0),
        affect_flags=AffectFlag(0),
        offensive_flags=OffFlag(0),
        immunity_flags=ImmFlag(0),
        resistance_flags=ResFlag(0),
        vulnerability_flags=VulnFlag(0),
        form_flags=FormFlag(0),
        part_flags=PartFlag(0),
    ),
)

RACE_TABLE: Final[tuple[RaceType, ...]] = (
    _UNIQUE_SENTINEL,
    *_PLAYABLE_RACES,
    *_NPC_RACES,
)

_RACES_BY_NAME: Final[dict[str, RaceType]] = {race.name: race for race in RACE_TABLE}
_PC_RACES_BY_NAME: Final[dict[str, PcRaceType]] = {race.name: race for race in PC_RACE_TABLE}


def get_race_by_index(index: int) -> RaceType | None:
    """Return race metadata by numeric index mirroring ROM ``race_table``."""

    try:
        resolved = int(index)
    except (TypeError, ValueError):  # pragma: no cover - defensive guard
        return None
    if resolved < 0 or resolved >= len(RACE_TABLE):
        return None
    return RACE_TABLE[resolved]


def get_race(name: str) -> RaceType | None:
    """Return base race metadata by lowercase name."""

    return _RACES_BY_NAME.get(name.lower())


def get_pc_race(name: str) -> PcRaceType | None:
    """Return PC creation metadata for the given race name."""

    return _PC_RACES_BY_NAME.get(name.lower())


def list_playable_races() -> tuple[PcRaceType, ...]:
    """Return all playable races in ROM order."""

    return PC_RACE_TABLE

