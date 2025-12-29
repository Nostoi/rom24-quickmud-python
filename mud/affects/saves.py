from __future__ import annotations

from mud.math.c_compat import c_div, urange
from mud.models.character import Character
from mud.models.constants import AffectFlag, DamageType, DefenseBit
from mud.utils import rng_mm


ROM_NEWLINE = "\n\r"

# Minimal fMana mapping from ROM const.c order: mage, cleric → True; thief, warrior → False
FMANA_BY_CLASS = {
    0: True,  # mage
    1: True,  # cleric
    2: False,  # thief
    3: False,  # warrior
}


def _check_immune(victim: Character, dam_type: int) -> int:
    """ROM-compatible check_immune.

    Returns one of: IS_NORMAL=0, IS_IMMUNE=1, IS_RESISTANT=2, IS_VULNERABLE=3.
    Mirrors src/handler.c:check_immune with globals (WEAPON/MAGIC) and per-type bits.
    """
    IS_NORMAL = 0
    IS_IMMUNE = 1
    IS_RESISTANT = 2
    IS_VULNERABLE = 3

    try:
        dam_value = int(dam_type)
    except (TypeError, ValueError):
        dam_value = int(DamageType.NONE)

    if dam_value == int(DamageType.NONE):
        return -1

    # Default from global WEAPON/MAGIC flags
    if dam_value <= int(DamageType.SLASH):
        if victim.imm_flags & DefenseBit.WEAPON:
            default = IS_IMMUNE
        elif victim.res_flags & DefenseBit.WEAPON:
            default = IS_RESISTANT
        elif victim.vuln_flags & DefenseBit.WEAPON:
            default = IS_VULNERABLE
        else:
            default = IS_NORMAL
    else:
        if victim.imm_flags & DefenseBit.MAGIC:
            default = IS_IMMUNE
        elif victim.res_flags & DefenseBit.MAGIC:
            default = IS_RESISTANT
        elif victim.vuln_flags & DefenseBit.MAGIC:
            default = IS_VULNERABLE
        else:
            default = IS_NORMAL

    # Map dam_type to specific IMM_* bit
    bit = None
    try:
        dt = DamageType(dam_value)
    except ValueError:
        return default
    mapping = {
        DamageType.BASH: DefenseBit.BASH,
        DamageType.PIERCE: DefenseBit.PIERCE,
        DamageType.SLASH: DefenseBit.SLASH,
        DamageType.FIRE: DefenseBit.FIRE,
        DamageType.COLD: DefenseBit.COLD,
        DamageType.LIGHTNING: DefenseBit.LIGHTNING,
        DamageType.ACID: DefenseBit.ACID,
        DamageType.POISON: DefenseBit.POISON,
        DamageType.NEGATIVE: DefenseBit.NEGATIVE,
        DamageType.HOLY: DefenseBit.HOLY,
        DamageType.ENERGY: DefenseBit.ENERGY,
        DamageType.MENTAL: DefenseBit.MENTAL,
        DamageType.DISEASE: DefenseBit.DISEASE,
        DamageType.DROWNING: DefenseBit.DROWNING,
        DamageType.LIGHT: DefenseBit.LIGHT,
        DamageType.CHARM: DefenseBit.CHARM,
        DamageType.SOUND: DefenseBit.SOUND,
    }
    bit = mapping.get(dt)
    if bit is None:
        return default

    immune = -1
    if victim.imm_flags & bit:
        immune = IS_IMMUNE
    elif (victim.res_flags & bit) and immune != IS_IMMUNE:
        immune = IS_RESISTANT

    # ROM C handler.c:306-314 - vuln check runs AFTER imm/res checks
    # This is NOT elif - it runs independently to allow downgrading immunity
    if victim.vuln_flags & bit:
        if immune == IS_IMMUNE:
            immune = IS_RESISTANT
        elif immune == IS_RESISTANT:
            immune = IS_NORMAL
        else:
            immune = IS_VULNERABLE

    return default if immune == -1 else immune


def saves_spell(level: int, victim: Character, dam_type: int) -> bool:
    """Compute ROM-like saving throw outcome.

    Mirrors src/magic.c:saves_spell() logic:
    - base: 50 + (victim.level - level) * 5 - victim.saving_throw * 2
    - berserk: + victim.level/2 (C integer division)
    - immunity/resistance/vulnerability adjustments via ``check_immune`` fallback
    - player classes with fMana: save = 9*save/10 (C division)
    - clamp 5..95, succeed if number_percent() < save
    """
    save = 50 + (victim.level - level) * 5 - victim.saving_throw * 2

    if victim.has_affect(AffectFlag.BERSERK):
        save += c_div(victim.level, 2)

    riv = _check_immune(victim, dam_type)
    # IS_IMMUNE(1) → auto success; IS_RESISTANT(2) → +2; IS_VULNERABLE(3) → -2
    if riv == 1:
        return True
    if riv == 2:
        save += 2
    elif riv == 3:
        save -= 2

    # Not NPC → apply fMana reduction if class gains mana
    if not victim.is_npc and FMANA_BY_CLASS.get(victim.ch_class, False):
        save = c_div(9 * save, 10)

    save = urange(5, save, 95)
    return rng_mm.number_percent() < save


def saves_dispel(dis_level: int, spell_level: int, duration: int) -> bool:
    """ROM saves_dispel helper (src/magic.c:243-252)."""

    if duration == -1:
        spell_level += 5

    save = 50 + (spell_level - dis_level) * 5
    save = urange(5, save, 95)
    return rng_mm.number_percent() < save


def check_dispel(dis_level: int, victim: Character, effect_name: str) -> bool:
    """Attempt to dispel an active spell effect by name."""

    effect = victim.spell_effects.get(effect_name)
    if effect is None:
        return False

    if not saves_dispel(dis_level, effect.level, effect.duration):
        removed = victim.remove_spell_effect(effect_name)
        if removed and removed.wear_off_message:
            victim.send_to_char(f"{removed.wear_off_message}{ROM_NEWLINE}")
        return True

    effect.level -= 1
    return False
