"""
Immortal admin commands - advance, trust, freeze, snoop, switch, return.

ROM Reference: src/act_wiz.c
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from mud.commands.imm_commands import MAX_LEVEL, get_char_world, get_trust
from mud.models.character import Character
from mud.models.constants import CommFlag

if TYPE_CHECKING:
    pass


def do_advance(char: Character, args: str) -> str:
    """
    Set a player's level.

    ROM Reference: src/act_wiz.c do_advance (lines 2652-2742)

    Usage: advance <player> <level>
    """
    if not args or not args.strip():
        return "Syntax: advance <char> <level>."

    parts = args.strip().split()
    if len(parts) < 2:
        return "Syntax: advance <char> <level>."

    target_name = parts[0]
    level_arg = parts[1]

    if not level_arg.isdigit():
        return "Syntax: advance <char> <level>."

    victim = get_char_world(char, target_name)
    if victim is None:
        return "That player is not here."

    if getattr(victim, "is_npc", False):
        return "Not on NPC's."

    level = int(level_arg)
    if level < 1 or level > MAX_LEVEL:
        return f"Level must be 1 to {MAX_LEVEL}."

    if level > get_trust(char):
        return "Limited to your trust level."

    old_level = getattr(victim, "level", 1)

    if level <= old_level:
        # Lowering level
        victim.level = level
        victim.hit = getattr(victim, "max_hit", 100)
        victim.mana = getattr(victim, "max_mana", 100)
        victim.move = getattr(victim, "max_move", 100)
        _send_to_char(victim, "**** OOOOHHHHHHHHHH  NNNNOOOO ****")
        return "Lowering a player's level!"
    else:
        # Raising level
        victim.level = level
        _send_to_char(victim, "**** OOOOHHHHHHHHHH  YYYYEEEESSS ****")
        _send_to_char(victim, f"You are now level {level}.")
        return "Raising a player's level!"


def do_trust(char: Character, args: str) -> str:
    """
    Set a player's trust level.

    ROM Reference: src/act_wiz.c do_trust (lines 2743-2783)

    Usage: trust <player> <level>

    Trust allows a lower-level immortal to use higher-level commands.
    """
    if not args or not args.strip():
        return "Syntax: trust <char> <level>."

    parts = args.strip().split()
    if len(parts) < 2:
        return "Syntax: trust <char> <level>."

    target_name = parts[0]
    level_arg = parts[1]

    if not level_arg.isdigit():
        return "Syntax: trust <char> <level>."

    victim = get_char_world(char, target_name)
    if victim is None:
        return "That player is not here."

    level = int(level_arg)
    if level < 0 or level > MAX_LEVEL:
        return f"Level must be 0 (reset) to {MAX_LEVEL}."

    if level > get_trust(char):
        return "Limited to your trust."

    victim.trust = level

    if level == 0:
        return "Trust removed."
    else:
        return f"Trust set to {level}."


def do_freeze(char: Character, args: str) -> str:
    """
    Freeze/unfreeze a player (prevents them from playing).

    ROM Reference: src/act_wiz.c:2872-2922
    """
    if not args or not args.strip():
        return "Freeze whom?\n\r"

    target_name = args.strip().split()[0]
    victim = get_char_world(char, target_name)

    if victim is None:
        return "They aren't here.\n\r"

    if getattr(victim, "is_npc", False):
        return "Not on NPC's.\n\r"

    if get_trust(victim) >= get_trust(char):
        return "You failed.\n\r"

    from mud.models.constants import PlayerFlag

    act_flags = int(getattr(victim, "act", 0))

    if act_flags & int(PlayerFlag.FREEZE):
        victim.act = act_flags & ~int(PlayerFlag.FREEZE)
        _send_to_char(victim, "You can play again.\n\r")
        from mud.wiznet import wiznet, WiznetFlag
        wiznet(f"$N thaws {victim.name}.", char, None, WiznetFlag.WIZ_PENALTIES, WiznetFlag.WIZ_SECURE, 0)
        return "FREEZE removed.\n\r"

    victim.act = act_flags | int(PlayerFlag.FREEZE)
    _send_to_char(victim, "You can't do ANYthing!\n\r")
    from mud.wiznet import wiznet, WiznetFlag
    wiznet(f"$N puts {victim.name} in the deep freeze.", char, None, WiznetFlag.WIZ_PENALTIES, WiznetFlag.WIZ_SECURE, 0)
    return "FREEZE set.\n\r"


def do_snoop(char: Character, args: str) -> str:
    """
    Snoop on a player's session (see what they see).

    ROM Reference: src/act_wiz.c do_snoop (lines 2120-2200)

    Usage:
    - snoop <player>  - Start snooping
    - snoop <self>    - Cancel all snoops
    """
    if not args or not args.strip():
        return "Snoop whom?"

    target_name = args.strip().split()[0]
    victim = get_char_world(char, target_name)

    if victim is None:
        return "They aren't here."

    desc = getattr(victim, "desc", None)
    if desc is None:
        return "No descriptor to snoop."

    if victim is char:
        # Cancel all snoops
        from mud import registry
        for d in getattr(registry, "descriptor_list", []):
            if getattr(d, "snoop_by", None) is getattr(char, "desc", None):
                d.snoop_by = None
        return "Cancelling all snoops."

    # Check if already being snooped
    if getattr(desc, "snoop_by", None) is not None:
        return "Busy already."

    # Check trust and snoop-proof
    if get_trust(victim) >= get_trust(char):
        return "You failed."

    if getattr(victim, "comm", 0) & int(CommFlag.SNOOP_PROOF):
        return "You failed."

    # Set up snoop
    char_desc = getattr(char, "desc", None)
    if char_desc:
        desc.snoop_by = char_desc

    return "Ok."


def do_switch(char: Character, args: str) -> str:
    """
    Switch into a mobile (control their body).

    ROM Reference: src/act_wiz.c do_switch (lines 2202-2270)

    Usage: switch <mob>
    """
    if not args or not args.strip():
        return "Switch into whom?"

    desc = getattr(char, "desc", None)
    if desc is None:
        return ""

    # Check if already switched
    if getattr(desc, "original", None) is not None:
        return "You are already switched."

    target_name = args.strip().split()[0]
    victim = get_char_world(char, target_name)

    if victim is None:
        return "They aren't here."

    if victim is char:
        return "Ok."

    if not getattr(victim, "is_npc", False):
        return "You can only switch into mobiles."

    if getattr(victim, "desc", None) is not None:
        return "Character in use."

    # Perform the switch
    desc.character = victim
    desc.original = char
    victim.desc = desc
    char.desc = None

    # Copy communication settings
    if getattr(char, "prompt", None):
        victim.prompt = char.prompt
    victim.comm = getattr(char, "comm", 0)
    victim.lines = getattr(char, "lines", 0)

    return "Ok."


def do_return(char: Character, args: str) -> str:
    """
    Return from a switched mobile to your original body.

    ROM Reference: src/act_wiz.c do_return (lines 2273-2310)

    Usage: return
    """
    desc = getattr(char, "desc", None)
    if desc is None:
        return ""

    original = getattr(desc, "original", None)
    if original is None:
        return "You aren't switched."

    # Return to original body
    char.desc = None
    desc.character = original
    desc.original = None
    original.desc = desc

    return "Ok."


# Helper function

def _send_to_char(char: Character, message: str) -> None:
    """Send message to character."""
    if not hasattr(char, "output_buffer"):
        char.output_buffer = []
    char.output_buffer.append(message)
