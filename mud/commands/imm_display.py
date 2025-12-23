"""
Immortal display commands - invis, wizinvis, poofin, poofout, echo.

ROM Reference: src/act_wiz.c
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from mud.models.character import Character
from mud.commands.imm_commands import get_trust

if TYPE_CHECKING:
    pass


def do_invis(char: Character, args: str) -> str:
    """
    Toggle wizard invisibility or set to specific level.
    
    ROM Reference: src/act_wiz.c do_invis (lines 4329-4375)
    
    Usage:
    - invis         - Toggle invisibility on/off
    - invis <level> - Set invisibility to specific level
    """
    invis_level = getattr(char, "invis_level", 0)
    
    if not args or not args.strip():
        # Toggle
        if invis_level:
            char.invis_level = 0
            return "You slowly fade back into existence."
        else:
            char.invis_level = get_trust(char)
            return "You slowly vanish into thin air."
    
    # Set specific level
    arg = args.strip().split()[0]
    if not arg.isdigit():
        return "Invis level must be a number."
    
    level = int(arg)
    if level < 2 or level > get_trust(char):
        return "Invis level must be between 2 and your level."
    
    char.invis_level = level
    char.reply = None  # Clear reply target
    return "You slowly vanish into thin air."


def do_wizinvis(char: Character, args: str) -> str:
    """
    Alias for invis command.
    
    ROM Reference: interp.c - wizinvis maps to do_invis
    """
    return do_invis(char, args)


def do_incognito(char: Character, args: str) -> str:
    """
    Toggle incognito mode (hidden from who/where but visible in room).
    
    ROM Reference: src/act_wiz.c do_incognito (lines 4377-4420)
    
    Usage:
    - incognito         - Toggle incognito on/off
    - incognito <level> - Set incognito to specific level
    """
    incog_level = getattr(char, "incog_level", 0)
    
    if not args or not args.strip():
        # Toggle
        if incog_level:
            char.incog_level = 0
            return "You are no longer cloaked."
        else:
            char.incog_level = get_trust(char)
            return "You cloak your presence."
    
    # Set specific level
    arg = args.strip().split()[0]
    if not arg.isdigit():
        return "Incognito level must be a number."
    
    level = int(arg)
    if level < 2 or level > get_trust(char):
        return "Incognito level must be between 2 and your level."
    
    char.incog_level = level
    return "You cloak your presence."


def do_poofin(char: Character, args: str) -> str:
    """
    Set or view your arrival message (shown when you goto).
    
    ROM Reference: src/act_wiz.c do_bamfin (lines 455-483)
    
    Usage:
    - poofin              - View current poofin
    - poofin <message>    - Set poofin (must include your name)
    """
    if getattr(char, "is_npc", False):
        return ""
    
    pcdata = getattr(char, "pcdata", None)
    if pcdata is None:
        return ""
    
    if not args or not args.strip():
        bamfin = getattr(pcdata, "bamfin", "$n appears in a swirling mist.")
        return f"Your poofin is {bamfin}"
    
    message = args.strip()
    char_name = getattr(char, "name", "")
    
    # Must include character's name
    if char_name.lower() not in message.lower():
        return "You must include your name."
    
    pcdata.bamfin = message
    return f"Your poofin is now {message}"


def do_poofout(char: Character, args: str) -> str:
    """
    Set or view your departure message (shown when you goto).
    
    ROM Reference: src/act_wiz.c do_bamfout (lines 485-513)
    
    Usage:
    - poofout              - View current poofout
    - poofout <message>    - Set poofout (must include your name)
    """
    if getattr(char, "is_npc", False):
        return ""
    
    pcdata = getattr(char, "pcdata", None)
    if pcdata is None:
        return ""
    
    if not args or not args.strip():
        bamfout = getattr(pcdata, "bamfout", "$n leaves in a swirling mist.")
        return f"Your poofout is {bamfout}"
    
    message = args.strip()
    char_name = getattr(char, "name", "")
    
    # Must include character's name
    if char_name.lower() not in message.lower():
        return "You must include your name."
    
    pcdata.bamfout = message
    return f"Your poofout is now {message}"


def do_echo(char: Character, args: str) -> str:
    """
    Echo a message globally to all players.
    
    ROM Reference: src/act_wiz.c do_echo (lines 674-695)
    
    Usage: echo <message>
    
    Note: Higher-trust immortals see "global>" prefix.
    """
    if not args or not args.strip():
        return "Global echo what?"
    
    message = args.strip()
    
    from mud import registry
    for player in getattr(registry, "players", {}).values():
        if get_trust(player) >= get_trust(char):
            _send_to_char(player, f"global> {message}")
        else:
            _send_to_char(player, message)
    
    return ""  # Already echoed


def do_recho(char: Character, args: str) -> str:
    """
    Echo a message to everyone in the room.
    
    ROM Reference: src/act_wiz.c do_recho (lines 697-720)
    
    Usage: recho <message>
    """
    if not args or not args.strip():
        return "Local echo what?"
    
    message = args.strip()
    room = getattr(char, "room", None)
    
    if not room:
        return "You're not in a room."
    
    for person in getattr(room, "people", []):
        if get_trust(person) >= get_trust(char):
            _send_to_char(person, f"local> {message}")
        else:
            _send_to_char(person, message)
    
    return ""  # Already echoed


def do_zecho(char: Character, args: str) -> str:
    """
    Echo a message to everyone in the same area.
    
    ROM Reference: src/act_wiz.c do_zecho (lines 722-750)
    
    Usage: zecho <message>
    """
    if not args or not args.strip():
        return "Zone echo what?"
    
    message = args.strip()
    room = getattr(char, "room", None)
    
    if not room:
        return "You're not in a room."
    
    area = getattr(room, "area", None)
    if not area:
        return "You're not in an area."
    
    from mud import registry
    for player in getattr(registry, "players", {}).values():
        p_room = getattr(player, "room", None)
        if p_room and getattr(p_room, "area", None) is area:
            if get_trust(player) >= get_trust(char):
                _send_to_char(player, f"zone> {message}")
            else:
                _send_to_char(player, message)
    
    return ""  # Already echoed


def do_pecho(char: Character, args: str) -> str:
    """
    Echo a message to a specific player.
    
    ROM Reference: src/act_wiz.c do_pecho (lines 752-780)
    
    Usage: pecho <player> <message>
    """
    if not args or not args.strip():
        return "Personal echo what?"
    
    parts = args.strip().split(None, 1)
    if len(parts) < 2:
        return "Personal echo what?"
    
    target_name = parts[0]
    message = parts[1]
    
    from mud.commands.imm_commands import get_char_world
    victim = get_char_world(char, target_name)
    
    if victim is None:
        return "They aren't here."
    
    if get_trust(victim) >= get_trust(char) and victim is not char:
        _send_to_char(victim, f"personal> {message}")
    else:
        _send_to_char(victim, message)
    
    return "Ok."


# Helper function

def _send_to_char(char: Character, message: str) -> None:
    """Send message to character."""
    if not hasattr(char, "output_buffer"):
        char.output_buffer = []
    char.output_buffer.append(message)
