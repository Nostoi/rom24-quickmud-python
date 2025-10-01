from __future__ import annotations

from mud import mobprog
from mud.models.character import Character
from mud.models.constants import ActFlag, AffectFlag, Direction, Position, RoomFlag
from mud.models.mob import MobIndex
from mud.models.room import Exit, Room
from mud.spawning.templates import MobInstance
from mud.world.movement import move_character


def _build_rooms() -> tuple[Room, Room]:
    start = Room(vnum=2000, name="Start")
    target = Room(vnum=2001, name="Target")
    start.exits[Direction.NORTH.value] = Exit(to_room=target, keyword="gate")
    return start, target


def test_followers_move_and_trigger_mobprogs(monkeypatch) -> None:
    start, target = _build_rooms()

    leader = Character(name="Leader", is_npc=False, move=20)
    follower = Character(name="Guard", is_npc=True, move=20)
    follower.master = leader
    follower.position = Position.STANDING

    start.add_character(leader)
    start.add_character(follower)

    exit_calls: list[tuple[Character, Direction]] = []
    greet_calls: list[Character] = []

    def fake_exit_trigger(ch: Character, direction: Direction) -> bool:
        exit_calls.append((ch, direction))
        return False

    def fake_greet_trigger(ch: Character) -> None:
        greet_calls.append(ch)

    monkeypatch.setattr(mobprog, "mp_exit_trigger", fake_exit_trigger)
    monkeypatch.setattr(mobprog, "mp_greet_trigger", fake_greet_trigger)

    result = move_character(leader, "north")

    assert "You walk north" in result
    assert leader.room is target
    assert follower.room is target
    assert "You follow Leader." in follower.messages
    follow_idx = follower.messages.index("You follow Leader.")
    auto_idx = next(i for i, message in enumerate(follower.messages) if message.startswith("Target"))
    assert follow_idx < auto_idx
    assert exit_calls == [(leader, Direction.NORTH)]
    assert greet_calls == [leader]


def test_aggressive_follower_blocked_in_law_room() -> None:
    start, target = _build_rooms()
    target.room_flags = int(RoomFlag.ROOM_LAW)

    leader = Character(name="Leader", is_npc=False, move=20)
    follower = Character(
        name="Berserker",
        is_npc=True,
        move=20,
        act=int(ActFlag.AGGRESSIVE),
    )
    follower.master = leader

    start.add_character(leader)
    start.add_character(follower)

    move_character(leader, "north")

    assert follower.room is start
    assert follower.messages[-1] == "You aren't allowed in the city."
    assert leader.messages[-1] == "You can't bring that follower into the city."


def test_player_receives_auto_look_after_move() -> None:
    start, target = _build_rooms()
    target.description = "A quiet chamber with soft light."

    leader = Character(name="Leader", is_npc=False, move=20)
    start.add_character(leader)

    move_character(leader, "north")

    assert leader.room is target
    assert any("A quiet chamber with soft light." in msg for msg in leader.messages)


def test_charmed_follower_stands_before_following() -> None:
    start, target = _build_rooms()

    leader = Character(name="Leader", is_npc=False, move=20)
    follower = Character(name="Pet", is_npc=True, move=20, position=Position.SLEEPING)
    follower.master = leader
    follower.affected_by = int(AffectFlag.CHARM)

    start.add_character(leader)
    start.add_character(follower)

    move_character(leader, "north")

    assert follower.room is target
    assert follower.position == Position.STANDING
    stand_idx = follower.messages.index("You wake and stand up.")
    follow_idx = follower.messages.index("You follow Leader.")
    assert stand_idx < follow_idx


def test_charmed_follower_stays_with_master() -> None:
    start, _ = _build_rooms()

    leader = Character(name="Leader", is_npc=False, move=20)
    start.add_character(leader)

    proto = MobIndex(vnum=4000, short_descr="A charmed pixie", affected_by="R")
    follower = MobInstance.from_prototype(proto)
    follower.master = leader
    follower.is_npc = True
    follower.move = 10
    follower.wait = 0
    follower.messages = []

    start.add_mob(follower)

    outcome = move_character(follower, "north")

    assert outcome == "What?  And leave your beloved master?"
    assert follower.room is start
    assert follower.affected_by & int(AffectFlag.CHARM)
