from mud.world import initialize_world, create_test_character, move_character, look
from mud.registry import room_registry


def test_movement_and_look():
    initialize_world('area/area.lst')
    char = create_test_character('Tester', 3001)
    assert char.room.vnum == 3001
    out1 = look(char)
    assert 'Temple' in out1
    msg = move_character(char, 'north')
    assert 'You walk north' in msg
    assert char.room.vnum == room_registry[3054].vnum
    out2 = look(char)
    assert 'temple' in out2.lower() or 'altar' in out2.lower()
