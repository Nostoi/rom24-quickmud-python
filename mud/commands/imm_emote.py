"""
Advanced emote commands - smote, pmote, gecho.

ROM Reference: src/act_wiz.c, src/act_comm.c
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from mud.models.character import Character
from mud.commands.imm_commands import get_trust

if TYPE_CHECKING:
    pass


# Comm flags
COMM_NOEMOTE = 0x00008000


def do_smote(char: Character, args: str) -> str:
    """
    Self-referencing emote that substitutes your name with 'you' for the viewer.
    
    ROM Reference: src/act_wiz.c do_smote (lines 362-453)
    
    Usage: smote <action containing your name>
    
    Example: smote John waves at Mary.
    - John sees: "John waves at Mary."
    - Mary sees: "John waves at you."
    """
    # Check noemote flag
    if not getattr(char, "is_npc", False):
        comm_flags = getattr(char, "comm", 0)
        if comm_flags & COMM_NOEMOTE:
            return "You can't show your emotions."
    
    if not args or not args.strip():
        return "Emote what?"
    
    char_name = getattr(char, "name", "Someone")
    
    # Must include character's name
    if char_name.lower() not in args.lower():
        return "You must include your name in an smote."
    
    # Send to self
    _send_to_char(char, args)
    
    # Send to room, substituting viewer names with "you"
    room = getattr(char, "room", None)
    if room:
        for viewer in getattr(room, "people", []):
            if viewer is char:
                continue
            
            viewer_name = getattr(viewer, "name", "")
            message = args
            
            # Replace viewer's name with "you"
            if viewer_name and viewer_name.lower() in message.lower():
                # Case-insensitive replacement
                import re
                pattern = re.compile(re.escape(viewer_name), re.IGNORECASE)
                message = pattern.sub("you", message)
            
            _send_to_char(viewer, message)
    
    return ""


def do_pmote(char: Character, args: str) -> str:
    """
    Possessive emote - handles possessive pronouns correctly.
    
    ROM Reference: src/act_comm.c do_pmote (lines 1098-1180)
    
    Usage: pmote <action>
    
    Like smote but handles 's and s correctly.
    Example: pmote 's eyes gleam.
    - Others see: "John's eyes gleam."
    """
    # Check noemote flag
    if not getattr(char, "is_npc", False):
        comm_flags = getattr(char, "comm", 0)
        if comm_flags & COMM_NOEMOTE:
            return "You can't show your emotions."
    
    if not args or not args.strip():
        return "Emote what?"
    
    # Check first character
    if not args[0].isalpha():
        return "Moron!"
    
    char_name = getattr(char, "name", "Someone")
    
    # Format: "CharName <emote>"
    full_message = f"{char_name} {args}"
    
    # Send to self
    _send_to_char(char, full_message)
    
    # Send to room, substituting viewer names with "you"
    room = getattr(char, "room", None)
    if room:
        for viewer in getattr(room, "people", []):
            if viewer is char:
                continue
            
            viewer_name = getattr(viewer, "name", "")
            message = full_message
            
            # Replace viewer's name with "you"
            if viewer_name and viewer_name.lower() in message.lower():
                import re
                pattern = re.compile(re.escape(viewer_name), re.IGNORECASE)
                message = pattern.sub("you", message)
            
            _send_to_char(viewer, message)
    
    return ""


def do_gecho(char: Character, args: str) -> str:
    """
    Global echo - sends message to all players.
    
    ROM Reference: Similar to do_echo but specifically for global
    
    Usage: gecho <message>
    
    Sends to all players in the game.
    """
    if not args or not args.strip():
        return "Global echo what?"
    
    message = args.strip()
    
    from mud import registry
    
    for player in getattr(registry, "players", {}).values():
        _send_to_char(player, message)
    
    return ""


# Helper function

def _send_to_char(char: Character, message: str) -> None:
    """Send message to character."""
    if not hasattr(char, "output_buffer"):
        char.output_buffer = []
    char.output_buffer.append(message)
