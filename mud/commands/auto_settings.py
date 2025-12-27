"""
Auto-settings commands - autolist, autoall, autoassist, autoexit, autogold, autoloot, autosac, autosplit.
Also: brief, compact, combine, prompt, color.

ROM Reference: src/act_info.c lines 659-950
"""

from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import CommFlag, PlayerFlag


def do_autolist(char: Character, args: str) -> str:
    """
    List all auto-settings and their status.

    ROM Reference: src/act_info.c do_autolist (lines 659-742)
    """
    if getattr(char, "is_npc", False):
        return ""

    act_flags = getattr(char, "act", 0)
    comm_flags = getattr(char, "comm", 0)

    lines = []
    lines.append("   action     status")
    lines.append("---------------------")

    # Auto settings
    settings = [
        ("autoassist", act_flags & PlayerFlag.AUTOASSIST),
        ("autoexit", act_flags & PlayerFlag.AUTOEXIT),
        ("autogold", act_flags & PlayerFlag.AUTOGOLD),
        ("autoloot", act_flags & PlayerFlag.AUTOLOOT),
        ("autosac", act_flags & PlayerFlag.AUTOSAC),
        ("autosplit", act_flags & PlayerFlag.AUTOSPLIT),
        ("telnetga", comm_flags & CommFlag.TELNET_GA),
        ("compact mode", comm_flags & CommFlag.COMPACT),
        ("prompt", comm_flags & CommFlag.PROMPT),
        ("combine items", comm_flags & CommFlag.COMBINE),
    ]

    for name, is_on in settings:
        status = "{GON{x" if is_on else "{ROFF{x"
        lines.append(f"{name:14} {status}")

    # Extra info
    if not (act_flags & PlayerFlag.CANLOOT):
        lines.append("Your corpse is safe from thieves.")
    else:
        lines.append("Your corpse may be looted.")

    if act_flags & PlayerFlag.NOSUMMON:
        lines.append("You cannot be summoned.")
    else:
        lines.append("You can be summoned.")

    if act_flags & PlayerFlag.NOFOLLOW:
        lines.append("You do not welcome followers.")
    else:
        lines.append("You accept followers.")

    return "\n".join(lines)


def do_autoall(char: Character, args: str) -> str:
    """
    Toggle all auto-settings on or off.

    ROM Reference: src/act_info.c do_autoall (lines 846-875)
    """
    if getattr(char, "is_npc", False):
        return ""

    arg = (args or "").strip().lower()

    if arg == "on":
        act_flags = getattr(char, "act", 0)
        act_flags |= PlayerFlag.AUTOASSIST
        act_flags |= PlayerFlag.AUTOEXIT
        act_flags |= PlayerFlag.AUTOGOLD
        act_flags |= PlayerFlag.AUTOLOOT
        act_flags |= PlayerFlag.AUTOSAC
        act_flags |= PlayerFlag.AUTOSPLIT
        char.act = act_flags
        return "All autos turned on."

    elif arg == "off":
        act_flags = getattr(char, "act", 0)
        act_flags &= ~PlayerFlag.AUTOASSIST
        act_flags &= ~PlayerFlag.AUTOEXIT
        act_flags &= ~PlayerFlag.AUTOGOLD
        act_flags &= ~PlayerFlag.AUTOLOOT
        act_flags &= ~PlayerFlag.AUTOSAC
        act_flags &= ~PlayerFlag.AUTOSPLIT
        char.act = act_flags
        return "All autos turned off."

    return "Usage: autoall [on|off]"


def do_autoassist(char: Character, args: str) -> str:
    """
    Toggle automatic assist in combat.

    ROM Reference: src/act_info.c do_autoassist (lines 744-758)
    """
    if getattr(char, "is_npc", False):
        return ""

    act_flags = getattr(char, "act", 0)

    if act_flags & PlayerFlag.AUTOASSIST:
        char.act = act_flags & ~PlayerFlag.AUTOASSIST
        return "Autoassist removed."
    else:
        char.act = act_flags | PlayerFlag.AUTOASSIST
        return "You will now assist when needed."


def do_autoexit(char: Character, args: str) -> str:
    """
    Toggle automatic exit display.

    ROM Reference: src/act_info.c do_autoexit (lines 761-775)
    """
    if getattr(char, "is_npc", False):
        return ""

    act_flags = getattr(char, "act", 0)

    if act_flags & PlayerFlag.AUTOEXIT:
        char.act = act_flags & ~PlayerFlag.AUTOEXIT
        return "Exits will no longer be displayed."
    else:
        char.act = act_flags | PlayerFlag.AUTOEXIT
        return "Exits will now be displayed."


def do_autogold(char: Character, args: str) -> str:
    """
    Toggle automatic gold looting from corpses.

    ROM Reference: src/act_info.c do_autogold (lines 778-792)
    """
    if getattr(char, "is_npc", False):
        return ""

    act_flags = getattr(char, "act", 0)

    if act_flags & PlayerFlag.AUTOGOLD:
        char.act = act_flags & ~PlayerFlag.AUTOGOLD
        return "Autogold removed."
    else:
        char.act = act_flags | PlayerFlag.AUTOGOLD
        return "Automatic gold looting set."


def do_autoloot(char: Character, args: str) -> str:
    """
    Toggle automatic corpse looting.

    ROM Reference: src/act_info.c do_autoloot (lines 795-809)
    """
    if getattr(char, "is_npc", False):
        return ""

    act_flags = getattr(char, "act", 0)

    if act_flags & PlayerFlag.AUTOLOOT:
        char.act = act_flags & ~PlayerFlag.AUTOLOOT
        return "Autolooting removed."
    else:
        char.act = act_flags | PlayerFlag.AUTOLOOT
        return "Automatic corpse looting set."


def do_autosac(char: Character, args: str) -> str:
    """
    Toggle automatic corpse sacrificing.

    ROM Reference: src/act_info.c do_autosac (lines 812-826)
    """
    if getattr(char, "is_npc", False):
        return ""

    act_flags = getattr(char, "act", 0)

    if act_flags & PlayerFlag.AUTOSAC:
        char.act = act_flags & ~PlayerFlag.AUTOSAC
        return "Autosacrificing removed."
    else:
        char.act = act_flags | PlayerFlag.AUTOSAC
        return "Automatic corpse sacrificing set."


def do_autosplit(char: Character, args: str) -> str:
    """
    Toggle automatic gold splitting with group.

    ROM Reference: src/act_info.c do_autosplit (lines 829-843)
    """
    if getattr(char, "is_npc", False):
        return ""

    act_flags = getattr(char, "act", 0)

    if act_flags & PlayerFlag.AUTOSPLIT:
        char.act = act_flags & ~PlayerFlag.AUTOSPLIT
        return "Autosplitting removed."
    else:
        char.act = act_flags | PlayerFlag.AUTOSPLIT
        return "Automatic gold splitting set."


def do_brief(char: Character, args: str) -> str:
    """
    Toggle brief room descriptions.

    ROM Reference: src/act_info.c do_brief (lines 877-888)
    """
    comm_flags = getattr(char, "comm", 0)

    if comm_flags & CommFlag.BRIEF:
        char.comm = comm_flags & ~CommFlag.BRIEF
        return "Full descriptions activated."
    else:
        char.comm = comm_flags | CommFlag.BRIEF
        return "Short descriptions activated."


def do_compact(char: Character, args: str) -> str:
    """
    Toggle compact output mode (no extra blank lines).

    ROM Reference: src/act_info.c do_compact (lines 890-901)
    """
    comm_flags = getattr(char, "comm", 0)

    if comm_flags & CommFlag.COMPACT:
        char.comm = comm_flags & ~CommFlag.COMPACT
        return "Compact mode removed."
    else:
        char.comm = comm_flags | CommFlag.COMPACT
        return "Compact mode set."


def do_combine(char: Character, args: str) -> str:
    """
    Toggle combining identical items in inventory display.

    ROM Reference: src/act_info.c do_combine
    """
    comm_flags = getattr(char, "comm", 0)

    if comm_flags & CommFlag.COMBINE:
        char.comm = comm_flags & ~CommFlag.COMBINE
        return "Items will no longer be combined in lists."
    else:
        char.comm = comm_flags | CommFlag.COMBINE
        return "Items will now be combined in lists."


def do_colour(char: Character, args: str) -> str:
    """
    Toggle ANSI color output.

    ROM Reference: src/act_info.c do_colour
    """
    act_flags = getattr(char, "act", 0)

    if act_flags & PlayerFlag.COLOUR:
        char.act = act_flags & ~PlayerFlag.COLOUR
        return "Colour is now OFF."
    else:
        char.act = act_flags | PlayerFlag.COLOUR
        return "{RColour{x is now {GON{x."


# Alias for American spelling
do_color = do_colour


def do_prompt(char: Character, args: str) -> str:
    """
    Toggle or set custom prompt.

    ROM Reference: src/act_info.c do_prompt

    Usage:
    - prompt         - Toggle prompt on/off
    - prompt all     - Set default full prompt
    - prompt <str>   - Set custom prompt string
    """
    arg = (args or "").strip()

    if not arg:
        # Toggle prompt
        comm_flags = getattr(char, "comm", 0)
        if comm_flags & CommFlag.PROMPT:
            char.comm = comm_flags & ~CommFlag.PROMPT
            return "You will no longer see prompts."
        else:
            char.comm = comm_flags | CommFlag.PROMPT
            return "You will now see prompts."

    if arg.lower() == "all":
        # Set default prompt
        pcdata = getattr(char, "pcdata", None)
        if pcdata:
            pcdata.prompt = "<%hhp %mm %vmv> "
        char.comm = getattr(char, "comm", 0) | CommFlag.PROMPT
        return "Prompt set."

    # Custom prompt
    pcdata = getattr(char, "pcdata", None)
    if pcdata:
        pcdata.prompt = arg
    char.comm = getattr(char, "comm", 0) | CommFlag.PROMPT
    return "Prompt set."
