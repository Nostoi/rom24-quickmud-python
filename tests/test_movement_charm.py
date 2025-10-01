from mud.models.character import Character
from mud.models.constants import AffectFlag, Direction
from mud.models.room import Exit, Room
from mud.world.movement import move_character


def _build_rooms() -> tuple[Room, Room]:
    start = Room(vnum=1000, name="Start")
    target = Room(vnum=1001, name="Target")
    exit_obj = Exit(to_room=target, keyword="door")
    start.exits[Direction.NORTH.value] = exit_obj
    return start, target


def test_charmed_character_cannot_leave_master_room() -> None:
    start, target = _build_rooms()

    master = Character(name="Master", is_npc=False, move=10)
    follower = Character(name="Follower", is_npc=True, move=10)

    start.add_character(master)
    start.add_character(follower)

    follower.master = master
    follower.affected_by = int(AffectFlag.CHARM)

    result = move_character(follower, "north")

    assert result == "What?  And leave your beloved master?"
    assert follower.room is start
    assert follower in start.people

    master.move = 10
    follower.move = 10

    move_character(master, "north")
    assert master.room is target
    assert follower.room is target

    result = move_character(follower, "north")

    assert result == "You cannot go that way."
    assert follower.room is target
