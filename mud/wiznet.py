"""Wiznet flags and helpers.

Provides flag definitions and broadcast filtering for immortal channels.
"""
from __future__ import annotations

from enum import IntFlag
from typing import TYPE_CHECKING


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
    WIZ_SPAM = 0x00040000
    WIZ_DEBUG = 0x00080000
    WIZ_MEMORY = 0x00100000
    WIZ_SKILLS = 0x00200000
    WIZ_TESTING = 0x00400000


if TYPE_CHECKING:  # pragma: no cover - for type hints only
    pass


def wiznet(message: str, flag: WiznetFlag) -> None:
    """Broadcast *message* to immortals subscribed to *flag*.

    Immortals must have WIZ_ON and the given *flag* set to receive the message.
    """
    from mud.models.character import character_registry

    for ch in list(character_registry):
        if not getattr(ch, "is_admin", False):
            continue
        if not getattr(ch, "wiznet", 0) & WiznetFlag.WIZ_ON:
            continue
        if not getattr(ch, "wiznet", 0) & flag:
            continue
        if hasattr(ch, "messages"):
            ch.messages.append(message)


def cmd_wiznet(char, args: str) -> str:
    """Toggle WIZ_ON for immortal *char*.

    Only immortals may use this command.  With no arguments it flips the
    :class:`WiznetFlag.WIZ_ON` bit and reports the new state.
    """
    from mud.models.character import Character  # local import to avoid cycle

    if not isinstance(char, Character) or not getattr(char, "is_admin", False):
        return "Huh?"

    char.wiznet ^= int(WiznetFlag.WIZ_ON)
    state = "on" if char.wiznet & int(WiznetFlag.WIZ_ON) else "off"
    return f"Wiznet is now {state}."
