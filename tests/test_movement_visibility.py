from mud.models.character import Character
from mud.models.constants import (
    LEVEL_HERO,
    LEVEL_IMMORTAL,
    AffectFlag,
    Direction,
    Position,
    RoomFlag,
    Sector,
)
from mud.models.room import Exit, Room
from mud.world.movement import move_character


def _build_rooms() -> tuple[Room, Room]:
    start = Room(vnum=3000, name="Start")
    target = Room(vnum=3001, name="Target")
    start.exits[Direction.NORTH.value] = Exit(to_room=target, keyword="gate")
    return start, target


def test_blind_player_blocked_by_dark_exit() -> None:
    start, target = _build_rooms()
    target.room_flags = int(RoomFlag.ROOM_DARK)

    player = Character(name="Blind", is_npc=False, move=20)
    player.affected_by = int(AffectFlag.BLIND)
    start.add_character(player)

    result = move_character(player, "north")

    assert result == "Alas, you cannot go that way."
    assert player.room is start


def test_follower_requires_visibility() -> None:
    start, target = _build_rooms()
    target.room_flags = int(RoomFlag.ROOM_DARK)

    leader = Character(name="Leader", is_npc=False, move=20)
    leader.affected_by = int(AffectFlag.INFRARED)

    follower = Character(
        name="Pet",
        is_npc=True,
        move=20,
        position=Position.SLEEPING,
    )
    follower.affected_by = int(AffectFlag.CHARM)
    follower.master = leader

    start.add_character(leader)
    start.add_character(follower)

    move_character(leader, "north")

    assert leader.room is target
    assert follower.room is start
    assert follower.position == Position.STANDING
    assert "You wake and stand up." in follower.messages
    assert all("You follow" not in message for message in follower.messages)


def test_sneaking_player_moves_silently() -> None:
    start, target = _build_rooms()

    observer_start = Character(name="Watcher", is_npc=True)
    observer_target = Character(name="Sentinel", is_npc=True)

    start.add_character(observer_start)
    target.add_character(observer_target)

    sneaker = Character(name="Sneak", is_npc=False, move=20)
    sneaker.affected_by = int(AffectFlag.SNEAK)
    start.add_character(sneaker)

    result = move_character(sneaker, "north")

    assert "You walk north" in result
    assert sneaker.room is target
    assert observer_start.messages == []
    assert observer_target.messages == []


def test_high_invis_player_arrives_quietly() -> None:
    start, target = _build_rooms()

    observer_start = Character(name="Watcher", is_npc=True)
    observer_target = Character(name="Sentinel", is_npc=True)

    start.add_character(observer_start)
    target.add_character(observer_target)

    wizard = Character(name="Wizard", is_npc=False, move=20, level=LEVEL_HERO)
    wizard.invis_level = LEVEL_HERO
    start.add_character(wizard)

    result = move_character(wizard, "north")

    assert "You walk north" in result
    assert wizard.room is target
    assert observer_start.messages == []
    assert observer_target.messages == []


def test_immortal_can_cross_air_without_flight() -> None:
    start, target = _build_rooms()
    target.sector_type = int(Sector.AIR)

    immortal = Character(name="Sky", is_npc=False, move=20, level=LEVEL_IMMORTAL)
    start.add_character(immortal)

    result = move_character(immortal, "north")

    assert "You walk north" in result
    assert immortal.room is target


def test_immortal_can_enter_noswim_without_boat() -> None:
    start, target = _build_rooms()
    target.sector_type = int(Sector.WATER_NOSWIM)

    immortal = Character(name="Captain", is_npc=False, move=20, level=LEVEL_IMMORTAL)
    start.add_character(immortal)

    result = move_character(immortal, "north")

    assert "You walk north" in result
    assert immortal.room is target
