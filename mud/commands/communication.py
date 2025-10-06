from __future__ import annotations

import asyncio

from mud import mobprog
from mud.characters import is_clan_member, is_same_clan
from mud.models.character import Character, character_registry
from mud.models.constants import CommFlag, Position
from mud.net.protocol import broadcast_global, broadcast_room, send_to_char


def _has_comm_flag(char: Character, flag: CommFlag) -> bool:
    if hasattr(char, "has_comm_flag"):
        try:
            return bool(char.has_comm_flag(flag))
        except Exception:
            pass
    try:
        return bool(int(getattr(char, "comm", 0) or 0) & int(flag))
    except Exception:
        return False


def _set_comm_flag(char: Character, flag: CommFlag) -> None:
    if hasattr(char, "set_comm_flag"):
        try:
            char.set_comm_flag(flag)
            return
        except Exception:
            pass
    current = int(getattr(char, "comm", 0) or 0)
    char.comm = current | int(flag)


def _clear_comm_flag(char: Character, flag: CommFlag) -> None:
    if hasattr(char, "clear_comm_flag"):
        try:
            char.clear_comm_flag(flag)
            return
        except Exception:
            pass
    current = int(getattr(char, "comm", 0) or 0)
    char.comm = current & ~int(flag)


def do_say(char: Character, args: str) -> str:
    if not args:
        return "Say what?"
    message = f"{char.name} says, '{args}'"
    if char.room:
        char.room.broadcast(message, exclude=char)
        broadcast_room(char.room, message, exclude=char)
        for mob in list(char.room.people):
            if mob is char or not getattr(mob, "is_npc", False):
                continue
            default_pos = getattr(mob, "default_pos", getattr(mob, "position", Position.STANDING))
            if getattr(mob, "position", default_pos) != default_pos:
                continue
            mobprog.mp_speech_trigger(args, mob, char)
    return f"You say, '{args}'"


def do_tell(char: Character, args: str) -> str:
    if "tell" in char.banned_channels:
        return "You are banned from tell."
    if _has_comm_flag(char, CommFlag.NOCHANNELS):
        return "The gods have revoked your channel privileges."
    if _has_comm_flag(char, CommFlag.NOTELL) or _has_comm_flag(char, CommFlag.DEAF):
        return "Your message didn't get through."
    if _has_comm_flag(char, CommFlag.QUIET):
        return "You must turn off quiet mode first."
    if not args:
        return "Tell whom what?"
    try:
        target_name, message = args.split(None, 1)
    except ValueError:
        return "Tell whom what?"
    target = next(
        (c for c in character_registry if c.name and c.name.lower() == target_name.lower()),
        None,
    )
    if not target:
        return "They aren't here."
    if "tell" in target.muted_channels:
        return "They aren't listening."
    if (
        (_has_comm_flag(target, CommFlag.QUIET) or _has_comm_flag(target, CommFlag.DEAF))
        and not char.is_immortal()
    ):
        return f"{target.name} is not receiving tells."
    text = f"{char.name} tells you, '{message}'"
    writer = getattr(target, "connection", None)
    if writer:
        asyncio.create_task(send_to_char(target, text))
    if hasattr(target, "messages"):
        target.messages.append(text)
    if getattr(target, "is_npc", False):
        default_pos = getattr(target, "default_pos", getattr(target, "position", Position.STANDING))
        if getattr(target, "position", default_pos) == default_pos:
            mobprog.mp_speech_trigger(message, target, char)
    return f"You tell {target.name}, '{message}'"


def do_shout(char: Character, args: str) -> str:
    if "shout" in char.banned_channels:
        return "You are banned from shout."
    cleaned = args.strip()
    if not cleaned:
        if _has_comm_flag(char, CommFlag.SHOUTSOFF):
            _clear_comm_flag(char, CommFlag.SHOUTSOFF)
            return "You can hear shouts again."
        _set_comm_flag(char, CommFlag.SHOUTSOFF)
        return "You will no longer hear shouts."
    if _has_comm_flag(char, CommFlag.NOCHANNELS):
        return "The gods have revoked your channel privileges."
    if _has_comm_flag(char, CommFlag.QUIET):
        return "You must turn off quiet mode first."
    if _has_comm_flag(char, CommFlag.NOSHOUT):
        return "You can't shout."
    if _has_comm_flag(char, CommFlag.SHOUTSOFF):
        return "You must turn shouts back on first."
    message = f"{char.name} shouts, '{cleaned}'"
    current_wait = getattr(char, "wait", 0) or 0
    char.wait = max(int(current_wait), 12)

    def _should_receive(target: Character) -> bool:
        return not (
            _has_comm_flag(target, CommFlag.SHOUTSOFF)
            or _has_comm_flag(target, CommFlag.QUIET)
        )
    broadcast_global(message, channel="shout", exclude=char, should_send=_should_receive)
    return f"You shout, '{cleaned}'"


def do_clantalk(char: Character, args: str) -> str:
    if "clan" in char.banned_channels:
        return "You are banned from clan."
    if not is_clan_member(char):
        return "You aren't in a clan."

    cleaned = args.strip()
    if not cleaned:
        if _has_comm_flag(char, CommFlag.NOCLAN):
            _clear_comm_flag(char, CommFlag.NOCLAN)
            return "Clan channel is now ON."
        _set_comm_flag(char, CommFlag.NOCLAN)
        return "Clan channel is now OFF."

    if _has_comm_flag(char, CommFlag.NOCHANNELS):
        return "The gods have revoked your channel privileges."

    _clear_comm_flag(char, CommFlag.NOCLAN)

    def _should_receive(target: Character) -> bool:
        if not is_same_clan(char, target):
            return False
        if _has_comm_flag(target, CommFlag.NOCLAN) or _has_comm_flag(target, CommFlag.QUIET):
            return False
        return True

    message = f"{char.name} clans, '{cleaned}'"
    broadcast_global(message, channel="clan", exclude=char, should_send=_should_receive)
    return f"You clan '{cleaned}'"


def do_immtalk(char: Character, args: str) -> str:
    if not char.is_immortal():
        return "You aren't an immortal."
    if "immtalk" in char.banned_channels:
        return "You are banned from immtalk."

    cleaned = args.strip()
    if not cleaned:
        if _has_comm_flag(char, CommFlag.NOWIZ):
            _clear_comm_flag(char, CommFlag.NOWIZ)
            return "Immortal channel is now ON."
        _set_comm_flag(char, CommFlag.NOWIZ)
        return "Immortal channel is now OFF."

    _clear_comm_flag(char, CommFlag.NOWIZ)

    def _should_receive(target: Character) -> bool:
        if not target.is_immortal():
            return False
        if _has_comm_flag(target, CommFlag.NOWIZ):
            return False
        return True

    message = f"[{char.name}]: {cleaned}"
    broadcast_global(message, channel="immtalk", exclude=char, should_send=_should_receive)
    return message
