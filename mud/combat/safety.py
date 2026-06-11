"""
Combat safety checks - determine if it's safe to attack.

ROM Reference: src/fight.c is_safe
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mud.models.character import Character


def is_safe(char: Character, victim: Character) -> bool:  # noqa: C901
    """
    Check if it's safe to attack victim (i.e., shouldn't attack).

    ROM Reference: src/fight.c is_safe (lines 130-230)

    Returns True if:
    - Victim is in a SAFE room
    - Victim is a shopkeeper
    - Victim is a healer
    - Attacker is too much lower level (for NPCs attacking players)
    """
    from mud.models.constants import ActFlag, AffectFlag, RoomFlag

    if char is None or victim is None:
        return True

    # Ghost can't fight
    if getattr(char, "is_ghost", False):
        return True

    # Can't fight yourself
    if char is victim:
        return True

    # Check for safe room
    room = getattr(victim, "room", None)
    if room:
        room_flags = getattr(room, "room_flags", 0)
        if room_flags & RoomFlag.ROOM_SAFE:
            return True

    # Check if victim is a shopkeeper or healer
    victim_act = getattr(victim, "act", 0)
    if getattr(victim, "is_npc", False):
        # Check for special mob types that shouldn't be attacked
        if victim_act & ActFlag.IS_HEALER:
            return True
        if victim_act & ActFlag.IS_CHANGER:
            return True
        if victim_act & ActFlag.TRAIN:
            return True
        if victim_act & ActFlag.PRACTICE:
            return True
        if victim_act & ActFlag.GAIN:
            return True

        # PC-attacker-only guards — mirroring ROM src/fight.c:1056-1071
        if not getattr(char, "is_npc", False):
            # no attacking pets — mirroring ROM src/fight.c:1059
            if victim_act & ActFlag.PET:
                return True
            # no attacking charmed creatures unless owner — mirroring ROM src/fight.c:1067
            victim_affected = getattr(victim, "affected_by", 0)
            if victim_affected & AffectFlag.CHARM:
                if getattr(victim, "master", None) is not char:
                    return True

    # Check shop - if mob has a shop, it's a shopkeeper.
    # mirroring ROM src/fight.c:1040 — victim->pIndexData->pShop != NULL.
    # Python MobInstances carry no pShop directly; the field lives on the
    # MobIndex prototype.  Check both to handle any edge case where pShop
    # was set directly on the instance.
    if getattr(victim, "pShop", None) is not None:
        return True
    proto = getattr(victim, "prototype", None) or getattr(victim, "pIndexData", None)
    if proto is not None and getattr(proto, "pShop", None) is not None:
        return True

    # NPC attacking player — mirroring ROM src/fight.c:1080-1093
    if getattr(char, "is_npc", False) and not getattr(victim, "is_npc", True):
        # charmed mobs and pets cannot attack players while master is not fighting them
        # mirroring ROM src/fight.c:1087-1093
        char_affected = getattr(char, "affected_by", 0)
        if char_affected & AffectFlag.CHARM:
            master = getattr(char, "master", None)
            if master is not None and getattr(master, "fighting", None) is not victim:
                return True

        char_level = getattr(char, "level", 1)
        victim_level = getattr(victim, "level", 1)
        if victim_level < char_level - 10:
            return True

    return False


def is_safe_spell(char: Character, victim: Character, area: bool = False) -> bool:
    """
    Check if it's safe to cast an offensive spell on victim.

    ROM Reference: src/fight.c is_safe_spell
    """
    # Can't spell yourself offensively in most cases
    if char is victim and not area:
        return True

    # Use same logic as regular combat safety
    return is_safe(char, victim)
