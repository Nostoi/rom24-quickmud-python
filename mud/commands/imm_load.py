"""
Immortal wizard commands - load, purge, restore, slay.

ROM Reference: src/act_wiz.c, src/fight.c
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from mud.models.character import Character
from mud.commands.imm_commands import get_trust, get_char_world, get_char_room, MAX_LEVEL

if TYPE_CHECKING:
    pass


def do_load(char: Character, args: str) -> str:
    """
    Load a mobile or object into the game.
    
    ROM Reference: src/act_wiz.c do_load (lines 2459-2485)
    
    Usage:
    - load mob <vnum>          - Load a mobile
    - load obj <vnum> [level]  - Load an object
    """
    if not args or not args.strip():
        return ("Syntax:\n"
                "  load mob <vnum>\n"
                "  load obj <vnum> <level>")
    
    parts = args.strip().split()
    load_type = parts[0].lower()
    
    if load_type in ("mob", "char"):
        if len(parts) < 2:
            return "Syntax: load mob <vnum>."
        return do_mload(char, parts[1])
    
    if load_type == "obj":
        if len(parts) < 2:
            return "Syntax: load obj <vnum> <level>."
        level_arg = parts[2] if len(parts) > 2 else None
        return do_oload(char, parts[1], level_arg)
    
    return ("Syntax:\n"
            "  load mob <vnum>\n"
            "  load obj <vnum> <level>")


def do_mload(char: Character, vnum_arg: str) -> str:
    """
    Load a mobile by vnum.
    
    ROM Reference: src/act_wiz.c do_mload (lines 2487-2520)
    """
    if not vnum_arg.isdigit():
        return "Syntax: load mob <vnum>."
    
    vnum = int(vnum_arg)
    
    from mud import registry
    
    # Find mob prototype
    mob_index = registry.mob_prototypes.get(vnum)
    if mob_index is None:
        return "No mob has that vnum."
    
    # Create the mobile
    from mud.spawning.mob_spawner import spawn_mob
    victim = spawn_mob(vnum)
    
    if victim is None:
        return "Failed to create mobile."
    
    # Place in room
    room = getattr(char, "room", None)
    if room:
        victim.room = room
        people = getattr(room, "people", None)
        if people is None:
            room.people = []
        room.people.append(victim)
    
    # Announce
    victim_name = getattr(victim, "short_descr", "something")
    return f"You have created {victim_name}!"


def do_oload(char: Character, vnum_arg: str, level_arg: str | None = None) -> str:
    """
    Load an object by vnum.
    
    ROM Reference: src/act_wiz.c do_oload (lines 2522-2572)
    """
    if not vnum_arg.isdigit():
        return "Syntax: load obj <vnum> <level>."
    
    vnum = int(vnum_arg)
    level = get_trust(char)  # Default to trust level
    
    if level_arg:
        if not level_arg.isdigit():
            return "Syntax: load obj <vnum> <level>."
        level = int(level_arg)
        if level < 0 or level > get_trust(char):
            return "Level must be between 0 and your level."
    
    from mud import registry
    
    # Find object prototype
    obj_index = registry.obj_prototypes.get(vnum)
    if obj_index is None:
        return "No object has that vnum."
    
    # Create the object
    from mud.spawning.obj_spawner import spawn_obj
    obj = spawn_obj(vnum, level)
    
    if obj is None:
        return "Failed to create object."
    
    # Place in inventory or room
    wear_flags = getattr(obj, "wear_flags", 0)
    if not hasattr(obj, "wear_flags"):
        proto = getattr(obj, "prototype", None)
        if proto:
            wear_flags = getattr(proto, "wear_flags", 0)
    
    ITEM_TAKE = 1
    if wear_flags & ITEM_TAKE:
        # Add to inventory
        carrying = getattr(char, "carrying", None)
        if carrying is None:
            char.carrying = []
        char.carrying.append(obj)
        obj.carried_by = char
    else:
        # Add to room
        room = getattr(char, "room", None)
        if room:
            contents = getattr(room, "contents", None)
            if contents is None:
                room.contents = []
            room.contents.append(obj)
            obj.in_room = room
    
    obj_name = getattr(obj, "short_descr", "something")
    return f"You have created {obj_name}!"


def do_purge(char: Character, args: str) -> str:
    """
    Purge mobiles and objects from a room, or a specific target.
    
    ROM Reference: src/act_wiz.c do_purge (lines 2574-2650)
    
    Usage:
    - purge           - Purge all mobs/objects in room
    - purge <target>  - Purge specific mob or player (kicks them)
    """
    room = getattr(char, "room", None)
    if not room:
        return "You're not in a room."
    
    if not args or not args.strip():
        # Purge entire room
        ACT_NOPURGE = 0x00002000
        ITEM_NOPURGE = 0x00000040
        
        # Purge mobs (not players, not self)
        people = list(getattr(room, "people", []))
        for victim in people:
            if victim is char:
                continue
            if not getattr(victim, "is_npc", False):
                continue
            act_flags = getattr(victim, "act", 0)
            if act_flags & ACT_NOPURGE:
                continue
            _extract_char(victim)
        
        # Purge objects
        contents = list(getattr(room, "contents", []))
        for obj in contents:
            extra_flags = getattr(obj, "extra_flags", 0)
            if extra_flags & ITEM_NOPURGE:
                continue
            _extract_obj(obj)
        
        return "Ok."
    
    # Purge specific target
    target_name = args.strip().split()[0]
    victim = get_char_world(char, target_name)
    
    if victim is None:
        return "They aren't here."
    
    if not getattr(victim, "is_npc", False):
        # Purging a player - special handling
        if victim is char:
            return "Ho ho ho."
        
        if get_trust(victim) >= get_trust(char):
            victim_name = getattr(victim, "name", "Someone")
            return f"Maybe that wasn't a good idea..."
        
        # Kick the player (simplified)
        _extract_char(victim)
        return "Ok."
    
    # Purge NPC
    _extract_char(victim)
    return "Ok."


def do_restore(char: Character, args: str) -> str:
    """
    Restore a character to full health/mana/move and remove afflictions.
    
    ROM Reference: src/act_wiz.c do_restore (lines 2785-2870)
    
    Usage:
    - restore         - Restore everyone in room
    - restore room    - Restore everyone in room
    - restore <char>  - Restore specific character
    - restore all     - Restore all online players
    """
    if not args or not args.strip() or args.strip().lower() == "room":
        # Restore room
        room = getattr(char, "room", None)
        if not room:
            return "You're not in a room."
        
        for victim in getattr(room, "people", []):
            _restore_char(victim)
            _send_to_char(victim, f"{getattr(char, 'name', 'Someone')} has restored you.")
        
        return "Room restored."
    
    arg = args.strip().lower()
    
    if arg == "all":
        if get_trust(char) < MAX_LEVEL - 1:
            return "Not at your level!"
        
        from mud import registry
        count = 0
        for player in getattr(registry, "players", {}).values():
            if not getattr(player, "is_npc", False):
                _restore_char(player)
                _send_to_char(player, f"{getattr(char, 'name', 'Someone')} has restored you.")
                count += 1
        
        return "All active players restored."
    
    # Restore specific character
    victim = get_char_world(char, args.strip())
    if victim is None:
        return "They aren't here."
    
    _restore_char(victim)
    _send_to_char(victim, f"{getattr(char, 'name', 'Someone')} has restored you.")
    
    return "Ok."


def do_slay(char: Character, args: str) -> str:
    """
    Instantly kill a target.
    
    ROM Reference: src/fight.c do_slay (lines 3252-3290)
    
    Usage: slay <target>
    """
    if not args or not args.strip():
        return "Slay whom?"
    
    target_name = args.strip().split()[0]
    victim = get_char_room(char, target_name)
    
    if victim is None:
        return "They aren't here."
    
    if victim is char:
        return "Suicide is a mortal sin."
    
    # Check trust for players
    if not getattr(victim, "is_npc", False):
        if getattr(victim, "level", 1) >= get_trust(char):
            return "You failed."
    
    # Slay the victim
    victim_name = getattr(victim, "name", "someone")
    
    # Extract/kill the victim
    _extract_char(victim)
    
    return f"You slay {victim_name} in cold blood!"


def do_sla(char: Character, args: str) -> str:
    """
    Typo guard for slay - prevents accidental slaying.
    
    ROM Reference: interp.c - sla is a separate command that does nothing
    """
    return "If you want to SLAY, spell it out."


# Helper functions

def _restore_char(char: Character) -> None:
    """Fully restore a character."""
    # Strip negative affects
    affected = getattr(char, "affected", [])
    # (In full implementation, would strip plague, poison, blindness, sleep, curse)
    
    # Restore stats
    char.hit = getattr(char, "max_hit", 100)
    char.mana = getattr(char, "max_mana", 100)
    char.move = getattr(char, "max_move", 100)
    
    # Update position
    from mud.models.constants import Position
    if getattr(char, "position", Position.STANDING) < Position.STANDING:
        char.position = Position.STANDING


def _extract_char(char: Character) -> None:
    """Remove character from the game."""
    # Stop fighting
    if getattr(char, "fighting", None):
        char.fighting = None
    
    # Remove from room
    room = getattr(char, "room", None)
    if room:
        people = getattr(room, "people", [])
        if char in people:
            people.remove(char)
    
    # Remove from global list
    from mud import registry
    char_list = getattr(registry, "char_list", [])
    if char in char_list:
        char_list.remove(char)
    
    char.room = None


def _extract_obj(obj) -> None:
    """Remove object from the game."""
    room = getattr(obj, "in_room", None)
    if room:
        contents = getattr(room, "contents", [])
        if obj in contents:
            contents.remove(obj)
    
    carrier = getattr(obj, "carried_by", None)
    if carrier:
        carrying = getattr(carrier, "carrying", [])
        if obj in carrying:
            carrying.remove(obj)
    
    container = getattr(obj, "in_obj", None)
    if container:
        contains = getattr(container, "contains", [])
        if obj in contains:
            contains.remove(obj)
    
    obj.in_room = None
    obj.carried_by = None
    obj.in_obj = None


def _send_to_char(char: Character, message: str) -> None:
    """Send message to character."""
    if not hasattr(char, "output_buffer"):
        char.output_buffer = []
    char.output_buffer.append(message)
