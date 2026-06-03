from mud.commands.group_commands import do_follow
from mud.models.character import Character
from mud.models.room import Room


def test_follow_self_clears_master_pet_pointer() -> None:
    """The command-path stop_follower must clear master.pet like ROM."""

    room = Room(vnum=3700)
    master = Character(name="Master", is_npc=False)
    follower = Character(name="Follower", is_npc=False)
    room.add_character(master)
    room.add_character(follower)
    follower.master = master
    master.pet = follower

    # ROM src/act_comm.c:1568-1570 delegates follow-self to stop_follower,
    # whose src/act_comm.c:1631-1632 branch clears ch->master->pet == ch.
    result = do_follow(follower, "self")

    assert result == ""
    assert follower.master is None
    assert follower.leader is None
    assert master.pet is None
