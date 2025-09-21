from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from mud.models.character import Character


CommandFunc = Callable[["Character", str], None]


@dataclass(frozen=True)
class MobCommand:
    name: str
    func: CommandFunc


def _split_command(argument: str) -> tuple[str, str]:
    stripped = argument.strip()
    if not stripped:
        return "", ""
    parts = stripped.split(None, 1)
    command = parts[0].lower()
    rest = parts[1] if len(parts) > 1 else ""
    return command, rest


def _find_char_in_room(ch: "Character", name: str) -> "Character" | None:
    room = getattr(ch, "room", None)
    if room is None:
        return None
    lowered = name.lower()
    for occupant in getattr(room, "people", []):
        occupant_name = getattr(occupant, "name", None)
        if occupant_name and occupant_name.lower().startswith(lowered):
            return occupant
    return None


def do_mpecho(ch: "Character", argument: str) -> None:
    if not argument:
        return
    room = getattr(ch, "room", None)
    if room is None:
        return
    room.broadcast(argument, exclude=ch)


def do_mpgecho(ch: "Character", argument: str) -> None:
    if not argument:
        return
    from mud.models.character import character_registry

    for target in character_registry:
        if hasattr(target, "messages"):
            target.messages.append(argument)


def do_mpcall(ch: "Character", argument: str) -> None:
    args = argument.split()
    if not args:
        return
    try:
        vnum = int(args[0])
    except ValueError:
        return
    target = None
    if len(args) > 1:
        target = _find_char_in_room(ch, args[1])
    from mud import mobprog

    context = getattr(ch, "_mp_context", None)
    mobprog.call_prog(vnum, ch, target, context=context)


def do_mpdelay(ch: "Character", argument: str) -> None:
    parts = argument.split()
    delay = 0
    if parts:
        try:
            delay = int(parts[0])
        except ValueError:
            delay = 0
    setattr(ch, "mprog_delay", max(0, delay))


def do_mpcancel(ch: "Character", argument: str) -> None:
    setattr(ch, "mprog_delay", 0)


_COMMANDS: list[MobCommand] = [
    MobCommand("echo", do_mpecho),
    MobCommand("gecho", do_mpgecho),
    MobCommand("call", do_mpcall),
    MobCommand("delay", do_mpdelay),
    MobCommand("cancel", do_mpcancel),
]

_COMMAND_LOOKUP = {cmd.name: cmd for cmd in _COMMANDS}


def mob_interpret(ch: "Character", argument: str) -> None:
    command_name, rest = _split_command(argument)
    if not command_name:
        return
    command = _COMMAND_LOOKUP.get(command_name)
    if command is None:
        for candidate in _COMMANDS:
            if candidate.name.startswith(command_name):
                command = candidate
                break
    if command is None:
        return
    command.func(ch, rest)
