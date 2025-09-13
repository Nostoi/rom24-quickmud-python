import pytest
from mud.world import initialize_world, create_test_character, move_character, look
from mud.registry import room_registry, area_registry
from mud.loaders import load_all_areas


def test_movement_and_look():
    initialize_world('area/area.lst')
    char = create_test_character('Tester', 3001)
    from tests.helpers import ensure_can_move
    ensure_can_move(char)
    assert char.room.vnum == 3001
    out1 = look(char)
    assert 'Temple' in out1
    msg = move_character(char, 'north')
    assert 'You walk north' in msg
    assert char.room.vnum == room_registry[3054].vnum
    out2 = look(char)
    assert 'temple' in out2.lower() or 'altar' in out2.lower()


def test_overweight_character_cannot_move():
    initialize_world('area/area.lst')
    char = create_test_character('Tester', 3001)
    from tests.helpers import ensure_can_move
    ensure_can_move(char)
    char.carry_weight = 200
    msg = move_character(char, 'north')
    assert msg == 'You are too encumbered to move.'
    assert char.room.vnum == 3001


def test_area_list_requires_sentinel(tmp_path):
    area_registry.clear()
    area_list = tmp_path / "area.lst"
    area_list.write_text("midgaard.are\n", encoding="latin-1")
    with pytest.raises(ValueError):
        load_all_areas(str(area_list))
    area_registry.clear()
