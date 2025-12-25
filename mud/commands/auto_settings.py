"""
Auto-settings commands - autolist, autoall, autoassist, autoexit, autogold, autoloot, autosac, autosplit.
Also: brief, compact, combine, prompt, color.

ROM Reference: src/act_info.c lines 659-950
"""
from __future__ import annotations

from mud.models.character import Character


# Player act flags (PLR_*)
PLR_AUTOASSIST = 0x00000100
PLR_AUTOEXIT = 0x00000200
PLR_AUTOGOLD = 0x00000400
PLR_AUTOLOOT = 0x00000800
PLR_AUTOSAC = 0x00001000
PLR_AUTOSPLIT = 0x00002000
PLR_HOLYLIGHT = 0x00004000
PLR_CANLOOT = 0x00008000
PLR_NOSUMMON = 0x00010000
PLR_NOFOLLOW = 0x00020000

# Comm flags (COMM_*)
COMM_COMPACT = 0x00000001
COMM_BRIEF = 0x00000002
COMM_PROMPT = 0x00000004
COMM_COMBINE = 0x00000008
COMM_TELNET_GA = 0x00000010
COMM_NOCOLOUR = 0x00000020


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
        ("autoassist", act_flags & PLR_AUTOASSIST),
        ("autoexit", act_flags & PLR_AUTOEXIT),
        ("autogold", act_flags & PLR_AUTOGOLD),
        ("autoloot", act_flags & PLR_AUTOLOOT),
        ("autosac", act_flags & PLR_AUTOSAC),
        ("autosplit", act_flags & PLR_AUTOSPLIT),
        ("telnetga", comm_flags & COMM_TELNET_GA),
        ("compact mode", comm_flags & COMM_COMPACT),
        ("prompt", comm_flags & COMM_PROMPT),
        ("combine items", comm_flags & COMM_COMBINE),
    ]
    
    for name, is_on in settings:
        status = "{GON{x" if is_on else "{ROFF{x"
        lines.append(f"{name:14} {status}")
    
    # Extra info
    if not (act_flags & PLR_CANLOOT):
        lines.append("Your corpse is safe from thieves.")
    else:
        lines.append("Your corpse may be looted.")
    
    if act_flags & PLR_NOSUMMON:
        lines.append("You cannot be summoned.")
    else:
        lines.append("You can be summoned.")
    
    if act_flags & PLR_NOFOLLOW:
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
        act_flags |= PLR_AUTOASSIST
        act_flags |= PLR_AUTOEXIT
        act_flags |= PLR_AUTOGOLD
        act_flags |= PLR_AUTOLOOT
        act_flags |= PLR_AUTOSAC
        act_flags |= PLR_AUTOSPLIT
        char.act = act_flags
        return "All autos turned on."
    
    elif arg == "off":
        act_flags = getattr(char, "act", 0)
        act_flags &= ~PLR_AUTOASSIST
        act_flags &= ~PLR_AUTOEXIT
        act_flags &= ~PLR_AUTOGOLD
        act_flags &= ~PLR_AUTOLOOT
        act_flags &= ~PLR_AUTOSAC
        act_flags &= ~PLR_AUTOSPLIT
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
    
    if act_flags & PLR_AUTOASSIST:
        char.act = act_flags & ~PLR_AUTOASSIST
        return "Autoassist removed."
    else:
        char.act = act_flags | PLR_AUTOASSIST
        return "You will now assist when needed."


def do_autoexit(char: Character, args: str) -> str:
    """
    Toggle automatic exit display.
    
    ROM Reference: src/act_info.c do_autoexit (lines 761-775)
    """
    if getattr(char, "is_npc", False):
        return ""
    
    act_flags = getattr(char, "act", 0)
    
    if act_flags & PLR_AUTOEXIT:
        char.act = act_flags & ~PLR_AUTOEXIT
        return "Exits will no longer be displayed."
    else:
        char.act = act_flags | PLR_AUTOEXIT
        return "Exits will now be displayed."


def do_autogold(char: Character, args: str) -> str:
    """
    Toggle automatic gold looting from corpses.
    
    ROM Reference: src/act_info.c do_autogold (lines 778-792)
    """
    if getattr(char, "is_npc", False):
        return ""
    
    act_flags = getattr(char, "act", 0)
    
    if act_flags & PLR_AUTOGOLD:
        char.act = act_flags & ~PLR_AUTOGOLD
        return "Autogold removed."
    else:
        char.act = act_flags | PLR_AUTOGOLD
        return "Automatic gold looting set."


def do_autoloot(char: Character, args: str) -> str:
    """
    Toggle automatic corpse looting.
    
    ROM Reference: src/act_info.c do_autoloot (lines 795-809)
    """
    if getattr(char, "is_npc", False):
        return ""
    
    act_flags = getattr(char, "act", 0)
    
    if act_flags & PLR_AUTOLOOT:
        char.act = act_flags & ~PLR_AUTOLOOT
        return "Autolooting removed."
    else:
        char.act = act_flags | PLR_AUTOLOOT
        return "Automatic corpse looting set."


def do_autosac(char: Character, args: str) -> str:
    """
    Toggle automatic corpse sacrificing.
    
    ROM Reference: src/act_info.c do_autosac (lines 812-826)
    """
    if getattr(char, "is_npc", False):
        return ""
    
    act_flags = getattr(char, "act", 0)
    
    if act_flags & PLR_AUTOSAC:
        char.act = act_flags & ~PLR_AUTOSAC
        return "Autosacrificing removed."
    else:
        char.act = act_flags | PLR_AUTOSAC
        return "Automatic corpse sacrificing set."


def do_autosplit(char: Character, args: str) -> str:
    """
    Toggle automatic gold splitting with group.
    
    ROM Reference: src/act_info.c do_autosplit (lines 829-843)
    """
    if getattr(char, "is_npc", False):
        return ""
    
    act_flags = getattr(char, "act", 0)
    
    if act_flags & PLR_AUTOSPLIT:
        char.act = act_flags & ~PLR_AUTOSPLIT
        return "Autosplitting removed."
    else:
        char.act = act_flags | PLR_AUTOSPLIT
        return "Automatic gold splitting set."


def do_brief(char: Character, args: str) -> str:
    """
    Toggle brief room descriptions.
    
    ROM Reference: src/act_info.c do_brief (lines 877-888)
    """
    comm_flags = getattr(char, "comm", 0)
    
    if comm_flags & COMM_BRIEF:
        char.comm = comm_flags & ~COMM_BRIEF
        return "Full descriptions activated."
    else:
        char.comm = comm_flags | COMM_BRIEF
        return "Short descriptions activated."


def do_compact(char: Character, args: str) -> str:
    """
    Toggle compact output mode (no extra blank lines).
    
    ROM Reference: src/act_info.c do_compact (lines 890-901)
    """
    comm_flags = getattr(char, "comm", 0)
    
    if comm_flags & COMM_COMPACT:
        char.comm = comm_flags & ~COMM_COMPACT
        return "Compact mode removed."
    else:
        char.comm = comm_flags | COMM_COMPACT
        return "Compact mode set."


def do_combine(char: Character, args: str) -> str:
    """
    Toggle combining identical items in inventory display.
    
    ROM Reference: src/act_info.c do_combine
    """
    comm_flags = getattr(char, "comm", 0)
    
    if comm_flags & COMM_COMBINE:
        char.comm = comm_flags & ~COMM_COMBINE
        return "Items will no longer be combined in lists."
    else:
        char.comm = comm_flags | COMM_COMBINE
        return "Items will now be combined in lists."


def do_colour(char: Character, args: str) -> str:
    """
    Toggle ANSI color output.
    
    ROM Reference: src/act_info.c do_colour
    """
    comm_flags = getattr(char, "comm", 0)
    
    if comm_flags & COMM_NOCOLOUR:
        char.comm = comm_flags & ~COMM_NOCOLOUR
        return "{RColour{x is now {GON{x."
    else:
        char.comm = comm_flags | COMM_NOCOLOUR
        return "Colour is now OFF."


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
        if comm_flags & COMM_PROMPT:
            char.comm = comm_flags & ~COMM_PROMPT
            return "You will no longer see prompts."
        else:
            char.comm = comm_flags | COMM_PROMPT
            return "You will now see prompts."
    
    if arg.lower() == "all":
        # Set default prompt
        pcdata = getattr(char, "pcdata", None)
        if pcdata:
            pcdata.prompt = "<%hhp %mm %vmv> "
        char.comm = getattr(char, "comm", 0) | COMM_PROMPT
        return "Prompt set."
    
    # Custom prompt
    pcdata = getattr(char, "pcdata", None)
    if pcdata:
        pcdata.prompt = arg
    char.comm = getattr(char, "comm", 0) | COMM_PROMPT
    return "Prompt set."
