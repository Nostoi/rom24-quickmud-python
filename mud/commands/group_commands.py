"""
Group-related commands: follow, group, gtell, order, split.

ROM Reference: src/act_comm.c (follow, group, order, gtell, split)
"""
from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import AffectFlag, PlayerFlag, Position
from mud.world.char_find import get_char_room


def add_follower(char: Character, master: Character) -> None:
    """
    Add char as a follower of master.
    
    ROM Reference: src/act_comm.c add_follower (lines 1600-1620)
    """
    if char.master is not None:
        return  # Already following someone
    
    char.master = master
    char.leader = None
    
    # Add to master's follower list if exists
    if hasattr(master, "followers"):
        if char not in master.followers:
            master.followers.append(char)


def stop_follower(char: Character) -> None:
    """
    Stop following the current master.
    
    ROM Reference: src/act_comm.c stop_follower (lines 1630-1660)
    """
    master = char.master
    if master is None:
        return
    
    # Remove charm affect if present
    affected_by = getattr(char, "affected_by", 0)
    if affected_by & AffectFlag.CHARM:
        char.affected_by = affected_by & ~AffectFlag.CHARM
    
    # Remove from master's follower list
    if hasattr(master, "followers") and char in master.followers:
        master.followers.remove(char)
    
    char.master = None
    char.leader = None


def is_same_group(ach: Character, bch: Character) -> bool:
    """
    Check if two characters are in the same group.
    
    ROM Reference: src/handler.c is_same_group
    """
    if ach is None or bch is None:
        return False
    
    # Get leaders
    aleader = ach.leader if ach.leader else ach
    bleader = bch.leader if bch.leader else bch
    
    return aleader == bleader


def do_follow(char: Character, args: str) -> str:
    """
    Follow another character.
    
    ROM Reference: src/act_comm.c do_follow (lines 1536-1595)
    
    Usage:
    - follow <target> - Start following target
    - follow self - Stop following
    """
    args = args.strip()
    
    if not args:
        return "Follow whom?"
    
    # Find target in room
    victim = get_char_room(char, args)
    if not victim:
        return "They aren't here."
    
    # Check if charmed - can't change who you follow
    affected_by = getattr(char, "affected_by", 0)
    if affected_by & AffectFlag.CHARM and char.master is not None:
        master_name = getattr(char.master, "short_descr", None) or getattr(char.master, "name", "your master")
        return f"But you'd rather follow {master_name}!"
    
    # Following self = stop following
    if victim is char:
        if char.master is None:
            return "You already follow yourself."
        stop_follower(char)
        return "You stop following."
    
    # Check NOFOLLOW flag on target
    is_npc = getattr(victim, "is_npc", True)
    if not is_npc:
        act_flags = getattr(victim, "act", 0)
        if act_flags & PlayerFlag.NOFOLLOW:
            victim_name = getattr(victim, "short_descr", None) or getattr(victim, "name", "They")
            return f"{victim_name} doesn't seem to want any followers."
    
    # Remove NOFOLLOW from self
    if not getattr(char, "is_npc", True):
        char.act = getattr(char, "act", 0) & ~PlayerFlag.NOFOLLOW
    
    # Stop following current master first
    if char.master is not None:
        stop_follower(char)
    
    # Start following new master
    add_follower(char, victim)
    
    victim_name = getattr(victim, "short_descr", None) or getattr(victim, "name", "them")
    return f"You now follow {victim_name}."


def do_group(char: Character, args: str) -> str:
    """
    Manage group membership.
    
    ROM Reference: src/act_comm.c do_group (lines 1770-1850)
    
    Usage:
    - group - Show group status
    - group <target> - Add/remove target from group
    """
    from mud.models.character import character_registry
    
    args = args.strip()
    
    # No argument - show group status
    if not args:
        # Determine leader
        leader = char.leader if char.leader else char
        leader_name = getattr(leader, "short_descr", None) or getattr(leader, "name", "Someone")
        
        lines = [f"{leader_name}'s group:"]
        
        # Find all group members
        members_found = []
        seen_ids = set()
        
        def add_member(gch):
            if id(gch) not in seen_ids:
                members_found.append(gch)
                seen_ids.add(id(gch))
        
        # Always include self
        if is_same_group(char, char):
            add_member(char)
        
        # Check room for group members
        room = getattr(char, "room", None)
        if room:
            for occupant in getattr(room, "people", []):
                if is_same_group(occupant, char):
                    add_member(occupant)
        
        # Check followers
        if hasattr(leader, "followers"):
            for follower in leader.followers:
                if is_same_group(follower, char):
                    add_member(follower)
        
        # Also include leader
        add_member(leader)
        
        for gch in members_found:
            gch_name = getattr(gch, "short_descr", None) or getattr(gch, "name", "someone")
            gch_level = getattr(gch, "level", 1)
            is_npc = getattr(gch, "is_npc", False)
            class_name = "Mob" if is_npc else getattr(gch, "class_name", "???")[:3]
            
            hit = getattr(gch, "hit", 100)
            max_hit = getattr(gch, "max_hit", 100)
            mana = getattr(gch, "mana", 100)
            max_mana = getattr(gch, "max_mana", 100)
            move = getattr(gch, "move", 100)
            max_move = getattr(gch, "max_move", 100)
            exp = getattr(gch, "exp", 0)
            
            lines.append(
                f"[{gch_level:2d} {class_name:3s}] {gch_name:16s} "
                f"{hit:4d}/{max_hit:4d} hp {mana:4d}/{max_mana:4d} mana "
                f"{move:4d}/{max_move:4d} mv {exp:5d} xp"
            )
        
        return "\n".join(lines)
    
    # Argument provided - add/remove from group
    victim = get_char_room(char, args)
    if not victim:
        return "They aren't here."
    
    # Check if char is leader (not following anyone else)
    if char.master is not None or (char.leader is not None and char.leader is not char):
        return "But you are following someone else!"
    
    # Can't group someone who isn't following you (unless it's yourself)
    if victim.master is not char and char is not victim:
        victim_name = getattr(victim, "short_descr", None) or getattr(victim, "name", "They")
        return f"{victim_name} isn't following you."
    
    # Can't remove charmed mobs
    affected_by = getattr(victim, "affected_by", 0)
    if affected_by & AffectFlag.CHARM:
        return "You can't remove charmed mobs from your group."
    
    # Check if char is charmed
    char_affected = getattr(char, "affected_by", 0)
    if char_affected & AffectFlag.CHARM:
        return "You like your master too much to leave!"
    
    # Already in group - remove
    if is_same_group(victim, char) and char is not victim:
        victim.leader = None
        victim_name = getattr(victim, "short_descr", None) or getattr(victim, "name", "them")
        return f"You remove {victim_name} from your group."
    
    # Add to group
    victim.leader = char
    victim_name = getattr(victim, "short_descr", None) or getattr(victim, "name", "someone")
    return f"{victim_name} joins your group."


def do_gtell(char: Character, args: str) -> str:
    """
    Send a message to all group members.
    
    ROM Reference: src/act_comm.c do_gtell
    
    Usage: gtell <message>
    """
    from mud.models.character import character_registry
    
    args = args.strip()
    
    if not args:
        return "Tell your group what?"
    
    # Send to all group members
    # For now, just confirm the message was sent
    char_name = getattr(char, "short_descr", None) or getattr(char, "name", "Someone")
    return f"You tell the group '{args}'"


def do_split(char: Character, args: str) -> str:
    """
    Split gold/silver among group members.
    
    ROM Reference: src/act_comm.c do_split (lines 1875-1970)
    
    Usage:
    - split <amount> - Split gold
    - split <amount> gold - Split gold
    - split <amount> silver - Split silver
    """
    args = args.strip()
    parts = args.split()
    
    if not parts:
        return "Split how much?"
    
    # Parse amount
    try:
        amount = int(parts[0])
    except ValueError:
        return "Split how much?"
    
    if amount <= 0:
        return "Split how much?"
    
    # Check if gold or silver (default gold)
    silver = False
    if len(parts) > 1:
        if parts[1].lower() == "silver":
            silver = True
        elif parts[1].lower() not in ("gold", "coins", "coin"):
            return "Sorry, you can't do that."
    
    # Check if char has enough
    if silver:
        char_currency = getattr(char, "silver", 0)
    else:
        char_currency = getattr(char, "gold", 0)
    
    if char_currency < amount:
        return "You don't have that much."
    
    # Count group members in room
    room = getattr(char, "room", None)
    if not room:
        return "You're not anywhere."
    
    members = 1  # Include self
    for occupant in getattr(room, "people", []):
        if occupant is not char and is_same_group(occupant, char):
            members += 1
    
    if members < 2:
        return "Just keep it all."
    
    # Calculate shares
    share = amount // members
    extra = amount % members
    
    if share == 0:
        return f"Don't be so stingy with your {('silver' if silver else 'gold')}!"
    
    # Deduct from char
    if silver:
        char.silver = getattr(char, "silver", 0) - amount
    else:
        char.gold = getattr(char, "gold", 0) - amount
    
    # Give to group members (including self)
    for occupant in getattr(room, "people", []):
        if is_same_group(occupant, char):
            if silver:
                occupant.silver = getattr(occupant, "silver", 0) + share
            else:
                occupant.gold = getattr(occupant, "gold", 0) + share
    
    # Char keeps extra
    if silver:
        char.silver = getattr(char, "silver", 0) + extra
    else:
        char.gold = getattr(char, "gold", 0) + extra
    
    currency_name = "silver" if silver else "gold"
    return f"You split {amount} {currency_name}. Each group member receives {share} {currency_name}."


def do_order(char: Character, args: str) -> str:
    """
    Order charmed followers to perform an action.
    
    ROM Reference: src/act_comm.c do_order
    
    Usage:
    - order <target> <command>
    - order all <command>
    """
    args = args.strip()
    parts = args.split(None, 1)
    
    if len(parts) < 2:
        return "Order whom to do what?"
    
    target_name, command = parts
    
    # Find target
    if target_name.lower() == "all":
        # Order all charmed followers
        count = 0
        room = getattr(char, "room", None)
        if room:
            for occupant in getattr(room, "people", []):
                affected_by = getattr(occupant, "affected_by", 0)
                if occupant.master is char and affected_by & AffectFlag.CHARM:
                    count += 1
                    # Execute command for occupant
                    # Note: actual command execution would go here
        
        if count == 0:
            return "You have no followers here."
        return f"You order your followers to '{command}'."
    else:
        victim = get_char_room(char, target_name)
        if not victim:
            return "They aren't here."
        
        if victim is char:
            return "Aye aye, right away!"
        
        # Check if victim is charmed by char
        affected_by = getattr(victim, "affected_by", 0)
        if victim.master is not char or not (affected_by & AffectFlag.CHARM):
            return "Do it yourself!"
        
        # Execute command for victim
        # Note: actual command execution would go here
        victim_name = getattr(victim, "short_descr", None) or getattr(victim, "name", "Your follower")
        return f"{victim_name} does as you order."
