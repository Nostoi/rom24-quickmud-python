from mud.agent.character_agent import CharacterAgentAdapter
from mud.world import initialize_world


def test_character_agent_actions(movable_char_factory):
    from mud.models.room import Exit
    from mud.models.constants import Direction
    from mud.registry import room_registry

    initialize_world("area/area.lst")
    char = movable_char_factory("Tester", 3001)

    room_from = room_registry[3001]
    room_to = room_registry[3054]
    north_idx = Direction.NORTH.value
    room_from.exits[north_idx] = Exit(to_room=room_to, vnum=3054)

    adapter = CharacterAgentAdapter(char)
    obs = adapter.get_observation()
    assert obs["name"] == "Tester"
    assert obs["room"]["vnum"] == 3001

    say_result = adapter.perform_action("say", ["hello"])
    assert "You say" in say_result

    move_result = adapter.perform_action("move", ["north"])
    assert "north" in move_result
    assert char.room.vnum != 3001


def test_mob_agent_movement(movable_mob_factory):
    from mud.models.room import Exit
    from mud.models.constants import Direction
    from mud.registry import room_registry

    initialize_world("area/area.lst")
    mob = movable_mob_factory(3000, 3001)

    room_from = room_registry[3001]
    room_to = room_registry[3054]
    north_idx = Direction.NORTH.value
    room_from.exits[north_idx] = Exit(to_room=room_to, vnum=3054)

    adapter = CharacterAgentAdapter(mob)
    move_result = adapter.perform_action("move", ["north"])
    assert mob.room.vnum != 3001
    assert "north" in move_result
