from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import Direction
from mud.world.vision import can_see_character, describe_character

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
        lines.append(
            "Objects: "
            + ", ".join(obj.short_descr or obj.name or "object" for obj in room.contents)
        )
    visible_characters: list[str] = []
    for occupant in room.people:
        if occupant is char:
            continue
        if not can_see_character(char, occupant):
            continue
        visible_characters.append(describe_character(char, occupant))
    if visible_characters:
        lines.append("Characters: " + ", ".join(visible_characters))
    return "\n".join(lines).strip()
