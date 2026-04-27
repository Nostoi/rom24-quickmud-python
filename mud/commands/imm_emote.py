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
from mud.models.constants import CommFlag

# ROM ``COMM_NOEMOTE`` lives in src/merc.h; the QuickMUD enum holds the truth.
COMM_NOEMOTE = int(CommFlag.NOEMOTE)


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


def _pmote_substitute(argument: str, name: str) -> str:
    """ROM ``do_pmote`` letter-by-letter substitution loop.

    Mirrors src/act_comm.c lines 1131-1175 exactly. Replaces each occurrence of
    ``name`` (case-sensitive, ROM uses ``strstr``) with "you"; turns a trailing
    ``'s`` into ``'r`` and absorbs a trailing plural ``s``.
    """
    # Mirrors the ROM block: detect first occurrence with strstr, then walk char
    # by char. We keep the same ``last`` pending-buffer semantics so partial
    # matches that diverge are flushed verbatim.
    letter_idx = argument.find(name)
    if letter_idx == -1:
        return argument

    # ``temp`` is the prefix up to the first ``letter`` position.
    temp = argument[:letter_idx]
    last = ""
    name_pos = 0  # index into name (== ROM ``name - vch->name``)
    matches = 0
    name_len = len(name)

    pos = letter_idx
    while pos < len(argument):
        ch = argument[pos]

        # ROM: if (*letter == '\'' && matches == strlen(vch->name)) -> "r"
        if ch == "'" and matches == name_len:
            temp += "r"
            pos += 1
            continue

        # ROM: if (*letter == 's' && matches == strlen(vch->name)) -> drop
        if ch == "s" and matches == name_len:
            matches = 0
            pos += 1
            continue

        # ROM: if (matches == strlen(vch->name)) matches = 0;
        if matches == name_len:
            matches = 0

        # ROM: if (*letter == *name)
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

        # Non-match: flush ``last``, append ``ch``, reset.
        matches = 0
        temp += last
        temp += ch
        last = ""
        name_pos = 0
        pos += 1

    return temp


def do_pmote(char: Character, args: str) -> str:
    """Possessive/pronoun-substituting emote.

    ROM Reference: src/act_comm.c do_pmote (lines 1098-1192).

    The argument is broadcast as ``"<actor> <argument>"`` to the actor and to
    every other player in the room, but for each viewer the actor's *and* their
    own name handling differs: viewers whose own name appears in the argument
    see it rewritten with ``you`` (and ``'s`` -> ``'r``, plural ``s``
    absorbed). Viewers without a name match see the unchanged argument.
    """
    # ROM C lines 1106-1110: NPCs bypass NOEMOTE; PCs cannot emote when flagged.
    if not getattr(char, "is_npc", False):
        comm_flags = getattr(char, "comm", 0) or 0
        if comm_flags & COMM_NOEMOTE:
            return "You can't show your emotions."

    if not args:
        return "Emote what?"

    # ROM C lines 1120-1124: ',{' guard.
    first = args[0]
    if not first.isalpha() or first.isspace():
        return "Moron!"

    char_name = getattr(char, "name", "Someone")

    # ROM C line 1126: act("$n $t", ch, argument, NULL, TO_CHAR)
    self_message = f"{char_name} {args}"
    _send_to_char(char, self_message)

    room = getattr(char, "room", None)
    if room:
        for viewer in getattr(room, "people", []):
            if viewer is char:
                continue
            # ROM C line 1131: skip viewers with no descriptor.
            if getattr(viewer, "desc", None) is None and not getattr(viewer, "is_npc", False):
                continue
            viewer_name = getattr(viewer, "name", "") or ""
            substituted = _pmote_substitute(args, viewer_name) if viewer_name else args
            _send_to_char(viewer, f"{char_name} {substituted}")

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
