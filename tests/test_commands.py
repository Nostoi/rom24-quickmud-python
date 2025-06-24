from mud.world import initialize_world, create_test_character
from mud.spawning.obj_spawner import spawn_object
from mud.commands import process_command
from mud.registry import room_registry


def test_process_command_sequence():
    initialize_world('area/area.lst')
    char = create_test_character('Tester', 3001)
    sword = spawn_object(3022)
    assert sword is not None
    char.room.add_object(sword)

    out1 = process_command(char, 'look')
    assert 'Temple' in out1

    out2 = process_command(char, 'get sword')
    assert 'pick up' in out2
    assert sword in char.inventory
    assert sword not in char.room.contents

    out3 = process_command(char, 'north')
    assert 'You walk north' in out3
    north_room = room_registry[3054]
    assert char.room is north_room

    other = create_test_character('Other', north_room.vnum)
    out4 = process_command(char, 'say hello')
    assert out4 == "You say, 'hello'"
    assert f"{char.name} says, 'hello'" in other.messages
