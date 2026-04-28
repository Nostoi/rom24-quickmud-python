"""Wiznet flags and helpers.

Provides flag definitions and broadcast filtering for immortal channels.
"""

from __future__ import annotations

from enum import IntFlag
from typing import TYPE_CHECKING, Any

from mud.models.constants import LEVEL_IMMORTAL, MAX_LEVEL
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
    {"name": "on", "flag": WiznetFlag.WIZ_ON, "level": LEVEL_IMMORTAL},
    {"name": "prefix", "flag": WiznetFlag.WIZ_PREFIX, "level": LEVEL_IMMORTAL},
    {"name": "ticks", "flag": WiznetFlag.WIZ_TICKS, "level": LEVEL_IMMORTAL},
    {"name": "logins", "flag": WiznetFlag.WIZ_LOGINS, "level": LEVEL_IMMORTAL},
    {"name": "sites", "flag": WiznetFlag.WIZ_SITES, "level": MAX_LEVEL - 4},
    {"name": "links", "flag": WiznetFlag.WIZ_LINKS, "level": MAX_LEVEL - 7},
    {"name": "newbies", "flag": WiznetFlag.WIZ_NEWBIE, "level": LEVEL_IMMORTAL},
    {"name": "spam", "flag": WiznetFlag.WIZ_SPAM, "level": MAX_LEVEL - 5},
    {"name": "deaths", "flag": WiznetFlag.WIZ_DEATHS, "level": LEVEL_IMMORTAL},
    {"name": "resets", "flag": WiznetFlag.WIZ_RESETS, "level": MAX_LEVEL - 4},
    {"name": "mobdeaths", "flag": WiznetFlag.WIZ_MOBDEATHS, "level": MAX_LEVEL - 4},
    {"name": "flags", "flag": WiznetFlag.WIZ_FLAGS, "level": MAX_LEVEL - 5},
    {"name": "penalties", "flag": WiznetFlag.WIZ_PENALTIES, "level": MAX_LEVEL - 5},
    {"name": "saccing", "flag": WiznetFlag.WIZ_SACCING, "level": MAX_LEVEL - 5},
    {"name": "levels", "flag": WiznetFlag.WIZ_LEVELS, "level": LEVEL_IMMORTAL},
    {"name": "load", "flag": WiznetFlag.WIZ_LOAD, "level": MAX_LEVEL - 2},
    {"name": "restore", "flag": WiznetFlag.WIZ_RESTORE, "level": MAX_LEVEL - 2},
    {"name": "snoops", "flag": WiznetFlag.WIZ_SNOOPS, "level": MAX_LEVEL - 2},
    {"name": "switches", "flag": WiznetFlag.WIZ_SWITCHES, "level": MAX_LEVEL - 2},
    {"name": "secure", "flag": WiznetFlag.WIZ_SECURE, "level": MAX_LEVEL - 1},
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

    mirrors ROM src/act_wiz.c:171-194 — iterates descriptor_list with CON_PLAYING check.
    Falls back to character_registry when descriptor_list is absent (test compat).
    """
    from mud import registry

    # Handle backward compatibility
    sender_ch = None
    if sender_ch_or_flag is not None:
        if isinstance(sender_ch_or_flag, WiznetFlag):
            flag = sender_ch_or_flag
        else:
            sender_ch = sender_ch_or_flag

    # mirrors ROM src/act_wiz.c:176 — iterate descriptor_list when available
    descriptor_list = getattr(registry, "descriptor_list", None)

    if descriptor_list is not None and len(descriptor_list) > 0:
        _wiznet_via_descriptors(message, sender_ch, obj, flag, flag_skip, min_level, descriptor_list)
    else:
        _wiznet_via_registry(message, sender_ch, obj, flag, flag_skip, min_level)


def _wiznet_via_descriptors(
    message: str,
    sender_ch: Any,
    obj: Any,
    flag: WiznetFlag | None,
    flag_skip: WiznetFlag | None,
    min_level: int,
    descriptor_list: list,
) -> None:
    """ROM-faithful wiznet broadcast via descriptor_list (src/act_wiz.c:176)."""
    for desc in descriptor_list:
        d_char = getattr(desc, "character", None)
        if d_char is None:
            continue

        # mirrors ROM src/act_wiz.c:178 — CON_PLAYING check
        if getattr(desc, "connected", 0) != 1:
            continue

        # Skip sender (identity compare)
        if sender_ch is not None and d_char is sender_ch:
            continue

        if not _wiznet_check(d_char, sender_ch, flag, flag_skip, min_level):
            continue

        _wiznet_deliver(d_char, message, sender_ch, obj)


def _wiznet_via_registry(
    message: str,
    sender_ch: Any,
    obj: Any,
    flag: WiznetFlag | None,
    flag_skip: WiznetFlag | None,
    min_level: int,
) -> None:
    """Fallback wiznet broadcast via character_registry (test compat)."""
    from mud.models.character import character_registry

    for ch in list(character_registry):
        if sender_ch is not None and ch is sender_ch:
            continue
        if getattr(ch, "is_npc", True):
            continue
        # mirrors ROM src/act_wiz.c:178 — IS_IMMORTAL check
        is_admin = bool(getattr(ch, "is_admin", False))
        is_immortal = False
        try:
            is_immortal = (
                bool(ch.is_immortal())
                if hasattr(ch, "is_immortal") and callable(ch.is_immortal)
                else _get_trust(ch) >= LEVEL_IMMORTAL
            )
        except Exception:
            is_immortal = _get_trust(ch) >= LEVEL_IMMORTAL
        if not (is_admin or is_immortal):
            continue
        if not _wiznet_check(ch, sender_ch, flag, flag_skip, min_level):
            continue
        _wiznet_deliver(ch, message, sender_ch, obj)


def _wiznet_check(
    ch: Any,
    sender_ch: Any,
    flag: WiznetFlag | None,
    flag_skip: WiznetFlag | None,
    min_level: int,
) -> bool:
    """Check whether *ch* should receive a wiznet message."""
    wiz = getattr(ch, "wiznet", 0)
    if not wiz & WiznetFlag.WIZ_ON:
        return False
    if flag and not wiz & flag:
        return False
    if flag_skip and wiz & flag_skip:
        return False
    if _get_trust(ch) < min_level:
        return False
    return True


def _wiznet_deliver(
    ch: Any,
    message: str,
    sender_ch: Any,
    obj: Any,
) -> None:
    """Format and deliver a wiznet message to *ch*."""
    if not hasattr(ch, "messages"):
        ch.messages = []

    # mirrors ROM src/act_wiz.c:184-189
    expanded = act_format(
        message,
        recipient=ch,
        actor=sender_ch or ch,
        arg1=obj,
        arg2=sender_ch,
    )

    wiz = getattr(ch, "wiznet", 0)
    prefix = "{Z--> " if wiz & WiznetFlag.WIZ_PREFIX else "{Z"
    ch.messages.append(f"{prefix}{expanded}{ROM_NEWLINE}{{x")


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

    if not isinstance(char, Character):
        return "Huh?"

    is_admin = bool(getattr(char, "is_admin", False))
    is_immortal = False
    try:
        is_immortal = char.is_immortal()
    except Exception:
        is_immortal = _get_trust(char) >= LEVEL_IMMORTAL

    if not (is_admin or is_immortal):
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
            if getattr(char, "wiznet", 0) & int(entry["flag"]):
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
