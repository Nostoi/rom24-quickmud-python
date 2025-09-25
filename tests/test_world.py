import pytest

from mud.loaders import load_all_areas
from mud.registry import area_registry, room_registry
from mud.world import initialize_world, look, move_character


def test_movement_and_look(movable_char_factory):
    initialize_world("area/area.lst")
    char = movable_char_factory("Tester", 3001)
    assert char.room.vnum == 3001
    out1 = look(char)
    assert "Temple" in out1
    msg = move_character(char, "north")
    assert "You walk north" in msg
    assert char.room.vnum == room_registry[3054].vnum
    out2 = look(char)
    assert "temple" in out2.lower() or "altar" in out2.lower()


def test_overweight_character_cannot_move(movable_char_factory):
    initialize_world("area/area.lst")
    char = movable_char_factory("Tester", 3001)
    char.carry_weight = 200
    msg = move_character(char, "north")
    assert msg == "You are too encumbered to move."
    assert char.room.vnum == 3001


def test_area_list_requires_sentinel(tmp_path):
    area_registry.clear()
    area_list = tmp_path / "area.lst"
    area_list.write_text("midgaard.are\n", encoding="latin-1")
    with pytest.raises(ValueError):
        load_all_areas(str(area_list))
    area_registry.clear()
