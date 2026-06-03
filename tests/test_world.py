import pytest

from mud.loaders import load_all_areas
from mud.models.character import character_registry
from mud.registry import area_registry, room_registry
from mud.world import initialize_world, look, move_character


def test_movement_and_look(movable_char_factory):
    from mud.models.constants import Direction
    from mud.models.room import Exit

    initialize_world("area/area.lst")
    char = movable_char_factory("Tester", 3001)

    room_from = room_registry[3001]
    room_to = room_registry[3054]
    north_idx = Direction.NORTH.value
    room_from.exits[north_idx] = Exit(to_room=room_to, vnum=3054)

    assert char.room.vnum == 3001
    out1 = look(char)
    assert "Temple" in out1
    msg = move_character(char, "north")
    assert msg and "You walk" not in msg  # ROM act_move.c:204 — mover sees room, no walk-line
    assert char.room.vnum == room_registry[3054].vnum
    out2 = look(char)
    assert "temple" in out2.lower() or "altar" in out2.lower()


def test_overweight_character_can_still_move(movable_char_factory):
    # MOVE-006: ROM src/act_move.c:move_char has no carry-weight movement gate
    # (caps are enforced at pickup time via do_get). An overweight PC moves freely.
    from mud.models.constants import Direction
    from mud.models.room import Exit

    initialize_world("area/area.lst")
    char = movable_char_factory("Tester", 3001)
    room_to = room_registry[3054]
    char.room.exits[Direction.NORTH.value] = Exit(to_room=room_to, vnum=3054)
    char.carry_weight = 200
    move_character(char, "north")
    assert char.room.vnum == 3054


def test_area_list_requires_sentinel(tmp_path):
    area_registry.clear()
    area_list = tmp_path / "area.lst"
    area_list.write_text("midgaard.are\n", encoding="latin-1")
    # Sentinel enforcement is part of the legacy .are loader path; the
    # default JSON loader scans `data/areas/*.json` and ignores `area.lst`.
    with pytest.raises(ValueError):
        load_all_areas(str(area_list), use_json=False)
    area_registry.clear()


def test_initialize_world_resets_character_registry_between_calls():
    initialize_world("area/area.lst")
    first_count = len(room_registry[3001].people)
    first_registry_count = len(character_registry)

    initialize_world("area/area.lst")
    second_count = len(room_registry[3001].people)
    second_registry_count = len(character_registry)

    assert second_count == first_count
    assert second_registry_count == first_registry_count
