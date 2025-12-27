"""
Give command - give items or gold/silver to another character.

ROM Reference: src/act_obj.c do_give (lines 659-770)
"""
from __future__ import annotations

from mud.models.character import Character
from mud.world.char_find import get_char_room
from mud.world.obj_find import get_obj_carry


def do_give(char: Character, args: str) -> str:
    """
    Give an item or currency to another character.
    
    ROM Reference: src/act_obj.c do_give (lines 659-770)
    
    Usage:
    - give <item> <target> - Give an item
    - give <amount> gold <target> - Give gold
    - give <amount> silver <target> - Give silver
    - give <amount> coins <target> - Give gold
    """
    args = args.strip()
    parts = args.split()
    
    if len(parts) < 2:
        return "Give what to whom?"
    
    # Check if giving currency (first arg is a number)
    try:
        amount = int(parts[0])
        is_currency = True
    except ValueError:
        is_currency = False
        amount = 0
    
    if is_currency:
        # 'give NNNN coins/gold/silver victim'
        if amount <= 0:
            return "Sorry, you can't do that."
        
        if len(parts) < 3:
            return "Give what to whom?"
        
        currency_type = parts[1].lower()
        if currency_type not in ("coins", "coin", "gold", "silver"):
            return "Sorry, you can't do that."
        
        silver = currency_type == "silver"
        target_name = parts[2]
        
        # Find target
        victim = get_char_room(char, target_name)
        if not victim:
            return "They aren't here."
        
        # Check if char has enough
        if silver:
            char_currency = getattr(char, "silver", 0)
            currency_name = "silver"
        else:
            char_currency = getattr(char, "gold", 0)
            currency_name = "gold"
        
        if char_currency < amount:
            return "You haven't got that much."
        
        # Transfer currency
        if silver:
            char.silver = getattr(char, "silver", 0) - amount
            victim.silver = getattr(victim, "silver", 0) + amount
        else:
            char.gold = getattr(char, "gold", 0) - amount
            victim.gold = getattr(victim, "gold", 0) + amount
        
        victim_name = getattr(victim, "short_descr", None) or getattr(victim, "name", "them")
        return f"You give {victim_name} {amount} {currency_name}."
    
    # Giving an object
    obj_name = parts[0]
    target_name = parts[1]
    
    # Handle "all." prefix
    if obj_name.lower().startswith("all."):
        # Give all matching items
        obj_keyword = obj_name[4:]
        return _give_all(char, obj_keyword, target_name)
    
    # Find the object in inventory
    obj = get_obj_carry(char, obj_name)
    if not obj:
        return "You do not have that item."
    
    # Find target
    victim = get_char_room(char, target_name)
    if not victim:
        return "They aren't here."
    
    # Check if object can be given (not nodrop)
    extra_flags = getattr(obj, "extra_flags", 0)
    from mud.models.constants import ExtraFlag
    if extra_flags & ExtraFlag.NODROP:
        return "You can't let go of it."
    
    # Check victim's carrying capacity
    victim_carry_number = len(getattr(victim, "carrying", []))
    victim_max_carry = _get_max_carry(victim)
    if victim_carry_number >= victim_max_carry:
        victim_name = getattr(victim, "short_descr", None) or getattr(victim, "name", "They")
        return f"{victim_name} can't carry any more items."
    
    # Check weight
    victim_carry_weight = sum(getattr(o, "weight", 0) for o in getattr(victim, "carrying", []))
    victim_max_weight = _can_carry_weight(victim)
    obj_weight = getattr(obj, "weight", 0)
    if victim_carry_weight + obj_weight > victim_max_weight:
        victim_name = getattr(victim, "short_descr", None) or getattr(victim, "name", "They")
        return f"{victim_name} can't carry that much weight."
    
    # Transfer the object
    char_carrying = getattr(char, "carrying", [])
    if obj in char_carrying:
        char_carrying.remove(obj)
    
    victim_carrying = getattr(victim, "carrying", [])
    if not hasattr(victim, "carrying"):
        victim.carrying = []
    victim.carrying.append(obj)
    obj.carried_by = victim
    
    obj_name = getattr(obj, "short_descr", None) or getattr(obj, "name", "something")
    victim_name = getattr(victim, "short_descr", None) or getattr(victim, "name", "them")
    
    # Trigger give mobprog if NPC and has trigger
    # ROM Reference: src/act_obj.c:841-842
    victim_is_npc = getattr(victim, "is_npc", False)
    if victim_is_npc:
        from mud.mobprog import mp_give_trigger
        mp_give_trigger(victim, char, obj)
    
    return f"You give {obj_name} to {victim_name}."


def _give_all(char: Character, keyword: str, target_name: str) -> str:
    """Give all matching items to target."""
    victim = get_char_room(char, target_name)
    if not victim:
        return "They aren't here."
    
    char_carrying = getattr(char, "carrying", [])
    given_count = 0
    
    for obj in list(char_carrying):
        obj_name = getattr(obj, "name", "")
        if keyword.lower() in obj_name.lower():
            # Check nodrop
            extra_flags = getattr(obj, "extra_flags", 0)
            from mud.models.constants import ExtraFlag
            if extra_flags & ExtraFlag.NODROP:
                continue
            
            # Transfer
            char_carrying.remove(obj)
            if not hasattr(victim, "carrying"):
                victim.carrying = []
            victim.carrying.append(obj)
            obj.carried_by = victim
            given_count += 1
    
    if given_count == 0:
        return "You have nothing matching to give."
    
    victim_name = getattr(victim, "short_descr", None) or getattr(victim, "name", "them")
    return f"You give {given_count} items to {victim_name}."


def _get_max_carry(char: Character) -> int:
    """Get maximum number of items character can carry."""
    # ROM Reference: can_carry_n in handler.c
    is_npc = getattr(char, "is_npc", False)
    if is_npc:
        return 1000  # NPCs can carry many items
    
    dex = getattr(char, "perm_stat", {}).get("dex", 13)
    level = getattr(char, "level", 1)
    return max(10, dex + level // 2)


def _can_carry_weight(char: Character) -> int:
    """Get maximum weight character can carry in pounds."""
    # ROM Reference: can_carry_w in handler.c
    is_npc = getattr(char, "is_npc", False)
    if is_npc:
        return 100000  # NPCs can carry a lot
    
    str_stat = getattr(char, "perm_stat", {}).get("str", 13)
    level = getattr(char, "level", 1)
    return str_stat * 10 + level * 5
