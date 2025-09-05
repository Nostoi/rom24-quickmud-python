from __future__ import annotations

from mud.models.character import Character

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

def exp_per_level(char: Character) -> int:
    """Base experience required for a single level."""
    class_mod = CLASS_XP_MOD.get(char.ch_class, 1.0)
    race_mod = RACE_XP_MOD.get(char.race, 1.0)
    return int(BASE_XP_PER_LEVEL * class_mod * race_mod)


def advance_level(char: Character) -> None:
    """Increase hit points, mana, move, practices, and trains."""
    hp, mana, move = LEVEL_BONUS.get(char.ch_class, (8, 6, 5))
    char.max_hit += hp
    char.max_mana += mana
    char.max_move += move
    char.practice += PRACTICES_PER_LEVEL
    char.train += TRAINS_PER_LEVEL

def gain_exp(char: Character, amount: int) -> None:
    """Grant experience and handle level ups.

    Experience required to reach *n* is ``exp_per_level(char) * n``.
    The character's ``exp`` tracks total lifetime experience.
    """
    if amount <= 0:
        return
    char.exp += amount
    # Level up while total exp meets threshold for next level.
    while char.exp >= exp_per_level(char) * (char.level + 1):
        char.level += 1
        advance_level(char)

