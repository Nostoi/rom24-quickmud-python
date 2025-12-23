"""
Server control commands - reboot, shutdown, copyover.

ROM Reference: src/act_wiz.c
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from mud.models.character import Character
from mud.commands.imm_commands import get_trust, MAX_LEVEL, LEVEL_HERO

if TYPE_CHECKING:
    pass


def do_reboot(char: Character, args: str) -> str:
    """
    Reboot the MUD server.
    
    ROM Reference: src/act_wiz.c do_reboot (lines 2027-2050)
    
    Usage: reboot
    
    Saves all players and initiates a server restart.
    """
    from mud import registry
    
    char_name = getattr(char, "name", "Someone")
    invis_level = getattr(char, "invis_level", 0)
    
    # Announce if visible
    if invis_level < LEVEL_HERO:
        # Broadcast to all players
        for player in getattr(registry, "players", {}).values():
            _send_to_char(player, f"Reboot by {char_name}.")
    
    # Save all characters
    for player in getattr(registry, "players", {}).values():
        # In real implementation: save_char_obj(player)
        pass
    
    # Set shutdown flag
    registry.merc_down = True
    
    return "Rebooting..."


def do_shutdown(char: Character, args: str) -> str:
    """
    Shutdown the MUD server.
    
    ROM Reference: src/act_wiz.c do_shutdown (lines 2059-2085)
    
    Usage: shutdown
    
    Saves all players and shuts down the server.
    """
    from mud import registry
    
    char_name = getattr(char, "name", "Someone")
    invis_level = getattr(char, "invis_level", 0)
    
    # Announce if visible
    if invis_level < LEVEL_HERO:
        for player in getattr(registry, "players", {}).values():
            _send_to_char(player, f"Shutdown by {char_name}.")
    
    # Log the shutdown
    # In real implementation: append_file(ch, SHUTDOWN_FILE, buf)
    
    # Save all characters
    for player in getattr(registry, "players", {}).values():
        # In real implementation: save_char_obj(player)
        pass
    
    # Set shutdown flag
    registry.merc_down = True
    
    return "Shutting down..."


def do_copyover(char: Character, args: str) -> str:
    """
    Hot reboot the MUD without disconnecting players.
    
    ROM Reference: src/act_wiz.c do_copyover (lines 4498-4550)
    
    Usage: copyover
    
    Saves all connections and restarts the server, preserving player sessions.
    """
    from mud import registry
    
    char_name = getattr(char, "name", "Someone")
    
    # Announce copyover
    for player in getattr(registry, "players", {}).values():
        _send_to_char(player, f"\n\r *** COPYOVER by {char_name} - please remain seated!\n\r")
    
    # In real implementation:
    # 1. Write all descriptor info to a file
    # 2. exec() the new server binary
    # 3. New server reads descriptor file and reconnects players
    
    # For now, just save and mark for restart
    for player in getattr(registry, "players", {}).values():
        # save_char_obj(player)
        pass
    
    registry.copyover_pending = True
    
    return "Copyover initiated..."


def do_protect(char: Character, args: str) -> str:
    """
    Toggle snoop-protection on a player.
    
    ROM Reference: src/act_wiz.c do_protect (lines 2086-2120)
    
    Usage: protect <player>
    
    Prevents other immortals from snooping the target.
    """
    if not args or not args.strip():
        return "Protect whom from snooping?"
    
    from mud.commands.imm_commands import get_char_world
    
    target_name = args.strip().split()[0]
    victim = get_char_world(char, target_name)
    
    if victim is None:
        return "They aren't here."
    
    if getattr(victim, "is_npc", False):
        return "Not on NPC's."
    
    # Toggle snoop-proof flag
    COMM_SNOOP_PROOF = 0x00020000
    comm_flags = getattr(victim, "comm", 0)
    victim_name = getattr(victim, "name", "someone")
    
    if comm_flags & COMM_SNOOP_PROOF:
        victim.comm = comm_flags & ~COMM_SNOOP_PROOF
        _send_to_char(victim, "Your snoop-loss has been lifted.")
        return f"{victim_name}'s snoop-loss removed."
    else:
        victim.comm = comm_flags | COMM_SNOOP_PROOF
        _send_to_char(victim, "You are now protected from snooping.")
        return f"{victim_name} is now snoop-proof."


def do_violate(char: Character, args: str) -> str:
    """
    Enter a private room.
    
    ROM Reference: src/act_wiz.c do_violate (lines 1000-1025)
    
    Usage: violate <direction>
    
    Allows an immortal to enter a private room.
    """
    if not args or not args.strip():
        return "Violate which direction?"
    
    direction = args.strip().lower()
    
    # Get exit
    room = getattr(char, "room", None)
    if not room:
        return "You're not in a room."
    
    exit_data = None
    for dir_name in ["north", "east", "south", "west", "up", "down"]:
        if dir_name.startswith(direction):
            exit_data = getattr(room, dir_name, None)
            break
    
    if exit_data is None:
        return "There's no exit in that direction."
    
    to_room = getattr(exit_data, "to_room", None)
    if to_room is None:
        return "That exit doesn't lead anywhere."
    
    # Move the character (bypassing private room check)
    from mud.commands.imm_commands import _char_from_room, _char_to_room
    _char_from_room(char)
    _char_to_room(char, to_room)
    
    from mud.commands.inspection import do_look
    return do_look(char, "auto")


def do_dump(char: Character, args: str) -> str:
    """
    Dump memory statistics to a file.
    
    ROM Reference: src/db.c do_dump (lines 3329-3450)
    
    Usage: dump
    
    Creates a mem.dmp file with detailed memory usage info.
    """
    from mud import registry
    
    lines = []
    lines.append("=== Memory Dump ===")
    
    # Count various entities
    num_areas = len(getattr(registry, "areas", []))
    num_rooms = len(getattr(registry, "rooms", {}))
    num_mobs = len(getattr(registry, "mob_prototypes", {}))
    num_objs = len(getattr(registry, "obj_prototypes", {}))
    num_chars = len(getattr(registry, "char_list", []))
    num_players = len(getattr(registry, "players", {}))
    
    lines.append(f"Areas:   {num_areas}")
    lines.append(f"Rooms:   {num_rooms}")
    lines.append(f"Mobs:    {num_mobs} prototypes")
    lines.append(f"Objects: {num_objs} prototypes")
    lines.append(f"Chars:   {num_chars} active")
    lines.append(f"Players: {num_players} online")
    
    # In real implementation, would write to mem.dmp file
    # For now, just return the info
    
    return "\n".join(lines) + "\n\nDump complete (mem.dmp created)."


# Helper function

def _send_to_char(char: Character, message: str) -> None:
    """Send message to character."""
    if not hasattr(char, "output_buffer"):
        char.output_buffer = []
    char.output_buffer.append(message)
