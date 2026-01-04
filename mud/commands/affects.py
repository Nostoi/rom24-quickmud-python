"""
Affects command - show active spell/affect effects on character.

ROM Reference: src/act_info.c do_affects (lines 2300-2400)
"""

from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import AffectFlag


# Mapping of affect flags to human-readable names
_AFFECT_NAMES = {
    AffectFlag.BLIND: "blindness",
    AffectFlag.INVISIBLE: "invisibility",
    AffectFlag.DETECT_EVIL: "detect evil",
    AffectFlag.DETECT_INVIS: "detect invisibility",
    AffectFlag.DETECT_MAGIC: "detect magic",
    AffectFlag.DETECT_HIDDEN: "detect hidden",
    AffectFlag.DETECT_GOOD: "detect good",
    AffectFlag.SANCTUARY: "sanctuary",
    AffectFlag.FAERIE_FIRE: "faerie fire",
    AffectFlag.INFRARED: "infrared vision",
    AffectFlag.CURSE: "curse",
    AffectFlag.POISON: "poison",
    AffectFlag.PROTECT_EVIL: "protection evil",
    AffectFlag.PROTECT_GOOD: "protection good",
    AffectFlag.SNEAK: "sneak",
    AffectFlag.HIDE: "hide",
    AffectFlag.SLEEP: "sleep",
    AffectFlag.CHARM: "charm",
    AffectFlag.FLYING: "fly",
    AffectFlag.PASS_DOOR: "pass door",
    AffectFlag.HASTE: "haste",
    AffectFlag.CALM: "calm",
    AffectFlag.PLAGUE: "plague",
    AffectFlag.WEAKEN: "weaken",
    AffectFlag.DARK_VISION: "dark vision",
    AffectFlag.BERSERK: "berserk",
    AffectFlag.SWIM: "swim",
    AffectFlag.REGENERATION: "regeneration",
    AffectFlag.SLOW: "slow",
}


def affect_loc_name(location: int) -> str:
    """
    Return ASCII name of an affect location.

    ROM Reference: src/handler.c affect_loc_name (lines 2718-2775)

    Args:
        location: APPLY_* constant (0-25)

    Returns:
        Human-readable location name (e.g., "strength", "armor class", "hit roll")
    """
    # ROM C APPLY_* constants (src/merc.h lines 1205-1231)
    APPLY_NAMES = {
        0: "none",  # APPLY_NONE
        1: "strength",  # APPLY_STR
        2: "dexterity",  # APPLY_DEX
        3: "intelligence",  # APPLY_INT
        4: "wisdom",  # APPLY_WIS
        5: "constitution",  # APPLY_CON
        6: "sex",  # APPLY_SEX
        7: "class",  # APPLY_CLASS
        8: "level",  # APPLY_LEVEL
        9: "age",  # APPLY_AGE
        10: "height",  # APPLY_HEIGHT (not shown in ROM affect_loc_name)
        11: "weight",  # APPLY_WEIGHT (not shown in ROM affect_loc_name)
        12: "mana",  # APPLY_MANA
        13: "hp",  # APPLY_HIT
        14: "moves",  # APPLY_MOVE
        15: "gold",  # APPLY_GOLD
        16: "experience",  # APPLY_EXP
        17: "armor class",  # APPLY_AC
        18: "hit roll",  # APPLY_HITROLL
        19: "damage roll",  # APPLY_DAMROLL
        20: "saves",  # APPLY_SAVES / APPLY_SAVING_PARA
        21: "save vs rod",  # APPLY_SAVING_ROD
        22: "save vs petrification",  # APPLY_SAVING_PETRI
        23: "save vs breath",  # APPLY_SAVING_BREATH
        24: "save vs spell",  # APPLY_SAVING_SPELL
        25: "none",  # APPLY_SPELL_AFFECT (returns "none" in ROM C)
    }

    return APPLY_NAMES.get(location, "(unknown)")


def do_affects(char: Character, args: str) -> str:
    """
    Display active affects on the character.

    ROM Reference: src/act_info.c do_affects (lines 1714-1755)

    Usage: affects

    Behavior:
    - Level <20: Shows simple format (spell name only)
    - Level 20+: Shows detailed format (modifier, location, duration)
    - Stacked affects (same spell, multiple modifiers): Indented continuation lines
    """
    # Primary ROM C behavior: iterate ch.affected list (AFFECT_DATA structures)
    affected = getattr(char, "affected", [])

    if not affected:
        return "You are not affected by any spells."

    lines = ["You are affected by the following spells:"]
    paf_last = None

    for paf in affected:
        # Deduplication: check if same spell as previous affect
        if paf_last and paf.type == paf_last.type:
            if char.level >= 20:
                # Level 20+: Show duplicate affects with indentation (22 spaces + ": ")
                buf = " " * 22 + ": "
            else:
                # Level <20: Skip duplicate spells entirely
                continue
        else:
            # New spell: show spell name (left-aligned, 15 chars)
            # TODO: Replace with proper skill_table[paf.type].name lookup when SN mapping is available
            # For now, assume paf.type is already a skill name string (temporary until spell system updated)
            spell_name = str(paf.type) if paf.type else "(unknown)"

            buf = f"Spell: {spell_name:15s}"

        # Level 20+: Show detailed modifier information
        if char.level >= 20:
            location_name = affect_loc_name(paf.location)

            # ROM C line 1737: uses raw %d (no explicit + sign)
            modifier_str = str(paf.modifier)

            if paf.duration == -1:
                duration_str = "permanently"
            else:
                duration_str = f"for {paf.duration} hours"

            # ROM C line 1736: ": modifies..." (colon prefix)
            buf += f": modifies {location_name} by {modifier_str} {duration_str}"

        lines.append(buf)
        paf_last = paf

    return "\n".join(lines)
