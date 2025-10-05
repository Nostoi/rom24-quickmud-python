"""ROM group_table metadata for character creation and customization."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Iterable, Tuple


@dataclass(frozen=True)
class GroupType:
    """Representation of ROM's ``group_type`` entries from ``src/const.c``."""

    name: str
    ratings: Tuple[int, int, int, int]
    skills: Tuple[str, ...]

    def cost_for_class_index(self, class_index: int) -> int | None:
        """Return the creation point cost for the class index or ``None``.

        ROM treats a negative rating as "not available" for that class. A cost
        of zero is free (used by `rom basics` and the class-specific basics).
        """

        if class_index < 0 or class_index >= len(self.ratings):
            return None
        cost = self.ratings[class_index]
        if cost < 0:
            return None
        return cost


GROUP_TABLE: Final[Tuple[GroupType, ...]] = (
    GroupType(
        name="rom basics",
        ratings=(0, 0, 0, 0),
        skills=("scrolls", "staves", "wands", "recall"),
    ),
    GroupType(
        name="mage basics",
        ratings=(0, -1, -1, -1),
        skills=("dagger",),
    ),
    GroupType(
        name="cleric basics",
        ratings=(-1, 0, -1, -1),
        skills=("mace",),
    ),
    GroupType(
        name="thief basics",
        ratings=(-1, -1, 0, -1),
        skills=("dagger", "steal"),
    ),
    GroupType(
        name="warrior basics",
        ratings=(-1, -1, -1, 0),
        skills=("sword", "second attack"),
    ),
    GroupType(
        name="mage default",
        ratings=(40, -1, -1, -1),
        skills=(
            "lore",
            "beguiling",
            "combat",
            "detection",
            "enhancement",
            "illusion",
            "maladictions",
            "protective",
            "transportation",
            "weather",
        ),
    ),
    GroupType(
        name="cleric default",
        ratings=(-1, 40, -1, -1),
        skills=(
            "flail",
            "attack",
            "creation",
            "curative",
            "benedictions",
            "detection",
            "healing",
            "maladictions",
            "protective",
            "shield block",
            "transportation",
            "weather",
        ),
    ),
    GroupType(
        name="thief default",
        ratings=(-1, -1, 40, -1),
        skills=(
            "mace",
            "sword",
            "backstab",
            "disarm",
            "dodge",
            "second attack",
            "trip",
            "hide",
            "peek",
            "pick lock",
            "sneak",
        ),
    ),
    GroupType(
        name="warrior default",
        ratings=(-1, -1, -1, 40),
        skills=(
            "weaponsmaster",
            "shield block",
            "bash",
            "disarm",
            "enhanced damage",
            "parry",
            "rescue",
            "third attack",
        ),
    ),
    GroupType(
        name="weaponsmaster",
        ratings=(40, 40, 40, 20),
        skills=(
            "axe",
            "dagger",
            "flail",
            "mace",
            "polearm",
            "spear",
            "sword",
            "whip",
        ),
    ),
    GroupType(
        name="attack",
        ratings=(-1, 5, -1, 8),
        skills=(
            "demonfire",
            "dispel evil",
            "dispel good",
            "earthquake",
            "flamestrike",
            "heat metal",
            "ray of truth",
        ),
    ),
    GroupType(
        name="beguiling",
        ratings=(4, -1, 6, -1),
        skills=("calm", "charm person", "sleep"),
    ),
    GroupType(
        name="benedictions",
        ratings=(-1, 4, -1, 8),
        skills=("bless", "calm", "frenzy", "holy word", "remove curse"),
    ),
    GroupType(
        name="combat",
        ratings=(6, -1, 10, 9),
        skills=(
            "acid blast",
            "burning hands",
            "chain lightning",
            "chill touch",
            "colour spray",
            "fireball",
            "lightning bolt",
            "magic missile",
            "shocking grasp",
        ),
    ),
    GroupType(
        name="creation",
        ratings=(4, 4, 8, 8),
        skills=(
            "continual light",
            "create food",
            "create spring",
            "create water",
            "create rose",
            "floating disc",
        ),
    ),
    GroupType(
        name="curative",
        ratings=(-1, 4, -1, 8),
        skills=("cure blindness", "cure disease", "cure poison"),
    ),
    GroupType(
        name="detection",
        ratings=(4, 3, 6, -1),
        skills=(
            "detect evil",
            "detect good",
            "detect hidden",
            "detect invis",
            "detect magic",
            "detect poison",
            "farsight",
            "identify",
            "know alignment",
            "locate object",
        ),
    ),
    GroupType(
        name="draconian",
        ratings=(8, -1, -1, -1),
        skills=(
            "acid breath",
            "fire breath",
            "frost breath",
            "gas breath",
            "lightning breath",
        ),
    ),
    GroupType(
        name="enchantment",
        ratings=(6, -1, -1, -1),
        skills=("enchant armor", "enchant weapon", "fireproof", "recharge"),
    ),
    GroupType(
        name="enhancement",
        ratings=(5, -1, 9, 9),
        skills=("giant strength", "haste", "infravision", "refresh"),
    ),
    GroupType(
        name="harmful",
        ratings=(-1, 3, -1, 6),
        skills=("cause critical", "cause light", "cause serious", "harm"),
    ),
    GroupType(
        name="healing",
        ratings=(-1, 3, -1, 6),
        skills=(
            "cure critical",
            "cure light",
            "cure serious",
            "heal",
            "mass healing",
            "refresh",
        ),
    ),
    GroupType(
        name="illusion",
        ratings=(4, -1, 7, -1),
        skills=("invis", "mass invis", "ventriloquate"),
    ),
    GroupType(
        name="maladictions",
        ratings=(5, 5, 9, 9),
        skills=(
            "blindness",
            "change sex",
            "curse",
            "energy drain",
            "plague",
            "poison",
            "slow",
            "weaken",
        ),
    ),
    GroupType(
        name="protective",
        ratings=(4, 4, 7, 8),
        skills=(
            "armor",
            "cancellation",
            "dispel magic",
            "fireproof",
            "protection evil",
            "protection good",
            "sanctuary",
            "shield",
            "stone skin",
        ),
    ),
    GroupType(
        name="transportation",
        ratings=(4, 4, 8, 9),
        skills=(
            "fly",
            "gate",
            "nexus",
            "pass door",
            "portal",
            "summon",
            "teleport",
            "word of recall",
        ),
    ),
    GroupType(
        name="weather",
        ratings=(4, 4, 8, 8),
        skills=(
            "call lightning",
            "control weather",
            "faerie fire",
            "faerie fog",
            "lightning bolt",
        ),
    ),
)


_GROUP_BY_NAME: Final[dict[str, GroupType]] = {
    group.name.lower(): group for group in GROUP_TABLE
}


def list_groups() -> Tuple[GroupType, ...]:
    """Return all group definitions in ROM order."""

    return GROUP_TABLE


def get_group(name: str) -> GroupType | None:
    """Lookup a group definition by case-insensitive name."""

    return _GROUP_BY_NAME.get(name.strip().lower())


def iter_group_names(groups: Iterable[str]) -> Tuple[str, ...]:
    """Normalize an iterable of group names into a tuple preserving order."""

    seen: set[str] = set()
    ordered: list[str] = []
    for entry in groups:
        lowered = entry.strip().lower()
        if not lowered or lowered in seen:
            continue
        seen.add(lowered)
        ordered.append(lowered)
    return tuple(ordered)

