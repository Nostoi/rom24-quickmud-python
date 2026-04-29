"""
Typo guard commands - prevents accidental execution of dangerous commands.

ROM Reference: src/interp.c
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from mud.models.character import Character

if TYPE_CHECKING:
    pass


def do_qui(char: Character, args: str) -> str:
    """
    Typo guard for quit - prevents accidental quit.

    ROM Reference: interp.c command table

    Usage: qui (does nothing)
    """
    return "If you want to QUIT, you have to spell it out."


def do_murde(char: Character, args: str) -> str:
    """
    Typo guard for murder - prevents accidental murder.

    ROM Reference: interp.c command table

    Usage: murde (does nothing)
    """
    return "If you want to MURDER, spell it out."


def do_reboo(char: Character, args: str) -> str:
    """
    Typo guard for reboot - prevents accidental reboot.

    ROM Reference: interp.c command table

    Usage: reboo (does nothing)
    """
    return "If you want to REBOOT, spell it out."


def do_shutdow(char: Character, args: str) -> str:
    """
    Typo guard for shutdown - prevents accidental shutdown.

    ROM Reference: interp.c command table

    Usage: shutdow (does nothing)
    """
    return "If you want to SHUTDOWN, spell it out."


def do_alia(char: Character, args: str) -> str:
    """ROM typo guard for `alias` from `src/alias.c:97-100`."""
    return "I'm sorry, alias must be entered in full.\n\r"
