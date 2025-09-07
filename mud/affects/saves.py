from __future__ import annotations

from mud.math.c_compat import c_div, urange
from mud.models.character import Character
from mud.models.constants import AffectFlag
from mud.utils import rng_mm


# Minimal fMana mapping from ROM const.c order: mage, cleric → True; thief, warrior → False
FMANA_BY_CLASS = {
    0: True,  # mage
    1: True,  # cleric
    2: False,  # thief
    3: False,  # warrior
}


def _check_immune(_victim: Character, _dam_type: int) -> int:
    """Placeholder for ROM check_immune: return 0 (normal) for now.

    Values would map to IS_IMMUNE=3, IS_RESISTANT=1, IS_VULNERABLE=2 in ROM.
    """
    return 0


def saves_spell(level: int, victim: Character, dam_type: int) -> bool:
    """Compute ROM-like saving throw outcome.

    Mirrors src/magic.c:saves_spell() logic:
    - base: 50 + (victim.level - level) * 5 - victim.saving_throw * 2
    - berserk: + victim.level/2 (C integer division)
    - immunity/resistance/vulnerability adjustments (stubbed to normal for now)
    - player classes with fMana: save = 9*save/10 (C division)
    - clamp 5..95, succeed if number_percent() < save
    """
    save = 50 + (victim.level - level) * 5 - victim.saving_throw * 2

    if victim.has_affect(AffectFlag.BERSERK):
        save += c_div(victim.level, 2)

    riv = _check_immune(victim, dam_type)
    # IS_IMMUNE(3) → auto success; IS_RESISTANT(1) → +2; IS_VULNERABLE(2) → -2
    if riv == 3:
        return True
    if riv == 1:
        save += 2
    elif riv == 2:
        save -= 2

    # Not NPC → apply fMana reduction if class gains mana
    if FMANA_BY_CLASS.get(victim.ch_class, False):
        save = c_div(9 * save, 10)

    save = urange(5, save, 95)
    return rng_mm.number_percent() < save
