"""
Thief skill commands - sneak, hide, visible, steal.

ROM Reference: src/act_move.c do_sneak, do_hide, do_visible
ROM Reference: src/act_obj.c do_steal
"""
from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import AffectFlag, Position
from mud.utils.rng_mm import number_percent, number_range
from mud.world.char_find import get_char_room


def do_sneak(char: Character, args: str) -> str:
    """
    Attempt to move silently (thief skill).
    
    ROM Reference: src/act_move.c do_sneak (lines 1496-1524)
    
    Success applies AFF_SNEAK for level duration.
    """
    # Remove any existing sneak effect
    _strip_affect(char, "sneak")
    
    # Check if already sneaking from another source
    affected_by = getattr(char, "affected_by", 0)
    if affected_by & AffectFlag.SNEAK:
        return "You attempt to move silently."
    
    # Get sneak skill
    skill_level = _get_skill(char, "sneak")
    if skill_level <= 0:
        return "You don't know how to sneak."
    
    # Skill check
    roll = number_percent()
    if roll < skill_level:
        # Success - apply sneak affect
        _apply_sneak_affect(char)
        _check_improve(char, "sneak", True)
        return "You attempt to move silently."
    else:
        _check_improve(char, "sneak", False)
        return "You attempt to move silently."


def do_hide(char: Character, args: str) -> str:
    """
    Attempt to hide in shadows (thief skill).
    
    ROM Reference: src/act_move.c do_hide (lines 1526-1546)
    
    Sets AFF_HIDE directly on affected_by.
    """
    # Remove existing hide
    affected_by = getattr(char, "affected_by", 0)
    if affected_by & AffectFlag.HIDE:
        char.affected_by = affected_by & ~AffectFlag.HIDE
    
    # Get hide skill
    skill_level = _get_skill(char, "hide")
    if skill_level <= 0:
        return "You don't know how to hide."
    
    # Skill check
    roll = number_percent()
    if roll < skill_level:
        # Success - set hide flag
        char.affected_by = getattr(char, "affected_by", 0) | AffectFlag.HIDE
        _check_improve(char, "hide", True)
    else:
        _check_improve(char, "hide", False)
    
    return "You attempt to hide."


def do_visible(char: Character, args: str) -> str:
    """
    Remove invisibility, sneak, and hide effects.
    
    ROM Reference: src/act_move.c do_visible (lines 1549-1560)
    """
    # Strip spell-based invisibility
    _strip_affect(char, "invisibility")
    _strip_affect(char, "mass invisibility")
    _strip_affect(char, "sneak")
    
    # Remove affect flags
    affected_by = getattr(char, "affected_by", 0)
    affected_by &= ~AffectFlag.HIDE
    affected_by &= ~AffectFlag.INVISIBLE
    affected_by &= ~AffectFlag.SNEAK
    char.affected_by = affected_by
    
    return "Ok."


def do_steal(char: Character, args: str) -> str:
    """
    Attempt to steal items or coins from a target.
    
    ROM Reference: src/act_obj.c do_steal (lines 2161-2310)
    
    Usage:
    - steal <item> <target>
    - steal coins <target>
    - steal gold <target>
    """
    parts = (args or "").strip().split(None, 1)
    
    if len(parts) < 2:
        return "Steal what from whom?"
    
    item_name = parts[0].lower()
    target_name = parts[1]
    
    # Find victim
    room = getattr(char, "room", None)
    if not room:
        return "You are nowhere."
    
    victim = get_char_room(char, target_name)
    if victim is None:
        return "They aren't here."
    
    if victim is char:
        return "That's pointless."
    
    # Safety check
    from mud.combat.safety import is_safe
    if is_safe(char, victim):
        return "You can't steal from them here."
    
    # Can't steal from fighting NPCs
    victim_is_npc = getattr(victim, "is_npc", False)
    victim_position = getattr(victim, "position", Position.STANDING)
    if victim_is_npc and victim_position == Position.FIGHTING:
        return "Kill stealing is not permitted.\nYou'd better not -- you might get hit."
    
    # Apply wait state
    skill_registry._apply_wait_state(char, 24)  # skill_table[gsn_steal].beats
    
    # Calculate success chance
    skill_level = _get_skill(char, "steal")
    if skill_level <= 0:
        return "You don't know how to steal."
    
    percent = number_percent()
    
    # Modifiers
    victim_awake = victim_position > Position.SLEEPING
    if not victim_awake:
        percent -= 10
    elif not _can_see(victim, char):
        percent += 25
    else:
        percent += 50
    
    # Level difference check for PvP
    char_is_npc = getattr(char, "is_npc", False)
    char_level = getattr(char, "level", 1)
    victim_level = getattr(victim, "level", 1)
    
    level_diff_too_big = (char_level + 7 < victim_level or char_level - 7 > victim_level)
    
    # Failure conditions
    if (not char_is_npc and not victim_is_npc and level_diff_too_big) or \
       (not char_is_npc and percent > skill_level):
        return _steal_failure(char, victim)
    
    # Success - determine what to steal
    if item_name in ("coin", "coins", "gold", "silver"):
        return _steal_coins(char, victim)
    else:
        return _steal_item(char, victim, item_name)


def _steal_failure(char: Character, victim: Character) -> str:
    """Handle failed steal attempt."""
    # Strip sneak
    _strip_affect(char, "sneak")
    char.affected_by = getattr(char, "affected_by", 0) & ~AffectFlag.SNEAK
    
    _check_improve(char, "steal", False)
    
    # Victim reacts
    victim_is_npc = getattr(victim, "is_npc", False)
    char_is_npc = getattr(char, "is_npc", False)
    
    if victim_is_npc and not char_is_npc:
        # NPC attacks
        from mud.combat import multi_hit
        multi_hit(victim, char, -1)
    
    return "Oops."


def _steal_coins(char: Character, victim: Character) -> str:
    """Steal gold/silver from victim."""
    char_level = getattr(char, "level", 1)
    max_level = 51
    
    victim_gold = getattr(victim, "gold", 0)
    victim_silver = getattr(victim, "silver", 0)
    
    gold_stolen = (victim_gold * number_range(1, char_level)) // max_level
    silver_stolen = (victim_silver * number_range(1, char_level)) // max_level
    
    if gold_stolen <= 0 and silver_stolen <= 0:
        return "You couldn't get any coins."
    
    # Transfer coins
    char.gold = getattr(char, "gold", 0) + gold_stolen
    char.silver = getattr(char, "silver", 0) + silver_stolen
    victim.gold = victim_gold - gold_stolen
    victim.silver = victim_silver - silver_stolen
    
    _check_improve(char, "steal", True)
    
    if silver_stolen <= 0:
        return f"Bingo! You got {gold_stolen} gold coins."
    elif gold_stolen <= 0:
        return f"Bingo! You got {silver_stolen} silver coins."
    else:
        return f"Bingo! You got {gold_stolen} gold and {silver_stolen} silver coins."


def _steal_item(char: Character, victim: Character, item_name: str) -> str:
    """Steal an item from victim's inventory."""
    from mud.world.obj_find import get_obj_carry
    
    obj = get_obj_carry(victim, item_name)
    if obj is None:
        return "You can't find it."
    
    # Check if item can be stolen
    if getattr(obj, "wear_loc", -1) != -1:  # WEAR_NONE
        return "You can't steal equipped items."
    
    # Check weight
    obj_weight = getattr(obj, "weight", 0)
    if not hasattr(obj, "weight"):
        proto = getattr(obj, "prototype", None)
        if proto:
            obj_weight = getattr(proto, "weight", 0)
    
    char_carry_weight = getattr(char, "carry_weight", 0)
    max_carry = _get_max_carry_weight(char)
    
    if char_carry_weight + obj_weight > max_carry:
        return "You can't carry that much weight."
    
    # Check inventory count
    char_carry_number = getattr(char, "carry_number", 0)
    max_items = _get_max_carry_number(char)
    
    if char_carry_number + 1 > max_items:
        return "You have your hands full."
    
    # Transfer the item
    victim_carrying = getattr(victim, "carrying", [])
    if obj in victim_carrying:
        victim_carrying.remove(obj)
    
    char_carrying = getattr(char, "carrying", [])
    if not hasattr(char, "carrying"):
        char.carrying = []
        char_carrying = char.carrying
    char_carrying.append(obj)
    
    obj.carried_by = char
    
    _check_improve(char, "steal", True)
    
    obj_name = getattr(obj, "short_descr", None) or getattr(obj, "name", "something")
    return f"You pocket {obj_name}."


# Helper functions

def _get_skill(char: Character, skill_name: str) -> int:
    """Get character's skill level."""
    pcdata = getattr(char, "pcdata", None)
    if pcdata:
        learned = getattr(pcdata, "learned", {})
        return learned.get(skill_name, 0)
    return 0


def _strip_affect(char: Character, affect_name: str) -> None:
    """Remove an affect by name."""
    affects = getattr(char, "affected", [])
    char.affected = [a for a in affects if getattr(a, "type", "") != affect_name]


def _apply_sneak_affect(char: Character) -> None:
    """Apply sneak affect to character."""
    from mud.models.affect import Affect
    
    level = getattr(char, "level", 1)
    
    affect = Affect(
        type="sneak",
        level=level,
        duration=level,
        location=0,  # APPLY_NONE
        modifier=0,
        bitvector=AffectFlag.SNEAK,
    )
    
    affects = getattr(char, "affected", [])
    if not hasattr(char, "affected"):
        char.affected = []
    char.affected.append(affect)
    
    char.affected_by = getattr(char, "affected_by", 0) | AffectFlag.SNEAK


def _check_improve(char: Character, skill_name: str, success: bool) -> None:
    """Check for skill improvement."""
    # Simplified - just log improvement opportunity
    pass


def _can_see(char: Character, target: Character) -> bool:
    """Check if char can see target."""
    target_affected = getattr(target, "affected_by", 0)
    if target_affected & (AffectFlag.INVISIBLE | AffectFlag.SNEAK | AffectFlag.HIDE):
        char_affected = getattr(char, "affected_by", 0)
        if not (char_affected & AffectFlag.DETECT_INVIS):
            return False
    return True


def _get_max_carry_weight(char: Character) -> int:
    """Get max carry weight for character."""
    str_stat = 18
    if hasattr(char, "get_curr_stat"):
        from mud.models.constants import Stat
        str_stat = char.get_curr_stat(Stat.STR) or 18
    return str_stat * 10 + 100


def _get_max_carry_number(char: Character) -> int:
    """Get max number of items character can carry."""
    dex_stat = 18
    if hasattr(char, "get_curr_stat"):
        from mud.models.constants import Stat
        dex_stat = char.get_curr_stat(Stat.DEX) or 18
    return dex_stat + 10
