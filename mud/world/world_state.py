from __future__ import annotations
from mud.loaders import load_all_areas
from mud.registry import room_registry, area_registry
from mud.models.character import Character
from mud.spawning.reset_handler import apply_resets
from .linking import link_exits


def initialize_world(area_list_path: str = "area/area.lst") -> None:
    load_all_areas(area_list_path)
    link_exits()
    for area in area_registry.values():
        apply_resets(area)


def fix_all_exits() -> None:
    link_exits()


def create_test_character(name: str, room_vnum: int) -> Character:
    room = room_registry.get(room_vnum)
    char = Character(name=name)
    if room:
        room.people.append(char)
        char.room = room
    return char
