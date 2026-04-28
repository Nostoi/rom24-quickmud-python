"""
Immortal display commands - invis, wizinvis, poofin, poofout, echo.

ROM Reference: src/act_wiz.c
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mud.commands.imm_commands import get_trust
from mud.models.character import Character

if TYPE_CHECKING:
    pass


def do_invis(char: Character, args: str) -> str:
    """
    Toggle wizard invisibility or set to specific level.

    ROM Reference: src/act_wiz.c:4329-4373
    """
    invis_level = getattr(char, "invis_level", 0)

    if not args or not args.strip():
        if invis_level:
            char.invis_level = 0
            _act_room(char, "$n slowly fades back into existence.", do_not_see_char=True)
            return "You slowly fade back into existence.\n\r"

        char.invis_level = get_trust(char)
        _act_room(char, "$n slowly fades into thin air.", do_not_see_char=True)
        return "You slowly vanish into thin air.\n\r"

    arg = args.strip().split()[0]
    if not arg.isdigit():
        return "Invis level must be a number.\n\r"

    level = int(arg)
    if level < 2 or level > get_trust(char):
        return "Invis level must be between 2 and your level.\n\r"

    char.invis_level = level
    char.reply = None
    return "You slowly vanish into thin air.\n\r"


def do_wizinvis(char: Character, args: str) -> str:
    """Alias for invis command."""
    return do_invis(char, args)


def do_incognito(char: Character, args: str) -> str:
    """
    Toggle incognito mode (hidden from who/where but visible in room).

    ROM Reference: src/act_wiz.c:4375-4420
    """
    incog_level = getattr(char, "incog_level", 0)

    if not args or not args.strip():
        if incog_level:
            char.incog_level = 0
            return "You are no longer cloaked.\n\r"

        char.incog_level = get_trust(char)
        _act_room(char, "$n cloaks $s presence.", do_not_see_char=True)
        return "You cloak your presence.\n\r"

    arg = args.strip().split()[0]
    if not arg.isdigit():
        return "Incognito level must be a number.\n\r"

    level = int(arg)
    if level < 2 or level > get_trust(char):
        return "Incognito level must be between 2 and your level.\n\r"

    char.incog_level = level
    char.reply = None
    return "You cloak your presence.\n\r"


def do_poofin(char: Character, args: str) -> str:
    """
    Set or view your arrival message (shown when you goto).

    ROM Reference: src/act_wiz.c:455-483
    """
    if getattr(char, "is_npc", False):
        return ""

    pcdata = getattr(char, "pcdata", None)
    if pcdata is None:
        return ""

    # mirrors ROM src/act_wiz.c:458-468 — smash_tilde, then check empty
    from mud.utils.text import smash_tilde

    args = smash_tilde(args) if args else args

    if not args or not args.strip():
        bamfin = getattr(pcdata, "bamfin", "$n appears in a swirling mist.")
        return f"Your poofin is {bamfin}\n\r"

    # mirrors ROM src/act_wiz.c:470 — strstr(name, argument) case-sensitive check
    char_name = getattr(char, "name", "")
    if char_name and char_name not in args:
        return "You must include your name.\n\r"

    pcdata.bamfin = args.strip()
    return f"Your poofin is now {pcdata.bamfin}\n\r"


def do_poofout(char: Character, args: str) -> str:
    """
    Set or view your departure message (shown when you goto).

    ROM Reference: src/act_wiz.c:485-512
    """
    if getattr(char, "is_npc", False):
        return ""

    pcdata = getattr(char, "pcdata", None)
    if pcdata is None:
        return ""

    # mirrors ROM src/act_wiz.c:491 — smash_tilde
    from mud.utils.text import smash_tilde

    args = smash_tilde(args) if args else args

    if not args or not args.strip():
        bamfout = getattr(pcdata, "bamfout", "$n leaves in a swirling mist.")
        return f"Your poofout is {bamfout}\n\r"

    # mirrors ROM src/act_wiz.c:500 — strstr name check
    char_name = getattr(char, "name", "")
    if char_name and char_name not in args:
        return "You must include your name.\n\r"

    pcdata.bamfout = args.strip()
    return f"Your poofout is now {pcdata.bamfout}\n\r"


def do_echo(char: Character, args: str) -> str:
    """
    Echo a message globally to all connected players.

    ROM Reference: src/act_wiz.c:674-695

    Iterates descriptor_list, sends to CON_PLAYING descriptors.
    Higher-trust immortals see "global>" prefix.
    """
    if not args or not args.strip():
        return "Global echo what?\n\r"

    message = args.strip()

    from mud import registry

    CON_PLAYING = 1
    for desc in getattr(registry, "descriptor_list", []):
        d_char = getattr(desc, "character", None)
        if d_char is None:
            continue
        connected = getattr(desc, "connected", 0)
        if connected != CON_PLAYING:
            continue
        if get_trust(d_char) >= get_trust(char):
            _send_to_char(d_char, f"global> {message}\n\r")
        else:
            _send_to_char(d_char, f"{message}\n\r")

    return ""


def do_recho(char: Character, args: str) -> str:
    """
    Echo a message to everyone in the same room.

    ROM Reference: src/act_wiz.c:700-724

    Iterates descriptor_list, matches room, CON_PLAYING only.
    Higher-trust immortals see "local>" prefix.
    """
    if not args or not args.strip():
        return "Local echo what?\n\r"

    message = args.strip()
    room = getattr(char, "room", None)
    if not room:
        return ""

    from mud import registry

    CON_PLAYING = 1
    for desc in getattr(registry, "descriptor_list", []):
        d_char = getattr(desc, "character", None)
        if d_char is None:
            continue
        connected = getattr(desc, "connected", 0)
        if connected != CON_PLAYING:
            continue
        d_room = getattr(d_char, "in_room", None) or getattr(d_char, "room", None)
        if d_room is not None and d_room is room:
            if get_trust(d_char) >= get_trust(char):
                _send_to_char(d_char, f"local> {message}\n\r")
            else:
                _send_to_char(d_char, f"{message}\n\r")

    return ""


def do_zecho(char: Character, args: str) -> str:
    """
    Echo a message to everyone in the same area/zone.

    ROM Reference: src/act_wiz.c:726-748

    Iterates descriptor_list, matches area, CON_PLAYING only.
    Higher-trust immortals see "zone>" prefix.
    """
    if not args or not args.strip():
        return "Zone echo what?\n\r"

    message = args.strip()
    room = getattr(char, "room", None)
    if not room:
        return ""

    area = getattr(room, "area", None)

    from mud import registry

    CON_PLAYING = 1
    for desc in getattr(registry, "descriptor_list", []):
        d_char = getattr(desc, "character", None)
        if d_char is None:
            continue
        connected = getattr(desc, "connected", 0)
        if connected != CON_PLAYING:
            continue
        d_room = getattr(d_char, "in_room", None) or getattr(d_char, "room", None)
        if d_room is None:
            continue
        d_area = getattr(d_room, "area", None)
        if area is not None and d_area is area:
            if get_trust(d_char) >= get_trust(char):
                _send_to_char(d_char, f"zone> {message}\n\r")
            else:
                _send_to_char(d_char, f"{message}\n\r")

    return ""


def do_pecho(char: Character, args: str) -> str:
    """
    Echo a message to a specific player.

    ROM Reference: src/act_wiz.c:750-777

    Usage: pecho <player> <message>
    """
    if not args or not args.strip():
        return "Personal echo what?\n\r"

    parts = args.strip().split(None, 1)
    if len(parts) < 2:
        return "Personal echo what?\n\r"

    target_name = parts[0]
    message = parts[1]

    from mud.commands.imm_commands import get_char_world

    victim = get_char_world(char, target_name)

    if victim is None:
        return "Target not found.\n\r"

    # mirrors ROM src/act_wiz.c:769 — higher-trust targets see "personal>" prefix
    max_level = 65
    if get_trust(victim) >= get_trust(char) and get_trust(char) != max_level:
        _send_to_char(victim, f"personal> {message}\n\r")
    else:
        _send_to_char(victim, f"{message}\n\r")

    _send_to_char(char, f"personal> {message}\n\r")
    return ""


# Helper function


def _send_to_char(char: Character, message: str) -> None:
    """Send message to character."""
    if not hasattr(char, "output_buffer"):
        char.output_buffer = []
    char.output_buffer.append(message)


def _act_room(char: Character, message: str, *, do_not_see_char: bool = False) -> None:
    """Send a message to all other characters in char's room.

    ROM C uses act() with TO_ROOM for this. This is a simplified version
    that sends the message (with $n/$s/$e substitution) to room occupants.

    Args:
        char: The source character (used for $n substitution).
        message: Message with $n for char name, $s for char possessive.
        do_not_see_char: If True, also shows the message to char (for
            invis fade-in/fade-out where others see it).
    """
    from mud.world.vision import can_see_character

    room = getattr(char, "room", None)
    if not room:
        return

    char_name = getattr(char, "name", "someone")
    display_msg = message.replace("$n", char_name).replace("$s", f"{char_name}'s").replace("$e", char_name)

    for person in getattr(room, "people", []):
        if person is char and do_not_see_char:
            continue
        if can_see_character(person, char):
            _send_to_char(person, f"{display_msg}\n\r")
