"""
Combat safety checks - determine if it's safe to attack.

ROM Reference: src/fight.c is_safe
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mud.models.character import Character


def is_safe(char: "Character", victim: "Character") -> bool:
    """
    Check if it's safe to attack victim (i.e., shouldn't attack).
    
    ROM Reference: src/fight.c is_safe (lines 130-230)
    
    Returns True if:
    - Victim is in a SAFE room
    - Victim is a shopkeeper
    - Victim is a healer
    - Attacker is too much lower level (for NPCs attacking players)
    """
    from mud.models.constants import RoomFlag, ActFlag
    
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
    
    # Check shop - if mob has a shop, it's a shopkeeper
    if hasattr(victim, "pShop") and getattr(victim, "pShop", None):
        return True
    
    # NPC attacking much lower level player
    if getattr(char, "is_npc", False) and not getattr(victim, "is_npc", True):
        char_level = getattr(char, "level", 1)
        victim_level = getattr(victim, "level", 1)
        if victim_level < char_level - 10:
            return True
    
    return False


def is_safe_spell(char: "Character", victim: "Character", area: bool = False) -> bool:
    """
    Check if it's safe to cast an offensive spell on victim.
    
    ROM Reference: src/fight.c is_safe_spell
    """
    # Can't spell yourself offensively in most cases
    if char is victim and not area:
        return True
    
    # Use same logic as regular combat safety
    return is_safe(char, victim)


def check_killer(char: "Character", victim: "Character") -> None:
    """
    Mark character as a killer if they attack an innocent.
    
    ROM Reference: src/fight.c check_killer
    """
    from mud.models.constants import PlayerFlag
    
    # Only applies to players
    if getattr(char, "is_npc", True):
        return
    
    # NPCs don't make you a killer
    if getattr(victim, "is_npc", True):
        return
    
    # Set KILLER flag
    char.act = getattr(char, "act", 0) | PlayerFlag.KILLER
