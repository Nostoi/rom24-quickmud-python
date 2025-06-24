from mud.loaders import load_all_areas
from mud.registry import room_registry


def test_load_midgaard():
    load_all_areas('area/area.lst')
    # midgaard area includes room 3001
    assert 3001 in room_registry
    room = room_registry[3001]
    assert room.name is not None
