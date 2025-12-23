"""
Murder command - attack peacefuls with lawful consequences.

ROM Reference: src/fight.c do_murder (lines 2831-2895)

Differences from kill:
- Triggers yell for help from victim
- Always checked by check_killer() for KILLER flag
- Logged as LOG_ALWAYS
"""
from __future__ import annotations

from mud.characters import is_same_group
from mud.combat import multi_hit
from mud.combat.engine import check_killer
from mud.config import get_pulse_violence
from mud.models.character import Character
from mud.models.constants import (
    ActFlag,
    AffectFlag,
    Position,
    RoomFlag,
)
from mud.skills import skill_registry
from mud.world.char_find import get_char_room


def do_murder(char: Character, args: str) -> str:
    """
    Murder a character - attack with lawful consequences.
    
    ROM Reference: src/fight.c do_murder (lines 2831-2895)
    
    Unlike kill, murder:
    - Works on peaceful NPCs (but triggers consequences)
    - Victim yells for help
    - Always sets KILLER flag via check_killer()
    
    Usage: murder <target>
    """
    target_name = (args or "").strip()
    
    if not target_name:
        return "Murder whom?"
    
    # Charmed/Pet characters can't murder
    affected_by = getattr(char, "affected_by", 0)
    if affected_by & AffectFlag.CHARM:
        return ""  # Silently fails for charmed chars
    
    is_npc = getattr(char, "is_npc", False)
    act_flags = getattr(char, "act", 0)
    if is_npc and act_flags & ActFlag.PET:
        return ""  # Pets can't murder
    
    # Find victim in room
    room = getattr(char, "room", None)
    if not room:
        return "You are nowhere."
    
    victim = get_char_room(char, target_name)
    if victim is None:
        return "They aren't here."
    
    if victim is char:
        return "Suicide is a mortal sin."
    
    # Safety checks
    safety_result = _murder_safety_check(char, victim)
    if safety_result:
        return safety_result
    
    # Can't murder if already fighting
    if getattr(char, "position", Position.STANDING) == Position.FIGHTING:
        return "You do the best you can!"
    
    # Apply wait state
    skill_registry._apply_wait_state(char, get_pulse_violence())
    
    # Victim yells for help (ROM behavior)
    victim_name = getattr(victim, "short_descr", None) or getattr(victim, "name", "someone")
    attacker_name = getattr(char, "short_descr", None) or getattr(char, "name", "someone")
    yell_msg = f"Help! I am being attacked by {attacker_name}!"
    
    # Check killer (this sets KILLER flag if attacking peaceful)
    check_killer(char, victim)
    
    # Start combat
    multi_hit(char, victim, -1)  # TYPE_UNDEFINED = -1
    
    return f"You attack {victim_name}!\n{yell_msg}"


def _murder_safety_check(char: Character, victim: Character) -> str | None:
    """
    Check if it's safe to murder the victim.
    
    ROM Reference: is_safe() in fight.c, but murder bypasses some checks
    """
    room = getattr(victim, "room", None)
    if not room:
        return "They aren't here."
    
    # Safe room check
    room_flags = getattr(room, "room_flags", 0)
    if room_flags & RoomFlag.ROOM_SAFE:
        return "Not in this room."
    
    # Kill stealing check
    victim_is_npc = getattr(victim, "is_npc", False)
    victim_fighting = getattr(victim, "fighting", None)
    if victim_is_npc and victim_fighting is not None:
        if not is_same_group(char, victim_fighting):
            return "Kill stealing is not permitted."
    
    # Can't murder your master
    affected_by = getattr(char, "affected_by", 0)
    master = getattr(char, "master", None)
    if affected_by & AffectFlag.CHARM and master is victim:
        return f"{getattr(victim, 'name', 'They')} is your beloved master."
    
    return None
