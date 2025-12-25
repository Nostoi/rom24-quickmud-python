from __future__ import annotations

from typing import TYPE_CHECKING

from mud.models.constants import AffectFlag, Position

if TYPE_CHECKING:
    from mud.models.character import Character


def do_sleep(ch: Character, args: str) -> str:
    if ch.position == Position.SLEEPING:
        return "You are already sleeping.\r\n"

    if ch.position == Position.FIGHTING:
        return "You are already fighting!\r\n"

    if args:
        return "You can't sleep on furniture yet.\r\n"

    if ch.position in (Position.RESTING, Position.SITTING, Position.STANDING):
        ch.position = Position.SLEEPING
        return "You go to sleep.\r\n"

    return "You can't sleep right now.\r\n"


def do_wake(ch: Character, args: str) -> str:
    if args:
        return "You can't wake others yet.\r\n"

    if ch.position > Position.SLEEPING:
        return "You are already awake.\r\n"

    if ch.affected_by & AffectFlag.SLEEP:
        return "You can't wake up!\r\n"

    ch.position = Position.STANDING
    return "You wake and stand up.\r\n"


def do_rest(ch: Character, args: str) -> str:
    if ch.position == Position.FIGHTING:
        return "You are already fighting!\r\n"

    if args:
        return "You can't rest on furniture yet.\r\n"

    if ch.position == Position.SLEEPING:
        if ch.affected_by & AffectFlag.SLEEP:
            return "You can't wake up!\r\n"
        ch.position = Position.RESTING
        return "You wake up and start resting.\r\n"

    if ch.position == Position.RESTING:
        return "You are already resting.\r\n"

    if ch.position == Position.STANDING:
        ch.position = Position.RESTING
        return "You rest.\r\n"

    return "You can't rest right now.\r\n"


def do_stand(ch: Character, args: str) -> str:
    if ch.position == Position.FIGHTING:
        return "Maybe you should finish fighting first?\r\n"

    if args:
        return "You can't stand on furniture yet.\r\n"

    if ch.position == Position.SLEEPING:
        if ch.affected_by & AffectFlag.SLEEP:
            return "You can't wake up!\r\n"
        ch.position = Position.STANDING
        return "You wake and stand up.\r\n"

    if ch.position in (Position.RESTING, Position.SITTING):
        ch.position = Position.STANDING
        return "You stand up.\r\n"

    if ch.position == Position.STANDING:
        return "You are already standing.\r\n"

    return "You can't stand right now.\r\n"
