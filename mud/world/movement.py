from __future__ import annotations
from typing import Dict

from mud.models.character import Character
from mud.models.constants import Direction
from mud.net.protocol import broadcast_room


dir_map: Dict[str, Direction] = {
    "north": Direction.NORTH,
    "east": Direction.EAST,
    "south": Direction.SOUTH,
    "west": Direction.WEST,
    "up": Direction.UP,
    "down": Direction.DOWN,
}


def move_character(char: Character, direction: str) -> str:
    dir_key = direction.lower()
    if dir_key not in dir_map:
        return "You cannot go that way."

    idx = dir_map[dir_key]
    exit = char.room.exits[idx]
    if exit is None or exit.to_room is None:
        return "You cannot go that way."

    current_room = char.room
    target_room = exit.to_room

    broadcast_room(current_room, f"{char.name} leaves {dir_key}.", exclude=char)
    if char in current_room.people:
        current_room.people.remove(char)
    target_room.people.append(char)
    char.room = target_room
    broadcast_room(target_room, f"{char.name} arrives.", exclude=char)
    return f"You walk {dir_key} to {target_room.name}."
