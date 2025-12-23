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
    """
    Typo guard for alias - shows proper usage.
    
    ROM Reference: interp.c command table
    
    Usage: alia (does nothing)
    """
    return "If you want to ALIAS, spell it out."


def do_colon(char: Character, args: str) -> str:
    """
    The colon command - used for socials in some MUDs.
    
    ROM Reference: interp.c command table
    
    In ROM, ':' is mapped to do_immtalk for immortal chat.
    
    Usage: : <message>
    """
    if not args or not args.strip():
        return "Say what on the immortal channel?"
    
    # Delegate to immtalk
    from mud.commands.communication import do_immtalk
    return do_immtalk(char, args)
