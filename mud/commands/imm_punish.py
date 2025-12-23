"""
Immortal punishment commands - nochannels, noemote, noshout, notell, pardon, disconnect.

ROM Reference: src/act_wiz.c
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from mud.models.character import Character
from mud.commands.imm_commands import get_trust, get_char_world

if TYPE_CHECKING:
    pass


# Comm flags
COMM_NOCHANNELS = 0x00004000
COMM_NOEMOTE = 0x00008000
COMM_NOSHOUT = 0x00010000
COMM_NOTELL = 0x00020000

# Player flags
PLR_KILLER = 0x00000004
PLR_THIEF = 0x00000008


def do_nochannels(char: Character, args: str) -> str:
    """
    Toggle a player's ability to use channels.
    
    ROM Reference: src/act_wiz.c do_nochannels (lines 314-360)
    
    Usage: nochannels <player>
    """
    if not args or not args.strip():
        return "Nochannel whom?"
    
    target_name = args.strip().split()[0]
    victim = get_char_world(char, target_name)
    
    if victim is None:
        return "They aren't here."
    
    if get_trust(victim) >= get_trust(char):
        return "You failed."
    
    comm_flags = getattr(victim, "comm", 0)
    victim_name = getattr(victim, "name", "someone")
    
    if comm_flags & COMM_NOCHANNELS:
        victim.comm = comm_flags & ~COMM_NOCHANNELS
        _send_to_char(victim, "The gods have restored your channel priviliges.")
        return "NOCHANNELS removed."
    else:
        victim.comm = comm_flags | COMM_NOCHANNELS
        _send_to_char(victim, "The gods have revoked your channel priviliges.")
        return "NOCHANNELS set."


def do_noemote(char: Character, args: str) -> str:
    """
    Toggle a player's ability to use emote.
    
    ROM Reference: src/act_wiz.c do_noemote (lines 2986-3032)
    
    Usage: noemote <player>
    """
    if not args or not args.strip():
        return "Noemote whom?"
    
    target_name = args.strip().split()[0]
    victim = get_char_world(char, target_name)
    
    if victim is None:
        return "They aren't here."
    
    if get_trust(victim) >= get_trust(char):
        return "You failed."
    
    comm_flags = getattr(victim, "comm", 0)
    
    if comm_flags & COMM_NOEMOTE:
        victim.comm = comm_flags & ~COMM_NOEMOTE
        _send_to_char(victim, "You can emote again.")
        return "NOEMOTE removed."
    else:
        victim.comm = comm_flags | COMM_NOEMOTE
        _send_to_char(victim, "You can't emote!")
        return "NOEMOTE set."


def do_noshout(char: Character, args: str) -> str:
    """
    Toggle a player's ability to shout.
    
    ROM Reference: src/act_wiz.c do_noshout (lines 3034-3085)
    
    Usage: noshout <player>
    """
    if not args or not args.strip():
        return "Noshout whom?"
    
    target_name = args.strip().split()[0]
    victim = get_char_world(char, target_name)
    
    if victim is None:
        return "They aren't here."
    
    if getattr(victim, "is_npc", False):
        return "Not on NPC's."
    
    if get_trust(victim) >= get_trust(char):
        return "You failed."
    
    comm_flags = getattr(victim, "comm", 0)
    
    if comm_flags & COMM_NOSHOUT:
        victim.comm = comm_flags & ~COMM_NOSHOUT
        _send_to_char(victim, "You can shout again.")
        return "NOSHOUT removed."
    else:
        victim.comm = comm_flags | COMM_NOSHOUT
        _send_to_char(victim, "You can't shout!")
        return "NOSHOUT set."


def do_notell(char: Character, args: str) -> str:
    """
    Toggle a player's ability to use tell.
    
    ROM Reference: src/act_wiz.c do_notell (lines 3087-3130)
    
    Usage: notell <player>
    """
    if not args or not args.strip():
        return "Notell whom?"
    
    target_name = args.strip().split()[0]
    victim = get_char_world(char, target_name)
    
    if victim is None:
        return "They aren't here."
    
    if get_trust(victim) >= get_trust(char):
        return "You failed."
    
    comm_flags = getattr(victim, "comm", 0)
    
    if comm_flags & COMM_NOTELL:
        victim.comm = comm_flags & ~COMM_NOTELL
        _send_to_char(victim, "You can tell again.")
        return "NOTELL removed."
    else:
        victim.comm = comm_flags | COMM_NOTELL
        _send_to_char(victim, "You can't tell!")
        return "NOTELL set."


def do_pardon(char: Character, args: str) -> str:
    """
    Remove killer or thief flag from a player.
    
    ROM Reference: src/act_wiz.c do_pardon (lines 619-672)
    
    Usage: pardon <player> <killer|thief>
    """
    if not args or not args.strip():
        return "Syntax: pardon <character> <killer|thief>."
    
    parts = args.strip().split()
    if len(parts) < 2:
        return "Syntax: pardon <character> <killer|thief>."
    
    target_name = parts[0]
    flag_type = parts[1].lower()
    
    victim = get_char_world(char, target_name)
    if victim is None:
        return "They aren't here."
    
    if getattr(victim, "is_npc", False):
        return "Not on NPC's."
    
    act_flags = getattr(victim, "act", 0)
    
    if flag_type == "killer":
        if act_flags & PLR_KILLER:
            victim.act = act_flags & ~PLR_KILLER
            _send_to_char(victim, "You are no longer a KILLER.")
            return "Killer flag removed."
        return "They aren't a killer."
    
    if flag_type == "thief":
        if act_flags & PLR_THIEF:
            victim.act = act_flags & ~PLR_THIEF
            _send_to_char(victim, "You are no longer a THIEF.")
            return "Thief flag removed."
        return "They aren't a thief."
    
    return "Syntax: pardon <character> <killer|thief>."


def do_disconnect(char: Character, args: str) -> str:
    """
    Disconnect a player from the game.
    
    ROM Reference: src/act_wiz.c do_disconnect (lines 561-618)
    
    Usage:
    - disconnect <player>     - Disconnect by name
    - disconnect <desc_num>   - Disconnect by descriptor number
    """
    if not args or not args.strip():
        return "Disconnect whom?"
    
    arg = args.strip().split()[0]
    
    from mud import registry
    
    # Try numeric descriptor
    if arg.isdigit():
        desc_num = int(arg)
        for desc in getattr(registry, "descriptor_list", []):
            if getattr(desc, "descriptor", -1) == desc_num:
                _close_socket(desc)
                return "Ok."
        return "Descriptor not found!"
    
    # Try character name
    victim = get_char_world(char, arg)
    if victim is None:
        return "They aren't here."
    
    desc = getattr(victim, "desc", None)
    if desc is None:
        victim_name = getattr(victim, "name", "They")
        return f"{victim_name} doesn't have a descriptor."
    
    _close_socket(desc)
    return "Ok."


# Helper functions

def _send_to_char(char: Character, message: str) -> None:
    """Send message to character."""
    if not hasattr(char, "output_buffer"):
        char.output_buffer = []
    char.output_buffer.append(message)


def _close_socket(desc) -> None:
    """Close a descriptor socket (simplified)."""
    # In real implementation, would properly close the socket
    char = getattr(desc, "character", None)
    if char:
        char.desc = None
    desc.character = None
