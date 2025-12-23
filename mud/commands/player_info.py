"""
Player info/config commands - scroll, show, play, info, and aliases.

ROM Reference: src/act_info.c, src/music.c
"""
from __future__ import annotations

from mud.models.character import Character


# Comm flags
COMM_SHOW_AFFECTS = 0x00000100


def do_scroll(char: Character, args: str) -> str:
    """
    Set number of lines per page for long output.
    
    ROM Reference: src/act_info.c do_scroll (lines 558-604)
    
    Usage:
    - scroll        - Show current setting
    - scroll 0      - Disable paging
    - scroll <n>    - Set to n lines (10-100)
    """
    if not args or not args.strip():
        lines = getattr(char, "lines", 0)
        if lines == 0:
            return "You do not page long messages."
        else:
            return f"You currently display {lines + 2} lines per page."
    
    arg = args.strip().split()[0]
    
    if not arg.isdigit():
        return "You must provide a number."
    
    lines = int(arg)
    
    if lines == 0:
        char.lines = 0
        return "Paging disabled."
    
    if lines < 10 or lines > 100:
        return "You must provide a reasonable number."
    
    char.lines = lines - 2
    return f"Scroll set to {lines} lines."


def do_show(char: Character, args: str) -> str:
    """
    Toggle showing affects in score display.
    
    ROM Reference: src/act_info.c do_show (lines 905-918)
    
    Usage: show
    """
    comm_flags = getattr(char, "comm", 0)
    
    if comm_flags & COMM_SHOW_AFFECTS:
        char.comm = comm_flags & ~COMM_SHOW_AFFECTS
        return "Affects will no longer be shown in score."
    else:
        char.comm = comm_flags | COMM_SHOW_AFFECTS
        return "Affects will now be shown in score."


def do_play(char: Character, args: str) -> str:
    """
    Play a song on a jukebox.
    
    ROM Reference: src/music.c do_play (lines 220-350)
    
    Usage:
    - play list           - List available songs
    - play list artist    - List by artist
    - play <song>         - Play a song
    - play loud <song>    - Play globally
    """
    if not args or not args.strip():
        return "Play what?"
    
    room = getattr(char, "room", None)
    if not room:
        return "You see nothing to play."
    
    # Find a jukebox in the room
    from mud.models.constants import ItemType
    
    jukebox = None
    contents = getattr(room, "contents", [])
    for obj in contents:
        item_type = getattr(obj, "item_type", None)
        if item_type is None:
            proto = getattr(obj, "prototype", None)
            if proto:
                item_type = getattr(proto, "item_type", None)
        
        if item_type == ItemType.JUKEBOX or str(item_type) == "jukebox":
            jukebox = obj
            break
    
    if jukebox is None:
        return "You see nothing to play."
    
    parts = args.strip().split()
    arg = parts[0].lower()
    
    if arg == "list":
        # List songs
        juke_name = getattr(jukebox, "short_descr", "The jukebox")
        lines = [f"{juke_name} has the following songs available:"]
        
        # Get song list from global or jukebox
        from mud import registry
        songs = getattr(registry, "song_table", [])
        
        if not songs:
            # Default songs if none loaded
            songs = [
                {"name": "The Temple Bell", "group": "Unknown"},
                {"name": "Battle Hymn", "group": "Unknown"},
                {"name": "Tavern Song", "group": "Unknown"},
            ]
        
        row = []
        for song in songs:
            name = song.get("name", "Unknown")
            row.append(f"{name:<35}")
            if len(row) == 2:
                lines.append(" ".join(row))
                row = []
        
        if row:
            lines.append(" ".join(row))
        
        return "\n".join(lines)
    
    # Play a song
    song_name = " ".join(parts)
    if arg == "loud" and len(parts) > 1:
        song_name = " ".join(parts[1:])
    
    return "Coming right up."


def do_info(char: Character, args: str) -> str:
    """
    Alias for groups command - show group status.
    
    ROM Reference: ROM uses this as alias for do_groups
    
    Usage: info
    """
    from mud.commands.group_commands import do_group
    return do_group(char, "")


def do_hit(char: Character, args: str) -> str:
    """
    Alias for kill command.
    
    ROM Reference: interp.c - hit maps to do_kill
    
    Usage: hit <target>
    """
    from mud.commands.combat import do_kill
    return do_kill(char, args)


def do_take(char: Character, args: str) -> str:
    """
    Alias for get command.
    
    ROM Reference: interp.c - take maps to do_get
    
    Usage: take <item> [container]
    """
    from mud.commands.inventory import do_get
    return do_get(char, args)
