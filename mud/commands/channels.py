"""
Channels command - list communication channels and their status.

ROM Reference: src/act_comm.c do_channels (lines 100-200)
"""
from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import CommFlag


# Channel definitions with their comm flags
_CHANNELS = [
    ("gossip", CommFlag.NOGOSSIP, "General chat channel"),
    ("auction", CommFlag.NOAUCTION, "Auction announcements"),
    ("music", CommFlag.NOMUSIC, "Music/songs channel"),
    ("question", CommFlag.NOQUESTION, "Newbie questions"),
    ("answer", CommFlag.NOQUESTION, "Answering newbie questions"),
    ("grats", CommFlag.NOGRATS, "Congratulations channel"),
    ("quote", CommFlag.NOQUOTE, "Quote of the day"),
    ("shout", CommFlag.NOSHOUT, "Shouting (area-wide)"),
    ("tell", CommFlag.NOTELL, "Private messages"),
]


def do_channels(char: Character, args: str) -> str:
    """
    Display available communication channels and their status.
    
    ROM Reference: src/act_comm.c do_channels (lines 100-200)
    
    Usage: channels
    """
    lines = ["Channel Status:"]
    lines.append("-" * 40)
    
    comm = getattr(char, "comm", 0)
    
    for channel_name, flag, description in _CHANNELS:
        if comm & flag:
            status = "[OFF]"
        else:
            status = "[ON] "
        
        lines.append(f"  {status} {channel_name:<12} - {description}")
    
    lines.append("")
    lines.append("Use the channel name to toggle it on/off.")
    lines.append("Example: 'gossip' to toggle gossip channel.")
    
    return "\n".join(lines)
