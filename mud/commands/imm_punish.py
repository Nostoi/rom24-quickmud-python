"""
Immortal punishment commands - nochannels, noemote, noshout, notell, pardon, disconnect.

ROM Reference: src/act_wiz.c
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from mud.models.character import Character
from mud.models.constants import CommFlag, PlayerFlag
from mud.commands.imm_commands import get_trust, get_char_world

if TYPE_CHECKING:
    pass


def do_nochannels(char: Character, args: str) -> str:
    """
    Toggle a player's ability to use channels.

    ROM Reference: src/act_wiz.c:314-359
    """
    if not args or not args.strip():
        return "Nochannel whom?\n\r"

    target_name = args.strip().split()[0]
    victim = get_char_world(char, target_name)

    if victim is None:
        return "They aren't here.\n\r"

    if get_trust(victim) >= get_trust(char):
        return "You failed.\n\r"

    comm_flags = int(getattr(victim, "comm", 0))

    if comm_flags & int(CommFlag.NOCHANNELS):
        victim.comm = comm_flags & ~int(CommFlag.NOCHANNELS)
        _send_to_char(victim, "The gods have restored your channel priviliges.\n\r")
        from mud.wiznet import wiznet, WiznetFlag
        wiznet(f"$N restores channels to {victim.name}", char, None, WiznetFlag.WIZ_PENALTIES, WiznetFlag.WIZ_SECURE, 0)
        return "NOCHANNELS removed.\n\r"

    victim.comm = comm_flags | int(CommFlag.NOCHANNELS)
    _send_to_char(victim, "The gods have revoked your channel priviliges.\n\r")
    from mud.wiznet import wiznet, WiznetFlag
    wiznet(f"$N revokes {victim.name}'s channels.", char, None, WiznetFlag.WIZ_PENALTIES, WiznetFlag.WIZ_SECURE, 0)
    return "NOCHANNELS set.\n\r"


def do_noemote(char: Character, args: str) -> str:
    """
    Toggle a player's ability to use emote.

    ROM Reference: src/act_wiz.c:2986-3032
    """
    if not args or not args.strip():
        return "Noemote whom?\n\r"

    target_name = args.strip().split()[0]
    victim = get_char_world(char, target_name)

    if victim is None:
        return "They aren't here.\n\r"

    if get_trust(victim) >= get_trust(char):
        return "You failed.\n\r"

    comm_flags = int(getattr(victim, "comm", 0))

    if comm_flags & int(CommFlag.NOEMOTE):
        victim.comm = comm_flags & ~int(CommFlag.NOEMOTE)
        _send_to_char(victim, "You can emote again.\n\r")
        from mud.wiznet import wiznet, WiznetFlag
        wiznet(f"$N allows {victim.name} to emote.", char, None, WiznetFlag.WIZ_PENALTIES, WiznetFlag.WIZ_SECURE, 0)
        return "NOEMOTE removed.\n\r"

    victim.comm = comm_flags | int(CommFlag.NOEMOTE)
    _send_to_char(victim, "You can't emote!\n\r")
    from mud.wiznet import wiznet, WiznetFlag
    wiznet(f"$N stops {victim.name} from emoting.", char, None, WiznetFlag.WIZ_PENALTIES, WiznetFlag.WIZ_SECURE, 0)
    return "NOEMOTE set.\n\r"


def do_noshout(char: Character, args: str) -> str:
    """
    Toggle a player's ability to shout.

    ROM Reference: src/act_wiz.c:3034-3085
    """
    if not args or not args.strip():
        return "Noshout whom?\n\r"

    target_name = args.strip().split()[0]
    victim = get_char_world(char, target_name)

    if victim is None:
        return "They aren't here.\n\r"

    if getattr(victim, "is_npc", False):
        return "Not on NPC's.\n\r"

    if get_trust(victim) >= get_trust(char):
        return "You failed.\n\r"

    comm_flags = int(getattr(victim, "comm", 0))

    if comm_flags & int(CommFlag.NOSHOUT):
        victim.comm = comm_flags & ~int(CommFlag.NOSHOUT)
        _send_to_char(victim, "You can shout again.\n\r")
        from mud.wiznet import wiznet, WiznetFlag
        wiznet(f"$N allows {victim.name} to shout.", char, None, WiznetFlag.WIZ_PENALTIES, WiznetFlag.WIZ_SECURE, 0)
        return "NOSHOUT removed.\n\r"

    victim.comm = comm_flags | int(CommFlag.NOSHOUT)
    _send_to_char(victim, "You can't shout!\n\r")
    from mud.wiznet import wiznet, WiznetFlag
    wiznet(f"$N stops {victim.name} from shouting.", char, None, WiznetFlag.WIZ_PENALTIES, WiznetFlag.WIZ_SECURE, 0)
    return "NOSHOUT set.\n\r"


def do_notell(char: Character, args: str) -> str:
    """
    Toggle a player's ability to use tell.

    ROM Reference: src/act_wiz.c:3087-3132
    """
    if not args or not args.strip():
        return "Notell whom?\n\r"

    target_name = args.strip().split()[0]
    victim = get_char_world(char, target_name)

    if victim is None:
        return "They aren't here.\n\r"

    if get_trust(victim) >= get_trust(char):
        return "You failed.\n\r"

    comm_flags = int(getattr(victim, "comm", 0))

    if comm_flags & int(CommFlag.NOTELL):
        victim.comm = comm_flags & ~int(CommFlag.NOTELL)
        _send_to_char(victim, "You can tell again.\n\r")
        from mud.wiznet import wiznet, WiznetFlag
        wiznet(f"$N allows {victim.name} to tell.", char, None, WiznetFlag.WIZ_PENALTIES, WiznetFlag.WIZ_SECURE, 0)
        return "NOTELL removed.\n\r"

    victim.comm = comm_flags | int(CommFlag.NOTELL)
    _send_to_char(victim, "You can't tell!\n\r")
    from mud.wiznet import wiznet, WiznetFlag
    wiznet(f"$N stops {victim.name} from telling.", char, None, WiznetFlag.WIZ_PENALTIES, WiznetFlag.WIZ_SECURE, 0)
    return "NOTELL set.\n\r"


def do_pardon(char: Character, args: str) -> str:
    """
    Remove killer or thief flag from a player.

    ROM Reference: src/act_wiz.c:619-670
    """
    if not args or not args.strip():
        return "Syntax: pardon <character> <killer|thief>.\n\r"

    parts = args.strip().split()
    if len(parts) < 2:
        return "Syntax: pardon <character> <killer|thief>.\n\r"

    target_name = parts[0]
    flag_type = parts[1].lower()

    victim = get_char_world(char, target_name)
    if victim is None:
        return "They aren't here.\n\r"

    if getattr(victim, "is_npc", False):
        return "Not on NPC's.\n\r"

    act_flags = int(getattr(victim, "act", 0))

    if flag_type == "killer":
        if act_flags & int(PlayerFlag.KILLER):
            victim.act = act_flags & ~int(PlayerFlag.KILLER)
            _send_to_char(victim, "You are no longer a KILLER.\n\r")
            return "Killer flag removed.\n\r"
        return "Killer flag removed.\n\r"

    if flag_type == "thief":
        if act_flags & int(PlayerFlag.THIEF):
            victim.act = act_flags & ~int(PlayerFlag.THIEF)
            _send_to_char(victim, "You are no longer a THIEF.\n\r")
            return "Thief flag removed.\n\r"
        return "Thief flag removed.\n\r"

    return "Syntax: pardon <character> <killer|thief>.\n\r"


def do_disconnect(char: Character, args: str) -> str:
    """
    Disconnect a player from the game.

    ROM Reference: src/act_wiz.c:561-617
    """
    if not args or not args.strip():
        return "Disconnect whom?\n\r"

    arg = args.strip().split()[0]

    from mud import registry

    if arg.isdigit():
        desc_num = int(arg)
        for desc in getattr(registry, "descriptor_list", []):
            if getattr(desc, "descriptor", -1) == desc_num:
                _close_socket(desc)
                return "Ok.\n\r"
        return "Descriptor not found!\n\r"

    victim = get_char_world(char, arg)
    if victim is None:
        return "They aren't here.\n\r"

    desc = getattr(victim, "desc", None)
    if desc is None:
        victim_name = getattr(victim, "name", "They")
        return f"{victim_name} doesn't have a descriptor.\n\r"

    _close_socket(desc)
    return "Ok.\n\r"


def _send_to_char(char: Character, message: str) -> None:
    """Send message to character."""
    if not hasattr(char, "output_buffer"):
        char.output_buffer = []
    char.output_buffer.append(message)


def _close_socket(desc) -> None:
    """Close a descriptor socket (simplified)."""
    char = getattr(desc, "character", None)
    if char:
        char.desc = None
    desc.character = None