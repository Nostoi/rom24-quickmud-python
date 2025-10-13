"""Wiznet flags and helpers.

Provides flag definitions and broadcast filtering for immortal channels.
"""

from __future__ import annotations

from enum import IntFlag
from typing import TYPE_CHECKING, Any

from mud.utils.act import act_format


ROM_NEWLINE = "\n\r"


class WiznetFlag(IntFlag):
    """Wiznet flags mirroring ROM bit values."""

    WIZ_ON = 0x00000001
    WIZ_TICKS = 0x00000002
    WIZ_LOGINS = 0x00000004
    WIZ_SITES = 0x00000008
    WIZ_LINKS = 0x00000010
    WIZ_DEATHS = 0x00000020
    WIZ_RESETS = 0x00000040
    WIZ_MOBDEATHS = 0x00000080
    WIZ_FLAGS = 0x00000100
    WIZ_PENALTIES = 0x00000200
    WIZ_SACCING = 0x00000400
    WIZ_LEVELS = 0x00000800
    WIZ_SECURE = 0x00001000
    WIZ_SWITCHES = 0x00002000
    WIZ_SNOOPS = 0x00004000
    WIZ_RESTORE = 0x00008000
    WIZ_LOAD = 0x00010000
    WIZ_NEWBIE = 0x00020000
    WIZ_PREFIX = 0x00040000
    WIZ_SPAM = 0x00080000
    WIZ_DEBUG = 0x00100000  # This was originally WIZ_SPAM value, moving it down
    WIZ_MEMORY = 0x00200000
    WIZ_SKILLS = 0x00400000
    WIZ_TESTING = 0x00800000


if TYPE_CHECKING:  # pragma: no cover - for type hints only
    pass


# Wiznet table mapping names to flags and minimum levels (mirroring C const.c)
WIZNET_TABLE = [
    {"name": "on", "flag": WiznetFlag.WIZ_ON, "level": 1},  # IM = 1 (immortal)
    {"name": "prefix", "flag": WiznetFlag.WIZ_PREFIX, "level": 1},
    {"name": "ticks", "flag": WiznetFlag.WIZ_TICKS, "level": 1},
    {"name": "logins", "flag": WiznetFlag.WIZ_LOGINS, "level": 1},
    {"name": "sites", "flag": WiznetFlag.WIZ_SITES, "level": 54},  # L4
    {"name": "links", "flag": WiznetFlag.WIZ_LINKS, "level": 57},  # L7
    {"name": "newbies", "flag": WiznetFlag.WIZ_NEWBIE, "level": 1},
    {"name": "spam", "flag": WiznetFlag.WIZ_SPAM, "level": 55},  # L5
    {"name": "deaths", "flag": WiznetFlag.WIZ_DEATHS, "level": 1},
    {"name": "resets", "flag": WiznetFlag.WIZ_RESETS, "level": 54},
    {"name": "mobdeaths", "flag": WiznetFlag.WIZ_MOBDEATHS, "level": 54},
    {"name": "flags", "flag": WiznetFlag.WIZ_FLAGS, "level": 55},
    {"name": "penalties", "flag": WiznetFlag.WIZ_PENALTIES, "level": 55},
    {"name": "saccing", "flag": WiznetFlag.WIZ_SACCING, "level": 55},
    {"name": "levels", "flag": WiznetFlag.WIZ_LEVELS, "level": 1},
    {"name": "load", "flag": WiznetFlag.WIZ_LOAD, "level": 52},  # L2
    {"name": "restore", "flag": WiznetFlag.WIZ_RESTORE, "level": 52},
    {"name": "snoops", "flag": WiznetFlag.WIZ_SNOOPS, "level": 52},
    {"name": "switches", "flag": WiznetFlag.WIZ_SWITCHES, "level": 52},
    {"name": "secure", "flag": WiznetFlag.WIZ_SECURE, "level": 51},  # L1
]


def wiznet_lookup(name: str) -> int:
    """Look up wiznet flag by name, return index or -1 if not found."""
    for i, entry in enumerate(WIZNET_TABLE):
        if entry["name"].startswith(name.lower()):
            return i
    return -1


def _get_trust(char: Any) -> int:
    """Return the effective trust level mirroring ROM's ``get_trust`` helper."""

    trust = getattr(char, "trust", 0)
    return trust if trust > 0 else getattr(char, "level", 0)


def wiznet(
    message: str,
    sender_ch_or_flag: Any = None,
    obj: Any = None,
    flag: WiznetFlag | None = None,
    flag_skip: WiznetFlag | None = None,
    min_level: int = 0,
) -> None:
    """Broadcast *message* to immortals subscribed to *flag*.

    Supports both old signature: wiznet(message, flag)
    and new C-compatible signature: wiznet(message, sender_ch, obj, flag, flag_skip, min_level)

    - sender_ch_or_flag: for backward compatibility - if WiznetFlag, treated as flag; if Character, treated as sender
    - obj: object context (currently unused but maintains C signature)
    - flag: required flag subscription (if None, only WIZ_ON is checked)
    - flag_skip: if set, skip characters who have this flag
    - min_level: minimum trust level required

    Immortals must have WIZ_ON and the given *flag* set to receive the message.
    """
    from mud.models.character import character_registry

    # Handle backward compatibility
    sender_ch = None
    if sender_ch_or_flag is not None:
        if isinstance(sender_ch_or_flag, WiznetFlag):
            # Old signature: wiznet(message, flag)
            flag = sender_ch_or_flag
        else:
            # New signature: sender_ch is provided
            sender_ch = sender_ch_or_flag

    for ch in list(character_registry):
        # Skip sender
        if ch == sender_ch:
            continue

        # Must be immortal/admin
        if not getattr(ch, "is_admin", False):
            continue

        # Must have WIZ_ON
        if not getattr(ch, "wiznet", 0) & WiznetFlag.WIZ_ON:
            continue

        # Check required flag
        if flag and not getattr(ch, "wiznet", 0) & flag:
            continue

        # Check skip flag
        if flag_skip and getattr(ch, "wiznet", 0) & flag_skip:
            continue

        # Check min level (get_trust equivalent)
        if _get_trust(ch) < min_level:
            continue

        if not hasattr(ch, "messages"):
            continue

        expanded = act_format(
            message,
            recipient=ch,
            actor=ch,
            arg1=obj,
            arg2=sender_ch,
        )

        if getattr(ch, "wiznet", 0) & WiznetFlag.WIZ_PREFIX:
            formatted_msg = f"{{Z--> {expanded}{{x"
        else:
            formatted_msg = f"{{Z{expanded}{{x"

        ch.messages.append(formatted_msg)


def cmd_wiznet(char: Any, args: str) -> str:
    """Complete wiznet command implementation mirroring C do_wiznet.

    Supports:
    - wiznet (no args): toggle WIZ_ON
    - wiznet on/off: explicitly set WIZ_ON
    - wiznet status: show current subscriptions
    - wiznet show: show available options
    - wiznet <flag>: toggle individual flag subscription
    """
    from mud.models.character import Character  # local import to avoid cycle

    if not isinstance(char, Character) or not getattr(char, "is_admin", False):
        return "Huh?"

    args = args.strip()

    # No arguments: toggle WIZ_ON
    if not args:
        if getattr(char, "wiznet", 0) & WiznetFlag.WIZ_ON:
            char.wiznet &= ~int(WiznetFlag.WIZ_ON)
            return "Signing off of Wiznet." + ROM_NEWLINE
        else:
            char.wiznet |= int(WiznetFlag.WIZ_ON)
            return "Welcome to Wiznet!" + ROM_NEWLINE

    # Explicit on/off
    if args.lower().startswith("on"):
        char.wiznet |= int(WiznetFlag.WIZ_ON)
        return "Welcome to Wiznet!" + ROM_NEWLINE

    if args.lower().startswith("off"):
        char.wiznet &= ~int(WiznetFlag.WIZ_ON)
        return "Signing off of Wiznet." + ROM_NEWLINE

    # Show status
    if args.lower().startswith("status"):
        tokens: list[str] = []

        if not (getattr(char, "wiznet", 0) & WiznetFlag.WIZ_ON):
            tokens.append("off")

        for entry in WIZNET_TABLE:
            if (getattr(char, "wiznet", 0) & int(entry["flag"])) and entry["name"] != "on":
                tokens.append(entry["name"])

        body = " ".join(tokens).strip()
        return f"Wiznet status:{ROM_NEWLINE}{body}{ROM_NEWLINE}"

    # Show available options
    if args.lower().startswith("show"):
        options: list[str] = []
        for entry in WIZNET_TABLE:
            if _get_trust(char) >= entry["level"]:
                options.append(entry["name"])

        body = " ".join(options)
        return f"Wiznet options available to you are:{ROM_NEWLINE}{body}{ROM_NEWLINE}"

    # Individual flag toggle
    flag_index = wiznet_lookup(args)
    if flag_index == -1:
        return "No such option." + ROM_NEWLINE

    entry = WIZNET_TABLE[flag_index]
    if _get_trust(char) < entry["level"]:
        return "No such option." + ROM_NEWLINE

    # Toggle the flag
    if getattr(char, "wiznet", 0) & int(entry["flag"]):
        char.wiznet &= ~int(entry["flag"])
        return f"You will no longer see {entry['name']} on wiznet." + ROM_NEWLINE
    else:
        char.wiznet |= int(entry["flag"])
        return f"You will now see {entry['name']} on wiznet." + ROM_NEWLINE
