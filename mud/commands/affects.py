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


def do_affects(char: Character, args: str) -> str:
    """
    Display active affects on the character.
    
    ROM Reference: src/act_info.c do_affects (lines 2300-2400)
    
    Usage: affects
    """
    lines = []
    
    # Check spell_effects (detailed spell effects with duration)
    spell_effects = getattr(char, "spell_effects", {})
    if spell_effects:
        lines.append("You are affected by the following spells:")
        for spell_name, effect in spell_effects.items():
            duration = getattr(effect, "duration", -1)
            if duration < 0:
                lines.append(f"  {spell_name}: permanent")
            else:
                lines.append(f"  {spell_name}: {duration} hours remaining")
    
    # Check affect bitvector for built-in affects
    affected_by = getattr(char, "affected_by", 0)
    if affected_by:
        if not spell_effects:
            lines.append("You are affected by:")
        else:
            lines.append("\nYou also have these affects:")
        
        for flag, name in _AFFECT_NAMES.items():
            if affected_by & flag:
                # Check if this isn't already shown in spell_effects
                if name not in spell_effects:
                    lines.append(f"  {name}")
    
    # Check for special conditions
    if getattr(char, "position", 0) == 0:  # DEAD
        lines.append("You are DEAD.")
    
    # Check for hunger/thirst (if applicable)
    pcdata = getattr(char, "pcdata", None)
    if pcdata:
        hunger = getattr(pcdata, "condition", [0, 0, 0, 0])
        if len(hunger) >= 2:
            if hunger[0] == 0:  # COND_FULL
                lines.append("You are hungry.")
            if hunger[1] == 0:  # COND_THIRST
                lines.append("You are thirsty.")
    
    if not lines:
        return "You are not affected by any spells."
    
    return "\n".join(lines)
