from __future__ import annotations

from mud.models.character import Character
from mud.world.look import look
from mud.models.constants import Direction


def do_scan(char: Character, args: str = "") -> str:
    """List visible characters in adjacent rooms by direction (range=1).

    Minimal ROM parity: order directions N,E,S,W,Up,Down; exclude self; include PC names.
    """
    if not char.room:
        return "You see nothing."
    order = [
        Direction.NORTH,
        Direction.EAST,
        Direction.SOUTH,
        Direction.WEST,
        Direction.UP,
        Direction.DOWN,
    ]
    dir_name = {
        Direction.NORTH: "north",
        Direction.EAST: "east",
        Direction.SOUTH: "south",
        Direction.WEST: "west",
        Direction.UP: "up",
        Direction.DOWN: "down",
    }
    lines: list[str] = ["You scan for life signs..."]
    room = char.room
    any_found = False
    for d in order:
        ex = room.exits[int(d)] if room.exits and int(d) < len(room.exits) else None
        to_room = ex.to_room if ex else None
        if not to_room:
            continue
        names = [p.name or "someone" for p in to_room.people if p is not char]
        if names:
            any_found = True
            lines.append(f"{dir_name[d]}: " + ", ".join(names))
    if not any_found:
        lines.append("No one is nearby.")
    return "\n".join(lines)


def do_look(char: Character, args: str = "") -> str:
    return look(char)
