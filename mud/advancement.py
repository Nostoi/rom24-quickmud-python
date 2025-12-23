from __future__ import annotations

import time

from mud.math.c_compat import c_div
from mud.models.character import Character
from mud.models.constants import LEVEL_HERO
from mud.models.classes import CLASS_TABLE, ClassType
from mud.models.races import PcRaceType, list_playable_races
from mud.wiznet import WiznetFlag, wiznet

BASE_XP_PER_LEVEL = 1000

# Multipliers roughly mirroring ROM class/race adjustments.
# Index by `ch_class` or `race` id; default to 1.0 if not found.
CLASS_XP_MOD = {
    0: 1.0,  # mage
    1: 1.0,  # cleric
    2: 1.1,  # thief
    3: 1.2,  # warrior
}

RACE_XP_MOD = {
    0: 1.0,  # human
    1: 1.1,  # elf
    2: 0.9,  # dwarf
}

# Per-class stat gains applied on level-up: (hp, mana, move)
LEVEL_BONUS = {
    0: (8, 6, 4),  # mage
    1: (6, 8, 4),  # cleric
    2: (7, 6, 5),  # thief
    3: (10, 4, 6),  # warrior
}

PRACTICES_PER_LEVEL = 2
TRAINS_PER_LEVEL = 1

ROM_NEWLINE = "\n\r"


def exp_per_level(char: Character) -> int:
    """ROM experience threshold for the next level."""

    if getattr(char, "is_npc", False):
        return BASE_XP_PER_LEVEL

    return _creation_exp_floor(char, BASE_XP_PER_LEVEL)


def exp_per_level_for_creation(
    race: PcRaceType, class_type: ClassType, creation_points: int
) -> int:
    """ROM-style experience curve based on creation points."""

    points = max(0, int(creation_points))
    class_index = 0
    for idx, entry in enumerate(CLASS_TABLE):
        if entry.name == class_type.name:
            class_index = idx
            break

    multiplier = 100
    if 0 <= class_index < len(race.class_multipliers):
        candidate = int(race.class_multipliers[class_index])
        multiplier = candidate if candidate > 0 else 100

    if points < 40:
        scaled = c_div(multiplier, 100)
        return BASE_XP_PER_LEVEL * (scaled if scaled > 0 else 1)

    points -= 40
    expl = 1000
    inc = 500
    while points > 9:
        expl += inc
        points -= 10
        if points > 9:
            expl += inc
            inc *= 2
            points -= 10

    expl += c_div(points * inc, 10)
    return c_div(expl * multiplier, 100)


def advance_level(char: Character) -> None:
    """Increase hit points, mana, move, practices, and trains."""
    hp, mana, move = LEVEL_BONUS.get(char.ch_class, (8, 6, 5))
    char.max_hit += hp
    char.max_mana += mana
    char.max_move += move
    char.practice += PRACTICES_PER_LEVEL
    char.train += TRAINS_PER_LEVEL

    pcdata = getattr(char, "pcdata", None)
    if pcdata is not None:
        try:
            played = int(getattr(char, "played", 0) or 0)
        except (TypeError, ValueError):  # pragma: no cover - defensive guard
            played = 0
        try:
            logon = int(getattr(char, "logon", 0) or 0)
        except (TypeError, ValueError):  # pragma: no cover - defensive guard
            logon = 0
        now = int(time.time())
        session_played = 0
        if logon:
            session_played = max(0, now - logon)
        pcdata.last_level = (played + session_played) // 3600
        pcdata.perm_hit = int(getattr(pcdata, "perm_hit", 0) or 0) + hp
        pcdata.perm_mana = int(getattr(pcdata, "perm_mana", 0) or 0) + mana
        pcdata.perm_move = int(getattr(pcdata, "perm_move", 0) or 0) + move

    if hasattr(char, "send_to_char") and not getattr(char, "is_npc", False):
        hit_suffix = "" if hp == 1 else "s"
        practice_suffix = "" if PRACTICES_PER_LEVEL == 1 else "s"
        message = (
            "You gain "
            f"{hp} hit point{hit_suffix}, {mana} mana, {move} move, and "
            f"{PRACTICES_PER_LEVEL} practice{practice_suffix}.{ROM_NEWLINE}"
        )
        char.send_to_char(message)


def _creation_exp_floor(char: Character, fallback: int) -> int:
    """Return the ROM creation-point XP floor for ``char``."""

    try:
        race_index = int(getattr(char, "race", 0) or 0)
    except (TypeError, ValueError):  # pragma: no cover - defensive guard
        race_index = 0
    playable_races = list_playable_races()
    race_meta: PcRaceType | None
    if 0 <= race_index < len(playable_races):
        race_meta = playable_races[race_index]
    else:
        race_meta = None

    try:
        class_index = int(getattr(char, "ch_class", 0) or 0)
    except (TypeError, ValueError):  # pragma: no cover - defensive guard
        class_index = 0
    class_meta: ClassType | None
    if 0 <= class_index < len(CLASS_TABLE):
        class_meta = CLASS_TABLE[class_index]
    else:
        class_meta = None

    creation_points = getattr(char, "creation_points", None)
    if creation_points in (None, ""):
        pcdata = getattr(char, "pcdata", None)
        if pcdata is not None:
            creation_points = getattr(pcdata, "points", None)

    try:
        points_value = int(creation_points) if creation_points is not None else None
    except (TypeError, ValueError):  # pragma: no cover - defensive guard
        points_value = None

    if race_meta is None or class_meta is None or points_value is None:
        return fallback

    return exp_per_level_for_creation(race_meta, class_meta, points_value)


def gain_exp(char: Character, amount: int) -> None:
    """Grant (or deduct) experience and handle ROM-style leveling."""

    if getattr(char, "is_npc", False):
        return

    if char.level >= LEVEL_HERO:
        return

    base = exp_per_level(char)
    floor = base
    current_exp = int(getattr(char, "exp", 0) or 0)
    new_total = current_exp + int(amount)

    char.exp = max(floor, new_total)

    if amount <= 0:
        return

    # Level up while total exp meets threshold for next level.
    while char.level < LEVEL_HERO and char.exp >= exp_per_level(char) * (char.level + 1):
        char.level += 1
        advance_level(char)
        if hasattr(char, "send_to_char"):
            char.send_to_char("{GYou raise a level!!  {x")
        wiznet(
            f"$N has attained level {char.level}!",
            char,
            None,
            WiznetFlag.WIZ_LEVELS,
            None,
            0,
        )
        # Lazy import to avoid circular dependency
        from mud.account.account_manager import save_character
        save_character(char)
