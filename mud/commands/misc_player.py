"""
Miscellaneous player commands - afk, replay, config.

ROM Reference: src/act_comm.c
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mud.models.character import Character
from mud.models.constants import CommFlag, PlayerFlag
from mud.skills.registry import check_improve
from mud.utils.rng_mm import number_percent

if TYPE_CHECKING:
    pass


# Comm flag alias — preserved for backwards compat with callers that
# import this name. Canonical value lives in `CommFlag.AFK` (ROM Z = 1<<25).
COMM_AFK = int(CommFlag.AFK)


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

    # PARALLEL-001: the hex literals previously here did not match the
    # canonical IntEnum values the toggle commands set, so the display
    # always disagreed with the actual flag state. Use the enums directly.
    configs = [
        ("autoassist", int(PlayerFlag.AUTOASSIST), act_flags, "You automatically assist group members."),
        ("autoexit", int(PlayerFlag.AUTOEXIT), act_flags, "You automatically see exits."),
        ("autogold", int(PlayerFlag.AUTOGOLD), act_flags, "You automatically loot gold from corpses."),
        ("autoloot", int(PlayerFlag.AUTOLOOT), act_flags, "You automatically loot corpses."),
        ("autosac", int(PlayerFlag.AUTOSAC), act_flags, "You automatically sacrifice corpses."),
        ("autosplit", int(PlayerFlag.AUTOSPLIT), act_flags, "You automatically split gold with group."),
        ("compact", int(CommFlag.COMPACT), comm_flags, "You see no extra blank lines."),
        ("brief", int(CommFlag.BRIEF), comm_flags, "You see brief room descriptions."),
        ("prompt", int(CommFlag.PROMPT), comm_flags, "You have a prompt."),
        ("combine", int(CommFlag.COMBINE), comm_flags, "You combine items in inventory."),
        ("afk", int(CommFlag.AFK), comm_flags, "You are Away From Keyboard."),
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
        if target_name.lower() in (getattr(person, "name", None) or "").lower():
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
        if target_name.lower() in (getattr(person, "name", None) or "").lower():
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

    # Skill check — ROM src/act_info.c:502 (number_percent() < get_skill(...)).
    if number_percent() > peek_skill:
        return "You fail to get a good look."

    # ROM src/act_info.c:505 — check_improve(ch, gsn_peek, TRUE, 4).
    check_improve(char, "peek", True, multiplier=4)

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

    # INV-046 family 3b: boards live in mud.notes.board_registry (name → Board)
    # and the per-board read stamp in pcdata.last_notes (name → timestamp). The
    # old code read phantom registry.note_boards / pcdata.last_read, so unread
    # always reported "no note boards" in production.
    from mud.notes import board_registry

    if not board_registry:
        return "There are no note boards."

    lines = []
    total_unread = 0

    pcdata = getattr(char, "pcdata", None)
    last_read = getattr(pcdata, "last_notes", {}) if pcdata else {}

    for board_name, board in board_registry.items():
        last_time = last_read.get(board_name, 0)
        unread = sum(1 for note in board.notes if getattr(note, "timestamp", 0) > last_time)
        if unread > 0:
            lines.append(f"  {board_name}: {unread} unread note{'s' if unread != 1 else ''}")
            total_unread += unread

    if total_unread == 0:
        return "You have no unread notes."

    return "Unread notes:\n" + "\n".join(lines)


# Helper functions


def _get_skill(char: Character, skill_name: str) -> int:
    """Get character's learned percentage for a skill.

    INV-046 family 3b: the canonical learned store is ``char.skills`` (name-keyed),
    NOT a phantom skill-table attribute indexed into ``pcdata.learned[sn]`` —
    that combination read nothing in production, so ``peek`` (and any other gated
    skill) always resolved to 0.
    """
    skills = getattr(char, "skills", None)
    if not skills:
        return 0

    target = skill_name.lower()
    for name, value in skills.items():
        if name.lower() == target:
            return int(value or 0)

    return 0
