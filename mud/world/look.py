from __future__ import annotations
from mud.models.character import Character
from mud.models.constants import Direction


dir_names = {
    Direction.NORTH: "north",
    Direction.EAST: "east",
    Direction.SOUTH: "south",
    Direction.WEST: "west",
    Direction.UP: "up",
    Direction.DOWN: "down",
}


def look(char: Character) -> str:
    room = char.room
    if not room:
        return "You are floating in a void..."
    exit_list = [dir_names[Direction(i)] for i, ex in enumerate(room.exits) if ex]
    lines = [room.name or "", room.description or ""]
    if exit_list:
        lines.append(f"[Exits: {' '.join(exit_list)}]")
    if room.contents:
        lines.append("Objects: " + ", ".join(obj.short_descr or obj.name or "object" for obj in room.contents))
    others = [p.name or "someone" for p in room.people if p is not char]
    if others:
        lines.append("Characters: " + ", ".join(others))
    return "\n".join(lines).strip()
