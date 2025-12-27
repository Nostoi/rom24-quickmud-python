"""
Helper utilities for player parity tests.

Provides convenient functions for setting up player state without repetitive boilerplate.
Following Oracle guidance: thin, explicit builders over many specialized fixtures.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mud.models.constants import CommFlag, PlayerFlag

if TYPE_CHECKING:
    from mud.models.character import Character


def set_conditions(
    char: Character,
    *,
    drunk: int | None = None,
    full: int | None = None,
    thirst: int | None = None,
    hunger: int | None = None,
) -> None:
    """Set player condition values.

    ROM Reference: merc.h COND_* indices
    - COND_DRUNK = 0
    - COND_FULL = 1
    - COND_THIRST = 2
    - COND_HUNGER = 3

    Args:
        char: Character to modify
        drunk: Drunk level (0-48, or -1 for immunity)
        full: Fullness level (0-48, or -1 for immunity)
        thirst: Thirst level (0-48, or -1 for immunity)
        hunger: Hunger level (0-48, or -1 for immunity)
    """
    pcdata = getattr(char, "pcdata", None)
    if not pcdata:
        return

    # Ensure condition list exists
    if not hasattr(pcdata, "condition") or pcdata.condition is None:
        pcdata.condition = [0, 48, 48, 48]

    # Ensure list is long enough
    while len(pcdata.condition) < 4:
        pcdata.condition.append(48)

    if drunk is not None:
        pcdata.condition[0] = drunk
    if full is not None:
        pcdata.condition[1] = full
    if thirst is not None:
        pcdata.condition[2] = thirst
    if hunger is not None:
        pcdata.condition[3] = hunger


def set_player_flags(
    char: Character,
    *,
    killer: bool | None = None,
    thief: bool | None = None,
    autoassist: bool | None = None,
    autoexit: bool | None = None,
    autogold: bool | None = None,
    autoloot: bool | None = None,
    autosac: bool | None = None,
    autosplit: bool | None = None,
) -> None:
    """Set player act flags.

    ROM Reference: merc.h PLR_* flags

    Args:
        char: Character to modify
        killer: Set/clear PLR_KILLER flag (0x10)
        thief: Set/clear PLR_THIEF flag (0x20)
        autoassist: Set/clear PLR_AUTOASSIST flag
        autoexit: Set/clear PLR_AUTOEXIT flag
        autogold: Set/clear PLR_AUTOGOLD flag
        autoloot: Set/clear PLR_AUTOLOOT flag
        autosac: Set/clear PLR_AUTOSAC flag
        autosplit: Set/clear PLR_AUTOSPLIT flag
    """
    act_flags = getattr(char, "act", 0)

    if killer is not None:
        if killer:
            act_flags |= PlayerFlag.KILLER
        else:
            act_flags &= ~PlayerFlag.KILLER

    if thief is not None:
        if thief:
            act_flags |= PlayerFlag.THIEF
        else:
            act_flags &= ~PlayerFlag.THIEF

    if autoassist is not None:
        if autoassist:
            act_flags |= PlayerFlag.AUTOASSIST
        else:
            act_flags &= ~PlayerFlag.AUTOASSIST

    if autoexit is not None:
        if autoexit:
            act_flags |= PlayerFlag.AUTOEXIT
        else:
            act_flags &= ~PlayerFlag.AUTOEXIT

    if autogold is not None:
        if autogold:
            act_flags |= PlayerFlag.AUTOGOLD
        else:
            act_flags &= ~PlayerFlag.AUTOGOLD

    if autoloot is not None:
        if autoloot:
            act_flags |= PlayerFlag.AUTOLOOT
        else:
            act_flags &= ~PlayerFlag.AUTOLOOT

    if autosac is not None:
        if autosac:
            act_flags |= PlayerFlag.AUTOSAC
        else:
            act_flags &= ~PlayerFlag.AUTOSAC

    if autosplit is not None:
        if autosplit:
            act_flags |= PlayerFlag.AUTOSPLIT
        else:
            act_flags &= ~PlayerFlag.AUTOSPLIT

    char.act = act_flags


def set_comm_flags(
    char: Character,
    *,
    compact: bool | None = None,
    brief: bool | None = None,
    prompt: bool | None = None,
    combine: bool | None = None,
    nocolour: bool | None = None,
    afk: bool | None = None,
) -> None:
    """Set player comm flags.

    ROM Reference: merc.h COMM_* flags

    Args:
        char: Character to modify
        compact: Set/clear COMM_COMPACT flag
        brief: Set/clear COMM_BRIEF flag
        prompt: Set/clear COMM_PROMPT flag
        combine: Set/clear COMM_COMBINE flag
        nocolour: Set/clear COMM_NOCOLOUR flag
        afk: Set/clear COMM_AFK flag
    """
    comm_flags = getattr(char, "comm", 0)

    if compact is not None:
        if compact:
            comm_flags |= CommFlag.COMPACT
        else:
            comm_flags &= ~CommFlag.COMPACT

    if brief is not None:
        if brief:
            comm_flags |= CommFlag.BRIEF
        else:
            comm_flags &= ~CommFlag.BRIEF

    if prompt is not None:
        if prompt:
            comm_flags |= CommFlag.PROMPT
        else:
            comm_flags &= ~CommFlag.PROMPT

    if combine is not None:
        if combine:
            comm_flags |= CommFlag.COMBINE
        else:
            comm_flags &= ~CommFlag.COMBINE

    if afk is not None:
        if afk:
            comm_flags |= CommFlag.AFK
        else:
            comm_flags &= ~CommFlag.AFK

    char.comm = comm_flags


def enable_autos(
    char: Character,
    *,
    autoassist: bool = False,
    autoexit: bool = False,
    autogold: bool = False,
    autoloot: bool = False,
    autosac: bool = False,
    autosplit: bool = False,
) -> None:
    """Convenience wrapper to enable multiple auto-settings at once.

    Args:
        char: Character to modify
        autoassist: Enable autoassist
        autoexit: Enable autoexit
        autogold: Enable autogold
        autoloot: Enable autoloot
        autosac: Enable autosac
        autosplit: Enable autosplit
    """
    set_player_flags(
        char,
        autoassist=autoassist,
        autoexit=autoexit,
        autogold=autogold,
        autoloot=autoloot,
        autosac=autosac,
        autosplit=autosplit,
    )
