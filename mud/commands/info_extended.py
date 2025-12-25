"""
Information commands - examine, read, count, whois, worth, sit.

ROM Reference: src/act_info.c do_examine, do_read, do_count, do_whois, do_worth
ROM Reference: src/act_move.c do_sit
"""
from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import Position, ItemType


def do_examine(char: Character, args: str) -> str:
    """
    Examine an object - look + show contents.
    
    ROM Reference: src/act_info.c do_examine (lines 1320-1385)
    
    Does a look, then shows additional info for containers, money, etc.
    """
    if not args or not args.strip():
        return "Examine what?"
    
    target = args.strip().split()[0]
    
    # First, do a look
    from mud.commands.inspection import do_look
    result = do_look(char, target)
    
    # Find the object to show additional info
    from mud.world.obj_find import get_obj_here
    obj = get_obj_here(char, target)
    
    if obj is None:
        return result
    
    # Get item type
    item_type = getattr(obj, "item_type", None)
    if item_type is None:
        proto = getattr(obj, "prototype", None)
        if proto:
            item_type = getattr(proto, "item_type", None)
    
    # Additional info based on item type
    extra_info = ""
    
    if item_type == ItemType.MONEY or str(item_type) == "money":
        # Show coin count
        value = getattr(obj, "value", [0, 0, 0, 0, 0])
        silver = value[0] if len(value) > 0 else 0
        gold = value[1] if len(value) > 1 else 0
        
        if silver == 0 and gold == 0:
            extra_info = "\nOdd...there's no coins in the pile."
        elif silver == 0:
            if gold == 1:
                extra_info = "\nWow. One gold coin."
            else:
                extra_info = f"\nThere are {gold} gold coins in the pile."
        elif gold == 0:
            if silver == 1:
                extra_info = "\nWow. One silver coin."
            else:
                extra_info = f"\nThere are {silver} silver coins in the pile."
        else:
            extra_info = f"\nThere are {gold} gold and {silver} silver coins in the pile."
    
    elif item_type in (ItemType.CONTAINER, ItemType.CORPSE_NPC, ItemType.CORPSE_PC,
                       "container", "corpse_npc", "corpse_pc"):
        # Show contents
        from mud.commands.inspection import do_look
        extra_info = "\n" + do_look(char, f"in {target}")
    
    elif item_type == ItemType.DRINK_CON or str(item_type) == "drink_con":
        # Show liquid info
        from mud.commands.inspection import do_look
        extra_info = "\n" + do_look(char, f"in {target}")
    
    return result + extra_info


def do_read(char: Character, args: str) -> str:
    """
    Read something - alias for look.
    
    ROM Reference: src/act_info.c do_read (lines 1315-1318)
    
    Just calls do_look.
    """
    from mud.commands.inspection import do_look
    return do_look(char, args)


def do_count(char: Character, args: str) -> str:
    """
    Count players currently online.
    
    ROM Reference: src/act_info.c do_count (lines 2228-2252)
    """
    from mud import registry
    
    count = 0
    for desc in getattr(registry, "descriptor_list", []):
        if hasattr(desc, "character") and desc.character:
            count += 1
    
    # Check player registry as fallback
    if count == 0:
        players = getattr(registry, "player_registry", {})
        count = len(players)
    
    # Track max online
    max_on = getattr(registry, "max_on_today", 0)
    if count > max_on:
        registry.max_on_today = count
        max_on = count
    
    if max_on == count:
        return f"There are {count} characters on, the most so far today."
    else:
        return f"There are {count} characters on, the most on today was {max_on}."


def do_whois(char: Character, args: str) -> str:
    """
    Get information about a specific player.
    
    ROM Reference: src/act_info.c do_whois (lines 1916-2010)
    """
    if not args or not args.strip():
        return "You must provide a name."
    
    target_name = args.strip().split()[0].lower()
    
    from mud import registry
    
    results = []
    
    # Search descriptors/players
    for desc in getattr(registry, "descriptor_list", []):
        if not hasattr(desc, "character") or not desc.character:
            continue
        
        wch = desc.character
        wch_name = getattr(wch, "name", "").lower()
        
        if wch_name.startswith(target_name):
            level = getattr(wch, "level", 1)
            race = getattr(wch, "race", "human")
            if hasattr(race, "name"):
                race = race.name
            
            # Determine class display
            char_class = getattr(wch, "char_class", None) or getattr(wch, "guild", "Adventurer")
            if hasattr(char_class, "name"):
                char_class = char_class.name
            
            # Check for immortal levels
            max_level = 51
            if level >= max_level - 8:
                immortal_classes = ["AVA", "ANG", "DEM", "IMM", "GOD", "DEI", "SUP", "CRE", "IMP"]
                idx = min(level - (max_level - 9), 8)
                class_display = immortal_classes[idx] if idx < len(immortal_classes) else char_class
            else:
                class_display = str(char_class)[:3].upper() if char_class else "ADV"
            
            # Build display line
            name = getattr(wch, "name", "Unknown")
            title = ""
            pcdata = getattr(wch, "pcdata", None)
            if pcdata:
                title = getattr(pcdata, "title", "")
            
            flags = ""
            act_flags = getattr(wch, "act", 0)
            if act_flags & 0x10:  # PLR_KILLER
                flags += "(KILLER) "
            if act_flags & 0x20:  # PLR_THIEF
                flags += "(THIEF) "
            
            comm_flags = getattr(wch, "comm", 0)
            if comm_flags & 0x1:  # COMM_AFK
                flags += "[AFK] "
            
            line = f"[{level:2d} {str(race)[:5]:>5} {class_display:>3}] {flags}{name}{title}"
            results.append(line)
    
    # Also check player registry
    players = getattr(registry, "player_registry", {})
    for name, player in players.items():
        if name.lower().startswith(target_name):
            if any(name.lower() in r.lower() for r in results):
                continue  # Already in list
            level = getattr(player, "level", 1)
            race = getattr(player, "race", "human")
            if hasattr(race, "name"):
                race = race.name
            char_class = getattr(player, "char_class", "Adv")
            if hasattr(char_class, "name"):
                char_class = char_class.name
            line = f"[{level:2d} {str(race)[:5]:>5} {str(char_class)[:3].upper():>3}] {name}"
            results.append(line)
    
    if not results:
        return "No one of that name is playing."
    
    return "\n".join(results)


def do_worth(char: Character, args: str) -> str:
    """
    Show character's monetary worth and experience.
    
    ROM Reference: src/act_info.c do_worth (lines 1453-1472)
    """
    gold = getattr(char, "gold", 0)
    silver = getattr(char, "silver", 0)
    
    is_npc = getattr(char, "is_npc", False)
    
    if is_npc:
        return f"You have {gold} gold and {silver} silver."
    
    exp = getattr(char, "exp", 0)
    level = getattr(char, "level", 1)
    
    # Calculate exp to next level
    exp_per_lvl = _exp_per_level(char)
    exp_to_level = (level + 1) * exp_per_lvl - exp
    
    return f"You have {gold} gold, {silver} silver, and {exp} experience ({exp_to_level} exp to level)."


def do_sit(char: Character, args: str) -> str:
    """
    Sit down.
    
    ROM Reference: src/act_move.c do_sit (lines 1249-1340)
    """
    position = getattr(char, "position", Position.STANDING)
    
    if position == Position.FIGHTING:
        return "Maybe you should finish this fight first?"
    
    # Handle furniture
    target_obj = None
    if args and args.strip():
        from mud.world.obj_find import get_obj_list
        room = getattr(char, "room", None)
        if room:
            contents = getattr(room, "contents", [])
            target_obj = get_obj_list(char, args.strip(), contents)
            if target_obj is None:
                return "You don't see that here."
            
            # Check if it's furniture
            item_type = getattr(target_obj, "item_type", None)
            if item_type is None:
                proto = getattr(target_obj, "prototype", None)
                if proto:
                    item_type = getattr(proto, "item_type", None)
            
            if item_type != ItemType.FURNITURE and str(item_type) != "furniture":
                return "You can't sit on that."
    
    # Handle based on current position
    if position == Position.SLEEPING:
        # Check for magical sleep
        affected_by = getattr(char, "affected_by", 0)
        from mud.models.constants import AffectFlag
        if affected_by & AffectFlag.SLEEP:
            return "You can't wake up!"
        
        char.position = Position.SITTING
        if target_obj:
            char.on = target_obj
            obj_name = getattr(target_obj, "short_descr", "it")
            return f"You wake and sit on {obj_name}."
        return "You wake and sit up."
    
    elif position == Position.RESTING:
        char.position = Position.SITTING
        if target_obj:
            char.on = target_obj
            obj_name = getattr(target_obj, "short_descr", "it")
            return f"You sit on {obj_name}."
        return "You stop resting and sit up."
    
    elif position == Position.SITTING:
        if target_obj:
            char.on = target_obj
            obj_name = getattr(target_obj, "short_descr", "it")
            return f"You sit on {obj_name}."
        return "You are already sitting."
    
    elif position == Position.STANDING:
        char.position = Position.SITTING
        if target_obj:
            char.on = target_obj
            obj_name = getattr(target_obj, "short_descr", "it")
            return f"You sit down on {obj_name}."
        return "You sit down."
    
    return "You can't sit down right now."


def _exp_per_level(char: Character) -> int:
    """Calculate experience per level."""
    # Base 1000 exp per level, modified by creation points
    pcdata = getattr(char, "pcdata", None)
    if pcdata:
        points = getattr(pcdata, "points", 40)
        base = 1000
        return base + points * 10
    return 1000
