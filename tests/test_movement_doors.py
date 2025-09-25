from mud.models.character import Character
from mud.models.constants import (
    EX_CLOSED,
    EX_NOPASS,
    LEVEL_IMMORTAL,
    AffectFlag,
    Direction,
)
from mud.models.room import Exit, Room
from mud.world import move_character


def _setup_rooms() -> tuple[Character, Room, Room, Exit]:
    start = Room(vnum=1000, name="Start")
    target = Room(vnum=1001, name="Target")
    exit_obj = Exit(to_room=target, keyword="door", exit_info=0)
    start.exits[Direction.NORTH.value] = exit_obj

    char = Character(name="Tester", level=1, ch_class=3, is_npc=False)
    char.move = 10
    start.add_character(char)

    return char, start, target, exit_obj


def test_closed_door_blocks_movement() -> None:
    char, start, _, exit_obj = _setup_rooms()
    exit_obj.exit_info = EX_CLOSED

    result = move_character(char, "north")

    assert result == "The door is closed."
    assert char.room is start
    assert char.wait == 0


def test_pass_door_allows_closed_door() -> None:
    char, _, target, exit_obj = _setup_rooms()
    exit_obj.exit_info = EX_CLOSED
    char.affected_by = int(AffectFlag.PASS_DOOR)

    result = move_character(char, "north")

    assert "You walk north" in result
    assert char.room is target
    assert char.wait == 1


def test_nopass_blocks_pass_door() -> None:
    char, start, _, exit_obj = _setup_rooms()
    exit_obj.exit_info = EX_CLOSED | EX_NOPASS
    char.affected_by = int(AffectFlag.PASS_DOOR)

    result = move_character(char, "north")

    assert result == "The door is closed."
    assert char.room is start


def test_immortal_bypasses_closed_door() -> None:
    char, _, target, exit_obj = _setup_rooms()
    exit_obj.exit_info = EX_CLOSED
    char.level = LEVEL_IMMORTAL

    result = move_character(char, "north")

    assert "You walk north" in result
    assert char.room is target
