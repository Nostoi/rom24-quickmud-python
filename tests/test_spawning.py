from mud.world import initialize_world
from mud.registry import room_registry


def test_resets_populate_world():
    initialize_world('area/area.lst')
    room = room_registry[3001]
    assert any(getattr(m, 'name', None) for m in room.people)
