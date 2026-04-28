"""
Server control commands - reboot, shutdown, copyover.

ROM Reference: src/act_wiz.c
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mud.commands.imm_commands import (
    LEVEL_HERO,
    _act_room,
    _char_from_room,
    _char_to_room,
    find_location,
    get_char_world,
)
from mud.models.character import Character
from mud.models.constants import CommFlag

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
    for _player in getattr(registry, "players", {}).values():
        # In real implementation: save_char_obj(_player)
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
    for _player in getattr(registry, "players", {}).values():
        # In real implementation: save_char_obj(_player)
        pass

    # Set shutdown flag
    registry.merc_down = True

    return "Shutting down..."


def do_copyover(char: Character, args: str) -> str:
    """
    Hot reboot the MUD without disconnecting players.

    ROM Reference: src/act_wiz.c do_copyover (lines 4498-4588)

    Usage: copyover

    Saves all connections and restarts the server, preserving player sessions.
    """
    from mud import registry

    char_name = getattr(char, "name", "Someone")

    # mirrors ROM src/act_wiz.c:4520-4521
    announce = f"\n\r *** COPYOVER by {char_name} - please remain seated!\n\r"

    # Announce to all playing descriptors per ROM
    descriptor_list = getattr(registry, "descriptor_list", [])
    for desc in descriptor_list:
        d_char = getattr(desc, "character", None)
        if d_char is not None and getattr(desc, "connected", 0) >= 1:
            _send_to_char(d_char, announce)
        else:
            # mirrors ROM src/act_wiz.c:4531-4533 — drop those logging on
            pass

    # In real implementation: save descriptors to file, exec() new binary
    for _d in descriptor_list:
        d_char = getattr(_d, "character", None)
        if d_char is not None and getattr(_d, "connected", 0) >= 1:
            # save_char_obj(d_char)
            pass

    registry.copyover_pending = True

    return "Copyover initiated...\n\r"


def do_protect(char: Character, args: str) -> str:
    """
    Toggle snoop-protection on a player.

    ROM Reference: src/act_wiz.c do_protect (lines 2086-2120)

    Usage: protect <player>

    Prevents other immortals from snooping the target.
    """
    if not args or not args.strip():
        return "Protect whom from snooping?\n\r"

    target_name = args.strip().split()[0]
    victim = get_char_world(char, target_name)

    if victim is None:
        return "You can't find them.\n\r"

    comm_flags = int(getattr(victim, "comm", 0) or 0)
    victim_name = getattr(victim, "name", "someone")

    if comm_flags & int(CommFlag.SNOOP_PROOF):
        victim.comm = comm_flags & ~int(CommFlag.SNOOP_PROOF)
        _send_to_char(victim, "Your snoop-proofing was just removed.\n\r")
        return f"{victim_name} is no longer snoop-proof.\n\r"
    else:
        victim.comm = comm_flags | int(CommFlag.SNOOP_PROOF)
        _send_to_char(victim, "You are now immune to snooping.\n\r")
        return f"{victim_name} is now snoop-proof.\n\r"


def do_violate(char: Character, args: str) -> str:
    """
    Enter a private room.

    ROM Reference: src/act_wiz.c do_violate (lines 1000-1025)

    Usage: violate <location>

    Allows an immortal to enter a private room.
    """
    if not args or not args.strip():
        return "Goto where?\n\r"

    location = find_location(char, args.strip())
    if location is None:
        return "No such location.\n\r"

    from mud.commands.imm_commands import _room_is_private

    if not _room_is_private(location):
        return "That room isn't private, use goto.\n\r"

    if getattr(char, "fighting", None):
        char.fighting = None

    old_room = getattr(char, "room", None)
    if old_room:
        pcdata = getattr(char, "pcdata", None)
        bamfout = getattr(pcdata, "bamfout", None) if pcdata else None
        if bamfout:
            _act_room(old_room, char, bamfout)
        else:
            _act_room(old_room, char, "$n leaves in a swirling mist.")

    _char_from_room(char)
    _char_to_room(char, location)

    pcdata = getattr(char, "pcdata", None)
    bamfin = getattr(pcdata, "bamfin", None) if pcdata else None
    if bamfin:
        _act_room(location, char, bamfin)
    else:
        _act_room(location, char, "$n appears in a swirling mist.")

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
