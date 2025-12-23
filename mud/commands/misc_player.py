"""
Miscellaneous player commands - afk, replay, config.

ROM Reference: src/act_comm.c
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from mud.models.character import Character

if TYPE_CHECKING:
    pass


# Comm flags
COMM_AFK = 0x00000800


def do_afk(char: Character, args: str) -> str:
    """
    Toggle Away From Keyboard mode.
    
    ROM Reference: src/act_comm.c do_afk (lines 242-255)
    
    Usage: afk
    
    When AFK, tells are stored and can be viewed with 'replay'.
    """
    comm_flags = getattr(char, "comm", 0)
    
    if comm_flags & COMM_AFK:
        char.comm = comm_flags & ~COMM_AFK
        return "AFK mode removed. Type 'replay' to see tells."
    else:
        char.comm = comm_flags | COMM_AFK
        return "You are now in AFK mode."


def do_replay(char: Character, args: str) -> str:
    """
    Replay stored tells from AFK mode.
    
    ROM Reference: src/act_comm.c do_replay (lines 257-275)
    
    Usage: replay
    """
    if getattr(char, "is_npc", False):
        return "You can't replay."
    
    pcdata = getattr(char, "pcdata", None)
    if pcdata is None:
        return "You have no tells to replay."
    
    buffer = getattr(pcdata, "buffer", None)
    if buffer is None or not buffer:
        return "You have no tells to replay."
    
    # Return stored tells and clear buffer
    tells = "\n".join(buffer) if isinstance(buffer, list) else str(buffer)
    pcdata.buffer = []
    
    return tells if tells else "You have no tells to replay."


def do_config(char: Character, args: str) -> str:
    """
    Configure character options (display current settings).
    
    ROM Reference: Similar to autoall display
    
    Usage: config
    
    Shows current configuration settings.
    """
    if getattr(char, "is_npc", False):
        return "NPCs don't have configurations."
    
    lines = ["[ Keyword  ] Option"]
    lines.append("-" * 40)
    
    # Auto flags
    act_flags = getattr(char, "act", 0)
    comm_flags = getattr(char, "comm", 0)
    
    # Define config options
    configs = [
        ("autoassist", 0x00001000, act_flags, "You automatically assist group members."),
        ("autoexit", 0x00002000, act_flags, "You automatically see exits."),
        ("autogold", 0x00004000, act_flags, "You automatically loot gold from corpses."),
        ("autoloot", 0x00008000, act_flags, "You automatically loot corpses."),
        ("autosac", 0x00010000, act_flags, "You automatically sacrifice corpses."),
        ("autosplit", 0x00020000, act_flags, "You automatically split gold with group."),
        ("compact", 0x00000200, comm_flags, "You see no extra blank lines."),
        ("brief", 0x00000100, comm_flags, "You see brief room descriptions."),
        ("prompt", 0x00000400, comm_flags, "You have a prompt."),
        ("combine", 0x00001000, comm_flags, "You combine items in inventory."),
        ("afk", COMM_AFK, comm_flags, "You are Away From Keyboard."),
    ]
    
    for name, flag, flags, desc in configs:
        status = "ON" if flags & flag else "OFF"
        lines.append(f"[{name:^10s}] {status:<3s} - {desc if flags & flag else ''}")
    
    return "\n".join(lines)


def do_permit(char: Character, args: str) -> str:
    """
    Permit a follower to enter private areas with you.
    
    ROM Reference: src/act_move.c (follower permission)
    
    Usage: permit <character>
    """
    if not args or not args.strip():
        return "Permit whom to follow you?"
    
    target_name = args.strip().split()[0]
    
    # Find character in room
    room = getattr(char, "room", None)
    if not room:
        return "You're not in a room."
    
    victim = None
    for person in getattr(room, "people", []):
        if target_name.lower() in getattr(person, "name", "").lower():
            victim = person
            break
    
    if victim is None:
        return "They aren't here."
    
    if victim is char:
        return "You can't permit yourself."
    
    # Toggle permit flag
    permitted = getattr(char, "permitted", set())
    if not isinstance(permitted, set):
        permitted = set()
    
    victim_name = getattr(victim, "name", "someone")
    
    if victim in permitted:
        permitted.discard(victim)
        char.permitted = permitted
        return f"You no longer permit {victim_name} to follow you into private areas."
    else:
        permitted.add(victim)
        char.permitted = permitted
        return f"You permit {victim_name} to follow you into private areas."


def do_peek(char: Character, args: str) -> str:
    """
    Peek at someone's inventory (thief skill).
    
    ROM Reference: Similar to do_look but for inventory
    
    Usage: peek <character>
    
    Requires the peek skill to use effectively.
    """
    if not args or not args.strip():
        return "Peek at whom?"
    
    target_name = args.strip().split()[0]
    
    # Find character in room
    room = getattr(char, "room", None)
    if not room:
        return "You're not in a room."
    
    victim = None
    for person in getattr(room, "people", []):
        if target_name.lower() in getattr(person, "name", "").lower():
            victim = person
            break
    
    if victim is None:
        return "They aren't here."
    
    if victim is char:
        return "Why peek at yourself? Use 'inventory'."
    
    # Check peek skill
    peek_skill = _get_skill(char, "peek")
    
    if peek_skill < 1:
        return "You don't know how to peek."
    
    # Skill check
    from mud.core.dice import number_percent
    if number_percent() > peek_skill:
        return "You fail to get a good look."
    
    # Improve skill
    _check_improve(char, "peek", True)
    
    # Show inventory
    victim_name = getattr(victim, "name", "Someone")
    carrying = getattr(victim, "carrying", [])
    
    if not carrying:
        return f"{victim_name} is not carrying anything."
    
    lines = [f"You peek at {victim_name}'s inventory:"]
    for obj in carrying:
        obj_name = getattr(obj, "short_descr", "something")
        lines.append(f"  {obj_name}")
    
    return "\n".join(lines)


def do_unread(char: Character, args: str) -> str:
    """
    Show unread notes.
    
    ROM Reference: src/note.c
    
    Usage: unread
    """
    if getattr(char, "is_npc", False):
        return "NPCs can't read notes."
    
    from mud import registry
    
    # Get note boards
    boards = getattr(registry, "note_boards", {})
    if not boards:
        return "There are no note boards."
    
    lines = []
    total_unread = 0
    
    pcdata = getattr(char, "pcdata", None)
    last_read = getattr(pcdata, "last_read", {}) if pcdata else {}
    
    for board_name, notes in boards.items():
        last_time = last_read.get(board_name, 0)
        unread = sum(1 for note in notes if getattr(note, "timestamp", 0) > last_time)
        if unread > 0:
            lines.append(f"  {board_name}: {unread} unread note{'s' if unread != 1 else ''}")
            total_unread += unread
    
    if total_unread == 0:
        return "You have no unread notes."
    
    return f"Unread notes:\n" + "\n".join(lines)


# Helper functions

def _get_skill(char: Character, skill_name: str) -> int:
    """Get character's skill level."""
    pcdata = getattr(char, "pcdata", None)
    if pcdata is None:
        return 0
    
    learned = getattr(pcdata, "learned", {})
    
    from mud import registry
    for sn, skill in enumerate(getattr(registry, "skill_table", [])):
        if skill and getattr(skill, "name", "").lower() == skill_name.lower():
            return learned.get(sn, 0)
    
    return 0


def _check_improve(char: Character, skill_name: str, success: bool) -> None:
    """Check for skill improvement."""
    # Simplified - real implementation would have chance to improve
    pass
