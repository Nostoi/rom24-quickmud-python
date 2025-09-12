from __future__ import annotations

from mud.models.character import Character
from mud.world.look import look, dir_names
from mud.models.constants import Direction


def do_scan(char: Character, args: str = "") -> str:
    """ROM-like scan output with distances and optional direction.

    - No arg: list current room (depth 0) and adjacent rooms (depth 1) in N,E,S,W,Up,Down order.
    - With direction: follow exits up to depth 3 and list visible characters per room.
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
    distance = [
        "right here.",
        "nearby to the %s.",
        "not far %s.",
        "off in the distance %s.",
    ]

    def list_room(room, depth: int, door: int) -> list[str]:
        lines: list[str] = []
        if not room:
            return lines
        for p in room.people:
            if p is char:
                continue
            who = p.name or "someone"
            if depth == 0:
                lines.append(f"{who}, {distance[0]}")
            else:
                dn = dir_name[Direction(door)]
                lines.append(f"{who}, {distance[depth] % dn}")
        return lines

    s = args.strip().lower()
    if not s:
        lines: list[str] = ["Looking around you see:"]
        # current room
        lines += list_room(char.room, 0, -1)
        # each direction at depth 1
        for d in order:
            ex = char.room.exits[int(d)] if char.room.exits and int(d) < len(char.room.exits) else None
            to_room = ex.to_room if ex else None
            lines += list_room(to_room, 1, int(d))
        if len(lines) == 1:
            lines.append("No one is nearby.")
        return "\n".join(lines)

    # Directional scan up to depth 3
    token_map = {
        "n": Direction.NORTH,
        "north": Direction.NORTH,
        "e": Direction.EAST,
        "east": Direction.EAST,
        "s": Direction.SOUTH,
        "south": Direction.SOUTH,
        "w": Direction.WEST,
        "west": Direction.WEST,
        "u": Direction.UP,
        "up": Direction.UP,
        "d": Direction.DOWN,
        "down": Direction.DOWN,
    }
    if s not in token_map:
        return "Which way do you want to scan?"
    d = token_map[s]
    dir_str = dir_name[d]
    lines = [f"Looking {dir_str} you see:"]
    scan_room = char.room
    for depth in (1, 2, 3):
        ex = scan_room.exits[int(d)] if scan_room and scan_room.exits and int(d) < len(scan_room.exits) else None
        scan_room = ex.to_room if ex else None
        if not scan_room:
            break
        lines += list_room(scan_room, depth, int(d))
    if len(lines) == 1:
        lines.append("Nothing of note.")
    return "\n".join(lines)


def do_look(char: Character, args: str = "") -> str:
    return look(char)


def do_exits(char: Character, args: str = "") -> str:
    """List obvious exits from the current room (ROM-style)."""
    room = char.room
    if not room or not getattr(room, "exits", None):
        return "Obvious exits: none."
    dirs = [dir_names[type(list(dir_names.keys())[0]) (i)] for i, ex in enumerate(room.exits) if ex]
    if not dirs:
        return "Obvious exits: none."
    return f"Obvious exits: {' '.join(dirs)}."
