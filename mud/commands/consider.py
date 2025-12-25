"""
Consider command - assess mob difficulty relative to player level.

ROM Reference: src/act_info.c do_consider (lines 2469-2510)
"""
from __future__ import annotations

from mud.models.character import Character
from mud.world.char_find import get_char_room
from mud.combat.safety import is_safe


def do_consider(char: Character, args: str) -> str:
    """
    Assess the difficulty of fighting a mob.
    
    ROM Reference: src/act_info.c lines 2469-2510
    
    Usage: consider <target>
    
    Shows relative difficulty based on level difference:
    - 10+ levels below: "You can kill $N naked and weaponless."
    - 5-9 levels below: "$N is no match for you."
    - 2-4 levels below: "$N looks like an easy kill."
    - -1 to +1 levels: "The perfect match!"
    - 2-4 levels above: "$N says 'Do you feel lucky, punk?'."
    - 5-9 levels above: "$N laughs at you mercilessly."
    - 10+ levels above: "Death will thank you for your gift."
    """
    args = args.strip()
    
    if not args:
        return "Consider killing whom?"
    
    # Find target in room
    victim = get_char_room(char, args)
    if not victim:
        return "They're not here."
    
    # Check if safe to attack
    if is_safe(char, victim):
        return "Don't even think about it."
    
    # Calculate level difference - ROM src/act_info.c line 2492
    char_level = getattr(char, "level", 1)
    victim_level = getattr(victim, "level", 1)
    diff = victim_level - char_level
    
    # Get victim's name for message
    victim_name = getattr(victim, "short_descr", None) or getattr(victim, "name", "someone")
    
    # ROM exact messages based on level difference - src/act_info.c lines 2494-2507
    if diff <= -10:
        msg = f"You can kill {victim_name} naked and weaponless."
    elif diff <= -5:
        msg = f"{victim_name} is no match for you."
    elif diff <= -2:
        msg = f"{victim_name} looks like an easy kill."
    elif diff <= 1:
        msg = "The perfect match!"
    elif diff <= 4:
        msg = f"{victim_name} says 'Do you feel lucky, punk?'."
    elif diff <= 9:
        msg = f"{victim_name} laughs at you mercilessly."
    else:
        msg = "Death will thank you for your gift."
    
    return msg
