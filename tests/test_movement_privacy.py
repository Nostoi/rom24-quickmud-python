from mud.models.character import Character
from mud.models.constants import LEVEL_IMMORTAL, Direction, RoomFlag
from mud.models.room import Exit, Room
from mud.world import move_character


def _setup_rooms(target_vnum: int = 2001) -> tuple[Character, Room, Room]:
    start = Room(vnum=2000, name="Start")
    target = Room(vnum=target_vnum, name="Target")
    exit_obj = Exit(to_room=target, keyword="archway")
    start.exits[Direction.NORTH.value] = exit_obj

    char = Character(name="Tester", level=10, ch_class=0, is_npc=False)
    char.move = 10
    start.add_character(char)

    return char, start, target


def test_private_room_blocks_entry() -> None:
    char, start, target = _setup_rooms()
    target.room_flags = int(RoomFlag.ROOM_PRIVATE)
    target.add_character(Character(name="Guest", is_npc=False))
    target.add_character(Character(name="Guest2", is_npc=False))

    result = move_character(char, "north")

    assert result == "That room is private right now."
    assert char.room is start


def test_solitary_room_blocks_entry() -> None:
    char, start, target = _setup_rooms()
    target.room_flags = int(RoomFlag.ROOM_SOLITARY)
    target.add_character(Character(name="Loner", is_npc=False))

    result = move_character(char, "north")

    assert result == "That room is private right now."
    assert char.room is start


def test_owner_can_enter_private_room() -> None:
    char, _, target = _setup_rooms()
    target.room_flags = int(RoomFlag.ROOM_PRIVATE)
    target.owner = "Tester"
    target.add_character(Character(name="Guest", is_npc=False))
    target.add_character(Character(name="Guest2", is_npc=False))

    result = move_character(char, "north")

    assert "You walk north" in result
    assert char.room is target


def test_trusted_enters_private_room() -> None:
    char, _, target = _setup_rooms()
    target.room_flags = int(RoomFlag.ROOM_PRIVATE)
    target.add_character(Character(name="Guest", is_npc=False))
    target.add_character(Character(name="Guest2", is_npc=False))
    char.level = LEVEL_IMMORTAL

    result = move_character(char, "north")

    assert "You walk north" in result
    assert char.room is target


def test_guild_room_rejects_other_classes() -> None:
    char, start, target = _setup_rooms(target_vnum=3018)
    char.ch_class = 3  # warrior attempting mage guild

    result = move_character(char, "north")

    assert result == "You aren't allowed in there."
    assert char.room is start


def test_guild_room_allows_own_class() -> None:
    char, _, target = _setup_rooms(target_vnum=3018)
    char.ch_class = 0  # mage guild

    result = move_character(char, "north")

    assert "You walk north" in result
    assert char.room is target
