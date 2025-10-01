from mud.commands.dispatcher import process_command
from mud.models.character import Character, character_registry
from mud.models.constants import Direction, Position
from mud.models.room import Exit, Room
from mud.world import create_test_character, initialize_world
from mud.world.movement import move_character


def _build_rooms() -> tuple[Room, Room]:
    start = Room(vnum=2000, name="Start")
    target = Room(vnum=2001, name="Target")
    start.exits[Direction.NORTH.value] = Exit(to_room=target, keyword="gate")
    return start, target


def test_follower_cascade():
    start, target = _build_rooms()

    leader = Character(name="Leader", is_npc=False, move=20)
    follower = Character(name="Guard", is_npc=True, move=20)
    follower.master = leader
    follower.position = Position.STANDING

    start.add_character(leader)
    start.add_character(follower)

    result = move_character(leader, "north")

    assert "You walk north" in result
    assert leader.room is target
    assert follower.room is target
    assert any(msg.startswith("You follow") for msg in follower.messages)


def test_followers_enter_portal(portal_factory):
    try:
        initialize_world("area/area.lst")
        leader = create_test_character("Leader", 3001)
        follower = create_test_character("Scout", 3001)
        follower.master = leader
        follower.position = Position.STANDING

        portal_factory(3001, to_vnum=3054, closed=False, charges=2)

        out = process_command(leader, "enter portal")

        assert out == "You walk through a shimmering portal and find yourself somewhere else..."
        assert follower.room is not None and follower.room.vnum == 3054
        assert any("follow" in msg.lower() for msg in follower.messages)
    finally:
        character_registry.clear()
