from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import Direction
from mud.world.look import dir_names, look
from mud.world.vision import can_see_character, describe_character


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

    def _get_exit(room, direction: Direction):  # type: ignore[valid-type]
        if not room:
            return None
        exits = getattr(room, "exits", None)
        if not exits:
            return None
        idx = int(direction)
        if isinstance(exits, dict):
            return exits.get(idx) or exits.get(direction)
        if 0 <= idx < len(exits):
            return exits[idx]
        return None

    def list_room(room, depth: int, door: int) -> list[str]:
        lines: list[str] = []
        if not room:
            return lines
        for p in room.people:
            if p is char:
                continue
            if not can_see_character(char, p):
                continue
            who = describe_character(char, p)
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
            ex = _get_exit(char.room, d)
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
        ex = _get_exit(scan_room, d)
        scan_room = ex.to_room if ex else None
        if not scan_room:
            break
        lines += list_room(scan_room, depth, int(d))
    if len(lines) == 1:
        lines.append("Nothing of note.")
    return "\n".join(lines)


def do_look(char: Character, args: str = "") -> str:
    """
    Look at room, character, object, or direction.
    
    ROM Reference: src/act_info.c do_look
    
    Usage:
    - look (show room)
    - look <character> (examine character)
    - look <object> (examine object)
    - look in <container> (show container contents)
    - look <direction> (peek through exit)
    """
    return look(char, args)


def do_exits(char: Character, args: str = "") -> str:
    """List obvious exits from the current room (ROM-style)."""
    room = char.room
    if not room or not getattr(room, "exits", None):
        return "Obvious exits: none."
    dirs = [dir_names[type(list(dir_names.keys())[0])(i)] for i, ex in enumerate(room.exits) if ex]
    if not dirs:
        return "Obvious exits: none."
    return f"Obvious exits: {' '.join(dirs)}."
