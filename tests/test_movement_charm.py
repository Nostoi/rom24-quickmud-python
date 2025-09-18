from mud.models.character import Character
from mud.models.constants import AffectFlag, Direction
from mud.models.room import Exit, Room
from mud.world import move_character


def test_charmed_character_cannot_leave_master_room() -> None:
    start = Room(vnum=1000, name="Start")
    target = Room(vnum=1001, name="Target")
    exit_obj = Exit(to_room=target, keyword="door", exit_info=0)
    start.exits[Direction.NORTH.value] = exit_obj

    master = Character(name="Master", is_npc=False)
    follower = Character(name="Follower")
    follower.move = 10
    follower.affected_by = int(AffectFlag.CHARM)
    follower.master = master

    start.add_character(master)
    start.add_character(follower)

    result = move_character(follower, "north")

    assert result == "What?  And leave your beloved master?"
    assert follower.room is start
    assert master.room is start
    assert follower.wait == 0
