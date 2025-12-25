"""
Immortal wizard commands - at, goto, transfer, force, peace.

ROM Reference: src/act_wiz.c
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from mud.models.character import Character

if TYPE_CHECKING:
    pass


# Trust levels
LEVEL_HERO = 51
LEVEL_IMMORTAL = 52
MAX_LEVEL = 60


def get_trust(char: Character) -> int:
    """Get character's trust level."""
    trust = getattr(char, "trust", 0)
    if trust != 0:
        return trust
    
    if getattr(char, "is_npc", False):
        return 0
    
    return getattr(char, "level", 1)


def find_location(char: Character, arg: str):
    """
    Find a room by vnum or character name.
    
    ROM Reference: src/act_wiz.c find_location
    """
    from mud import registry
    
    # Try numeric vnum first
    if arg.isdigit():
        vnum = int(arg)
        return registry.rooms.get(vnum)
    
    # Try to find character
    victim = get_char_world(char, arg)
    if victim:
        return getattr(victim, "room", None)
    
    # Try to find object
    # (simplified - not implementing object location for now)
    
    return None


def get_char_world(char: Character, name: str):
    """Find a character anywhere in the world."""
    from mud import registry
    
    name_lower = name.lower()
    
    # Handle numbered prefix (2.guard)
    number = 1
    if "." in name and name.split(".")[0].isdigit():
        parts = name.split(".", 1)
        number = int(parts[0])
        name_lower = parts[1].lower()
    
    count = 0
    
    # Search all characters
    for ch in getattr(registry, "char_list", []):
        ch_name = getattr(ch, "name", "").lower()
        if name_lower in ch_name or name_lower == ch_name:
            count += 1
            if count == number:
                return ch
    
    # Also check players
    for player in getattr(registry, "players", {}).values():
        p_name = getattr(player, "name", "").lower()
        if name_lower in p_name or name_lower == p_name:
            count += 1
            if count == number:
                return player
    
    return None


def get_char_room(char: Character, name: str):
    """Find a character in the same room."""
    room = getattr(char, "room", None)
    if not room:
        return None
    
    name_lower = name.lower()
    
    # Handle numbered prefix
    number = 1
    if "." in name and name.split(".")[0].isdigit():
        parts = name.split(".", 1)
        number = int(parts[0])
        name_lower = parts[1].lower()
    
    count = 0
    for person in getattr(room, "people", []):
        p_name = getattr(person, "name", "").lower()
        if name_lower in p_name or name_lower == p_name:
            count += 1
            if count == number:
                return person
    
    return None


def do_at(char: Character, args: str) -> str:
    """
    Execute a command at another location.
    
    ROM Reference: src/act_wiz.c do_at (lines 882-935)
    
    Usage: at <location> <command>
    
    Location can be a room vnum or character name.
    """
    if not args or not args.strip():
        return "At where what?"
    
    parts = args.strip().split(None, 1)
    if len(parts) < 2:
        return "At where what?"
    
    location_arg = parts[0]
    command = parts[1]
    
    location = find_location(char, location_arg)
    if location is None:
        return "No such location."
    
    # Check private room
    if _room_is_private(location) and get_trust(char) < MAX_LEVEL:
        return "That room is private right now."
    
    # Save original location
    original_room = getattr(char, "room", None)
    original_on = getattr(char, "on", None)
    
    # Move to location
    _char_from_room(char)
    _char_to_room(char, location)
    
    # Execute command
    from mud.commands import process_command
    result = process_command(char, command)
    
    # Return to original location (if still exists)
    _char_from_room(char)
    _char_to_room(char, original_room)
    char.on = original_on
    
    return result if result else "Ok."


def do_goto(char: Character, args: str) -> str:
    """
    Teleport to a location.
    
    ROM Reference: src/act_wiz.c do_goto (lines 937-1015)
    
    Usage: goto <location>
    
    Location can be a room vnum or character name.
    """
    if not args or not args.strip():
        return "Goto where?"
    
    location = find_location(char, args.strip())
    if location is None:
        return "No such location."
    
    # Check private room
    room_count = len(getattr(location, "people", []))
    if _room_is_private(location) and room_count > 1 and get_trust(char) < MAX_LEVEL:
        return "That room is private right now."
    
    # Stop fighting
    if getattr(char, "fighting", None):
        char.fighting = None
    
    # Announce departure (bamfout)
    old_room = getattr(char, "room", None)
    if old_room:
        pcdata = getattr(char, "pcdata", None)
        bamfout = getattr(pcdata, "bamfout", None) if pcdata else None
        if bamfout:
            _act_room(old_room, char, bamfout)
        else:
            _act_room(old_room, char, "$n leaves in a swirling mist.")
    
    # Move character
    _char_from_room(char)
    _char_to_room(char, location)
    
    # Announce arrival (bamfin)
    pcdata = getattr(char, "pcdata", None)
    bamfin = getattr(pcdata, "bamfin", None) if pcdata else None
    if bamfin:
        _act_room(location, char, bamfin)
    else:
        _act_room(location, char, "$n appears in a swirling mist.")
    
    # Show room
    from mud.commands.inspection import do_look
    return do_look(char, "auto")


def do_transfer(char: Character, args: str) -> str:
    """
    Transfer a player to your location or another location.
    
    ROM Reference: src/act_wiz.c do_transfer (lines 799-880)
    
    Usage:
    - transfer <player>         - Transfer to your location
    - transfer <player> <room>  - Transfer to specific room
    - transfer all              - Transfer all players to you
    """
    if not args or not args.strip():
        return "Transfer whom (and where)?"
    
    parts = args.strip().split()
    target_name = parts[0]
    location_arg = parts[1] if len(parts) > 1 else None
    
    # Handle "transfer all"
    if target_name.lower() == "all":
        from mud import registry
        count = 0
        for player in list(getattr(registry, "players", {}).values()):
            if player is not char:
                do_transfer(char, getattr(player, "name", ""))
                count += 1
        return f"Transferred {count} players." if count > 0 else "No one to transfer."
    
    # Find destination
    if location_arg:
        location = find_location(char, location_arg)
        if location is None:
            return "No such location."
        
        if _room_is_private(location) and get_trust(char) < MAX_LEVEL:
            return "That room is private right now."
    else:
        location = getattr(char, "room", None)
    
    # Find victim
    victim = get_char_world(char, target_name)
    if victim is None:
        return "They aren't here."
    
    if getattr(victim, "room", None) is None:
        return "They are in limbo."
    
    # Stop fighting
    if getattr(victim, "fighting", None):
        victim.fighting = None
    
    # Announce and transfer
    old_room = getattr(victim, "room", None)
    if old_room:
        _act_room(old_room, victim, "$n disappears in a mushroom cloud.")
    
    _char_from_room(victim)
    _char_to_room(victim, location)
    
    _act_room(location, victim, "$n arrives from a puff of smoke.")
    
    if char is not victim:
        # Notify victim
        char_name = getattr(char, "name", "Someone")
        _send_to_char(victim, f"{char_name} has transferred you.")
    
    # Make victim look
    from mud.commands.inspection import do_look
    do_look(victim, "auto")
    
    return "Ok."


def do_force(char: Character, args: str) -> str:
    """
    Force a player or mob to execute a command.
    
    ROM Reference: src/act_wiz.c do_force (lines 4183-4300)
    
    Usage:
    - force <target> <command>
    - force all <command>      - Force all players
    - force players <command>  - Force mortal players only
    
    Note: Cannot force "delete" or "mob" commands.
    """
    if not args or not args.strip():
        return "Force whom to do what?"
    
    parts = args.strip().split(None, 1)
    if len(parts) < 2:
        return "Force whom to do what?"
    
    target_name = parts[0]
    command = parts[1]
    
    # Safety check - don't allow delete or mob commands
    cmd_first = command.split()[0].lower() if command else ""
    if cmd_first in ("delete", "mob"):
        return "That will NOT be done."
    
    # Handle "force all"
    if target_name.lower() == "all":
        if get_trust(char) < MAX_LEVEL - 3:
            return "Not at your level!"
        
        from mud import registry
        count = 0
        for player in list(getattr(registry, "players", {}).values()):
            if get_trust(player) < get_trust(char):
                _send_to_char(player, f"{getattr(char, 'name', 'Someone')} forces you to '{command}'.")
                from mud.commands import process_command
                process_command(player, command)
                count += 1
        return f"Forced {count} players." if count > 0 else "No one to force."
    
    # Handle "force players" (mortals only)
    if target_name.lower() == "players":
        if get_trust(char) < MAX_LEVEL - 2:
            return "Not at your level!"
        
        from mud import registry
        count = 0
        for player in list(getattr(registry, "players", {}).values()):
            if get_trust(player) < get_trust(char) and getattr(player, "level", 1) < LEVEL_HERO:
                _send_to_char(player, f"{getattr(char, 'name', 'Someone')} forces you to '{command}'.")
                from mud.commands import process_command
                process_command(player, command)
                count += 1
        return f"Forced {count} players." if count > 0 else "No one to force."
    
    # Find specific target
    victim = get_char_world(char, target_name)
    if victim is None:
        return "They aren't here."
    
    if victim is char:
        return "Aye aye, right away!"
    
    # Check trust
    if not getattr(victim, "is_npc", False) and get_trust(victim) >= get_trust(char):
        return "Do it yourself!"
    
    # Force the command
    _send_to_char(victim, f"{getattr(char, 'name', 'Someone')} forces you to '{command}'.")
    
    from mud.commands import process_command
    process_command(victim, command)
    
    return "Ok."


def do_peace(char: Character, args: str) -> str:
    """
    Stop all combat in the current room.
    
    ROM Reference: src/act_wiz.c do_peace (lines 3134-3150)
    
    Usage: peace
    """
    room = getattr(char, "room", None)
    if not room:
        return "You're not in a room."
    
    for person in getattr(room, "people", []):
        # Stop fighting
        if getattr(person, "fighting", None):
            person.fighting = None
        
        # Remove aggressive flag from NPCs
        if getattr(person, "is_npc", False):
            act_flags = getattr(person, "act", 0)
            ACT_AGGRESSIVE = 0x00000020
            if act_flags & ACT_AGGRESSIVE:
                person.act = act_flags & ~ACT_AGGRESSIVE
    
    return "Ok."


# Helper functions

def _room_is_private(room) -> bool:
    """Check if room is private."""
    room_flags = getattr(room, "room_flags", 0)
    ROOM_PRIVATE = 0x00000200
    ROOM_SOLITARY = 0x00000400
    
    if room_flags & ROOM_PRIVATE:
        count = len(getattr(room, "people", []))
        return count >= 2
    
    if room_flags & ROOM_SOLITARY:
        count = len(getattr(room, "people", []))
        return count >= 1
    
    return False


def _char_from_room(char: Character) -> None:
    """Remove character from their current room."""
    room = getattr(char, "room", None)
    if room:
        people = getattr(room, "people", [])
        if char in people:
            people.remove(char)
    char.room = None


def _char_to_room(char: Character, room) -> None:
    """Place character in a room."""
    if room is None:
        return
    
    char.room = room
    people = getattr(room, "people", None)
    if people is None:
        room.people = []
        people = room.people
    if char not in people:
        people.append(char)


def _act_room(room, char: Character, message: str) -> None:
    """Send action message to room (except actor)."""
    char_name = getattr(char, "name", "Someone")
    formatted = message.replace("$n", char_name)
    
    for person in getattr(room, "people", []):
        if person is not char:
            _send_to_char(person, formatted)


def _send_to_char(char: Character, message: str) -> None:
    """Send message to character."""
    # In a real implementation, this would use the session
    # For now, store in a buffer attribute
    if not hasattr(char, "output_buffer"):
        char.output_buffer = []
    char.output_buffer.append(message)
