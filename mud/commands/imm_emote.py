"""
Advanced emote commands - smote, pmote, gecho.

ROM Reference: src/act_wiz.c, src/act_comm.c
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mud.models.character import Character

if TYPE_CHECKING:
    pass


# Comm flags
from mud.models.constants import CommFlag

# ROM ``COMM_NOEMOTE`` lives in src/merc.h; the QuickMUD enum holds the truth.
COMM_NOEMOTE = int(CommFlag.NOEMOTE)


def do_smote(char: Character, args: str) -> str:
    # mirrors ROM src/act_wiz.c:362-453
    if not getattr(char, "is_npc", False):
        comm_flags = getattr(char, "comm", 0)
        if comm_flags & COMM_NOEMOTE:
            return "You can't show your emotions.\n\r"

    if not args or not args.strip():
        return "Emote what?\n\r"

    char_name = getattr(char, "name", "Someone")
    if char_name not in args:
        return "You must include your name in an smote.\n\r"

    _send_to_char(char, f"{args}\n\r")

    room = getattr(char, "room", None)
    if not room:
        return ""

    for viewer in getattr(room, "people", []):
        # mirrors ROM src/act_wiz.c:392-393 — skip self and no-descriptor
        if viewer is char:
            continue
        if getattr(viewer, "desc", None) is None and not getattr(viewer, "is_npc", False):
            continue

        message = args
        viewer_name = getattr(viewer, "name", "")
        if viewer_name and viewer_name in message:
            message = _smote_substitute(message, viewer_name)
        _send_to_char(viewer, f"{message}\n\r")

    return ""


def _smote_substitute(argument: str, name: str) -> str:
    """ROM ``do_smote`` letter-by-letter substitution loop.

    Mirrors src/act_wiz.c:395-446 exactly.
    """
    letter_idx = argument.find(name)
    if letter_idx == -1:
        return argument

    temp = argument[:letter_idx]
    last = ""
    name_pos = 0
    matches = 0
    name_len = len(name)

    pos = letter_idx
    while pos < len(argument):
        ch = argument[pos]

        if ch == "'" and matches == name_len:
            temp += "r"
            pos += 1
            continue

        if ch == "s" and matches == name_len:
            matches = 0
            pos += 1
            continue

        if matches == name_len:
            matches = 0

        if name_pos < name_len and ch == name[name_pos]:
            matches += 1
            name_pos += 1
            if matches == name_len:
                temp += "you"
                last = ""
                name_pos = 0
                pos += 1
                continue
            last += ch
            pos += 1
            continue

        matches = 0
        temp += last
        temp += ch
        last = ""
        name_pos = 0
        pos += 1

    return temp


def _pmote_substitute(argument: str, name: str) -> str:
    """ROM ``do_pmote`` letter-by-letter substitution loop.

    Mirrors src/act_comm.c lines 1131-1175 exactly.
    """
    letter_idx = argument.find(name)
    if letter_idx == -1:
        return argument

    temp = argument[:letter_idx]
    last = ""
    name_pos = 0
    matches = 0
    name_len = len(name)

    pos = letter_idx
    while pos < len(argument):
        ch = argument[pos]

        if ch == "'" and matches == name_len:
            temp += "r"
            pos += 1
            continue

        if ch == "s" and matches == name_len:
            matches = 0
            pos += 1
            continue

        if matches == name_len:
            matches = 0

        if name_pos < name_len and ch == name[name_pos]:
            matches += 1
            name_pos += 1
            if matches == name_len:
                temp += "you"
                last = ""
                name_pos = 0
                pos += 1
                continue
            last += ch
            pos += 1
            continue

        matches = 0
        temp += last
        temp += ch
        last = ""
        name_pos = 0
        pos += 1

    return temp


def do_pmote(char: Character, args: str) -> str:
    # mirrors ROM src/act_comm.c:1098-1192
    if not getattr(char, "is_npc", False):
        comm_flags = getattr(char, "comm", 0) or 0
        if comm_flags & COMM_NOEMOTE:
            return "You can't show your emotions.\n\r"

    if not args:
        return "Emote what?\n\r"

    # ROM C lines 1120-1124: ',{' guard.
    first = args[0]
    if not first.isalpha() or first.isspace():
        return "Moron!\n\r"

    char_name = getattr(char, "name", "Someone")
    self_message = f"{char_name} {args}"
    _send_to_char(char, f"{self_message}\n\r")

    room = getattr(char, "room", None)
    if room:
        for viewer in getattr(room, "people", []):
            if viewer is char:
                continue
            if getattr(viewer, "desc", None) is None and not getattr(viewer, "is_npc", False):
                continue
            viewer_name = getattr(viewer, "name", "") or ""
            substituted = _pmote_substitute(args, viewer_name) if viewer_name else args
            _send_to_char(viewer, f"{char_name} {substituted}\n\r")

    return ""


def do_gecho(char: Character, args: str) -> str:
    if not args or not args.strip():
        return "Global echo what?\n\r"

    message = args.strip()

    from mud import registry

    for player in getattr(registry, "players", {}).values():
        _send_to_char(player, f"{message}\n\r")

    return ""


def _send_to_char(char: Character, message: str) -> None:
    """Send message to character."""
    if not hasattr(char, "output_buffer"):
        char.output_buffer = []
    char.output_buffer.append(message)
