from mud.registry import room_registry
from mud.world.world_state import initialize_world


def test_load_midgaard():
    # Use JSON loader system (default in world_state)
    initialize_world(use_json=True)
    # midgaard area includes room 3001
    assert 3001 in room_registry
    room = room_registry[3001]
    assert room.name is not None
    # Verify ROM defaults are applied
    assert room.heal_rate == 100
    assert room.mana_rate == 100
    # Verify ROOM_LAW flag is set for Midgaard
    from mud.models.constants import RoomFlag

    assert room.room_flags & RoomFlag.ROOM_LAW != 0
