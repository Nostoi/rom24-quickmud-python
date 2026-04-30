from mud.registry import room_registry
from mud.world import initialize_world


def test_midgaard_room_3001_exits_and_keys():
    initialize_world("area/area.lst")
    room = room_registry[3001]
    # D0 → no exit (NORTH exit is NOT in the .are file;
    # old JSON had a stale ghost north exit to 3054).
    assert room.exits[0] is None
    # D2 → 3005, key -1 (south to Temple Square)
    ex2 = room.exits[2]
    assert ex2 is not None
    assert ex2.vnum == 3005
    assert ex2.key == -1
    # D4 → 3700, key 0 (up to Mud School)
    ex4 = room.exits[4]
    assert ex4 is not None
    assert ex4.vnum == 3700
    assert ex4.key == 0
